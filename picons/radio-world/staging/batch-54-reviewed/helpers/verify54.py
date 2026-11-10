"""Admit only exact publisher programme paths supported by a newer immutable audio/ICY audit."""
import gzip,hashlib,json,re,sys,unicodedata,urllib.parse
from pathlib import Path
S=Path(__file__).resolve().parents[1];R=S.parents[1];N=int(S.name.split('-')[1]);sys.path.insert(0,str(R/'tools'))
from visual_gate import read,merge_ledgers,validate_selection
from saved_artwork_import import get
sys.path.insert(0,str(S.parent/'batch-50-reviewed/helpers'));import baseline_admission
cfg=read(S/'configuration.json');facts=read(S/'source-inputs/public-observations.json');rows=read(S/'selection.json.gz')['entries'];base=read(S.parent/'batch-50-reviewed/selection.json.gz')['entries'][0]
assert cfg['references']==len(rows)=={54:43,55:12}[N]
baseline_admission.BASELINE_SHA=cfg['baseline_index']['sha256'];assert hashlib.sha256((S/'baseline.previous.json').read_bytes()).hexdigest()==baseline_admission.BASELINE_SHA
assert facts['official_API_body_sha256']=='cf5aa52090b55fb483b8219d1208bddd448f52dd2dced26809d72e70b18c86ac' and facts['no_new_endpoint_requests']
assert facts['stream_audit']['url']=='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/2b294878b14ca322fa277ba1e9781f83ec5649cf/picons/IPTV-SK-CZ/catalog/global/stream-audit.json.gz'
audit=json.loads(gzip.decompress(get(facts['stream_audit'])))['checks'];world=json.loads(gzip.decompress(get(facts['current_world'])))
original=read(S.parent/'batch-50-reviewed/results/next-source-observations.json.gz')
original_rows=[e['station']for e in original['remaining_legacy_URI_checks']['entries']]if N==54 else original['remaining_name_unmatched']['station_rows']
def norm(s):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',s.lower().replace('&','and')))
for r,f in zip(rows,facts['entries']):
 st=f['station'];p=f['programme'];a=f['stream_audit'];assert st in original_rows and st['reference']==r['ref']==f['reference'] and r['station']=={k:st[k]for k in ['name','url','group']}
 assert a==audit[st['url']] and a['url']==a['final_url']==st['url'] and a['status']=='audio-confirmed' and a['http_status']==200 and a['content_type'].startswith('audio/')
 assert a['checked_at'].startswith('2026-11-08T11:') and a['sample_bytes']>0 and len(a['sample_sha256'])==64
 u=urllib.parse.urlsplit(st['url']);assert u.hostname in ['live.radioart.com','air-tunein.radioart.com','air.radioart.com'] and u.scheme in ['http','https'] and u.query in ['','dlid=']
 assert u.path==urllib.parse.urlsplit(p['streamf']).path=='/f'+p['suburl']+'.mp3'
 expected={norm(p['name']),norm(p['suburl'])}
 if N==55 and p['id']=='63':
  assert p['name']=='Johann S. Bach' and p['suburl']=='Bach';expected.add(norm('J.S. Bach'))
 icy=re.sub(r'^radio\s*art\s*[-:]?\s*','',a.get('icy_name',''),flags=re.I);aliases={norm(icy)}
 try:aliases.add(norm(icy.encode('latin1').decode('utf8')))
 except UnicodeError:pass
 assert aliases&expected and sorted(aliases&expected)==f['accepted_ICY_normalizations']
 if N==54:
  old=next(e for e in original['remaining_legacy_URI_checks']['entries']if e['station']==st)
  assert all(p[k]==old['programme'][k]for k in ['id','name','suburl','streamf'])
 assert r['country']=={'Greece':'GR','United States':'US'}[st['group']] and any(w['reference']==r['ref']and all(w[k]==st[k]for k in ['name','url','group'])for w in world)
 assert r['source_commit']==base['source_commit']=='90359d45eb71afb2aa077ac1b5097fae328863df' and r['asset_root']==base['asset_root'] and r['variants']==base['variants'] and r['final_visual_approval']['reviewed_variants']==base['variants']
 assert r['ref']not in cfg['held_references'] and r['provenance']['official_programme_id']==p['id']
paths=[R/'staging/source-ledger-reviewed-20261107/visual-ledger.json.gz',R/'staging/visual-review-34-36/decisions.json.gz']+[R/f'staging/batch-{n}-reviewed/visual-ledger.json.gz'for n in range(39,N+1)]
assert validate_selection(rows,merge_ledgers(paths))==len(rows)
new,result=baseline_admission.inspect(rows,(S/'baseline.previous.json').read_bytes(),Path('/tmp/radio-legacy-manifests'));assert len(new)==len(rows)and not result['reused']and not result['held']
proof=dict(status='pass',references=len(rows),png_instances=9*len(rows),unchanged_approved_variants=9,exact_publisher_path_and_ICY_matches=len(rows),current_main_exact_service_matches=len(rows),historical_ledgers=len(paths),source_hold_exceptions=0,new_endpoint_requests=0)
(S/'verification-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(proof)
