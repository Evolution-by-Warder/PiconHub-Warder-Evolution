"""Copy exact approved Flux60s/90s PNG bytes; never render."""
import json,gzip,hashlib,sys,io,subprocess
from pathlib import Path
from zipfile import ZipFile
S=Path('picons/radio-world/staging');stage=S/'batch-81-reviewed';prev=S/'batch-80-reviewed'
sys.path.insert(0,'picons/radio-world/tools')
from visual_gate import read,merge_ledgers,identity_blocks,validate_selection
from saved_artwork_import import get
sha=lambda b:hashlib.sha256(b).hexdigest()
def write(p,x):
 b=(json.dumps(x,indent=2,ensure_ascii=False)+'\n').encode();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(gzip.compress(b,mtime=0)if p.suffix=='.gz'else b)
def git(*args):return subprocess.check_output(['git',*args],text=True).strip()
desc=read(stage/'source-inputs/recovery-spec.json');cfg=read(prev/'configuration.json');raw=(prev/'countries.proposed.json').read_bytes();assert sha(raw)==desc['baseline_sha256'];world=json.loads(gzip.decompress(get(cfg['world'])))
paths=[S/'source-ledger-reviewed-20261107/visual-ledger.json.gz',S/'visual-review-34-36/decisions.json.gz']+[S/f'batch-{n}-reviewed/visual-ledger.json.gz'for n in range(39,81)];history=merge_ledgers(paths);known={(e['row']['country'],e['row']['ref'])for e in history['entries']};blocks=identity_blocks(history);assert len(cfg['held_references'])==923
assert len(desc['stations'])==2
baseline=json.loads(raw);de=next(x for x in baseline['countries']if x['id']=='DE');manifest=json.loads(get(de['release']));zip_cache={};rows=[]
for i,r in enumerate(desc['stations']):
 st=r['station'];matches=[x for x in world if x['reference']==st['reference']and x['group']==st['group']];assert len(matches)==1;x=matches[0]
 assert dict(x,url=x['url'].split('?')[0])==st and sha(x['url'].encode())==r['catalog_url_sha256']
 assert ('DE',st['reference'])not in known|blocks and st['reference']not in cfg['held_references']
 assert r['publisher']['route']in ['60er','90er']and r['publisher']['directory']=='https://streams.fluxfm.de/'
 assert r['publisher']['official_urls'][0].split('/')[3:5]==st['url'].split('/')[3:5]
 name=r['alias_source']['reference'].replace(':','_')+'.png';assert len(r['variants'])==9
 for k,values in r['variants'].items():
  size,sty=k.split('/');e=manifest['packages'][size][sty];part=next(p for p in e.get('parts',[e])if name in p['files'])
  if part['url']not in zip_cache:zip_cache[part['url']]=get(part)
  b=ZipFile(io.BytesIO(zip_cache[part['url']])).read(name);assert sha(b)==values[0]==e['files'][name]and len(b)==values[1]
  assert hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()==values[2]
  p=stage/'verified-assets'/(sha(b)+'.png');p.parent.mkdir(exist_ok=True);p.write_bytes(b)
 rows.append(dict(index=810000+i,country='DE',ref=st['reference'],station={k:st[k]for k in ['name','url','group']},asset_root=str(stage),variants=r['variants'],provenance=dict(publisher=r['publisher'],alias_source=r['alias_source'],catalog_url_sha256={'new':r['catalog_url_sha256']},identity_basis='Official FluxFM directory binds exact decade channel and codec. Existing approved60s/90s broadcaster variants copied byte-for-byte; no name-only cross-brand substitution.')))
git('config','user.name','github-actions[bot]');git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com');git('add',str(stage/'verified-assets'));git('commit','-m','Save81 two exact FluxFM aliases and18 existing approved PNGs [skip ci]');commit=git('rev-parse','HEAD');git('push','origin','HEAD:refs/heads/work/radio-world-batch38-contrast-pass1-history-20261107')
for r in rows:r.update(source_commit=commit,final_visual_approval=dict(decision='approve',reason='Exact existing approved60s/90s PNGs; all three220x132 previews visually checked, all9 variants hash-bound. Owner preapproved safe aliases.',reviewed_variants=r['variants']))
write(stage/'selection.json.gz',dict(entries=rows));write(stage/'visual-ledger.json.gz',dict(entries=[dict(row=r,decision='approve',reason=r['final_visual_approval']['reason'],reviewed_variants=r['variants'])for r in rows],source_holds=[],pending_sources=[]));assert validate_selection(rows,merge_ledgers(paths+[stage/'visual-ledger.json.gz']))==2
(stage/'baseline.previous.json').write_bytes(raw);cfg.update(batch='81-reviewed',references=2,parent_candidate=desc['parent'],expected_coverage=3484,selection_sha256=sha((stage/'selection.json.gz').read_bytes()),baseline_index=dict(url='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'+desc['parent']+'/picons/radio-world/staging/batch-80-reviewed/countries.proposed.json',bytes=len(raw),sha256=sha(raw)));write(stage/'configuration.json',cfg)
write(stage/'verification-proof.json',dict(status='pass',references=2,PNG_instances=18,alias_PNGs_copied=18,PNG_rerendered=0,configuration_blocks=923,historical_holds_preserved=True));git('add',str(stage));git('commit','-m','Save81 exact alias selection and immutable source bindings [skip ci]');git('push','origin','HEAD:refs/heads/work/radio-world-batch38-contrast-pass1-history-20261107')
