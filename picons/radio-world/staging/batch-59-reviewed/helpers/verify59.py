"""Admit only explicitly reviewed named-stream aliases with exact historical PNG reuse."""
import gzip,hashlib,json,sys,urllib.parse,subprocess,html
from pathlib import Path
S=Path(__file__).resolve().parents[1];R=S.parents[1];N=int(S.name.split('-')[1]);sys.path.insert(0,str(R/'tools'))
from visual_gate import read,merge_ledgers,validate_selection
from saved_artwork_import import get
sys.path.insert(0,str(S.parent/'batch-50-reviewed/helpers'));import baseline_admission
EXPECTED=[['Classique', 'http://01.solumedia.com.ar:8562/;stream.nsv', 'Classique: Una radio de clásicos', 'https://01.solumedia.com.ar:8562/stream', 'CLASSIQUE #unaradiodeclasicos'], ['Hrvatski Katolički Radio', 'https://stream.hkr.hr/hkr.mp3', 'HKR', 'http://stream.hkr.hr:8000/hkr.mp3', 'Hrvatski katolicki radio'], ['RBB Radio Eins', 'http://www.radioeins.de/livemp3', 'radio eins | rbb | neuer Stream | niedrige Qualität', 'http://www.radioeins.de/livemp3_s', 'RadioEins'], ['Idea Radio', 'http://nr7.newradio.it:9361/stream', 'Idea Radio Nel Mondo', 'http://nr7.newradio.it:9361/;', 'Idea Radio'], ['TRV TeleRadioVeneta', 'http://onair18.xdevel.com:8428/;', 'Tele Radio Veneta', 'http://onair18.xdevel.com:8428/;stream.mp3', 'Radio TRV - Teleradioveneta'], ['Amabmay FM 100.5', 'http://cp9.serverse.com:7221/amambayfm', 'Radio Amambay 100.5 FM', 'http://cp9.serverse.com:7221/stream', 'AMAMBAY FM 100.5'], ['Megapolis Samara', 'https://online.radio-megapolis.ru/megapolis_mp3', 'Радио МЕГАПОЛИС', 'http://online.radio-megapolis.ru:8000/megapolis', 'Ð\xa0Ð°Ð´Ð¸Ð¾ Ð\x9cÐµÐ³Ð°Ð¿Ð¾Ð»Ð¸Ñ\x81, Ð¡Ð°Ð¼Ð°Ñ\x80Ð°, 103.6 FM'], ['NAŠ MM Radio 97.8', 'https://radio.dukahosting.com:7045/stream', 'NAS Radio 97.8', 'https://radio.dukahosting.com:7045/;', 'NAÅ\xa0 RADIO'], ['Radio Bergeijk FLAC', 'https://stream.radiobergeijk.nl/listen/radio_bergeijk/flac', 'Radio Bergeijk', 'https://stream.radiobergeijk.nl/listen/radio_bergeijk/mobiel', 'Radio Bergeijk'], ['107.9 Pearl Fm', 'https://dc4.serverse.com/proxy/pearlfm/stream', 'PEARL FM', 'https://dc4.serverse.com/proxy/pearlfm/stream/1/', 'Pearl Fm 107.9 Uganda'], ['RadioEins', 'https://dispatcher.rndfnk.com/rbb/radioeins/live/mp3/mid', 'radio eins | rbb | neuer Stream | niedrige Qualität', 'http://www.radioeins.de/livemp3_s', 'RadioEins'], ['Italo4you', 'https://ssl-1.radiohost.pl:8018/stream', 'Radio Italo4you 64kbps', 'http://s0.radiohost.pl:8018/Italo4you', 'Radio Italo4you'], ['Радио Мегаполис Самара 103.6 FM', 'http://online2.radio-megapolis.ru:8000/megapolis', 'Радио МЕГАПОЛИС', 'http://online.radio-megapolis.ru:8000/megapolis', 'Ð\xa0Ð°Ð´Ð¸Ð¾ Ð\x9cÐµÐ³Ð°Ð¿Ð¾Ð»Ð¸Ñ\x81, Ð¡Ð°Ð¼Ð°Ñ\x80Ð°, 103.6 FM'], ['Gravity Radio 105.3', 'https://01.solumedia.com.ar:8094/stream', 'Gravity Radio', 'https://media.xweb.ar/stream/gravity', 'GRAVITY RADIO ARGENTINA'], ['Radio Effe Italia', 'https://nr11.newradio.it/proxy/sbfsuper?mp=/stream', 'Radio Effe', 'http://nr1.newradio.it:9378/stream', 'Radio Effe Italia'], ['Agnus Rádió -Cluj Napoca 88,3 FM', 'https://agnusradio.ro/radio-stream/', 'Agnus Rádió', 'http://radio2.tirek.hu:8000/agnusradio', 'Agnus Radio 88,3MHz']]
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
 assert a['icy_name'].strip().casefold()==b['icy_name'].strip().casefold() and len(a['icy_name'].strip())>=4
 assert not any(w in a['icy_name'].lower()for w in ['no name','autodj','auto-dj','radiocaster','streammystation','myradio','my radio','securenet','orban','alsolnet','stream name','netcast','unnamed','my station','my server'])
 u=urllib.parse.urlsplit(st['url']);v=urllib.parse.urlsplit(old['station']['url'])
 if u.hostname!=v.hostname:
  assert N==59
  if 'primary_page_observation'in f:
   pp=f['primary_page_observation'];assert pp['station']==st and pp['approved_ref']==old['ref']and pp['exact_new_stream_literal']and pp['http_fetch_exit']==0
   assert pp['page_url']==(old.get('provenance',{}).get('page_final_url')or old.get('provenance',{}).get('page_url'))and st['url']in pp['literal_context']
   req=subprocess.run(['curl','-fLsS','--max-time','35',pp['page_url']],capture_output=True);assert req.returncode==0,('publisher page unavailable',st['name'])
   body=html.unescape(req.stdout.decode('utf8',errors='replace')).replace('\\/','/');assert st['url']in body,('publisher stream changed',st['name'])
  elif st['name']=='RadioEins':
   a_final=urllib.parse.urlsplit(audit[st['url']]['final_url']);b_final=urllib.parse.urlsplit(audit[old['station']['url']]['final_url'])
   assert a_final.hostname.endswith('.rndfnk.com')and b_final.hostname.endswith('.rndfnk.com')and a_final.path=='/ard/rbb/radioeins/live/mp3/128/stream.mp3'and b_final.path=='/ard/rbb/radioeins/live/mp3/48/stream.mp3'
  elif st['name']=='Italo4you':
   assert u.hostname=='ssl-1.radiohost.pl'and v.hostname=='s0.radiohost.pl'and u.port==v.port==8018 and u.path=='/stream'and v.path=='/Italo4you'and a['icy_name']=='Radio Italo4you'
  else:
   assert st['name']=='Радио Мегаполис Самара 103.6 FM'and u.hostname=='online2.radio-megapolis.ru'and v.hostname=='online.radio-megapolis.ru'and u.port==v.port==8000 and u.path==v.path=='/megapolis'

 assert r['ref']==st['reference']and r['station']=={k:st[k]for k in ['name','url','group']}and r['ref']not in cfg['held_references']
 assert all(r[k]==old[k]for k in ['source_commit','variants'])and r['final_visual_approval']['reviewed_variants']==old['variants']
 assert r['asset_root']==old['asset_root'].removesuffix('/verified-assets')
 assert any(w['reference']==r['ref']and all(w[k]==st[k]for k in ['name','url','group'])for w in world)
assert validate_selection(rows,merge_ledgers(paths+[S/'visual-ledger.json.gz']))==len(rows)
baseline_admission.BASELINE_SHA=cfg['baseline_index']['sha256'];raw=(S/'baseline.previous.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==baseline_admission.BASELINE_SHA
new,result=baseline_admission.inspect(rows,raw,Path('/tmp/radio-alias-manifests'));assert len(new)==len(rows)and not result['reused']and not result['held']
proof=dict(status='pass',references=len(rows),png_instances=9*len(rows),explicit_named_endpoint_pairs=len(rows),current_main_exact_service_matches=len(rows),source_hold_exceptions=0,new_renders=0,new_endpoint_requests=0)
(S/'verification-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(proof)
