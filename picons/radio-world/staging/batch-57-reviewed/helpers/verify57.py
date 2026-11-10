"""Admit only explicitly reviewed named-stream aliases with exact historical PNG reuse."""
import gzip,hashlib,json,sys,urllib.parse
from pathlib import Path
S=Path(__file__).resolve().parents[1];R=S.parents[1];N=int(S.name.split('-')[1]);sys.path.insert(0,str(R/'tools'))
from visual_gate import read,merge_ledgers,validate_selection
from saved_artwork_import import get
sys.path.insert(0,str(S.parent/'batch-50-reviewed/helpers'));import baseline_admission
EXPECTED=[['Radio Megalonisos', 'http://s3.onweb.gr:8540/', 'Μεγαλόνησος 89.8', 'http://s3.onweb.gr:8540/stream', 'Radio megalonisos 89,8'], ['Radio Nostalgia', 'http://radionostalgiagr.dyndns.org:2314/', 'Νοσταλγία', 'http://radionostalgiagr.dyndns.org:2314/stream?type=http&nocache=167', 'Radio Nostalgia'], ['Wave FM 974 Patras GR', 'http://sp1.32bit.gr:8018/', 'Wave 97.4', 'https://sp1.32bit.gr/8018/;', 'Wave 97.4 Patras'], ['Super FM Brasov 93.8', 'https://live.superfm.ro/stream.mp3?time=1697692801', 'Super FM', 'https://live.superfm.ro/stream.mp3', 'Super FM Brasov 93.8 FM'], ['SuperFM Brasov 93.8 FM', 'https://live.superfm.ro/stream.mp3?nocache=0.19023860954617056', 'Super FM', 'https://live.superfm.ro/stream.mp3', 'Super FM Brasov 93.8 FM'], ['TOP Radio -Suceava 104.0 FM', 'http://live.radiotop.ro:8000/radio.mp3', 'Radio Top Suceava', 'https://live.radiotop.ro/radio/8000/radio.mp3', 'Radio TOP Suceava'], ['Valori Românești Radio', 'https://securestreams6.autopo.st:2250/', 'Radio Valori Românești -Cluj Napoca', 'https://securestreams6.autopo.st:2250/stream', 'Valori Romanesti Radio'], ['Radio Xtream Romania - Brăila', 'https://asculta.radioxtream.com/8022/stream', 'Radio Xtream Romania', 'https://asculta.radioxtream.com:8022/stream', 'Radio Xtream Romania']]
cfg=read(S/'configuration.json');facts=read(S/'source-inputs/public-observations.json');rows=read(S/'selection.json.gz')['entries'];assert len(rows)==cfg['references']==len(EXPECTED)
assert facts['stream_audit']['url']=='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/481e9b9154a510c64c743de72c1a73ed808307bf/picons/IPTV-SK-CZ/catalog/global/stream-audit.json.gz'
audit=json.loads(gzip.decompress(get(facts['stream_audit'])))['checks'];world=json.loads(gzip.decompress(get(facts['current_world'])))
paths=[R/'staging/source-ledger-reviewed-20261107/visual-ledger.json.gz',R/'staging/visual-review-34-36/decisions.json.gz']+[R/f'staging/batch-{n}-reviewed/visual-ledger.json.gz'for n in range(39,N)];history=merge_ledgers(paths)
# Some aliases reuse the same historical source; validate each original once.
oldrows=list({(f['approved']['country'],f['approved']['ref']):f['approved']for f in facts['entries']}.values());assert validate_selection(oldrows,history)==len(oldrows)
for r,f,pair in zip(rows,facts['entries'],EXPECTED):
 st=f['station'];old=f['approved'];a=f['new_audit'];b=f['approved_audit'];assert [st['name'],st['url'],old['station']['name'],old['station']['url'],a['icy_name']]==pair
 for x,u in [(a,st['url']),(b,old['station']['url'])]:
  assert x=={k:audit[u].get(k)for k in x}and x['url']==u and x['status']=='audio-confirmed'and x['http_status']==200 and x['content_type'].startswith('audio/')and x['sample_bytes']>0 and len(x['sample_sha256'])==64
 assert a['icy_name'].strip().casefold()==b['icy_name'].strip().casefold() and len(a['icy_name'].strip())>=4
 assert not any(w in a['icy_name'].lower()for w in ['no name','autodj','auto-dj','radiocaster','streammystation','myradio','my radio','securenet','orban','alsolnet','stream name','netcast','unnamed','my station','my server'])
 assert urllib.parse.urlsplit(st['url']).hostname==urllib.parse.urlsplit(old['station']['url']).hostname
 assert r['ref']==st['reference']and r['station']=={k:st[k]for k in ['name','url','group']}and r['ref']not in cfg['held_references']
 assert all(r[k]==old[k]for k in ['source_commit','variants'])and r['final_visual_approval']['reviewed_variants']==old['variants']
 assert r['asset_root']==old['asset_root'].removesuffix('/verified-assets')
 assert any(w['reference']==r['ref']and all(w[k]==st[k]for k in ['name','url','group'])for w in world)
assert validate_selection(rows,merge_ledgers(paths+[S/'visual-ledger.json.gz']))==len(rows)
baseline_admission.BASELINE_SHA=cfg['baseline_index']['sha256'];raw=(S/'baseline.previous.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==baseline_admission.BASELINE_SHA
new,result=baseline_admission.inspect(rows,raw,Path('/tmp/radio-alias-manifests'));assert len(new)==len(rows)and not result['reused']and not result['held']
proof=dict(status='pass',references=len(rows),png_instances=9*len(rows),explicit_named_endpoint_pairs=len(rows),current_main_exact_service_matches=len(rows),source_hold_exceptions=0,new_renders=0,new_endpoint_requests=0)
(S/'verification-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(proof)
