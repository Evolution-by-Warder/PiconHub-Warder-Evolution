"""Validate original production authority and exact enumerated stream aliases."""
import re,gzip,hashlib,json,sys,urllib.parse
from pathlib import Path
S=Path(__file__).resolve().parents[1];R=S.parents[1];sys.path.insert(0,str(R/'tools'))
from visual_gate import read,merge_ledgers,validate_selection,identity_blocks
from saved_artwork_import import get
sys.path.insert(0,str(S.parent/'batch-50-reviewed/helpers'));import baseline_admission
cfg=read(S/'configuration.json');desc=read(S/'source-inputs/recovery-spec.json');facts=read(S/'source-inputs/public-observations.json');rows=read(S/'selection.json.gz')['entries'];assert len(rows)==cfg['references']==3
paths=[R/'staging/source-ledger-reviewed-20261107/visual-ledger.json.gz',R/'staging/visual-review-34-36/decisions.json.gz']+[R/f'staging/batch-{n}-reviewed/visual-ledger.json.gz'for n in range(39,66)];history=merge_ledgers(paths)
audit=json.loads(gzip.decompress(get(desc['audit'])))['checks'];world=json.loads(gzip.decompress(get(desc['current'])));prod=json.loads(get(desc['production_index']));prod={c['id']:c for c in prod['countries']};cache={}
for r,f,p in zip(rows,facts['entries'],desc['pairs']):
 st=p['new'];old=p['old'];assert f['station']==st and f['approved_station']==old and st in world
 assert r['ref']==st['reference']and r['station']=={k:st[k]for k in ['name','url','group']}and r['ref']not in cfg['held_references']
 for x,u in [(f['new_audit'],st['url']),(f['approved_audit'],old['url'])]:
  assert x=={k:audit[u].get(k)for k in x}and x['url']==u and x['status']=='audio-confirmed'and x['http_status']==200 and x['content_type'].startswith('audio/')and x['sample_bytes']>0
 assert f['new_audit']['icy_name']==f['approved_audit']['icy_name']==p['icy_name']
 a=urllib.parse.urlsplit(st['url']);b=urllib.parse.urlsplit(old['url']);fa=urllib.parse.urlsplit(audit[st['url']]['final_url']);fb=urllib.parse.urlsplit(audit[old['url']]['final_url'])
 kind=p['kind']
 if kind=='publisher-primary':
  e=p['primary'];assert len(e['publisher_sha256'])==64
  if st['name']=='Javeriana Estéreo (Bogotá)':
   assert e['publisher_page']=='https://javerianaestereo.com/' and e['publisher_stream']=='https://radio06.cehis.net/proxy/javerian?mp=/stream'
   m=e['api_fields'];assert m['title']=='Javeriana Estéreo Bogotá' and m['mountpoint']=='/stream' and m['tuneinurl']=='http://167.114.90.38:8001/stream' and m['proxytuneinurltls']=='https://radio06.cehis.net/proxy/javerian/stream'
   assert any(q['type']==1 and q['data']=='167.114.90.38' and q['name']=='radio06.cehis.net.'for q in e['dns']['Answer'])
   assert a.hostname=='radio06.cehis.net' and a.port==8001 and a.path=='/stream'
  elif st['name']=='Radio Horeb 128k':
   assert e['publisher_page']=='https://www.horeb.org/empfang/' and e['publisher_stream']=='https://rs16.stream24.net/horeb.mp3'
   assert any(q['type']==5 and q['name']=='rs16.stream24.org.'and q['data']=='rs16.stream24.net.'for q in e['dns']['Answer'])
   assert a.hostname=='rs16.stream24.org' and b.hostname=='rs16.stream24.net' and a.path==b.path=='/horeb.mp3' and a.port is None and b.port is None
  elif st['name']=='Radio Schwany - Souvenier 2':
   assert e['publisher_page']=='https://www.schwany.de/programme.html' and e['linked_player']=='https://souvenir2.spcast.eu/' and e['player_stream']==st['url'] and e['player_title']=='Schwany Souvenir 2 Livestream'
   assert e['old_primary_redirect']['url']==old['url'] and 'location: https://souvenir2.sp.radio.fm/stream' in e['old_primary_redirect']['headers']
  else:raise ValueError(st['name'])
 elif kind=='query-only':assert a.netloc==b.netloc and a.path.rstrip('/')==b.path.rstrip('/')and set(urllib.parse.parse_qs(a.query))|set(urllib.parse.parse_qs(b.query))<=set(p['allowed_query'])
 elif kind=='primary-301':
  obs=p['primary_redirects'];assert [q['url']for q in obs]==[st['url'],old['url']] and all(q['status']==301 and len(q['header_sha256'])==64 for q in obs) and obs[0]['location']==obs[1]['location']
 elif kind=='mapped-programme':
  assert [a.hostname,b.hostname]==p['publisher_hosts'] and [a.path,b.path]==p['publisher_paths'] and fa.path==fb.path==p['final_path']
  assert re.fullmatch(p['cdn_pattern'],fa.hostname) and re.fullmatch(p['cdn_pattern'],fb.hostname)
  qa={k:v for k,v in urllib.parse.parse_qsl(fa.query) if k not in p['allowed_query']};qb={k:v for k,v in urllib.parse.parse_qsl(fb.query) if k not in p['allowed_query']};assert qa==qb
 elif kind=='publisher-codec':assert a.netloc==b.netloc==p['publisher_host']and [a.path,b.path]==p['paths']
 elif kind=='publisher-redirect':assert a.hostname.removeprefix('www.')==b.hostname.removeprefix('www.')==p['publisher_host']and fa.path==fb.path==p['final_path']and fa.hostname.endswith(p['cdn_suffix'])and fb.hostname.endswith(p['cdn_suffix'])
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
proof=dict(status='pass',references=3,png_instances=27,production_authority_verified=True,explicit_named_endpoint_pairs=3,source_hold_exceptions=0,new_renders=0,new_endpoint_requests=0)
(S/'verification-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(proof)
