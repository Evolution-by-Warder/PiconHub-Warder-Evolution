"""Admit only explicitly reviewed named-stream aliases with exact historical PNG reuse."""
import gzip,hashlib,json,sys,urllib.parse,subprocess,html
from pathlib import Path
S=Path(__file__).resolve().parents[1];R=S.parents[1];N=int(S.name.split('-')[1]);sys.path.insert(0,str(R/'tools'))
from visual_gate import read,merge_ledgers,validate_selection
from saved_artwork_import import get
sys.path.insert(0,str(S.parent/'batch-50-reviewed/helpers'));import baseline_admission
EXPECTED=[['Open Broadcast', 'https://www.digris.ch/stream/092210ed-4eb4-483b-814f-21df6ecb1352', 'Openbroadcast.ch | mp3', 'http://stream.openbroadcast.ch/256.mp3', 'openbroadcast.ch'], ['centreforce', 'http://centreforce.streamgb.com:8830/320', 'Centreforce 883', 'https://listen.centreforceradio.com/96', 'Centreforce']]
cfg=read(S/'configuration.json');facts=read(S/'source-inputs/public-observations.json');rows=read(S/'selection.json.gz')['entries'];assert len(rows)==cfg['references']==len(EXPECTED)
assert facts['stream_audit']['url']=='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/481e9b9154a510c64c743de72c1a73ed808307bf/picons/IPTV-SK-CZ/catalog/global/stream-audit.json.gz'
audit=json.loads(gzip.decompress(get(facts['stream_audit'])))['checks'];world=json.loads(gzip.decompress(get(facts['current_world'])))
paths=[R/'staging/source-ledger-reviewed-20261107/visual-ledger.json.gz',R/'staging/visual-review-34-36/decisions.json.gz']+[R/f'staging/batch-{n}-reviewed/visual-ledger.json.gz'for n in range(39,N)];history=merge_ledgers(paths)
# Some aliases reuse the same historical source; validate each original once.
oldrows=list({(f['approved']['country'],f['approved']['ref']):f['approved']for f in facts['entries']}.values());assert validate_selection(oldrows,history)==len(oldrows)
for r,f,pair in zip(rows,facts['entries'],EXPECTED):
 st=f['station'];old=f['approved'];a=f['new_audit'];b=f['approved_audit'];assert [st['name'],st['url'],old['station']['name'],old['station']['url'],a['icy_name']]==pair
 for x,u in [(a,st['url']),(b,old['station']['url'])]:
  assert x=={k:audit[u].get(k)for k in x}and x['url']==u and x['status']=='audio-confirmed'and x['http_status']==200 and (x['content_type'].startswith('audio/') or (st['name']=='Radio Bergeijk FLAC' and x is a and x['content_type']=='application/ogg'))and x['sample_bytes']>0 and len(x['sample_sha256'])==64
 u=urllib.parse.urlsplit(st['url']);v=urllib.parse.urlsplit(old['station']['url']);e=f['identity_evidence']
 assert e==read(S/'source-inputs/recovery-spec.json')['evidence'][st['name']]
 assert a['icy_name']==b['icy_name']
 if st['name']=='Open Broadcast':
  p=e['program'];assert p['uuid']=='092210ed-4eb4-483b-814f-21df6ecb1352' and p['name']=='Open Broadcast' and p['country_code']=='ch' and p['public_stream_url']==u.path and p['enable_stream_relay'] and p['has_relay_stream']
  assert st['url']=='https://www.digris.ch'+p['public_stream_url'] and v.hostname=='stream.openbroadcast.ch' and v.path=='/256.mp3' and a['icy_name']=='openbroadcast.ch'
 else:
  assert st['name']=='centreforce' and u.hostname=='centreforce.streamgb.com' and u.port==8830 and u.path=='/320' and v.hostname=='listen.centreforceradio.com' and v.path=='/96'
  assert e['host']==v.hostname and e['status_url']=='http://centreforce.streamgb.com:8830/status-json.xsl'
  assert any(m['listenurl']=='http://listen.centreforceradio.com:8830/320' and m['server_name']=='Centreforce' and m['server_url']=='https://centreforceradio.com' for m in e['mounts'])
  assert a['icy_name']=='Centreforce'

 assert r['ref']==st['reference']and r['station']=={k:st[k]for k in ['name','url','group']}and r['ref']not in cfg['held_references']
 assert all(r[k]==old[k]for k in ['source_commit','variants'])and r['final_visual_approval']['reviewed_variants']==old['variants']
 assert r['asset_root']==old['asset_root'].removesuffix('/verified-assets')
 assert any(w['reference']==r['ref']and all(w[k]==st[k]for k in ['name','url','group'])for w in world)
assert validate_selection(rows,merge_ledgers(paths+[S/'visual-ledger.json.gz']))==len(rows)
baseline_admission.BASELINE_SHA=cfg['baseline_index']['sha256'];raw=(S/'baseline.previous.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==baseline_admission.BASELINE_SHA
new,result=baseline_admission.inspect(rows,raw,Path('/tmp/radio-alias-manifests'));assert len(new)==len(rows)and not result['reused']and not result['held']
proof=dict(status='pass',references=len(rows),png_instances=9*len(rows),explicit_named_endpoint_pairs=len(rows),current_main_exact_service_matches=len(rows),source_hold_exceptions=0,new_renders=0,new_endpoint_requests=0)
(S/'verification-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(proof)
