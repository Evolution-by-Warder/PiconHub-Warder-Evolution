"""Conservative verification of wordmarks linked from a station's own domain.

No name inference: the complete distinctive catalogue station name must appear
in OCR of its own image. Unconfirmed artwork remains a candidate.
"""
from pathlib import Path
from PIL import Image,ImageDraw
import hashlib,html,io,json,re,subprocess,tempfile,unicodedata
from urllib.parse import urlsplit
SHA=lambda b:hashlib.sha256(b).hexdigest()
PINS={'white':'c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589','black':'61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe'}
def norm(s):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',s.lower().replace('ł','l')).encode('ascii','ignore').decode())
def distinctive(name):
 n=norm(name)
 return len(n)>=9 and len(set(n))>=5 and n not in {'internetradio','onlineradio','classicrock','radiostation','classicalmusic','radioclassic','radioclassical','relaxingmusic','chilloutmusic','christmasradio'}
DIRECTORIES={'akouradio.com','tunein.com','radio-browser.info','onlineradiobox.com','mytuner-radio.com','streema.com','radioline.co','radio.net','radio.de','onlineradio.de','liveonlineradio.net','radio.garden','facebook.com','twitter.com','x.com','youtube.com','instagram.com','getmeradio.com','radioguide.fm'}
def directory_host(url):
 host=(urlsplit(url).hostname or '').lower()
 return any(host==d or host.endswith('.'+d) for d in DIRECTORIES)
class Wordmarks:
 def __init__(self,root,masters):
  self.root=root;self.ocr={};self.renders={};self.pages={};self.masters={'transparent':Image.new('RGBA',(220,132))}
  for style,pin in PINS.items():
   p=masters/(style+'-sablona.png');raw=p.read_bytes();assert SHA(raw)==pin
   self.masters[style]=Image.open(io.BytesIO(raw)).convert('RGBA')
 def verify(self,row):
  if not distinctive(row['name']):return False
  if directory_host(row['source']['url']):return False
  source=row['source'];digest=source['sha256'];raw=(self.root/source['path']).read_bytes();assert SHA(raw)==digest
  original=Image.open(io.BytesIO(raw)).convert('RGBA')
  if original.width<96 or original.height<48 or original.width/original.height>6 or original.height/original.width>6:return False
  if digest not in self.ocr:
   # OCR inspection uses a white backing only; generated assets preserve the original.
   inspect=original.copy();inspect.thumbnail((640,640),Image.Resampling.LANCZOS)
   if max(inspect.size)<400:inspect=inspect.resize((inspect.width*2,inspect.height*2),Image.Resampling.LANCZOS)
   backing=Image.new('RGBA',inspect.size,'white');backing.alpha_composite(inspect)
   with tempfile.TemporaryDirectory(prefix='radio-wordmark-') as folder:
    p=Path(folder)/'inspect.png';backing.convert('RGB').save(p)
    try:
     r=subprocess.run(['tesseract',str(p),'stdout','--psm','11','-l','eng'],capture_output=True,text=True,timeout=10)
     self.ocr[digest]=r.stdout if r.returncode==0 else ''
    except subprocess.TimeoutExpired:self.ocr[digest]=''
  text=self.ocr[digest]
  if norm(row['name']) not in norm(text):return False
  # Require the current page itself to identify the same station in a title/H1.
  host=urlsplit(source['url']).hostname
  pages=[u for u in row.get('homepages',[]) if urlsplit(u).hostname==host and not directory_host(u)]
  confirmed=None
  for url in pages[:2]:
   if url not in self.pages:
    try:
     page=subprocess.run(['curl','--fail','--location','--silent','--show-error','--proto','=http,https','--proto-redir','=http,https','--connect-timeout','3','--max-time','8','--max-filesize','2097152',url],capture_output=True,timeout=10)
     body=page.stdout.decode('utf-8',errors='replace') if page.returncode==0 else ''
     self.pages[url]=[html.unescape(re.sub('<[^>]+>',' ',s)) for s in re.findall(r'<(?:title|h1)\b[^>]*>(.*?)</(?:title|h1)>',body,flags=re.I|re.S)]
    except subprocess.TimeoutExpired:self.pages[url]=[]
   if any(norm(row['name']) in norm(s) for s in self.pages[url]):confirmed=url;break
  if not confirmed:return False
  if digest not in self.renders:
   mark=original.copy();mark.thumbnail((192,104),Image.Resampling.LANCZOS);pos=((220-mark.width)//2,(132-mark.height)//2)
   box=(*pos,pos[0]+mark.width,pos[1]+mark.height);variants={}
   for style,background in self.masters.items():
    canvas=background.copy()
    if style=='transparent':canvas.paste(mark,pos)
    else:canvas.alpha_composite(mark,pos)
    expected=mark if style=='transparent' else Image.alpha_composite(background.crop(box),mark)
    assert canvas.crop(box).tobytes()==expected.tobytes()
    outside=canvas.copy();unchanged=background.copy()
    for im in [outside,unchanged]:ImageDraw.Draw(im).rectangle((box[0],box[1],box[2]-1,box[3]-1),fill=(0,0,0,0))
    assert outside.tobytes()==unchanged.tobytes()
    for size in ('50x30','220x132','400x240'):
     final=canvas if size=='220x132' else canvas.resize(tuple(map(int,size.split('x'))),Image.Resampling.LANCZOS)
     buf=io.BytesIO();final.save(buf,'PNG');body=buf.getvalue();p=self.root/'verified-assets'/(SHA(body)+'.png');p.parent.mkdir(exist_ok=True);p.write_bytes(body)
     with Image.open(io.BytesIO(body)) as check:assert check.mode=='RGBA' and check.size==tuple(map(int,size.split('x')));check.verify()
     variants[size+'/'+style]=dict(path=str(p.relative_to(self.root)),sha256=SHA(body),bytes=len(body))
   self.renders[digest]=variants
  row.update(status='ready_verified_official_wordmark',renders=self.renders[digest],verification={'identity':'unique exact stream in current catalogue','provenance':'same-origin station image and current matching station title/H1; known directory hosts excluded','website_title_confirmed':True,'confirmed_homepage':confirmed,'website_titles':self.pages[confirmed],'wordmark':'complete distinctive catalogue name confirmed in source image','ocr_text':text,'whole_original_and_master_outside_logo_preserved':True,'png_variants_verified':9,'physical_receiver_tested':False})
  return True
