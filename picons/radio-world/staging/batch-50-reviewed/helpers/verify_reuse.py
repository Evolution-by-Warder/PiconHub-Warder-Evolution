"""Check exact programme membership and immutable already-approved common brand reuse."""
import gzip,hashlib,io,json,re,unicodedata,urllib.parse,urllib.request
from PIL import Image
from baseline_admission import fetch_release
COMMIT='90359d45eb71afb2aa077ac1b5097fae328863df'
def read(p):
 b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def norm(s):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',s.lower()))
def validate_alias(r,o,base):
 assert r['country']=='GR' and o['row']==dict(country='GR',ref=r['ref'],station=r['station'])
 brand=re.fullmatch(r'Radio Art\s*-\s*(.+)',r['station']['name'],flags=re.I);assert brand and r['station']['group']=='Greece'
 assert r['source_commit']==base['source_commit']==COMMIT and r['asset_root']==base['asset_root'] and r['variants']==base['variants'],'Only byte-identical approved common brand allowed'
 assert r['provenance']['approved_source_ref']==base['ref'] and r['provenance']['unchanged_approved_PNGs_reused']
 assert o['approved_brand_source_ref']==base['ref'] and o['approved_brand_source_commit']==COMMIT
 p=o['programme'];assert norm(brand.group(1))==norm(p['name'])==norm(p['official_card_title'])
 assert p['id']==r['provenance']['official_programme_id']
 u=urllib.parse.urlsplit(p['official_player_url']);assert u.scheme=='https' and u.netloc=='www.radioart.com' and u.path=='/radioart-player/play' and urllib.parse.parse_qs(u.query)=={'channel':[p['id']]}
 b=o['stream_binding'];assert o['binding_kind']=='exact_primary_free_stream_field' and b['field']in('livef','streamf') and b['exact_decoded_JSON_equality']
 assert b['text']==r['station']['url'] and b['bytes']==len(b['text'].encode()) and b['sha256']==hashlib.sha256(b['text'].encode()).hexdigest()
 assert r['final_visual_approval']['decision']=='approve' and r['final_visual_approval']['reviewed_variants']==r['variants']
def verify_reuse(rows,source,baseline,cache):
 p=read(source/'source-proof.json');assert p['references']==78 and p['png_instances']==702 and p['unique_existing_approved_PNGs']==9 and p['no_new_PNG_rendered']
 for f,k in [('public-observations.json','public_observations_sha256'),('approved-source-rows.json.gz','approved_source_rows_sha256'),('source-readback-proof.json','readback_proof_sha256')]:assert hashlib.sha256((source/f).read_bytes()).hexdigest()==p[k]
 approved=read(source/'approved-source-rows.json.gz')['entries'];assert len(approved)==8;physical=read(source/'source-readback-proof.json');assert physical['status']=='pass';base=physical['base_approved_row'];assert base in approved
 m=fetch_release(next(c['release']for c in baseline['countries']if c['id']=='GR'),cache)
 for old in approved:
  assert old['country']=='GR' and old['source_commit']==COMMIT and old['variants']==base['variants']
  for key,v in old['variants'].items():
   size,style=key.split('/');assert m['packages'][size][style]['files'][old['ref'].replace(':','_')+'.png']==v[0],'Claimed approved graphic absent from verified baseline'
 facts=read(source/'public-observations.json');assert facts['official_API_path_without_public_client_query']=='https://www.radioart.com/japi/get/radioart/channels/' and facts['official_API_body_sha256']=='cf5aa52090b55fb483b8219d1208bddd448f52dd2dced26809d72e70b18c86ac'
 assert not facts['raw_HTML_JS_API_archive_published'] and not facts['public_player_client_identifier_published'] and not facts['official_card_photographs_used_as_station_logos']
 byref={o['row']['ref']:o for o in facts['entries']};assert len(byref)==len(rows)==78
 for r in rows:validate_alias(r,byref[r['ref']],base)
 assert len(physical['actual_readback'])==9
 for x in physical['actual_readback']:
  key=x['variant'];h,n,bid=base['variants'][key];assert (x['sha256'],x['bytes'],x['git_blob'])==(h,n,bid)
  u='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'+COMMIT+'/'+base['asset_root']+'/verified-assets/'+h+'.png';assert x['url']==u
  raw=urllib.request.urlopen(u,timeout=60).read(n+1);assert len(raw)==n and hashlib.sha256(raw).hexdigest()==h and hashlib.sha1(b'blob '+str(n).encode()+b'\0'+raw).hexdigest()==bid
  im=Image.open(io.BytesIO(raw));assert im.mode=='RGBA' and im.size==tuple(map(int,key.split('/')[0].split('x')));im.verify()
 print('PASS78exactprogrammealiases,8priorapprovedprogrammes,9actualunchangedPNGbodies')
