"""Recover only the selected batch60 inputs on the existing authorized Actions runner."""
import json,gzip,copy,hashlib,re,subprocess,html,sys
from pathlib import Path
S=Path('picons/radio-world/staging');stage=S/'batch-62-reviewed';prev=S/'batch-61-reviewed'
sys.path.insert(0,'picons/radio-world/tools')
from visual_gate import read,merge_ledgers,validate_selection
from saved_artwork_import import get
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,x):
 b=(json.dumps(x,indent=2,ensure_ascii=False)+'\n').encode();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(gzip.compress(b,mtime=0)if p.suffix=='.gz'else b)
cfg=read(prev/'configuration.json');raw=(prev/'countries.proposed.json').read_bytes()
assert sha(raw)=='2d168d430bfcdcc3c09555a7796fd7e3cd35c8da028c285ac5aee140428c2e2f'
desc=read(stage/'source-inputs/recovery-spec.json')
world=json.loads(gzip.decompress(get(cfg['world'])));current=json.loads(gzip.decompress(get(desc['current'])));audit=json.loads(gzip.decompress(get(desc['audit'])))['checks']
countries={c['id']:c['name']for c in json.loads(raw)['countries']}
paths=[S/'source-ledger-reviewed-20261107/visual-ledger.json.gz',S/'visual-review-34-36/decisions.json.gz']+[S/f'batch-{n}-reviewed/visual-ledger.json.gz'for n in range(39,62)]
ledger=merge_ledgers(paths);approved=[e['row']for e in ledger['entries']if e['decision']=='approve'];known={(e['row']['country'],e['row']['ref'])for e in ledger['entries']}
rows=[];facts=[];pairs=[];keys=['url','checked_at','http_status','content_type','icy_name','sample_bytes','sample_sha256','status']
for code,name,url,oldname,oldurl in desc['pairs']:
 matches=[r for r in approved if r.get('station',{}).get('name')==oldname and r['station'].get('url')==oldurl]
 assert matches,(name,'missing approved original')
 assert len({tuple(sorted((k,v[0])for k,v in r['variants'].items()))for r in matches})==1,(name,'ambiguous artwork')
 old=matches[0];assert validate_selection([old],ledger)==1
 candidates=[r for r in world if r['name']==name and r['url']==url and r['group']==countries[code]];assert len(candidates)==1,(name,'ambiguous catalogue tuple');st=candidates[0]
 assert any(w['reference']==st['reference']and all(w[k]==st[k]for k in ['name','url','group'])for w in current),(name,'current identity changed')
 assert (code,st['reference'])not in known and st['reference']not in cfg['held_references']
 a=audit[url];b=audit[oldurl];r=copy.deepcopy(old);r.update(ref=st['reference'],country=code,station={k:st[k]for k in ['name','url','group']},index=620000+len(rows));r['asset_root']=r['asset_root'].removesuffix('/verified-assets')
 r['provenance']=copy.deepcopy(old.get('provenance',{}));r['provenance'].update(alias_of_approved_ref=old['ref'],alias_of_approved_country=old['country'],stream_audit_main_commit='481e9b9154a510c64c743de72c1a73ed808307bf',identity_basis='Explicit publisher player or DNS mapping plus exact audited endpoint identity; no artwork changes')
 r['final_visual_approval']=dict(decision='approve',reason='Byte-identical reuse of all nine historical approved variants; no new graphic or render',reviewed_variants=r['variants'])
 f=dict(station=st,approved=old,new_audit={k:a.get(k)for k in keys},approved_audit={k:b.get(k)for k in keys})
 f['identity_evidence']=desc['evidence'][name]
 rows.append(r);facts.append(f);pairs.append([name,url,oldname,oldurl,a['icy_name']])
assert len(rows)==2 and len({r['ref']for r in rows})==2
write(stage/'selection.json.gz',dict(entries=rows));write(stage/'visual-ledger.json.gz',dict(entries=[dict(row=r,decision='approve',reason=r['final_visual_approval']['reason'],reviewed_variants=r['variants'])for r in rows],source_holds=[],pending_sources=[]))
write(stage/'source-inputs/public-observations.json',dict(schema=1,stream_audit=desc['audit'],current_world=desc['current'],entries=facts,no_new_endpoint_requests=True,no_new_artwork=True))
(stage/'baseline.previous.json').write_bytes(raw);cfg.update(batch='62-reviewed',references=2,parent_candidate='29743441d41c9d6a71850fe38cba36be8fc1d407',expected_coverage=3355,selection_sha256=sha((stage/'selection.json.gz').read_bytes()),baseline_index=dict(url='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/29743441d41c9d6a71850fe38cba36be8fc1d407/picons/radio-world/staging/batch-61-reviewed/countries.proposed.json',bytes=len(raw),sha256=sha(raw)))
write(stage/'configuration.json',cfg)

write(stage/'results/next-source-observations.json.gz',dict(schema=1,next_batch=63,previous_frontier='../batch-61-reviewed/results/next-source-observations.json.gz',configuration_holds_unchanged=923,completed_selection_refs=[r['ref']for r in rows],next='Continue independent publisher-mapped aliases; exclude generic ICY, conflicts and all existing holds.'))
print('Prepared2 references /18 byte-identical approved PNG variants')
