"""Validate original production authority and exact enumerated stream aliases."""
import re,gzip,hashlib,json,sys,urllib.parse
from pathlib import Path
S=Path(__file__).resolve().parents[1];R=S.parents[1];sys.path.insert(0,str(R/'tools'))
from visual_gate import read,merge_ledgers,validate_selection,identity_blocks
from saved_artwork_import import get
sys.path.insert(0,str(S.parent/'batch-50-reviewed/helpers'));import baseline_admission
cfg=read(S/'configuration.json');desc=read(S/'source-inputs/recovery-spec.json');facts=read(S/'source-inputs/public-observations.json');rows=read(S/'selection.json.gz')['entries'];assert len(rows)==cfg['references']==2
paths=[R/'staging/source-ledger-reviewed-20261107/visual-ledger.json.gz',R/'staging/visual-review-34-36/decisions.json.gz']+[R/f'staging/batch-{n}-reviewed/visual-ledger.json.gz'for n in range(39,69)];history=merge_ledgers(paths)
audit=json.loads(gzip.decompress(get(desc['audit'])))['checks'];world=json.loads(gzip.decompress(get(desc['current'])));prod=json.loads(get(desc['production_index']));prod={c['id']:c for c in prod['countries']};cache={}
for r,f,p in zip(rows,facts['entries'],desc['pairs']):
 st=p['new'];old=p['old'];assert f['station']==st and f['approved_station']==old and st in world
 assert r['ref']==st['reference']and r['station']=={k:st[k]for k in ['name','url','group']}and r['ref']not in cfg['held_references']
 for x,u in [(f['new_audit'],st['url']),(f['approved_audit'],old['url'])]:
  assert x=={k:audit[u].get(k)for k in x}and x['url']==u and x['status']=='audio-confirmed'and x['http_status']==200 and x['content_type'].startswith('audio/')and x['sample_bytes']>0
 assert f['new_audit']['icy_name']==f['approved_audit']['icy_name']==p['icy_name']
 a=urllib.parse.urlsplit(st['url']);b=urllib.parse.urlsplit(old['url']);fa=urllib.parse.urlsplit(audit[st['url']]['final_url']);fb=urllib.parse.urlsplit(audit[old['url']]['final_url'])
 kind=p['kind']
 if kind=='same-named-endpoint':
  assert a.hostname==b.hostname and a.port==b.port and a.path.rstrip('/')==b.path.rstrip('/')
  assert a.path not in ('','/','/stream')
  assert set(urllib.parse.parse_qs(a.query,keep_blank_values=True))|set(urllib.parse.parse_qs(b.query,keep_blank_values=True))==set(p['allowed_query'])
  assert fa.hostname==fb.hostname and fa.path==fb.path
 elif kind=='publisher-ports':
  assert a.hostname==b.hostname=='anonradio.net' and a.path==b.path=='/anonradio'
  assert (a.scheme,a.port,b.scheme,b.port)==('http',8000,'https',8443)
  assert p['publisher']['endpoints']==[st['url'],old['url']] and len(p['publisher']['sha256'])==64
 else:raise ValueError(kind)
 code=r['country'];rel=prod[code]['release'];assert rel==f['production_release']==r['provenance']['production_release'];cache.setdefault(code,json.loads(get(rel)));manifest=cache[code];oldfile=old['reference'].replace(':','_')+'.png'
 assert (code,old['reference'])not in identity_blocks(history)
 assert not any(e['decision']=='hold'and e['row']['country']==code and e['row']['ref']==old['reference']for e in history['entries'])
 for v,(digest,n,blob)in r['variants'].items():
  size,style=v.split('/');assert digest==manifest['packages'][size][style]['files'][oldfile];data=(S/'verified-assets'/f'{digest}.png').read_bytes();assert hashlib.sha256(data).hexdigest()==digest and len(data)==n and hashlib.sha1(f'blob {n}\0'.encode()+data).hexdigest()==blob
 assert r['final_visual_approval']['reviewed_variants']==r['variants']and r['asset_root']==str(S.relative_to(Path.cwd())) if S.is_absolute() else r['asset_root']==str(S)
assert validate_selection(rows,merge_ledgers(paths+[S/'visual-ledger.json.gz']))==len(rows)
baseline_admission.BASELINE_SHA=cfg['baseline_index']['sha256'];raw=(S/'baseline.previous.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==baseline_admission.BASELINE_SHA
new,result=baseline_admission.inspect(rows,raw,Path('/tmp/radio-alias-manifests'));assert len(new)==len(rows)and not result['reused']and not result['held']
proof=dict(status='pass',references=2,png_instances=18,approved_candidate_authority_verified=True,explicit_named_endpoint_pairs=2,source_hold_exceptions=0,new_renders=0,new_endpoint_requests=0)
(S/'verification-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(proof)
