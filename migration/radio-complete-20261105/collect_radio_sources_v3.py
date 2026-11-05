"""Resumeable source acquisition for every Radio catalogue reference.

Inputs are immutable catalogue files and an approved ready-reference seed.
Only sources and candidates are saved. Production packages are never modified.
Downloaded images require assistant visual verification before joining ready PNGs.
Progress commits every 50 candidates make a terminated run resumeable.
"""
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request,urlopen
from concurrent.futures import ThreadPoolExecutor
from PIL import Image,ImageDraw,ImageFont
import argparse, gzip, hashlib, io, json, re, subprocess, tempfile, time, unicodedata

SHA=lambda b:hashlib.sha256(b).hexdigest()
LIMIT=8*1024*1024
def dump(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');t.replace(p)
def get(url,attempts=1,timeout=8):
 p=urlsplit(url)
 if p.scheme not in ('http','https') or not p.hostname or p.username:raise ValueError('unsupported_source_url')
 for attempt in range(attempts):
  try:
   with tempfile.TemporaryDirectory(prefix='radio-source-') as folder:
    target=Path(folder)/'body'
    result=subprocess.run(['curl','--fail','--location','--silent','--show-error','--proto','=http,https','--proto-redir','=http,https','--connect-timeout','3','--max-time',str(timeout),'--max-filesize',str(LIMIT),'--user-agent','Warder-Radio-Logo-Archive/1.0','--output',str(target),'--write-out','%{url_effective}\n%{content_type}',url],capture_output=True,timeout=timeout+2)
    if result.returncode:raise ValueError('HTTP acquisition failed: '+result.stderr.decode(errors='replace')[:200])
    body=target.read_bytes()
    if len(body)>LIMIT:raise ValueError('source_larger_than_8MiB')
    meta=result.stdout.decode(errors='replace').splitlines()
    return body,meta[0] if meta else url,meta[1] if len(meta)>1 else ''
  except Exception:
   if attempt==attempts-1:raise
   time.sleep(attempt+1)
def norm(s):
 s=re.sub(r'^laut\.fm\s*-\s*','',s,flags=re.I)
 return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',s.lower().replace('ł','l')).encode('ascii','ignore').decode())
def lautkey(u):
 p=urlsplit(u);host=p.hostname or '';key=p.path.strip('/')
 return key if (host=='stream.laut.fm' or host.endswith('.stream.laut.fm')) and re.fullmatch('[a-z0-9_-]+',key) else None
def endpoint(u):
 p=urlsplit(u);return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path,p.query,''))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--catalogue',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--masters',type=Path);ap.add_argument('--commit',action='store_true');args=ap.parse_args()
 root=args.output;root.mkdir(parents=True,exist_ok=True)
 ready=set(json.loads((root/'ready-references.json').read_text()))
 receiver=json.load(gzip.open(args.catalogue/'world-radio.receiver.json.gz'));world=json.load(gzip.open(args.catalogue/'world-radio.json.gz'))
 saved=root/'source-acquisition.json';state=json.loads(saved.read_text()) if saved.exists() else {'schema':1,'catalogue_sha256':SHA((args.catalogue/'world-radio.receiver.json.gz').read_bytes()),'project':'Radio plugin','production_changed':False,'stations':{},'errors':[]}
 assert state['catalogue_sha256']==SHA((args.catalogue/'world-radio.receiver.json.gz').read_bytes())
 evidence=root/'evidence';evidence.mkdir(exist_ok=True)
 verifier=None
 if args.masters:
  from verify_radio_wordmarks_v3 import Wordmarks
  verifier=Wordmarks(root,args.masters)
  for row in state['stations'].values():
   if row.get('status')=='ready_verified_official_wordmark' and not row.get('verification',{}).get('website_title_confirmed'):
    row['previous_wordmark_check']=row.pop('verification',{})
    row.pop('renders',None);row['status']='candidate_assistant_identity_and_visual_check'
    verifier.verify(row)
 def checkpoint(event):
  state['counts']={key:sum(r['status']==key for r in state['stations'].values()) for key in sorted({r['status'] for r in state['stations'].values()})}
  state['updated_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime());state['last_event']=event
  dump(saved,state)
  auto_ready=[r for r in state['stations'].values() if r.get('status')=='ready_verified_official_wordmark']
  dump(root/'verified-ready.json',auto_ready)
  journal=root/'acquisition-journal.jsonl'
  with journal.open('a') as f:f.write(json.dumps({'time':state['updated_utc'],'event':event,'counts':state['counts']})+'\n')
  print(event,json.dumps(state['counts']),flush=True)
  if args.commit:
   subprocess.run(['git','add','--',str(root)],check=True)
   if subprocess.run(['git','diff','--cached','--quiet']).returncode:
    subprocess.run(['git','commit','-m','Radio source checkpoint: '+event],check=True)
    subprocess.run(['git','push','origin','HEAD:review/radio-laut-large-batch04-20261105'],check=True)
 def save_image(url):
  raw,final,ctype=get(url);image=Image.open(io.BytesIO(raw));image.load()
  if image.format not in ('PNG','JPEG','WEBP','ICO','GIF'):raise ValueError('unsupported_image_format')
  if image.width<48 or image.height<30:raise ValueError('image_too_small')
  if image.width>8192 or image.height>8192:raise ValueError('image_dimensions_exceed_limit')
  rgba=image.convert('RGBA')
  if rgba.getchannel('A').getbbox() is None:raise ValueError('empty_transparent_image')
  digest=SHA(raw);p=root/'sources'/(digest+'.img');p.parent.mkdir(exist_ok=True)
  if not p.exists():p.write_bytes(raw)
  return dict(url=url,final_url=final,path=str(p.relative_to(root)),sha256=digest,bytes=len(raw),dimensions=list(image.size),format=image.format)
 # Official provider registry proves the exact programme route and image association.
 laut={}
 for station in receiver:
  ref=station['reference']
  if ref in ready:state['stations'][ref]=dict(station,status='already_ready');continue
  if ref in state['stations'] and state['stations'][ref]['status'] not in ('download_failed','registry_request_failed'):continue
  key=lautkey(station['url'])
  if key:laut.setdefault(key,[]).append(station)
 checkpoint('catalogue_and_previous_ready_state_loaded')
 keys=sorted(laut)
 for offset in range(0,len(keys),40):
  chunk=keys[offset:offset+40];url='https://api.laut.fm/stations/'+','.join(chunk)
  try:
   raw,_,_=get(url,attempts=3,timeout=12);rows=json.loads(raw);rows=rows if isinstance(rows,list) else [rows]
   dump(evidence/f'laut-{offset:04d}.json',{'url':url,'response':rows});bykey={x['name']:x for x in rows}
  except Exception as e:
   for key in chunk:
    for s in laut[key]:state['stations'][s['reference']]=dict(s,status='registry_request_failed',reason=str(e)[:300])
   checkpoint(f'laut_registry_failed_{offset}');continue
  def one(key):
   provider=bykey.get(key)
   result=[]
   for s in laut[key]:
    row=dict(s,provider_id=key)
    reason=None
    if provider is None:reason='missing_from_current_provider_registry'
    elif not provider.get('active'):reason='inactive_in_current_provider_registry'
    elif lautkey(provider.get('stream_url',''))!=key:reason='provider_stream_mismatch'
    elif norm(s['name']) not in (norm(key),norm(provider.get('display_name',''))):reason='catalogue_and_provider_names_differ'
    image_url=(provider or {}).get('images',{}).get('station_640x640','')
    if not reason and (urlsplit(image_url).hostname!='assets.laut.fm' or 'e837bb137d5e31a048d55632f3f84394' in image_url):reason='missing_or_generic_provider_image'
    if reason:row.update(status='blocked_identity_or_original',reason=reason)
    else:
     try:
      source=save_image(image_url)
      row.update(status='candidate_assistant_visual_check',identity_method='exact_provider_slug_and_current_programme_name',official_label=provider['display_name'],source=source)
     except Exception as e:row.update(status='download_failed',reason=str(e)[:300],source_url=image_url)
    result.append(row)
   return result
  with ThreadPoolExecutor(6) as pool:
   for result in pool.map(one,chunk):
    for row in result:state['stations'][row['reference']]=row
  checkpoint(f'laut_sources_{min(offset+40,len(keys))}_of_{len(keys)}')
 # Every remaining catalogue item is queued; exact stream matching is mandatory.
 byurl={}
 for station in world:
  for u in [station['url'],*station.get('aliases',[])]:byurl.setdefault(endpoint(u),[]).append(station)
 remaining=[r for r in state['stations'].values() if r.get('status')=='pending_official_homepage_image' or (r.get('status')=='download_failed' and 'provider_id' not in r and r.get('source_url'))]
 for s in receiver:
  if s['reference'] in state['stations']:continue
  matches=byurl.get(endpoint(s['url']),[])
  identities={m['id'] for m in matches}
  row=dict(s,status='blocked_no_verified_original')
  if len(identities)!=1:row['reason']='No unique current station metadata for this exact stream.'
  else:
   m=matches[0];row.update(station_id=m['id'],country=m.get('countrycode') or 'WORLD',homepages=m.get('homepages',[]),candidate_image_urls=m.get('favicons',[]))
   hosts={urlsplit(h).hostname for h in m.get('homepages',[])}
   urls=[u for u in m.get('favicons',[]) if urlsplit(u).scheme in ('http','https') and urlsplit(u).hostname in hosts]
   if urls:row.update(status='pending_official_homepage_image',source_url=urls[0]);remaining.append(row)
   else:row['reason']='No same-origin broadcaster image; directory images require independent broadcaster verification.'
  state['stations'][s['reference']]=row
 checkpoint('all_catalogue_references_queued')
 # Exact same-origin favicon is a candidate, never automatically counted as a logo.
 urls=sorted({r['source_url'] for r in remaining});images={}
 for offset in range(0,len(urls),50):
  chunk=urls[offset:offset+50]
  def acquire(url):
   try:return url,dict(source=save_image(url))
   except Exception as e:return url,dict(reason=str(e)[:300])
  with ThreadPoolExecutor(8) as pool:images.update(pool.map(acquire,chunk))
  for row in remaining:
   result=images.get(row['source_url'])
   if result:
    row.update(result,status='candidate_assistant_identity_and_visual_check' if 'source' in result else 'download_failed')
    if 'source' in result and verifier:verifier.verify(row)
  checkpoint(f'homepage_images_{min(offset+50,len(urls))}_of_{len(urls)}')
 # Candidate sheets support assistant checks without asking the owner for reviews.
 unique={r['source']['sha256']:r for r in state['stations'].values() if 'source' in r}
 rows=list(unique.values())
 for offset in range(0,len(rows),48):
  chunk=rows[offset:offset+48];sheet=Image.new('RGB',(1280,8*145),'#152338');draw=ImageDraw.Draw(sheet)
  for i,row in enumerate(chunk):
   x=(i%6)*212;y=(i//6)*145
   image=Image.open(root/row['source']['path']).convert('RGBA');image.thumbnail((190,105),Image.Resampling.LANCZOS)
   sheet.paste(image,(x+(200-image.width)//2,y),image)
   draw.text((x+4,y+108),row['name'][:30],fill='white');draw.text((x+4,y+124),row['source']['sha256'][:16],fill='#98cddd')
  p=root/'candidate-sheets'/f'page-{offset//48+1:03d}.jpg';p.parent.mkdir(exist_ok=True);sheet.save(p,quality=90)
 checkpoint('source_acquisition_complete_candidates_require_assistant_verification')

if __name__=='__main__':main()
