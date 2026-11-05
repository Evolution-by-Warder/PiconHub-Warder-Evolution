"""Reproduce the review PNGs offline, retaining complete broadcaster images.

Requires Pillow 13.0.0 for the pinned PNG bytes. Run:
  python render_review.py --output /temporary/review --verify
Only --record updates the review manifest. This script cannot publish data.
"""
from pathlib import Path
import argparse, csv, gzip, hashlib, io, json
from PIL import Image, ImageDraw, ImageFont

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
 plan=json.loads((ROOT/'source-plan.json').read_text())
 assert plan['production_changed'] is False and len(plan['source_artwork'])==20
 cat_raw=(ROOT/'evidence/catalogue-DE.json.gz').read_bytes();assert SHA(cat_raw)==plan['catalogue_sha256']
 catalogue=json.loads(gzip.decompress(cat_raw))
 baseline=(ROOT/'evidence/production-release-baseline.json').read_bytes();assert SHA(baseline)==plan['production_release_sha256']
 prior=set(json.loads(baseline)['packages']['220x132']['transparent']['files'])
 evidence={}
 for filename,pin in plan['evidence_json_sha256'].items():
  raw=(ROOT/'evidence'/filename).read_bytes();assert SHA(raw)==pin;evidence[filename]=json.loads(raw)
 for row in evidence.values():assert row['source_html_sha256']==plan['source_pages'][row['page']]
 publisher_assets={r['slug']:r for r in evidence['programme-links.json']['assets']}
 publisher_streams={r['reference']:r['official_stream_url'] for r in evidence['stream-links.json']['streams']}
 masters={'transparent':Image.new('RGBA',(220,132),(0,0,0,0))}
 for style,pin in PINS.items():
  raw=(ROOT/'masters'/(style+'-sablona.png')).read_bytes();assert SHA(raw)==pin
  masters[style]=Image.open(io.BytesIO(raw)).convert('RGBA');assert masters[style].size==(220,132)
 sources={s['slug']:s for s in plan['source_artwork']}
 cached={};source_evidence=[]
 for slug,row in sources.items():
  raw=(ROOT/row['path']).read_bytes();assert SHA(raw)==row['sha256'] and len(raw)==row['bytes']
  published=publisher_assets[slug]
  assert row['url']==published['image_url'] and row['programme_page']==published['programme_page'] and row['name']==published['label']
  original=Image.open(io.BytesIO(raw)).convert('RGBA');assert list(original.size)==row['dimensions']
  mark=original.copy();mark.thumbnail((192,104),Image.Resampling.LANCZOS)
  assert mark.getchannel('A').getextrema()==(255,255)
  pos=((220-mark.width)//2,(132-mark.height)//2)
  box=(*pos,pos[0]+mark.width,pos[1]+mark.height)
  renders={}
  for style in STYLES:
   canvas=masters[style].copy();canvas.alpha_composite(mark,pos)
   # Every fitted logo pixel is preserved; masters outside the logo are exact.
   assert canvas.crop(box).tobytes()==mark.tobytes()
   outside=canvas.copy();background=masters[style].copy()
   ImageDraw.Draw(outside).rectangle((box[0],box[1],box[2]-1,box[3]-1),fill=(0,0,0,0))
   ImageDraw.Draw(background).rectangle((box[0],box[1],box[2]-1,box[3]-1),fill=(0,0,0,0))
   assert outside.tobytes()==background.tobytes()
   for w,h in SIZES:
    final=canvas if (w,h)==(220,132) else canvas.resize((w,h),Image.Resampling.LANCZOS)
    b=io.BytesIO();final.save(b,'PNG');renders[f'{w}x{h}/{style}']=b.getvalue()
  cached[slug]=renders
  source_evidence.append({'slug':slug,'source_sha256':row['sha256'],'fitted_dimensions':list(mark.size),'fitted_rgba_sha256':SHA(mark.tobytes()),'whole_fitted_logo_pixels_preserved':True,'master_pixels_outside_logo_preserved':True})
 outputs=[];names=set()
 for station in plan['stations']:
  assert station['production_approved'] is False
  matches=[r for r in catalogue if r['reference']==station['reference']]
  assert len(matches)==1 and matches[0]['name']==station['name'] and matches[0]['url']==station['url']
  assert station['official_stream_url']==publisher_streams[station['reference']]
  filename=station['reference'].replace(':','_')+'.png'
  assert filename==station['picon_filename'] and filename not in prior and filename not in names
  names.add(filename);entries={}
  for key,raw in cached[station['slug']].items():
   p=out/'kontrola'/key/filename;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
   entries[key]={'path':str(p.relative_to(out)),'bytes':len(raw),'sha256':SHA(raw)}
   with Image.open(io.BytesIO(raw)) as im:
    assert im.mode=='RGBA' and im.size==tuple(map(int,key.split('/')[0].split('x')));im.verify()
  outputs.append({'name':station['name'],'label':station['official_programme_label'],'reference':station['reference'],'slug':station['slug'],'renders':entries})
 assert len(outputs)==21 and len(list((out/'kontrola').rglob('*.png')))==189
 euro=[s for s in outputs if s['slug']=='90er-eurodance'];assert len(euro)==2
 for key in euro[0]['renders']:assert euro[0]['renders'][key]['sha256']==euro[1]['renders'][key]['sha256']
 manifest={'schema':1,'date':'2026-11-05','stage':'review_only','production_changed':False,'pillow':'13.0.0','master_sha256':PINS,'counts':plan['counts'],'source_checks':source_evidence,'stations':outputs,'verification':{'source_hashes':20,'catalogue_references':21,'png_decode_and_dimensions':189,'variants_per_reference':9,'unapproved_artwork_published':False}}
 mp=ROOT/'render-manifest.json'
 if args.record:mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 else:assert json.loads(mp.read_text())==manifest,'Review hashes changed.'
 if args.verify:
  print('PASS: 20 whole-logo and template checks, 21 catalogue references, 189 byte-identical PNG regenerations, two exact Eurodance references; no production writes.');return
 with (out/'parovanie.csv').open('w',encoding='utf-8-sig',newline='') as f:
  writer=csv.writer(f);writer.writerow(['Stanica v katalógu','Oficiálny program','Referencia','PNG','Zdroj'])
  for row in plan['stations']:writer.writerow([row['name'],row['official_programme_label'],row['reference'],row['picon_filename'],sources[row['slug']]['url']])
 (out/'SHA256SUMS.txt').write_text(''.join(f"{meta['sha256']}  {meta['path']}\n" for row in outputs for meta in row['renders'].values()))
 font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',19)
 small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14)
 tiny=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',12)
 # Show each original once; the two Eurodance service files are byte-identical.
 display=list(sources)
 for page,start in enumerate(range(0,len(display),7),1):
  chunk=display[start:start+7]
  sheet=Image.new('RGB',(1050,120+len(chunk)*208),'#122236');draw=ImageDraw.Draw(sheet)
  draw.text((24,18),f'WARDER · ANTENNE BAYERN · KONTROLA {page}/3',font=font,fill='white')
  draw.text((24,49),'Celé podklady vysielateľa · pôvodné farby · čaká na vizuálne schválenie',font=small,fill='#b9cede')
  for j,label in enumerate(('TRANSPARENT','WHITE','BLACK')):draw.text((290+j*245,85),label,font=small,fill='#9fe3ee')
  for i,slug in enumerate(chunk):
   y=120+i*208;source=sources[slug]
   label=source['name'];lines=[label]
   if len(label)>25:lines=[label[:label.rfind(' ',0,25)],label[label.rfind(' ',0,25)+1:]]
   for k,line in enumerate(lines):draw.text((24,y+28+k*22),line,font=small,fill='white')
   if slug=='90er-eurodance':draw.text((24,y+86),'2 referencie · rovnaké PNG',font=tiny,fill='#a8c1d4')
   for j,style in enumerate(STYLES):
    x=290+j*245;tile=Image.new('RGB',(220,132),'#1b3045');g=ImageDraw.Draw(tile)
    if style=='transparent':
     for yy in range(0,132,11):
      for xx in range(0,220,11):g.rectangle((xx,yy,xx+10,yy+10),fill='#697e91' if (xx//11+yy//11)%2 else '#8193a2')
    im=Image.open(io.BytesIO(cached[slug]['220x132/'+style]));tile.paste(im,(0,0),im);sheet.paste(tile,(x,y))
    im=Image.open(io.BytesIO(cached[slug]['50x30/'+style]));sheet.paste(im,(x,y+144),im)
    draw.text((x+60,y+151),'50×30 · skutočná veľkosť',font=tiny,fill='#a8c1d4')
  sheet.save(out/f'Warder_Antenne_Bayern_kontrola_{page}.png')
 print('PASS: 20 artwork sets, 21 references, 189 review PNGs; original colours and master pixels protected.')

if __name__=='__main__':main()
