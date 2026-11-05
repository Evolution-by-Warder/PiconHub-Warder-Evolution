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
 catalogues={};prior={}
 for country,pins in plan['countries'].items():
  raw=(ROOT/f'evidence/catalogue-{country}.json.gz').read_bytes();assert SHA(raw)==pins['catalogue_sha256'];catalogues[country]=json.loads(gzip.decompress(raw))
  raw=(ROOT/f'evidence/production-{country}.json').read_bytes();assert SHA(raw)==pins['production_release_sha256'];prior[country]=set(json.loads(raw)['packages']['220x132']['transparent']['files'])
 evidence={}
 for filename,pin in plan['evidence_json_sha256'].items():
  raw=(ROOT/'evidence'/filename).read_bytes();assert SHA(raw)==pin;evidence[filename]=json.loads(raw)
 from urllib.parse import urlsplit
 import re,unicodedata
 def norm(s):
  s=s.lower().replace('ł','l');s=unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode();s=re.sub(r'\b(radio|polska|kbps|and)\b|\b\d+\s*k(?:bps)?\b','',s);s=re.sub('maxx+','maxx',s);return re.sub('[^a-z0-9]','',s)
 def rmfn(s):return norm(re.sub(r'\.pl$','',s,flags=re.I))
 def key(u):
  p=urlsplit(u);h=p.hostname or '';k=p.path.strip('/');return k if (h=='stream.laut.fm' or h.endswith('.stream.laut.fm')) and re.fullmatch('[a-z0-9_-]+',k) else None
 rmf=evidence['rmf-api-list.json'];laut={x['name']:x for i in range(3) for x in evidence[f'laut-batch-{i:02}.json']}
 artwork={s['slug']:s for s in plan['source_artwork']}
 for station in plan['stations']:
  source=artwork[station['slug']]
  if station['country']=='PL':
   path=urlsplit(station['url']).path.strip('/').split('/')[0]
   matches=[s for s in rmf if path in [s['mountpoint_mp3'],s['mountpoint_aac']] and (rmfn(station['name'])==rmfn(s['name']) or (rmfn(station['name'])=='rmfprzebojroku' and rmfn(re.sub(r'\s+20\d\d$','',s['name']))=='rmfprzebojroku'))]
   assert len(matches)==1;s=matches[0];assert s['id']==station['provider_id'] and s['img']==source['url'] and s['name']==station['official_programme_label']
   streams=evidence[f"rmf-stream-{s['id']}.json"]
   urls=streams.get('playlist',{}).get('item',[])+streams.get('playlistMp3',{}).get('item_mp3',[])
   assert any(urlsplit(u).path.strip('/')==path for u in urls)
  else:
   s=laut[station['provider_id']];assert s['active'] and key(station['url'])==s['name']==key(s['stream_url']) and norm(station['name']) in [norm(s['name']),norm(s['display_name'])]
   assert s['images']['station_640x640']==source['url'] and 'e837bb137d5e31a048d55632f3f84394' not in source['url']
   assert s['display_name']==station['official_programme_label'] and station['official_stream_url']==s['stream_url']
  assert station['endpoint_playback_verified'] is False
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
  matches=[r for r in catalogues[station['country']] if r['reference']==station['reference']]
  assert len(matches)==1 and matches[0]['name']==station['name'] and matches[0]['url']==station['url']
  assert station['reference'] not in plan['previous_approved_references']
  filename=station['reference'].replace(':','_')+'.png'
  assert filename==station['picon_filename'] and filename not in prior[station['country']] and filename not in names
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
  draw.text((24,18),f'WARDER · RADIO · VEĽKÁ DÁVKA 03 · KONTROLA {page}/{(len(display)+6)//7}',font=font,fill='white')
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
  target=out/f'Warder_Radio_Davka03_detail_{page:02d}.png'
  buffer=io.BytesIO();sheet.save(buffer,'PNG');raw=buffer.getvalue()
  temporary=target.with_suffix('.tmp');temporary.write_bytes(raw);temporary.replace(target)
  assert target.read_bytes()==raw
  with Image.open(target) as checked:checked.verify()
 # Three family overviews retain all 220x132 images at their native size.
 for family in plan['counts']['families']:
  items=[p for p in plan['source_artwork'] if p['family']==family]
  if not items:continue
  cw=700;rh=190;sheet=Image.new('RGB',(1400,75+((len(items)+1)//2)*rh),'#122236');draw=ImageDraw.Draw(sheet)
  draw.text((20,15),f'WARDER · {family} · GRAFIKY: {len(items)} · KONTROLA',font=font,fill='white')
  draw.text((20,45),'Transparent / White / Black · pôvodné celé grafiky · 220×132 v skutočnej veľkosti',font=small,fill='#b9cede')
  for i,source in enumerate(items):
   x=(i%2)*cw+10;y=75+(i//2)*rh;label=source['name'];draw.text((x,y),label,font=small,fill='white')
   for j,style in enumerate(STYLES):
    tile=Image.new('RGBA',(220,132),'#77899a');im=Image.open(io.BytesIO(cached[source['slug']]['220x132/'+style]));tile.alpha_composite(im);sheet.paste(tile.convert('RGB'),(x+j*230,y+26))
  sheet.save(out/f'Warder_Radio_Davka03_{family}.png')
 print('PASS:',len(sources),'artwork sets;',len(outputs),'references;',len(outputs)*9,'review PNGs; original colours and master pixels protected.')

if __name__=='__main__':main()
