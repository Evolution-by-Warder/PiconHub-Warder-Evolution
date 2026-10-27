import hashlib,io,json,urllib.request,zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent;REF='17ac58f68dc2016b161790781d6532d859f30c98';REPO='Evolution-by-Warder/FullHDGlass-Warder-Evolution';DIR='assets/warder/downloads/picons/channels/';RAW='https://raw.githubusercontent.com/'+REPO+'/'+REF+'/'
def sha(b):return hashlib.sha256(b).hexdigest()
def get(url):
 return urllib.request.urlopen(urllib.request.Request(url,headers={'Cache-Control':'no-cache'}),timeout=60).read()
def identity(name):
 p=name.removesuffix('.png').split('_')
 if len(p)!=10:raise ValueError(name)
 return '_'.join(format(int(x,16),'X') for x in p[3:6])+('_%X'%(int(p[6],16)>>16))
def visible(im):return sha(str(im.size).encode()+im.convert('RGBA').convert('RGBa').tobytes())
docraw=get(RAW+DIR+'manifest.json');doc=json.loads(docraw);metadata={p['filename']:p for p in doc['parts']}
packages=[p for p in doc['packages'] if p['selector_id'] in ('SKYLINK','CANALPLUS_SK','CANALPLUS_CZ') and p['resolution']=='220x132'];assert len(packages)==9
urls={url for p in packages for url in p['parts']};cache=ROOT/'parts';cache.mkdir(exist_ok=True)
def fetch(url):
 name=url.rsplit('/',1)[-1];meta=metadata[name];path=cache/meta['sha256']
 if path.exists():raw=path.read_bytes()
 else:raw=get(RAW+DIR+name);path.write_bytes(raw)
 assert len(raw)==meta['bytes'] and sha(raw)==meta['sha256'];return url,path
with ThreadPoolExecutor(max_workers=6) as pool:parts=dict(pool.map(fetch,urls))
records=defaultdict(dict);images=defaultdict(dict);stats=[]
for package in packages:
 selector=package['selector_id'];style=package['family'].removeprefix('channel-');raw=b''.join(parts[u].read_bytes() for u in package['parts']);assert len(raw)==package['bytes'] and sha(raw)==package['sha256']
 byid=defaultdict(list)
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert len(z.namelist())==len(set(z.namelist())) and len(z.namelist())==package['png_count']
  for n in z.namelist():
   b=z.read(n);im=Image.open(io.BytesIO(b)).convert('RGBA');key=identity(n);item={'filename':n,'sha256':sha(b),'visible_sha256':visible(im),'dimensions':list(im.size)};byid[key].append(item);images[(selector,style)].setdefault(key,im)
 records[(selector,style)]=dict(byid);stats.append({'selector':selector,'style':style,'files':len(z.namelist()),'service_identities':len(byid),'alias_files':len(z.namelist())-len(byid),'archive_sha256':package['sha256']})
comparisons={};skylink_only_union={};different={}
for style in ('transparent','white','black'):
 sky=records[('SKYLINK',style)];sk=records[('CANALPLUS_SK',style)];cz=records[('CANALPLUS_CZ',style)];union=set(sk)|set(cz)
 for selector,other in [('CANALPLUS_SK',sk),('CANALPLUS_CZ',cz)]:
  common=set(sky)&set(other);diff=[];encoding=[]
  for key in sorted(common):
   a={x['visible_sha256'] for x in sky[key]};b={x['visible_sha256'] for x in other[key]}
   if a!=b:diff.append(key)
   elif {x['sha256'] for x in sky[key]}!={x['sha256'] for x in other[key]}:encoding.append(key)
  comparisons[selector+'/'+style]={'skylink_only':sorted(set(sky)-set(other)),'canal_only':sorted(set(other)-set(sky)),'common':len(common),'different_visible_images':diff,'encoding_only':encoding}
  different[(selector,style)]=diff
 extras=[]
 for key in sorted(set(sky)-union):
  match=[];h={x['visible_sha256'] for x in sky[key]}
  for selector,other in [('CANALPLUS_SK',sk),('CANALPLUS_CZ',cz)]:
   for otherkey,v in other.items():
    if h&{x['visible_sha256'] for x in v}:match.append({'selector':selector,'identity':otherkey})
  extras.append({'identity':key,'same_image_other_reference':match})
 skylink_only_union[style]=extras
report={'schema':1,'skin_commit':REF,'manifest_sha256':sha(docraw),'resolution':'220x132','packages':stats,'comparisons':comparisons,'skylink_only_vs_canal_union':skylink_only_union,'all_records':{sel+'/'+style:r for (sel,style),r in records.items()},'method':'Compare normalized SID/TSID/ONID/orbital namespace identities; separate service-type aliases, PNG encoding differences and visible premultiplied RGBA pixels. No station removal or broadcast validity claim.'}
(ROOT/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
for style in ('transparent','white','black'):
 keys=[x['identity'] for x in skylink_only_union[style]];sheet=Image.new('RGB',(4*240,max(1,(len(keys)+3)//4)*160),(30,39,51));d=ImageDraw.Draw(sheet)
 for i,key in enumerate(keys):
  x,y=(i%4)*240,(i//4)*160;im=images[('SKYLINK',style)][key];im.thumbnail((220,132));sheet.paste(im,(x,y),im);d.text((x,y+135),key,fill='white')
 sheet.save(ROOT/('skylink-only-'+style+'.png'))
for selector in ('CANALPLUS_SK','CANALPLUS_CZ'):
 keys=different[(selector,'black')];pages=[]
 for offset in range(0,len(keys),12):
  subset=keys[offset:offset+12];sheet=Image.new('RGB',(660,max(1,len(subset))*160),(30,39,51));d=ImageDraw.Draw(sheet)
  for i,key in enumerate(subset):
   for col,sel in enumerate(('SKYLINK',selector)):
    im=images[(sel,'black')][key];sheet.paste(im,(col*330,i*160),im)
   d.text((0,i*160+135),key,fill='white')
  sheet.save(ROOT/(selector.lower()+'-different-%02d.png'%(offset//12+1)))
print(json.dumps({'packages':stats,'comparisons':{k:{x:len(v[x]) if isinstance(v[x],list) else v[x] for x in v} for k,v in comparisons.items()},'skylink_only_vs_union':{k:len(v) for k,v in skylink_only_union.items()}},indent=2),flush=True)
