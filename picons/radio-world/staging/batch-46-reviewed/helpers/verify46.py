"""Data-only batch46 verification with existing gates, no source-hold exceptions."""
import hashlib,json,os,re,sys,urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent;RADIO=Path(os.environ.get('WARDER_RADIO_ROOT',HERE.parents[2]));STAGE=HERE.parent
sys.path.insert(0,str(RADIO/'tools'))
from visual_gate import read,merge_ledgers,validate_selection,identity_blocks,fingerprint
from baseline_admission import inspect,fetch_release
BASE='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'
PARENT='9d5a3c4de8e5300dbcc485230ad11df588d7bdc8'
BASELINE_SHA='b921b0942816557ff7eed43348a0b17ebfcd5bcdedf580f3e50d4c34d05040c7'
HISTORY=['source-ledger-reviewed-20261107/visual-ledger.json.gz','visual-review-34-36/decisions.json.gz',*[f'batch-{n}-reviewed/visual-ledger.json.gz'for n in(39,40,41,42,43,44,45)]]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
    proof=read(STAGE/'preparation-proof.json');cfg=read(STAGE/'configuration.json');baseline_raw=(STAGE/'baseline.previous.json').read_bytes();selection_raw=(STAGE/'selection.json.gz').read_bytes();ledger_raw=(STAGE/'visual-ledger.json.gz').read_bytes()
    assert sha((STAGE/'configuration.json').read_bytes())==proof['configuration_sha256']
    assert sha(baseline_raw)==BASELINE_SHA and sha(selection_raw)==proof['selection_sha256']==cfg['selection_sha256'] and sha(ledger_raw)==proof['visual_ledger_sha256']
    assert cfg['parent_candidate']==PARENT and cfg['baseline_index']==dict(url=BASE+PARENT+'/picons/radio-world/staging/batch-45-reviewed/countries.proposed.json',bytes=len(baseline_raw),sha256=BASELINE_SHA)
    public_rows=[]
    for source in proof['sources']:
        for resource in source['files']:
            assert re.fullmatch('[0-9a-f]{40}',resource['commit']) and resource['path'].startswith('picons/radio-world/staging/')
            raw=(STAGE/resource['file']).read_bytes();assert len(raw)==resource['bytes']and sha(raw)==resource['sha256']
            remote=urllib.request.urlopen(BASE+resource['commit']+'/'+resource['path'],timeout=90).read(resource['bytes']+1)
            assert remote==raw,'Prepared source file differs from immutable producer export'
        export=read(STAGE/source['selection_file']);metadata=read(STAGE/source['metadata_file'])
        assert metadata['status']=='pass'and metadata['selection_sha256']==sha((STAGE/source['selection_file']).read_bytes())
        assert len(export['entries'])==source['references']
        if 'source_commit'in metadata:assert all(r['source_commit']==metadata['source_commit']for r in export['entries'])
        public_rows+=export['entries']
    rows=read(STAGE/'selection.json.gz')['entries'];ledger=read(STAGE/'visual-ledger.json.gz');assert rows==public_rows
    assert len(rows)==len({r['ref']for r in rows})==cfg['references']==21 and cfg['expected_coverage']==3111+len(rows)
    baseline=read(STAGE/'baseline.previous.json');countries={r['id']:r for r in baseline['countries']};assert len(countries)==219 and sum(r['picons']for r in countries.values())==3111
    cache=Path(os.environ.get('WARDER_MANIFEST_CACHE',STAGE/'manifest-cache'))
    negative=[e['row']for e in ledger['entries']if e['decision']=='hold']+ledger.get('source_holds',[]);assert len(negative)==18
    negative_overlap=[]
    for r in negative:
        c=countries[r['country']]
        if not c['release']:continue
        m=fetch_release(c['release'],cache);name=r['ref'].replace(':','_')+'.png'
        if any(name in m['packages'][size][style]['files']for size in('50x30','220x132','400x240')for style in('transparent','white','black')):negative_overlap.append(dict(country=r['country'],ref=r['ref']))
    assert not negative_overlap,'New bad probes cannot invalidate prior approved artwork: '+str(negative_overlap)
    paths=[RADIO/'staging'/name for name in HISTORY];assert len(paths)==9 and all(f.is_file()for f in paths)
    assert len(proof['history'])==9
    for name,path,expected in zip(HISTORY,paths,proof['history']):
        body=path.read_bytes();assert expected['commit']==PARENT and expected['path']=='picons/radio-world/staging/'+name
        assert len(body)==expected['bytes']and sha(body)==expected['sha256'],'Historical ledger bytes differ from verified parent'
    combined=merge_ledgers(paths+[STAGE/'visual-ledger.json.gz']);assert validate_selection(rows,combined)==21
    assert not identity_blocks(combined)&{(r['country'],r['ref'])for r in rows},'No new source-hold exception is permitted'
    assert not any(e.get('resolves_source_hold')is True for e in ledger['entries']if e['decision']=='approve')
    world=cfg['world'];raw=urllib.request.urlopen(world['url'],timeout=90).read();assert len(raw)==world['bytes']and sha(raw)==world['sha256']
    import gzip
    world_rows=json.loads(gzip.decompress(raw))
    for r in rows:
        assert re.fullmatch('[0-9a-f]{40}',r['source_commit'])and r['ref']not in cfg['held_references']
        assert r['station']['group']==countries[r['country']]['name']
        assert any(w['reference']==r['ref']and all(w[k]==r['station'][k]for k in('name','url','group'))for w in world_rows)
    new,disjoint=inspect(rows,baseline_raw,cache);assert len(new)==21 and not disjoint['reused']and not disjoint['held']
    result=dict(schema=1,status='pass',references=21,png_instances=189,baseline_references=3111,expected_coverage=3132,historical_ledgers=9,source_hold_exceptions=0,world_exact_matches=21,existing_baseline_filename_matches=0,negative_references_checked=18,negative_baseline_matches=0,no_png_or_zip_generated=True)
    (STAGE/'verification-proof.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
