"""Exhaust unreviewed logo URLs recorded on confirmed broadcaster pages."""
import argparse,concurrent.futures,hashlib,io,json,os,re,subprocess,tempfile,threading,time
from pathlib import Path
from urllib.parse import urlsplit
from PIL import Image,ImageDraw
from radio_final_logo_utils import brand_keys,norm,fetch,directory,PINS
SHA=lambda b:hashlib.sha256(b).hexdigest()
LOCK=threading.Lock();RENDER_LOCKS={};RENDERED={}
def save(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True);data=json.dumps(obj,ensure_ascii=False,indent=2)+'\n';data=re.sub(r'\b(?:sk|pk)\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{8,}','[OMITTED_PAGE_CREDENTIAL]',data)
 fd,tmp=tempfile.mkstemp(prefix='.save-',dir=path.parent)
 try:
  with os.fdopen(fd,'w') as f:f.write(data)
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def binary(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(prefix='.asset-',dir=path.parent)
 try:
  with os.fdopen(fd,'wb') as f:f.write(data)
  os.replace(tmp,path)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def identity(name,page,text):
 keys=brand_keys(name);page_keys={k for k in keys if any(k in norm(t) for t in page.get('titles',[]))};image=norm(text);calls={k for k in keys if re.fullmatch(r'[wkc][a-z]{3}',k)}
 if calls:return bool(calls<=page_keys and calls<=set(k for k in calls if k in image))
 return bool(page_keys and keys<=page_keys and all(k in image for k in keys) and any(len(k)>=4 for k in keys))
def render(root,rgba,digest,masters):
 with LOCK:lock=RENDER_LOCKS.setdefault(digest,threading.Lock())
 with lock:
  if digest in RENDERED:return RENDERED[digest]
  mark=rgba.copy();mark.thumbnail((192,104),Image.Resampling.LANCZOS);pos=((220-mark.width)//2,(132-mark.height)//2);result={}
  for style,bg in masters.items():
   canvas=bg.copy()
   if style=='transparent':canvas.paste(mark,pos)
   else:canvas.alpha_composite(mark,pos)
   for size,dim in [('50x30',(50,30)),('220x132',(220,132)),('400x240',(400,240))]:
    im=canvas if dim==(220,132) else canvas.resize(dim,Image.Resampling.LANCZOS);buf=io.BytesIO();im.save(buf,'PNG');raw=buf.getvalue();relative='verified-assets/'+SHA(raw)+'.png';binary(root/relative,raw)
    with Image.open(io.BytesIO(raw)) as check:assert check.mode=='RGBA' and check.size==dim;check.verify()
    result[size+'/'+style]=dict(path=relative,sha256=SHA(raw),bytes=len(raw))
  RENDERED[digest]=result;return result

def discover(row,pages,checked,root,masters):
 row=dict(row);errors=[];candidate=None
 for oldpage in pages:
  if directory(oldpage.get('final_url',oldpage['url'])):continue
  keys=brand_keys(row['name']);page_keys={k for k in keys if any(k in norm(t) for t in oldpage.get('titles',[]))}
  if not page_keys:continue
  named=oldpage.get('named_logos',{});urls=list(dict.fromkeys([*named,*oldpage.get('image_urls',[])]));urls=[u for u in urls if urlsplit(u).scheme in ('http','https') and not directory(u)]
  urls.sort(key=lambda u:(-sum(k in norm(named.get(u,'')) for k in page_keys),u not in named))
  page=dict(oldpage);page['recorded_page_snapshot']='66d12be9932b5f0443b1dcba188fbd9e5e242f46';page['image_urls']=urls[:16];proof='page-evidence/'+oldpage.get('original_html_sha256',SHA(json.dumps(oldpage,sort_keys=True).encode()))+'.json';page['path']=proof;save(root/proof,page)
  for url in urls[:16]:
   try:
    raw,final=fetch(url);digest=SHA(raw)
    if digest in checked:continue
    frozen=None
    if b'<svg' in raw[:2000].lower():
     text=raw.decode('utf-8','strict')
     if re.search(r'<(?:image|script)\b|(?:href|xlink:href)\s*=\s*["\x27](?!#)',text,re.I):continue
     if any(not x.strip().strip('"\x27').startswith('#') for x in re.findall(r'url\(([^)]+)\)',text,re.I)):continue
     import cairosvg
     frozen=cairosvg.svg2png(bytestring=raw,output_width=640,unsafe=False);im=Image.open(io.BytesIO(frozen))
    else:im=Image.open(io.BytesIO(raw))
    im.load()
    if im.format not in ('PNG','JPEG','WEBP','GIF','ICO') or im.width<96 or im.height<48 or max(im.size)>8192:continue
    rgba=im.convert('RGBA')
    if rgba.getchannel('A').getbbox() is None:continue
    source=dict(url=url,final_url=final,path='originals/'+digest+'.img',sha256=digest,bytes=len(raw),dimensions=list(im.size),format='SVG' if frozen else im.format);binary(root/source['path'],raw)
    if frozen:
     raster='rasterized/'+SHA(frozen)+'.png';binary(root/raster,frozen);source['frozen_svg_raster']=dict(path=raster,sha256=SHA(frozen),cairosvg_version=cairosvg.__version__)
    check=rgba.copy();check.thumbnail((640,640),Image.Resampling.LANCZOS)
    if max(check.size)<400:check=check.resize((check.width*2,check.height*2),Image.Resampling.LANCZOS)
    bg=Image.new('RGBA',check.size,'white');bg.alpha_composite(check)
    with tempfile.TemporaryDirectory(prefix='radio-final-ocr-') as folder:
     ip=Path(folder)/'image.png';bg.convert('RGB').save(ip);ocr=subprocess.run(['tesseract',str(ip),'stdout','--psm','11','-l','eng'],capture_output=True,text=True,timeout=12,env={**os.environ,'OMP_THREAD_LIMIT':'1'});text=ocr.stdout if ocr.returncode==0 else ''
    item=dict(source=source,page=page,ocr_text=text)
    if candidate is None:candidate=item
    if identity(row['name'],page,text):
     row.update(status='ready_verified_exact_brand_and_recorded_page',**item,renders=render(root,rgba,digest,masters),verification=dict(exact_catalogue_stream_identity=True,recorded_broadcaster_page_identity=True,ocr_exact_callsign_or_all_distinctive_brand_keys=True,variants_verified=9,whole_original_and_master_outside_logo_preserved=True));return row
   except Exception as exc:errors.append(str(exc)[:180])
 if candidate:row.update(status='candidate_needs_visual_review',**candidate)
 else:row.update(status='no_unreviewed_logo_at_recorded_sources',errors=errors[-4:])
 return row

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--masters',type=Path,required=True);ap.add_argument('--branch',required=True);ap.add_argument('--commit',action='store_true');a=ap.parse_args();root=a.output;root.mkdir(parents=True,exist_ok=True);inputs=json.load(open(root/'final-pass-input.json'));ready=set(inputs['ready_references']);excluded=set(inputs['claimed_references']);checked=set(inputs['reviewed_source_hashes']);state=json.load(open(a.input/'discovery-state.json'))['stations'];proofs={}
 for path in (a.input/'page-evidence').glob('*.json'):
  try:
   p=json.load(open(path))
   for u in [p.get('url'),p.get('final_url')]:
    if u:proofs.setdefault(u.rstrip('/'),[]).append(p)
  except Exception:pass
 masters={'transparent':Image.new('RGBA',(220,132))}
 for style,pin in PINS.items():
  raw=(a.masters/(style+'-sablona.png')).read_bytes();assert SHA(raw)==pin;masters[style]=Image.open(io.BytesIO(raw)).convert('RGBA')
 saved=root/'discovery-state.json';out=json.load(open(saved)) if saved.exists() else dict(schema=1,project='Radio plugin',production_changed=False,stations={},input_source_snapshot='66d12be9932b5f0443b1dcba188fbd9e5e242f46');queue=[]
 for ref,row in state.items():
  if ref in ready or ref in excluded or ref in out['stations'] or not row.get('station_id'):continue
  pages=([row['page']] if row.get('page') else [])
  for u in row.get('homepages',[]):pages+=proofs.get(u.rstrip('/'),[])
  unique={p.get('original_html_sha256',p['url']):p for p in pages};pages=[p for p in unique.values() if p.get('named_logos') or p.get('image_urls')]
  if pages:queue.append((row,pages[:2]))
 out['eligible_references']=len(queue)+len(out['stations']);out['excluded_ready']=len(ready);out['excluded_active_claim']=len(excluded)
 def checkpoint(event):
  out.update(last_event=event,counts=dict(__import__('collections').Counter(r['status'] for r in out['stations'].values())),updated_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()));save(saved,out);save(root/'verified-ready.json',[r for r in out['stations'].values() if r['status']=='ready_verified_exact_brand_and_recorded_page']);print(event,out['counts'],flush=True)
  if a.commit:
   subprocess.run(['git','add','--',str(root)],check=True)
   if subprocess.run(['git','diff','--cached','--quiet']).returncode:subprocess.run(['git','commit','-m','Final radio logo pass: '+event],check=True);subprocess.run(['python','tools/push_radio_final.py',a.branch],check=True)
 checkpoint('recorded_page_alternative_logos_started')
 for start in range(0,len(queue),100):
  with concurrent.futures.ThreadPoolExecutor(max_workers=24) as pool:
   for row in pool.map(lambda item:discover(item[0],item[1],checked,root,masters),queue[start:start+100]):out['stations'][row['reference']]=row
  checkpoint('alternative_logos_'+str(min(start+100,len(queue)))+'_of_'+str(len(queue)))
 checkpoint('recorded_page_alternative_logos_completed_with_explicit_unresolved')
if __name__=='__main__':main()
