"""Admit only explicitly reviewed named-stream aliases with exact historical PNG reuse."""
import gzip,hashlib,json,sys,urllib.parse,subprocess,html
from pathlib import Path
S=Path(__file__).resolve().parents[1];R=S.parents[1];N=int(S.name.split('-')[1]);sys.path.insert(0,str(R/'tools'))
from visual_gate import read,merge_ledgers,validate_selection
from saved_artwork_import import get
sys.path.insert(0,str(S.parent/'batch-50-reviewed/helpers'));import baseline_admission
EXPECTED=[['Wild Horse FM', 'https://s6.myradiostream.com:46712/;', 'Wild Horse FM - Yarraman - 99.7 FM (MP3)', 'http://s6.myradiostream.com:46712/;listen.mp3', 'My Radio Stream'], ['Radio 1 Bulgaria', 'https://play.global.audio:80/radio164', 'Radio 1 радио 1 класическите хитове', 'http://stream.radioreklama.bg/radio164', 'RADIO 1'], ['Radio Sol FM 97.7', 'http://us9.maindigitalstream.com:7389/stream/;', 'RADIO SOL', 'https://us9.maindigitalstream.com/ssl/7389', 'RADIO SOL'], ['Yoga Chill', 'http://178.32.111.41:8027/stream-128kmp3-YogaChill', 'Yoga Chill on Vip-Radios.fm', 'https://radio4.vip-radios.fm:18027/stream-128kmp3-YogaChill', 'Vip-Radios.FM - Yoga Chill'], ['www.cosmos995.gr', 'https://solid2.streamupsolutions.com/proxy/yavljnhi?mp=/stream', 'Cosmos 99.5', 'http://solid2.streamupsolutions.com:24896/stream', 'mos 99,5 FM'], ['RELAX FM Lietuva', 'https://stream1.relaxfm.lt/relaxfm128.mp3', 'Relax FM', 'https://stream4.radijas.lt/relaxfm', 'RELAX FM'], ['Radio Olympia - 100% Piratenhits en Nederlandstalige muziek', 'https://streams.olympia-streams.nl/olympia', 'Olympia Radio', 'http://streams.olympia-radio.nl/olympia', '100% Piratenhits en Nederlandstalige muziek'], ['Love radio only 70 80 90 love songs', 'https://loveradio.streamingmedia.it/usa', 'LOVE RADIO Only Love Songs 70s80s90s - www.love.radio', 'http://shoutcast3.streamingmedia.it:3162/', 'LOVE RADIO - LOVE.radio']]
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
 u=urllib.parse.urlsplit(st['url']);v=urllib.parse.urlsplit(old['station']['url']);name=st['name'];e=f['identity_evidence']
 assert e==read(S/'source-inputs/recovery-spec.json')['evidence'][name]
 if 'context'in e:assert e['literal']in e['context'] and len(e['sha256'])==64 and e['bytes']>0
 assert a['icy_name'].casefold()==b['icy_name'].casefold()
 if name=='Wild Horse FM':
  assert u.hostname==v.hostname=='s6.myradiostream.com' and u.port==v.port==46712 and u.path== '/;' and v.path=='/;listen.mp3'
  assert e['page_url']=='https://www.wildhorsefm.com/listen-live/' and 's6.myradiostream.com:46712/;listen.pls?sid=1' in e['context']
 elif name=='Radio 1 Bulgaria':
  assert u.hostname=='play.global.audio' and u.port==80 and u.path==v.path=='/radio164' and v.hostname=='stream.radioreklama.bg'
  assert e['page_url']=='https://www.radio1.bg/' and e['literal']=='http://play.global.audio/radio164?dist=WEBSITEBG' and a['icy_name']=='RADIO 1'
 elif name=='Radio Sol FM 97.7':
  assert u.hostname==v.hostname=='us9.maindigitalstream.com' and u.port==7389 and v.path=='/ssl/7389' and a['icy_name']=='RADIO SOL'
  assert e['page_url']=='https://radiosol.cl/' and e['literal']==old['station']['url'] and 'Radio+Sol+97.7'in e['context']
 elif name=='Yoga Chill':
  assert u.hostname=='178.32.111.41' and v.hostname=='radio4.vip-radios.fm' and u.path==v.path=='/stream-128kmp3-YogaChill' and u.port==8027 and v.port==18027
  assert e['dns']['Status']==0 and any(d['name']=='radio4.vip-radios.fm.' and d['type']==1 and d['data']==u.hostname for d in e['dns']['Answer'])
  assert a['icy_name']=='Vip-Radios.FM - Yoga Chill'
 elif name=='www.cosmos995.gr':
  assert e['page_url'].startswith('https://www.cosmos995.gr/index.php/') and e['literal']==st['url'] and a['icy_name']=='mos 99,5 FM'
 elif name=='RELAX FM Lietuva':
  assert e['page_url']=='https://relaxfm.lt/' and e['literal']==old['station']['url'] and u.hostname=='stream1.relaxfm.lt' and u.path=='/relaxfm128.mp3' and a['icy_name']=='RELAX FM'
 elif name=='Radio Olympia - 100% Piratenhits en Nederlandstalige muziek':
  assert u.hostname=='streams.olympia-streams.nl' and v.hostname=='streams.olympia-radio.nl' and u.path==v.path=='/olympia'
  assert e['literal']==old['station']['url'] and e['page_url'].startswith('https://www.olympia-radio.nl/') and e['dns']['Status']==0
  assert any(d['name']==v.hostname+'.' and d['type']==5 and d['data']==u.hostname+'.' for d in e['dns']['Answer'])
 else:
  assert name=='Love radio only 70 80 90 love songs' and e['page_url']=='https://www.love.radio/' and e['literal']=='https://loveradio.streamingmedia.it'
  assert u.hostname=='loveradio.streamingmedia.it' and u.path=='/usa' and a['icy_name']=='LOVE RADIO - LOVE.radio'

 assert r['ref']==st['reference']and r['station']=={k:st[k]for k in ['name','url','group']}and r['ref']not in cfg['held_references']
 assert all(r[k]==old[k]for k in ['source_commit','variants'])and r['final_visual_approval']['reviewed_variants']==old['variants']
 assert r['asset_root']==old['asset_root'].removesuffix('/verified-assets')
 assert any(w['reference']==r['ref']and all(w[k]==st[k]for k in ['name','url','group'])for w in world)
assert validate_selection(rows,merge_ledgers(paths+[S/'visual-ledger.json.gz']))==len(rows)
baseline_admission.BASELINE_SHA=cfg['baseline_index']['sha256'];raw=(S/'baseline.previous.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==baseline_admission.BASELINE_SHA
new,result=baseline_admission.inspect(rows,raw,Path('/tmp/radio-alias-manifests'));assert len(new)==len(rows)and not result['reused']and not result['held']
proof=dict(status='pass',references=len(rows),png_instances=9*len(rows),explicit_named_endpoint_pairs=len(rows),current_main_exact_service_matches=len(rows),source_hold_exceptions=0,new_renders=0,new_endpoint_requests=0)
(S/'verification-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(proof)
