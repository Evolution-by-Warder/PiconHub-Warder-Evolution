import json,io,zipfile,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent;d=json.loads((ROOT/'comparison.json').read_text());ref=d['skin_commit'];doc=json.load(urllib.request.urlopen('https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/'+ref+'/assets/warder/downloads/picons/channels/manifest.json',timeout=30));meta={p['filename']:p for p in doc['parts']};archives={}
def pic(sel,style,key):
 if (sel,style) not in archives:
  p=next(p for p in doc['packages'] if p['selector_id']==sel and p['resolution']=='220x132' and p['family']=='channel-'+style);raw=b''.join((ROOT/'parts'/meta[u.rsplit('/',1)[-1]]['sha256']).read_bytes() for u in p['parts']);archives[(sel,style)]=zipfile.ZipFile(io.BytesIO(raw))
 rec=d['all_records'][sel+'/'+style][key][0];return Image.open(io.BytesIO(archives[(sel,style)].read(rec['filename']))).convert('RGBA')
keys=d['comparisons']['CANALPLUS_SK/transparent']['different_visible_images'];sheet=Image.new('RGB',(660,len(keys)*160),(30,39,51));draw=ImageDraw.Draw(sheet)
for i,key in enumerate(keys):
 for col,sel in enumerate(('SKYLINK','CANALPLUS_SK')):
  im=pic(sel,'transparent',key);sheet.paste(im,(col*330,i*160),im)
 draw.text((0,i*160+135),key,fill='white')
sheet.save(ROOT/'transparent-differences.png')
keys=d['comparisons']['CANALPLUS_SK/transparent']['canal_only'];sheet=Image.new('RGB',(960,((len(keys)+3)//4)*160),(30,39,51));draw=ImageDraw.Draw(sheet)
for i,key in enumerate(keys):
 im=pic('CANALPLUS_SK','transparent',key);x=(i%4)*240;y=(i//4)*160;sheet.paste(im,(x,y),im);draw.text((x,y+135),key,fill='white')
sheet.save(ROOT/'canal-only-transparent.png')
keys=sorted(set(d['all_records']['CANALPLUS_SK/black'])-set(d['all_records']['CANALPLUS_SK/transparent']));sheet=Image.new('RGB',(480,160),(30,39,51));draw=ImageDraw.Draw(sheet)
for i,key in enumerate(keys):
 im=pic('CANALPLUS_SK','black',key);sheet.paste(im,(i*240,0),im);draw.text((i*240,135),key,fill='white')
sheet.save(ROOT/'canal-sk-black-only.png')
print('Detailed source galleries ready; no published assets modified.')

for selector in ('CANALPLUS_SK','CANALPLUS_CZ'):
 keys=d['comparisons'][selector+'/transparent']['skylink_only']
 for off in range(0,len(keys),20):
  subset=keys[off:off+20];sheet=Image.new('RGB',(960,((len(subset)+3)//4)*160),(30,39,51));draw=ImageDraw.Draw(sheet)
  for i,key in enumerate(subset):
   im=pic('SKYLINK','transparent',key);x=(i%4)*240;y=(i//4)*160;sheet.paste(im,(x,y),im);draw.text((x,y+135),key,fill='white')
  sheet.save(ROOT/(selector.lower()+'-skylink-only-%02d.png'%(off//20+1)))
