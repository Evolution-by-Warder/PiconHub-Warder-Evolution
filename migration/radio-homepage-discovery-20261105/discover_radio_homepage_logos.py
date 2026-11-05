"""Find missing Radio logos on the current station website, preserving evidence.

Processes catalogue references with no usable same-origin image URL. A logo is
ready only when its linked station page and image both name the exact station.
No production branches or live packages are modified.
"""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,urljoin,urlunsplit
from concurrent.futures import ThreadPoolExecutor
from PIL import Image,ImageDraw
import argparse,gzip,hashlib,html,io,json,re,subprocess,tempfile,time,unicodedata
SHA=lambda b:hashlib.sha256(b).hexdigest()
PINS={'white':'c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589','black':'61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe'}
DIRECTORIES={'akouradio.com','tunein.com','radio-browser.info','onlineradiobox.com','mytuner-radio.com','streema.com','radioline.co','radio.net','radio.de','onlineradio.de','liveonlineradio.net','radio.garden','facebook.com','twitter.com','x.com','youtube.com','instagram.com','getmeradio.com','radioguide.fm','zeno.fm','laut.fm'}
def directory(u):
 h=(urlsplit(u).hostname or '').lower();return any(h==d or h.endswith('.'+d) for d in DIRECTORIES)
def norm(s):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',s.lower().replace('ł','l')).encode('ascii','ignore').decode())
def distinctive(s):return len(norm(s))>=9 and len(set(norm(s)))>=5 and norm(s) not in {'internetradio','onlineradio','classicrock','radiostation','classicalmusic','radioclassic','relaxingmusic','chilloutmusic','christmasradio'}
def endpoint(u):
 p=urlsplit(u);return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path,p.query,''))
def dump(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');tmp.replace(p)
def fetch(url,limit=4*1024*1024):
 if urlsplit(url).scheme not in ('http','https'):raise ValueError('unsupported_url')
 with tempfile.TemporaryDirectory(prefix='radio-discovery-') as folder:
  p=Path(folder)/'response';r=subprocess.run(['curl','--fail','--silent','--show-error','--location','--proto','=http,https','--proto-redir','=http,https','--connect-timeout','3','--max-time','8','--max-filesize',str(limit),'--user-agent','Warder-Radio-Logo-Archive/1.0','--output',str(p),'--write-out','%{url_effective}',url],capture_output=True,timeout=10)
  if r.returncode:raise ValueError(r.stderr.decode(errors='replace')[:180])
  b=p.read_bytes()
  if len(b)>limit:raise ValueError('source_exceeds_limit')
  return b,r.stdout.decode(errors='replace') or url
class Images(HTMLParser):
 def __init__(self,base):super().__init__();self.base=base;self.items=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs);value=None;priority=9
  if tag=='img' and 'logo' in (' '.join(str(a.get(k,'')) for k in ['alt','class','id','src'])).lower():value=a.get('src') or a.get('data-src');priority=0
  if tag=='link' and 'icon' in a.get('rel','').lower():value=a.get('href');priority=1
  if tag=='meta' and (a.get('property') or a.get('name') or '').lower() in ('og:image','twitter:image'):value=a.get('content');priority=2
  if value:
   u=urljoin(self.base,html.unescape(value))
   if urlsplit(u).scheme in ('http','https') and not directory(u):self.items.append((priority,u))
def titles(body):return [html.unescape(re.sub('<[^>]+>',' ',s)) for s in re.findall(r'<(?:title|h1)\b[^>]*>(.*?)</(?:title|h1)>',body,flags=re.I|re.S)]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--catalogue',type=Path,required=True);ap.add_argument('--masters',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--commit',action='store_true');args=ap.parse_args();root=args.output;root.mkdir(parents=True,exist_ok=True)
 receiver=json.load(gzip.open(args.catalogue/'world-radio.receiver.json.gz'));world=json.load(gzip.open(args.catalogue/'world-radio.json.gz'));ready=set(json.loads((root/'ready-references-seed.json').read_text()))
 masters={'transparent':Image.new('RGBA',(220,132))}
 for style,pin in PINS.items():
  raw=(args.masters/(style+'-sablona.png')).read_bytes();assert SHA(raw)==pin;masters[style]=Image.open(io.BytesIO(raw)).convert('RGBA')
 saved=root/'discovery-state.json';state=json.loads(saved.read_text()) if saved.exists() else {'schema':1,'project':'Radio plugin','production_changed':False,'catalogue_sha256':SHA((args.catalogue/'world-radio.receiver.json.gz').read_bytes()),'stations':{}}
 assert state['catalogue_sha256']==SHA((args.catalogue/'world-radio.receiver.json.gz').read_bytes())
 byurl={}
 for s in world:
  for u in [s['url'],*s.get('aliases',[])]:byurl.setdefault(endpoint(u),[]).append(s)
 queue=[]
 for s in receiver:
  ref=s['reference']
  if ref in state['stations'] and state['stations'][ref].get('status') not in ('pending_homepage_discovery','transient_discovery_error'):continue
  row=dict(s)
  if ref in ready:row['status']='already_ready_in_saved_checkpoint'
  else:
   matches=byurl.get(endpoint(s['url']),[])
   if len({m['id'] for m in matches})!=1:row.update(status='blocked_no_unique_current_station_metadata')
   else:
    m=matches[0];hosts={urlsplit(h).hostname for h in m.get('homepages',[])};existing=[u for u in m.get('favicons',[]) if urlsplit(u).scheme in ('http','https') and urlsplit(u).hostname in hosts]
    pages=[u for u in m.get('homepages',[]) if urlsplit(u).scheme in ('http','https') and not directory(u)]
    row.update(station_id=m['id'],country=m.get('countrycode') or 'WORLD',homepages=pages)
    if existing:row['status']='covered_by_primary_image_acquisition_worker'
    elif not pages:row['status']='blocked_no_independent_station_homepage'
    elif not distinctive(s['name']):row['status']='needs_assistant_identity_research_for_short_or_generic_name'
    else:row['status']='pending_homepage_discovery';queue.append(row)
  state['stations'][ref]=row
 def checkpoint(event):
  counts={k:sum(r['status']==k for r in state['stations'].values()) for k in sorted({r['status'] for r in state['stations'].values()})};state.update(counts=counts,last_event=event,updated_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()));dump(saved,state)
  verified=[r for r in state['stations'].values() if r.get('status')=='ready_verified_homepage_and_wordmark'];dump(root/'verified-ready.json',verified)
  with (root/'discovery-journal.jsonl').open('a') as f:f.write(json.dumps({'time':state['updated_utc'],'event':event,'counts':counts})+'\n')
  print(event,counts,flush=True)
  if args.commit:
   subprocess.run(['git','add','--',str(root)],check=True)
   if subprocess.run(['git','diff','--cached','--quiet']).returncode:
    subprocess.run(['git','commit','-m','Save Radio homepage logo discovery checkpoint: '+event],check=True);subprocess.run(['git','push','origin','HEAD:radio-global-catalogue-20261103'],check=True)
 def render(original):
  mark=original.copy();mark.thumbnail((192,104),Image.Resampling.LANCZOS);pos=((220-mark.width)//2,(132-mark.height)//2);box=(*pos,pos[0]+mark.width,pos[1]+mark.height);variants={}
  for style,background in masters.items():
   canvas=background.copy()
   if style=='transparent':canvas.paste(mark,pos)
   else:canvas.alpha_composite(mark,pos)
   expected=mark if style=='transparent' else Image.alpha_composite(background.crop(box),mark);assert canvas.crop(box).tobytes()==expected.tobytes()
   outside=canvas.copy();unchanged=background.copy()
   for im in [outside,unchanged]:ImageDraw.Draw(im).rectangle((box[0],box[1],box[2]-1,box[3]-1),fill=(0,0,0,0))
   assert outside.tobytes()==unchanged.tobytes()
   for size in ('50x30','220x132','400x240'):
    image=canvas if size=='220x132' else canvas.resize(tuple(map(int,size.split('x'))),Image.Resampling.LANCZOS);buf=io.BytesIO();image.save(buf,'PNG');raw=buf.getvalue();p=root/'verified-assets'/(SHA(raw)+'.png');p.parent.mkdir(exist_ok=True);p.write_bytes(raw)
    with Image.open(io.BytesIO(raw)) as check:assert check.mode=='RGBA' and check.size==tuple(map(int,size.split('x')));check.verify()
    variants[size+'/'+style]=dict(path=str(p.relative_to(root)),sha256=SHA(raw),bytes=len(raw))
  return variants
 def discover(row):
  row=dict(row);errors=[];candidate=None
  for url in row['homepages'][:2]:
   try:
    raw,final=fetch(url,2*1024*1024)
    if directory(final):continue
    body=raw.decode('utf-8',errors='replace');ts=titles(body)
    if not any(norm(row['name']) in norm(t) for t in ts):continue
    parser=Images(final);parser.feed(body);urls=list(dict.fromkeys(u for _,u in sorted(parser.items)))[:3]
    proof=root/'page-evidence'/(SHA(raw)+'.html');proof.parent.mkdir(exist_ok=True);proof.write_bytes(raw)
    page=dict(url=url,final_url=final,sha256=SHA(raw),path=str(proof.relative_to(root)),titles=ts,image_urls=urls)
    for image_url in urls:
     try:
      data,image_final=fetch(image_url);rasterized=None
      if b'<svg' in data[:2000].lower():
       svg=data.decode('utf-8',errors='strict')
       if re.search(r'<(?:image|script)\b|(?:href|xlink:href)\s*=\s*["\x27](?!#)',svg,re.I):raise ValueError('SVG has external or embedded active content')
       if any(not u.strip().strip('"\x27').startswith('#') for u in re.findall(r'url\(([^)]+)\)',svg,re.I)):raise ValueError('SVG resource URLs need independent verification')
       import cairosvg
       rasterized=cairosvg.svg2png(bytestring=data,output_width=640,unsafe=False);original=Image.open(io.BytesIO(rasterized))
      else:original=Image.open(io.BytesIO(data))
      original.load()
      if original.format not in ('PNG','JPEG','WEBP','ICO','GIF') or original.width<96 or original.height<48 or max(original.size)>8192:continue
      rgba=original.convert('RGBA')
      if rgba.getchannel('A').getbbox() is None:continue
      digest=SHA(data);p=root/'originals'/(digest+'.img');p.parent.mkdir(exist_ok=True);p.write_bytes(data);source=dict(url=image_url,final_url=image_final,path=str(p.relative_to(root)),sha256=digest,bytes=len(data),dimensions=list(original.size),format='SVG' if rasterized else original.format)
      if rasterized:
       rp=root/'rasterized'/(SHA(rasterized)+'.png');rp.parent.mkdir(exist_ok=True);rp.write_bytes(rasterized);source['frozen_svg_raster']=dict(path=str(rp.relative_to(root)),sha256=SHA(rasterized),cairosvg_version=cairosvg.__version__)
      check=rgba.copy();check.thumbnail((640,640),Image.Resampling.LANCZOS)
      if max(check.size)<400:check=check.resize((check.width*2,check.height*2),Image.Resampling.LANCZOS)
      bg=Image.new('RGBA',check.size,'white');bg.alpha_composite(check)
      with tempfile.TemporaryDirectory(prefix='radio-logo-ocr-') as folder:
       ip=Path(folder)/'source.png';bg.convert('RGB').save(ip);ocr=subprocess.run(['tesseract',str(ip),'stdout','--psm','11','-l','eng'],capture_output=True,text=True,timeout=10);text=ocr.stdout if ocr.returncode==0 else ''
      if candidate is None:candidate=dict(source=source,page=page,ocr_text=text)
      if norm(row['name']) in norm(text):
       row.update(status='ready_verified_homepage_and_wordmark',source=source,page=page,renders=render(rgba),verification=dict(exact_stream_and_current_page_name=True,image_link_recorded_in_page=True,full_distinctive_wordmark=text,variants_verified=9,whole_original_and_master_outside_logo_preserved=True));return row
     except Exception as e:errors.append(str(e)[:180])
   except Exception as e:errors.append(str(e)[:180])
  if candidate:row.update(status='candidate_assistant_visual_and_identity_check',**candidate)
  else:row.update(status='blocked_no_confirmed_station_page_and_logo',errors=errors)
  return row
 checkpoint('entire_catalogue_evaluated_missing_homepage_logos_queued')
 for offset in range(0,len(queue),25):
  chunk=queue[offset:offset+25]
  with ThreadPoolExecutor(6) as pool:
   for row in pool.map(discover,chunk):state['stations'][row['reference']]=row
  checkpoint(f'homepages_{min(offset+25,len(queue))}_of_{len(queue)}')
 checkpoint('homepage_discovery_completed_with_explicit_unresolved_items')
if __name__=='__main__':main()
