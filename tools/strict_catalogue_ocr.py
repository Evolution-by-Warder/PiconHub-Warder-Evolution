"""Accept only an exact wordmark on the station's own attributed image host."""
import argparse,base64,gzip,hashlib,io,json,os,re,subprocess,tempfile,time,unicodedata
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
from PIL import Image,ImageStat
from final_logo_pass import render,save,PINS,SHA,directory
COMMON={'radio','radyo','fm','am','www','com','net','org','aac','flac','mp3','kbps','mhz','khz','live','stream','online','music','the','and','classic','classical','jazz','rock','pop','dance','country','news','talk','best','hits','oldies','stereo','christian','internet','relax','lounge','blues','soul','house','sport','sports','city','club','digital','smooth','station','channel','playlist','hd'}
def words(text):
 text=''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if not unicodedata.combining(c))
 return set(re.findall(r'[^\W_]+',text,flags=re.U))
def host(url):return (urlsplit(url).hostname or '').lower().removeprefix('www.')
def same_owner(row):
 src=row['source'];hosts=[host(src['url']),host(src['final_url'])]
 for homepage in row.get('homepages',[]):
  base=host(homepage)
  if not base or '.' not in base or directory(homepage):continue
  if all(h==base or h.endswith('.'+base) for h in hosts):return True
 return False
def identity(name,text,country="US"):
 w=words(text);forbidden={'paypal','facebook','youtube','tunein','radioking','radiobrowser','shoutcast','icecast'}
 if w&forbidden:return False
 calls=set(re.findall(r'\b[WK][A-Z]{3}\b',name)) if country=='US' else set(re.findall(r'\bC[FIHJK][A-Z]{2}\b',name)) if country=='CA' else set()
 if calls:return all(c.casefold() in w for c in calls)
 keys={k for k in words(name) if k not in COMMON and len(k)>=3 and not k.isdigit() and not re.fullmatch(r'\d+s',k)}
 return bool(keys and keys<=w and (any(len(k)>=10 for k in keys) or len(keys)>=2 and sum(map(len,keys))>=10))
def check(row,base,root,masters):
 row=dict(row);src=row['source'];proof=row.get('catalogue_evidence',{})
 if not(row.get('station_id') and proof.get('catalogue_station_id')==row['station_id'] and proof.get('exact_receiver_reference')==row['reference'] and proof.get('exact_receiver_stream')==row['url']):return dict(reference=row['reference'],status='pending_exact_programme_evidence')
 if not same_owner(row):return dict(reference=row['reference'],status='pending_manual_review_source_host')
 try:
  raw=(base/src['path']).read_bytes();assert SHA(raw)==src['sha256'];raster=src.get('frozen_svg_raster',src);raw=(base/raster['path']).read_bytes();assert SHA(raw)==raster['sha256'];rgba=Image.open(io.BytesIO(raw)).convert('RGBA');im=rgba.copy();im.thumbnail((800,800),Image.Resampling.LANCZOS)
  if max(im.size)<400:im=im.resize((im.width*2,im.height*2),Image.Resampling.LANCZOS)
  brightness=sum(ImageStat.Stat(im.convert('RGB'),mask=im.getchannel('A')).mean);bg=Image.new('RGBA',im.size,'black' if brightness>540 else 'white');bg.alpha_composite(im)
  with tempfile.TemporaryDirectory(prefix='radio-strict-') as d:
   f=Path(d)/'logo.png';bg.convert('RGB').save(f);r=subprocess.run(['tesseract',str(f),'stdout','--psm','11','-l','eng'],capture_output=True,text=True,timeout=15,env={**os.environ,'OMP_THREAD_LIMIT':'1'});text=r.stdout if r.returncode==0 else ''
  if not identity(row['name'],text,row.get('country')):return dict(reference=row['reference'],source_sha256=src['sha256'],status='pending_manual_visual_identity',ocr_text=text)
  row.update(status='ready_strict_catalogue_wordmark_and_owned_image_host',ocr_text=text,renders=render(root,rgba,src['sha256'],masters),asset_root=str(root),source_asset_root=str(base),verification=dict(exact_frozen_programme_id_reference_and_stream=True,image_original_and_final_host_match_frozen_station_homepage=True,exact_callsign_or_full_distinctive_multitoken_wordmark_in_logo=True,known_platform_wordmarks_rejected=True,current_homepage_not_confirmed=True,whole_original_colours_and_master_pixels_preserved=True,variants_verified=9));return row
 except Exception as e:return dict(reference=row['reference'],status='pending_manual_processing',error=str(e)[:200])
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--branch',required=True);a=ap.parse_args();root=a.output;root.mkdir(exist_ok=True);seed=json.loads(gzip.decompress(base64.b64decode((root/'seed.b64').read_bytes())));ready=set(seed['ready_references']);excluded=set(seed['excluded_references']);known=set(seed['reviewed_and_claimed_source_hashes']);state=json.load(open(a.base/'discovery-state.json'))['stations'];masters={'transparent':Image.new('RGBA',(220,132))}
 for st,pin in PINS.items():
  raw=(Path('plugin/artwork/templates/picons')/(st+'-sablona.png')).read_bytes();assert SHA(raw)==pin;masters[st]=Image.open(io.BytesIO(raw)).convert('RGBA')
 queue=[r for ref,r in state.items() if ref not in ready|excluded and r.get('status')=='candidate_catalogue_artwork_needs_visual_identity' and r['source']['sha256'] not in known];out=dict(schema=1,project='Radio plugin',production_changed=False,source_snapshot=seed['source_snapshot'],eligible_references=len(queue),stations={})
 subprocess.run(['git','config','user.name','Warder Radio artwork automation'],check=True);subprocess.run(['git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com'],check=True)
 for start in range(0,len(queue),100):
  with ThreadPoolExecutor(max_workers=12) as pool:
   for row in pool.map(lambda row:check(row,a.base,root,masters),queue[start:start+100]):out['stations'][row['reference']]=row
  out.update(last_event='strict_screen_'+str(min(start+100,len(queue)))+'_of_'+str(len(queue)),counts=dict(__import__('collections').Counter(r['status'] for r in out['stations'].values())));save(root/'screen-state.json',out);save(root/'verified-ready.json',[r for r in out['stations'].values() if r['status']=='ready_strict_catalogue_wordmark_and_owned_image_host']);print(out['last_event'],out['counts'],flush=True);subprocess.run(['git','add','--',str(root)],check=True)
  if subprocess.run(['git','diff','--cached','--quiet']).returncode:subprocess.run(['git','commit','-m',out['last_event']],check=True);subprocess.run(['python','tools/push_radio_final.py',a.branch],check=True)
 save(root/'completion.json',dict(complete=True,eligible_references=len(queue),counts=out.get('counts',{}),production_changed=False,unaccepted_items_remain_candidates=True));subprocess.run(['git','add','--',str(root)],check=True);subprocess.run(['git','commit','-m','Complete strict Radio catalogue wordmark screen'],check=True);subprocess.run(['python','tools/push_radio_final.py',a.branch],check=True)
if __name__=='__main__':main()
