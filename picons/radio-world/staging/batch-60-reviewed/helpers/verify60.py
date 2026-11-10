"""Admit only explicitly reviewed named-stream aliases with exact historical PNG reuse."""
import gzip,hashlib,json,sys,urllib.parse,subprocess,html
from pathlib import Path
S=Path(__file__).resolve().parents[1];R=S.parents[1];N=int(S.name.split('-')[1]);sys.path.insert(0,str(R/'tools'))
from visual_gate import read,merge_ledgers,validate_selection
from saved_artwork_import import get
sys.path.insert(0,str(S.parent/'batch-50-reviewed/helpers'));import baseline_admission
EXPECTED=[['917TheWave', 'https://tls3.coastdev.net/6mm-mp3', 'Wave FM 91.7', 'http://east.coastdev.net/6mm-mp3', ''], ['Galaxie Radio', 'https://www.radioking.com/play/galaxieradio', 'Galaxie FM 95.30', 'https://listen.radioking.com/radio/15684/stream/29075', ''], ['Radio21 Leer vf', 'https://streams.radio21.de/leer/mp3-192/streams.radio21.de/', 'Radio 21 Leer', 'https://streams.radio21.de/leer/mp3-192/web', ''], ['FG.be - Vlaanderen', 'http://radiofg.impek.com/fga', 'Radio FG Antwerpen', 'https://stream.rcs.revma.com/5wesqhfap98uv', 'Radio FG Belgium'], ['La X 96.5', 'https://tupanel.info/stream/2digitalradioHDsslLIVE040', 'LA X 96.5 Cali', 'https://onlineradiobox.com/json/co/lax/play?platform=web', 'LA X 96.5 CALI'], ['Radio Elecroshock', 'http://manager.conceptradio.fr:1250/stream', 'ELECTRO CHOC', 'https://manager.conceptradio.fr:1255/stream?x=1778074871622', 'ELECTRO-CHOC'], ['NPO Radio5', 'https://icecast.omroep.nl/radio5-bb-aac', 'NPO Radio %', 'https://icecast.omroep.nl/radio5-sb-mp3', 'NPO Radio5']]
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
 u=urllib.parse.urlsplit(st['url']);v=urllib.parse.urlsplit(old['station']['url'])
 af=urllib.parse.urlsplit(audit[st['url']]['final_url']);bf=urllib.parse.urlsplit(audit[old['station']['url']]['final_url'])
 name=st['name']
 if name in ['917TheWave','Galaxie Radio','Radio21 Leer vf']:
  assert (af.scheme,af.netloc,af.path,af.query)==(bf.scheme,bf.netloc,bf.path,bf.query)
 elif name=='FG.be - Vlaanderen':
  assert af.hostname.endswith('.rcs.revma.com') and bf.hostname.endswith('.rcs.revma.com') and af.path==bf.path=='/5wesqhfap98uv'
  assert a['icy_name']==b['icy_name']=='Radio FG Belgium'
 elif name=='La X 96.5':
  assert af.hostname==bf.hostname=='tupanel.info' and af.path==bf.path=='/stream/2digitalradioHDsslLIVE040'
  assert af.port is None and bf.port==2000 and a['icy_name']==b['icy_name']=='LA X 96.5 CALI'
 elif name=='Radio Elecroshock':
  assert u.hostname==v.hostname=='manager.conceptradio.fr' and u.port==1250 and v.port==1255
  assert a['icy_name']==b['icy_name']=='ELECTRO-CHOC' and a['sample_sha256']==b['sample_sha256'] and a['sample_bytes']==b['sample_bytes']==1024
 else:
  assert name=='NPO Radio5' and u.hostname==v.hostname=='icecast.omroep.nl' and u.path=='/radio5-bb-aac' and v.path=='/radio5-sb-mp3'
  assert a['icy_name']==b['icy_name']=='NPO Radio5'

 assert r['ref']==st['reference']and r['station']=={k:st[k]for k in ['name','url','group']}and r['ref']not in cfg['held_references']
 assert all(r[k]==old[k]for k in ['source_commit','variants'])and r['final_visual_approval']['reviewed_variants']==old['variants']
 assert r['asset_root']==old['asset_root'].removesuffix('/verified-assets')
 assert any(w['reference']==r['ref']and all(w[k]==st[k]for k in ['name','url','group'])for w in world)
assert validate_selection(rows,merge_ledgers(paths+[S/'visual-ledger.json.gz']))==len(rows)
baseline_admission.BASELINE_SHA=cfg['baseline_index']['sha256'];raw=(S/'baseline.previous.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==baseline_admission.BASELINE_SHA
new,result=baseline_admission.inspect(rows,raw,Path('/tmp/radio-alias-manifests'));assert len(new)==len(rows)and not result['reused']and not result['held']
proof=dict(status='pass',references=len(rows),png_instances=9*len(rows),explicit_named_endpoint_pairs=len(rows),current_main_exact_service_matches=len(rows),source_hold_exceptions=0,new_renders=0,new_endpoint_requests=0)
(S/'verification-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(proof)
