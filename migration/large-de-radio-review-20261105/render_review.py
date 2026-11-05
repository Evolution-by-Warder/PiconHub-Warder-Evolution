"""Reproduce the review PNGs offline, retaining complete broadcaster images.

Requires Pillow 13.0.0 for the pinned PNG bytes. Run:
  python render_review.py --output /temporary/review --verify
Only --record updates the review manifest. This script cannot publish data.
"""
from pathlib import Path
import argparse, csv, gzip, hashlib, io, json
from PIL import Image, ImageDraw, ImageFont, features, ImageChops

ROOT=Path(__file__).resolve().parent
SHA=lambda b:hashlib.sha256(b).hexdigest()
PINS={'white':'c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589','black':'61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe'}
STYLES=('transparent','white','black')
SIZES=((50,30),(220,132),(400,240))

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--output',type=Path,required=True)
 parser.add_argument('--record',action='store_true')
 parser.add_argument('--verify',action='store_true')
 args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
 assert Image.__version__=='13.0.0','Use the recorded Pillow version for exact PNG bytes.'
 assert features.version_module('webp')=='1.6.0','Use the recorded libwebp decoder version.'
 plan=json.loads((ROOT/'source-plan.json').read_text())
 assert plan['production_changed'] is False and len(plan['source_artwork'])==plan['counts']['original_programme_tiles']
 cat_raw=(ROOT/'evidence/catalogue-DE.json.gz').read_bytes();assert SHA(cat_raw)==plan['catalogue_sha256']
 catalogue=json.loads(gzip.decompress(cat_raw))
 baseline=(ROOT/'evidence/production-release-baseline.json').read_bytes();assert SHA(baseline)==plan['production_release_sha256']
 prior=set(json.loads(baseline)['packages']['220x132']['transparent']['files'])
 evidence={}
 for filename,pin in plan['evidence_json_sha256'].items():
  raw=(ROOT/'evidence'/filename).read_bytes();assert SHA(raw)==pin;evidence[filename]=json.loads(raw)
 for page in plan['source_pages'].values():assert SHA((ROOT/page['path']).read_bytes())==page['sha256']
 publishers=evidence['publisher-programmes.json']
 publisher_assets={r['slug']:r for r in plan['source_artwork']}
 for source in plan['source_artwork']:
  if source['family']=='BOB':
   blocks=[p for p in publishers['BOB'] if p['image_url']==source['url'] and p['label']==source['name']]
   assert len(blocks)==1 and source['official_stream_url'] in blocks[0]['stream_urls']
  else:
   tiles=[p for p in publishers['ON_and_1A_tiles'] if p['key']==source['key']]
   assert len(tiles)==1 and tiles[0]['label']==source['name'] and tiles[0]['image_url']==source['url']
   raw=(ROOT/source['config_path']).read_bytes();assert SHA(raw)==source['config_sha256']
   config=json.loads(raw.decode(source['config_encoding']));assert config['title']==source['published_json_title'] and config['mp3SSL']==source['official_stream_url']
   for key in ['mp3','mp3SSL','aac','aacSSL']:assert config[key]==source['published_streams'][key]
 masters={'transparent':Image.new('RGBA',(220,132),(0,0,0,0))}
 for style,pin in PINS.items():
  raw=(ROOT/'masters'/(style+'-sablona.png')).read_bytes();assert SHA(raw)==pin
  masters[style]=Image.open(io.BytesIO(raw)).convert('RGBA');assert masters[style].size==(220,132)
 sources={s['slug']:s for s in plan['source_artwork']}
 cached={};source_evidence=[]
 for slug,row in sources.items():
  raw=(ROOT/row['path']).read_bytes();assert SHA(raw)==row['sha256'] and len(raw)==row['bytes']
  assert list(Image.open(io.BytesIO(raw)).convert('RGBA').getchannel('A').getextrema())==row['source_alpha_extrema']
  original=Image.open(io.BytesIO(raw)).convert('RGBA');assert list(original.size)==row['dimensions']
  mark=original.copy();mark.thumbnail((192,104),Image.Resampling.LANCZOS)
  assert mark.size[0]<=192 and mark.size[1]<=104
  pos=((220-mark.width)//2,(132-mark.height)//2)
  box=(*pos,pos[0]+mark.width,pos[1]+mark.height)
  renders={}
  for style in STYLES:
   canvas=masters[style].copy()
   if style=='transparent':canvas.paste(mark,pos)
   else:canvas.alpha_composite(mark,pos)
   # Every fitted logo pixel is preserved; masters outside the logo are exact.
   if style=='transparent':assert canvas.crop(box).tobytes()==mark.tobytes()
   else:
    expected=Image.alpha_composite(masters[style].crop(box),mark)
    assert canvas.crop(box).tobytes()==expected.tobytes()
    opaque=mark.getchannel('A').point(lambda x:255 if x==255 else 0)
    for band in ImageChops.difference(canvas.crop(box),mark).split()[:3]:assert ImageChops.multiply(band,opaque).getbbox() is None
   outside=canvas.copy();background=masters[style].copy()
   ImageDraw.Draw(outside).rectangle((box[0],box[1],box[2]-1,box[3]-1),fill=(0,0,0,0))
   ImageDraw.Draw(background).rectangle((box[0],box[1],box[2]-1,box[3]-1),fill=(0,0,0,0))
   assert outside.tobytes()==background.tobytes()
   for w,h in SIZES:
    final=canvas if (w,h)==(220,132) else canvas.resize((w,h),Image.Resampling.LANCZOS)
    b=io.BytesIO();final.save(b,'PNG');renders[f'{w}x{h}/{style}']=b.getvalue()
  cached[slug]=renders
  source_evidence.append({'slug':slug,'source_sha256':row['sha256'],'fitted_dimensions':list(mark.size),'fitted_rgba_sha256':SHA(mark.tobytes()),'whole_source_and_alpha_preserved':True,'master_pixels_outside_logo_preserved':True})
 outputs=[];names=set()
 for station in plan['stations']:
  assert station['production_approved'] is False
  matches=[r for r in catalogue if r['reference']==station['reference']]
  assert len(matches)==1 and matches[0]['name']==station['name'] and matches[0]['url']==station['url']
  if station['family']=='BOB':
   block=next(p for p in publishers['BOB'] if p['image_url']==sources[station['slug']]['url']);assert station['official_stream_url'] in block['stream_urls']
  else:assert station['official_stream_url']==sources[station['slug']]['official_stream_url']
  from urllib.parse import urlsplit
  u=urlsplit(station['url']);official=urlsplit(station['official_stream_url'])
  assert u.hostname==official.hostname
  if station['family']=='BOB':assert u.path.strip('/').split('/')[:3]==official.path.strip('/').split('/')[:3]
  else:
   key=sources[station['slug']]['key'];assert u.path=='/'+key+'.mp3' and official.path in ['/'+key+'_web.mp3','/'+key+'.mp3']
  filename=station['reference'].replace(':','_')+'.png'
  assert filename==station['picon_filename'] and filename not in prior and filename not in names
  names.add(filename);entries={}
  for key,raw in cached[station['slug']].items():
   p=out/'kontrola'/key/filename;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
   assert p.read_bytes()==raw
   entries[key]={'path':str(p.relative_to(out)),'bytes':len(raw),'sha256':SHA(raw)}
   with Image.open(io.BytesIO(raw)) as im:
    assert im.mode=='RGBA' and im.size==tuple(map(int,key.split('/')[0].split('x')));im.verify()
  outputs.append({'name':station['name'],'label':station['official_programme_label'],'reference':station['reference'],'slug':station['slug'],'family':station['family'],'renders':entries})
 assert len(outputs)==plan['counts']['catalogue_entries'] and len(list((out/'kontrola').rglob('*.png')))==plan['counts']['reference_pngs']
 assert len({r['slug'] for r in outputs})==plan['counts']['original_programme_tiles']
 manifest={'schema':1,'date':'2026-11-05','stage':'review_only','production_changed':False,'pillow':'13.0.0','libwebp':features.version_module('webp'),'master_sha256':PINS,'counts':plan['counts'],'source_checks':source_evidence,'stations':outputs,'verification':{'source_hashes':len(sources),'catalogue_references':len(outputs),'png_decode_and_dimensions':len(outputs)*9,'variants_per_reference':9,'unapproved_artwork_published':False}}
 mp=ROOT/'render-manifest.json'
 if args.record:mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 else:assert json.loads(mp.read_text())==manifest,'Review hashes changed.'
 if args.verify:
  print('PASS:',len(sources),'whole-logo/template checks;',len(outputs),'catalogue references;',len(outputs)*9,'byte-identical PNG regenerations; no production writes.');return
 with (out/'parovanie.csv').open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.writer(f);writer.writerow(['Stanica v katalógu','Oficiálny program','Referencia','PNG','Zdroj'])
  for row in plan['stations']:writer.writerow([row['name'],row['official_programme_label'],row['reference'],row['picon_filename'],sources[row['slug']]['url']])
 (out/'SHA256SUMS.txt').write_text(''.join(f"{meta['sha256']}  {meta['path']}\n" for row in outputs for meta in row['renders'].values()))
 font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',19)
 small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14)
 tiny=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',12)
 # Show each complete publisher original once.
 display=list(sources)
 for page,start in enumerate(range(0,len(display),7),1):
  chunk=display[start:start+7]
  sheet=Image.new('RGB',(1050,120+len(chunk)*208),'#122236');draw=ImageDraw.Draw(sheet)
  draw.text((24,18),f'WARDER · RADIO · VEĽKÁ DÁVKA · KONTROLA {page}/{(len(display)+6)//7}',font=font,fill='white')
  draw.text((24,49),'Celé podklady vysielateľa · pôvodné farby · čaká na vizuálne schválenie',font=small,fill='#b9cede')
  for j,label in enumerate(('TRANSPARENT','WHITE','BLACK')):draw.text((290+j*245,85),label,font=small,fill='#9fe3ee')
  for i,slug in enumerate(chunk):
   y=120+i*208;source=sources[slug]
   label=source['name'];lines=[label]
   if len(label)>25:lines=[label[:label.rfind(' ',0,25)],label[label.rfind(' ',0,25)+1:]]
   for k,line in enumerate(lines):draw.text((24,y+28+k*22),line,font=small,fill='white')
   for j,style in enumerate(STYLES):
    x=290+j*245;tile=Image.new('RGB',(220,132),'#1b3045');g=ImageDraw.Draw(tile)
    if style=='transparent':
     for yy in range(0,132,11):
      for xx in range(0,220,11):g.rectangle((xx,yy,xx+10,yy+10),fill='#697e91' if (xx//11+yy//11)%2 else '#8193a2')
    im=Image.open(io.BytesIO(cached[slug]['220x132/'+style]));tile.paste(im,(0,0),im);sheet.paste(tile,(x,y))
    im=Image.open(io.BytesIO(cached[slug]['50x30/'+style]));sheet.paste(im,(x,y+144),im)
    draw.text((x+60,y+151),'50×30 · skutočná veľkosť',font=tiny,fill='#a8c1d4')
  target=out/f'Warder_Radio_Velka_davka_detail_{page:02d}.png'
  buffer=io.BytesIO();sheet.save(buffer,'PNG');raw=buffer.getvalue()
  temporary=target.with_suffix('.tmp');temporary.write_bytes(raw);temporary.replace(target)
  assert target.read_bytes()==raw
  with Image.open(target) as checked:checked.verify()
 # Three family overviews retain all 220x132 images at their native size.
 for family in ['BOB','ON','1A']:
  items=[p for p in plan['source_artwork'] if p['family']==family]
  cw=700;rh=190;sheet=Image.new('RGB',(1400,75+((len(items)+1)//2)*rh),'#122236');draw=ImageDraw.Draw(sheet)
  draw.text((20,15),f'WARDER · {family} · {len(items)} PROGRAMOV · KONTROLA',font=font,fill='white')
  draw.text((20,45),'Transparent / White / Black · pôvodné celé grafiky · 220×132 v skutočnej veľkosti',font=small,fill='#b9cede')
  for i,source in enumerate(items):
   x=(i%2)*cw+10;y=75+(i//2)*rh;label=source['name'];draw.text((x,y),label,font=small,fill='white')
   for j,style in enumerate(STYLES):
    tile=Image.new('RGBA',(220,132),'#77899a');im=Image.open(io.BytesIO(cached[source['slug']]['220x132/'+style]));tile.alpha_composite(im);sheet.paste(tile.convert('RGB'),(x+j*230,y+26))
  sheet.save(out/f'Warder_Radio_Velka_davka_{family}.png')
 print('PASS:',len(sources),'artwork sets;',len(outputs),'references;',len(outputs)*9,'review PNGs; original colours and master pixels protected.')

if __name__=='__main__':main()
