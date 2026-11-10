#!/usr/bin/env python3
"""Prepare/verify batch44 from actual pinned exports; never render, build ZIPs or publish."""
import argparse,copy,gzip,hashlib,json,re,sys
from pathlib import Path,PurePosixPath
HERE=Path(__file__).resolve().parent;RADIO=HERE.parents[2];STAGING=RADIO/'staging';TOOLS=RADIO/'tools'
sys.path.insert(0,str(TOOLS))
from visual_gate import read,merge_ledgers,validate_selection,fingerprint,identity_blocks
from technical_resolution import authority,recovery,authorize,require,sha,RECEIPT_SHA,SNAPSHOT_SHA,VARIANTS
from baseline_admission import inspect as baseline_inspect
PARENT='2db89afad0f414fe7c4b1a6a1a836382d47090d3'
BASELINE_SHA='b2018e346e88cef556b27290ff241d850cb01135855fc643dfe1d92965185d0e'
CONFIG_SHA='e781684463a3a4cb20f2738ab5d1ad46e8200a9d6e2508bb0f183f29f333c0cb'
HISTORY=['source-ledger-reviewed-20261107/visual-ledger.json.gz','visual-review-34-36/decisions.json.gz',*[f'batch-{n}-reviewed/visual-ledger.json.gz'for n in(39,40,41,42,43)]]
def packed(x):return gzip.compress((json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n').encode(),mtime=0)
def source_pair(value):
    pair=value.split(':');require(len(pair)==2 and all(pair),'Use SELECTION:LEDGER paths without colons');return tuple(map(Path,pair))
def validate_rows(rows):
    require(bool(rows) and len(rows)==len({r['ref']for r in rows}),'Empty or duplicate selection; never rebuild old ZIPs for zero new references')
    for r in rows:
        require(isinstance(r.get('source_commit'),str)and re.fullmatch('[0-9a-f]{40}',r['source_commit']),'Actual full source pixel commit missing')
        root=r.get('asset_root','');path=PurePosixPath(root)
        require(bool(root)and bool(path.parts)and not path.is_absolute()and'..'not in path.parts and'\\'not in root and'pending'not in root.lower()and path.parts[-1]!='verified-assets','Unsafe/unpinned parent asset root')
        require(set(r['variants'])==VARIANTS,'Actual all-nine variant inventory required')
        require(all(isinstance(r['station'].get(k),str)and r['station'][k]for k in('name','url','group')),'Station identity missing')
        for v in r['variants'].values():require(isinstance(v,list)and len(v)==3 and re.fullmatch('[0-9a-f]{64}',v[0])and type(v[1])is int and v[1]>0 and re.fullmatch('[0-9a-f]{40}',v[2]),'Actual SHA256/bytes/Gitblob tuple missing')

def evaluate(rows,new_ledger,history,receipt,snapshot,final_snapshot,recovery_path,recovery_sha,baseline_raw,config_raw):
    validate_rows(rows)
    require(sha(baseline_raw)==BASELINE_SHA and sha(config_raw)==CONFIG_SHA,'Pinned3010 baseline/config changed')
    countries=json.loads(baseline_raw)['countries'];country_ids={r['id']for r in countries}
    require(len(countries)==len(country_ids)==219 and sum(r['picons']for r in countries)==3010 and sum(bool(r['release'])for r in countries)==125 and sum(r['status']=='complete'for r in countries)==12,'Wrong baseline state')
    require({r['country']for r in rows}<=country_ids,'Unknown source country')
    validate_selection(rows,new_ledger)
    approved=authority(receipt,snapshot,final_snapshot)
    technical_selected=any((r['country'],r['ref'])in identity_blocks(merge_ledgers(history))for r in rows)
    physical=recovery(recovery_path,recovery_sha,approved)if technical_selected else None
    combined=merge_ledgers(history);combined['entries']+=new_ledger['entries'];combined['source_holds']+=new_ledger.get('source_holds',[])
    blocked={}
    for h in combined.get('source_holds',[]):blocked.setdefault((h['country'],h['ref']),[]).append(h)
    resolved=[]
    for r in rows:
        identity=(r['country'],r['ref']);holds=blocked.get(identity,[])
        if not holds:continue
        reviews=[e for e in new_ledger['entries']if e['decision']=='approve'and fingerprint(e['row'])==fingerprint(r)]
        require(bool(reviews)and all(set(e.get('reviewed_variants',[]))==VARIANTS for e in reviews),'Fresh actual all-nine visual QA required for recovered output')
        require(all((h['country'],h['ref'])==identity for h in combined['source_holds']if h['ref']==r['ref']),'A different blocked country identity shares this service reference')
        proof=authorize(r,reviews[-1],holds,approved,physical);proof['variants']=copy.deepcopy(r['variants']);resolved.append(proof)
    validate_selection(rows,combined)
    resolved_refs={r['ref']for r in resolved};cfg=copy.deepcopy(json.loads(config_raw))
    cfg.update(batch='44-reviewed',references=len(rows),parent_candidate=PARENT,expected_coverage=3010+len(rows),selection_filename='selection.json.gz',visual_ledger_filename='visual-ledger.json.gz')
    for k in('source_ledger_commit','reuse_index'):cfg.pop(k,None)
    cfg['baseline_index']=dict(url='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'+PARENT+'/picons/radio-world/catalog/countries.json',bytes=len(baseline_raw),sha256=BASELINE_SHA)
    cfg['held_references']=sorted((set(cfg['held_references'])|{ref for country,ref in identity_blocks(combined)})-resolved_refs)
    require(not set(cfg['held_references'])&{r['ref']for r in rows},'Unresolved identity/source hold remains selected')
    selection=packed(dict(entries=rows));cfg['selection_sha256']=sha(selection)
    resolution=dict(schema=1,status='verified-technical-resolution-only-with-fresh-exact-artwork-approvals',old_manual_receipt_sha256=RECEIPT_SHA,new_recovery_proof_sha256=(physical['sha256']if physical else None),snapshot_sha256=SNAPSHOT_SHA,actual_authorized_receipt_references=len(approved),resolved_references=len(resolved),entries=resolved,historical_source_holds_not_removed=True,genuine_source_or_HDF_holds_not_clearable=True)
    return cfg,selection,resolution

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=('prepare','verify'),nargs='?',default='prepare')
    p.add_argument('--source',action='append',type=source_pair,default=[]);p.add_argument('--expected-source-count',action='append',type=int)
    p.add_argument('--expected-total',type=int);p.add_argument('--receipt',type=Path,default=HERE/'evidence/recovered-new96-review-receipts.json');p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--final-snapshot',type=Path,required=True);p.add_argument('--recovery-proof',type=Path);p.add_argument('--expected-recovery-proof-sha256')
    p.add_argument('--manifest-cache',type=Path);p.add_argument('--stage',type=Path,default=STAGING/'batch-44-reviewed');p.add_argument('--baseline',type=Path,default=RADIO/'catalog/countries.json');p.add_argument('--history-root',type=Path,default=STAGING)
    a=p.parse_args(argv);history=[a.history_root/name for name in HISTORY];require(all(f.is_file()for f in history),'Partial historical ledger inventory')
    baseline_raw=a.baseline.read_bytes();config_raw=(a.history_root/'batch-43-reviewed/configuration.json').read_bytes()
    if a.mode=='prepare':
        require(bool(a.source),'Actual source exports are not ready: no preparation emitted')
        if a.expected_source_count is not None:require(len(a.source)==len(a.expected_source_count),'Exact counts must match source order')
        rows=[];inputs=[]
        for i,(selection,ledger)in enumerate(a.source):
            entries=read(selection)['entries'];validate_rows(entries);validate_selection(entries,read(ledger))
            if a.expected_source_count is not None:require(len(entries)==a.expected_source_count[i],'Actual producer count differs')
            rows+=entries;inputs.append(dict(selection=str(selection),ledger=str(ledger),actual_references=len(entries),selection_sha256=sha(selection.read_bytes()),ledger_sha256=sha(ledger.read_bytes())))
        if a.expected_total is not None:require(len(rows)==a.expected_total,'Actual total differs')
        new=merge_ledgers([pair[1]for pair in a.source])
        rows,disjoint=baseline_inspect(rows,baseline_raw,a.manifest_cache or a.stage/'manifest-cache')
        conflicting={(h['country'],h['ref'])for h in disjoint['held']}
        for e in new['entries']:
            if(e['row']['country'],e['row']['ref'])in conflicting and e['decision']=='approve':
                e['source_visual_decision']='approve';e['decision']='hold';e['hold_kind']='existing-approved-artwork-protected';e['reason']='New country admission held: existing approved filename must remain unchanged; '+e.get('reason','')
        require(bool(rows),'No new references remain: existing ZIPs must not be rebuilt')
        cfg,selection,resolution=evaluate(rows,new,history,a.receipt,a.snapshot,a.final_snapshot,a.recovery_proof,a.expected_recovery_proof_sha256,baseline_raw,config_raw)
        proof=dict(schema=1,status='prepared-not-country-built',parent=PARENT,baseline_references=3010,baseline_available=125,baseline_complete=12,actual_source_inputs=inputs,references=len(rows),png_instances=9*len(rows),expected_coverage=3010+len(rows),technical_resolved=resolution['resolved_references'],old_manual_receipt_sha256=RECEIPT_SHA,new_recovery_proof_sha256=a.expected_recovery_proof_sha256,snapshot_sha256=SNAPSHOT_SHA,production_protected_variant_entries=10332,all_prior_candidate_variant_entries=27666,historical_ledgers=[dict(path=str(f),sha256=sha(f.read_bytes()))for f in history],no_png_or_zip_generation=True)
        writes={'selection.json.gz':selection,'visual-ledger.json.gz':packed(new),'configuration.json':(json.dumps(cfg,indent=2)+'\n').encode(),'resolution-proof.json':(json.dumps(resolution,indent=2)+'\n').encode(),'preparation-proof.json':(json.dumps(proof,indent=2)+'\n').encode(),'baseline.previous.json':baseline_raw,'baseline-disjoint-proof.json':(json.dumps(disjoint,indent=2)+'\n').encode()}
        if a.recovery_proof:writes['recovery-proof.json']=a.recovery_proof.read_bytes()
        for name,raw in writes.items():require(not(a.stage/name).exists()or(a.stage/name).read_bytes()==raw,'Unequal existing preparation: '+name)
        a.stage.mkdir(parents=True,exist_ok=True)
        for name,raw in writes.items():
            if not(a.stage/name).exists():(a.stage/name).write_bytes(raw)
        print(json.dumps(proof,indent=2))
    else:
        rows=read(a.stage/'selection.json.gz')['entries'];fresh,disjoint=baseline_inspect(rows,baseline_raw,a.manifest_cache or a.stage/'manifest-cache')
        require(len(fresh)==len(rows)and not disjoint['reused']and not disjoint['held'],'Prepared selection is not disjoint from protected baseline filenames')
        new=read(a.stage/'visual-ledger.json.gz');cfg,selection,resolution=evaluate(rows,new,history,a.receipt,a.snapshot,a.final_snapshot,a.recovery_proof,a.expected_recovery_proof_sha256,baseline_raw,config_raw)
        require(selection==(a.stage/'selection.json.gz').read_bytes()and cfg==read(a.stage/'configuration.json')and resolution==read(a.stage/'resolution-proof.json'),'Prepared stage or resolution proof changed')
        require((a.stage/'baseline.previous.json').read_bytes()==baseline_raw,'Baseline preservation bytes changed')
        print(json.dumps(dict(status='pass',actual_references=len(rows),technical_resolved=resolution['resolved_references'],receipt_sha256=RECEIPT_SHA,all_new_png_fingerprints_exactly_approved=True)))
if __name__=='__main__':main()
