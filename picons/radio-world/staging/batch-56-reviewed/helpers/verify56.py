"""Verify five explicit stream aliases; never admit on normalized station name alone."""
import gzip,hashlib,json,re,sys,urllib.parse
from pathlib import Path
S=Path(__file__).resolve().parents[1];R=S.parents[1];sys.path.insert(0,str(R/'tools'))
from visual_gate import read,merge_ledgers,validate_selection
from saved_artwork_import import get
sys.path.insert(0,str(S.parent/'batch-50-reviewed/helpers'));import baseline_admission
cfg=read(S/'configuration.json');facts=read(S/'source-inputs/public-observations.json');rows=read(S/'selection.json.gz')['entries'];assert len(rows)==cfg['references']==5
assert facts['stream_audit']['url'].startswith('https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/2b294878b14ca322fa277ba1e9781f83ec5649cf/')
audit=json.loads(gzip.decompress(get(facts['stream_audit'])))['checks'];world=json.loads(gzip.decompress(get(facts['current_world'])))
paths=[R/'staging/source-ledger-reviewed-20261107/visual-ledger.json.gz',R/'staging/visual-review-34-36/decisions.json.gz']+[R/f'staging/batch-{n}-reviewed/visual-ledger.json.gz'for n in range(39,56)];history=merge_ledgers(paths)
assert validate_selection([f['approved']for f in facts['entries']],history)==5
for r,f in zip(rows,facts['entries']):
 st=f['station'];old=f['approved'];a=f['new_audit'];b=f['approved_audit'];assert a==audit[st['url']] and b==audit[old['station']['url']]
 for x in (a,b):assert x['status']=='audio-confirmed'and x['http_status']==200 and x['content_type'].startswith('audio/')and x['sample_bytes']>0 and len(x['sample_sha256'])==64
 assert r['ref']==st['reference']and r['station']=={k:st[k]for k in ['name','url','group']}and r['country']==old['country']and r['ref']not in cfg['held_references']
 assert all(r[k]==old[k]for k in ['source_commit','asset_root','variants']);assert r['final_visual_approval']['reviewed_variants']==old['variants']
 assert any(w['reference']==r['ref']and all(w[k]==st[k]for k in ['name','url','group'])for w in world)
 u=urllib.parse.urlsplit(st['url']);v=urllib.parse.urlsplit(old['station']['url']);name=st['name']
 if name=='Air Connect Radio':
  assert u.hostname=='stream2.airconnectradio.com'and v.hostname=='stream.airconnectradio.com'and u.path=='/ac128.mp3'and v.path=='/ac192.mp3'and not u.query and not v.query
  assert a['icy_name']=='Air Connect'and b['icy_name']=='Air Connect Radio'and old['provenance']['page_url']=='https://airconnectradio.com/'
 elif name=='MAXI FRANCE':
  assert u.scheme==v.scheme=='https'and u.netloc==v.netloc=='stream.maxifrance.radio'and u.path==v.path=='/stream'and u.query=='nocache=52665'and not v.query
  assert a['icy_name']==b['icy_name']=='MAXI FRANCE - WWW.MAXIFRANCE.RADIO'
 elif name=='Balatonica':
  assert u.scheme==v.scheme=='http'and u.netloc==v.netloc=='balatonica.hu:8000'and u.path=='/stream_low'and v.path=='/stream_high'and not u.query and not v.query
  assert a['icy_name']==b['icy_name']=='Balatonica'
 elif name=='BANKER':
  assert u.scheme==v.scheme=='http'and u.netloc==v.netloc=='banker96-naxinacional.streaming.rs:8540'and u.path=='/'and v.path=='/;'and not u.query and not v.query
  assert a['icy_name']==b['icy_name']=='Naxi Banker Radio'
 elif name=='LAKHANDA RADIO':
  assert u.scheme==v.scheme=='https'and u.netloc==v.netloc=='cp12.serverse.com'and u.path==v.path=='/proxy/itnfm'and u.query=='mp=/stream&1707017036'and v.query=='mp=/stream'
  assert a['icy_name']==b['icy_name']=='Lakhanda.lk'and old['provenance']['primary_exact_stream']['catalogue_url']==old['station']['url']
 else:raise AssertionError('Unknown identity mapping')
 assert urllib.parse.urldefrag(st['url'])[0]==a['final_url']and old['station']['url']==b['final_url']
assert validate_selection(rows,merge_ledgers(paths+[S/'visual-ledger.json.gz']))==5
baseline_admission.BASELINE_SHA=cfg['baseline_index']['sha256'];raw=(S/'baseline.previous.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==baseline_admission.BASELINE_SHA
new,result=baseline_admission.inspect(rows,raw,Path('/tmp/radio56-manifests'));assert len(new)==5 and not result['reused']and not result['held']
proof=dict(status='pass',references=5,png_instances=45,approved_originals_checked_against_historical_ledgers=5,explicit_endpoint_identity_mappings=5,current_main_exact_service_matches=5,source_hold_exceptions=0,new_renders=0,new_endpoint_requests=0)
(S/'verification-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(proof)
