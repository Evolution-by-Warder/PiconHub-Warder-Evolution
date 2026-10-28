"""Build review-only Warder variants from pinned, identified logo sources."""
from pathlib import Path
from PIL import Image,ImageDraw
from xml.etree import ElementTree as ET
import json,io,hashlib,copy
import cairosvg
from component_variants import negative_wordmark
R=Path(__file__).resolve().parent;styles=('transparent','white','black');sizes=((50,30),(220,132),(400,240))
templates=R/'templates' if (R/'templates').exists() else R.parents[1]/'plugin/artwork/templates/picons'
masters={s:Image.open(templates/f'{s}-sablona.png').convert('RGBA') for s in ('white','black')}
expected=json.loads((R/'catalog/master-sha256.json').read_text())
for s in masters:assert hashlib.sha256((templates/f'{s}-sablona.png').read_bytes()).hexdigest()==expected[s]
masks=json.loads((R/'catalog/component-masks.json').read_text())
canvases={(size,style):(Image.new('RGBA',size) if style=='transparent' else masters[style].copy() if size==(220,132) else masters[style].convert('RGBa').resize(size,Image.Resampling.LANCZOS).convert('RGBA')) for size in sizes for style in styles}
def beta_black(source):
 image=Image.open(source).convert('RGBA');image=image.crop(image.getbbox())
 pixels=list(image.getdata());w,h=image.size;pending={i for i,p in enumerate(pixels) if p[3]};groups=[]
 while pending:
  first=min(pending);pending.remove(first);todo=[first];group=[]
  while todo:
   i=todo.pop();group.append(i);x,y=i%w,i//w
   neighbours=([i-1] if x else [])+([i+1] if x+1<w else [])+([i-w] if y else [])+([i+w] if y+1<h else [])
   for j in neighbours:
    if j in pending:pending.remove(j);todo.append(j)
  groups.append(group)
 assert [len(g) for g in groups]==[9308,1275,815,1176]
 before=list(pixels)
 for group in groups[1:]:
  for i in group:pixels[i]=(255,255,255,pixels[i][3])
 assert all(pixels[i]==before[i] for i in groups[0])
 image.putdata(pixels);return image

sources=json.loads((R/'catalog/downloaded-logos.json').read_text());rows=json.loads((R/'catalog/refreshed-artwork-sources.json').read_text())['rows'];report=[];unique={}
for row in rows:
 spec=row.get('logo');entry=dict(country=row['country'],name=row['name'],picon_filename=row['picon_filename'])
 if not spec or 'path' not in sources[spec['url']]:entry['status']='MISSING_SOURCE';report.append(entry);continue
 src=sources[spec['url']];p=R/src['path'];entry['source']=src
 if spec.get('approved_variants'):
  entry.update(status='OWNER_APPROVED_PASSTHROUGH',files={})
  for size in sizes:
   res='%dx%d'%size
   for style in styles:
    original=spec['approved_variants'][res][style];raw=(R/original['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==original['sha256']
    target=R/'preview'/res/style/row['picon_filename'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    entry['files'][res+'/'+style]={'path':str(target.relative_to(R)),'sha256':original['sha256']}
  unique.setdefault(src['sha256'],entry);report.append(entry);continue
 try:
  raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==src['sha256']
  if p.suffix=='.svg':
   tree=ET.fromstring(raw)
   if any(k.endswith('href') and not v.startswith(('#','data:')) for n in tree.iter() for k,v in n.attrib.items()):raise ValueError('External SVG dependency')
   raw=cairosvg.svg2png(bytestring=raw,output_width=800)
  logo=Image.open(io.BytesIO(raw)).convert('RGBA');bbox=logo.getbbox()
  if not bbox:raise ValueError('Empty logo')
  logo=logo.crop(bbox);opaque=logo.getextrema()[3][0]==255
  solid=[(r,g,b) for r,g,b,a in logo.getdata() if a>=200]
  mono=bool(solid) and all(max(rgb)-min(rgb)<3 for rgb in solid) and max(rgb[0] for rgb in solid)-min(rgb[0] for rgb in solid)<=8
  entry.update(status='REVIEW_OPAQUE_SOURCE' if opaque else 'REVIEW_PREVIEW',monochrome=mono,files={})
  for size in sizes:
   fitted=logo.copy();fitted.thumbnail((round(size[0]*192/220),round(size[1]*104/132)),Image.Resampling.LANCZOS)
   for style in styles:
    canvas=canvases[(size,style)].copy()
    art=fitted.copy()
    if style=='black' and row['identity_key'] in masks:
     art=negative_wordmark(p,masks[row['identity_key']]);art.thumbnail((round(size[0]*192/220),round(size[1]*104/132)),Image.Resampling.LANCZOS)
    if style in spec.get('style_sources',{}):
     variant=spec['style_sources'][style];source=R/variant['path'];assert hashlib.sha256(source.read_bytes()).hexdigest()==variant['sha256']
     raw=source.read_bytes()
     if source.suffix=='.svg':raw=cairosvg.svg2png(bytestring=raw,output_width=800)
     art=Image.open(io.BytesIO(raw)).convert('RGBA');art=art.crop(art.getbbox());art.thumbnail((round(size[0]*192/220),round(size[1]*104/132)),Image.Resampling.LANCZOS)
    if style=='black' and spec['url'].endswith('frontinus_logo_transparent_1.png'):
     variant=next(x for x in json.loads((R/'catalog/extra-pinned-sources.json').read_text()) if x['url'].endswith('frontinus_logo_transparent_white.png'))
     source=R/variant['path'];assert hashlib.sha256(source.read_bytes()).hexdigest()==variant['sha256']
     art=Image.open(source).convert('RGBA');art=art.crop(art.getbbox());art.thumbnail((round(size[0]*192/220),round(size[1]*104/132)),Image.Resampling.LANCZOS)
    if style=='black' and spec['url'].endswith('beta-radio-logo.png'):
     art=beta_black(p);art.thumbnail((round(size[0]*192/220),round(size[1]*104/132)),Image.Resampling.LANCZOS)
    if style=='black' and spec['url'].endswith('logo_re.svg'):
     vector=ET.fromstring(p.read_bytes());nodes=list(vector.iter());assert nodes[5].get('id')=='Path_1'
     preserved={i:ET.tostring(nodes[i]) for i in (6,7,8)}
     nodes[5].set('style','fill:#ffffff !important')
     assert all(ET.tostring(nodes[i])==raw for i,raw in preserved.items())
     art=Image.open(io.BytesIO(cairosvg.svg2png(bytestring=ET.tostring(vector),output_width=1600))).convert('RGBA');art=art.crop(art.getbbox());art.thumbnail((round(size[0]*192/220),round(size[1]*104/132)),Image.Resampling.LANCZOS)
    if style=='white' and spec['url'].endswith('R7-logo_biele_new.svg'):
     vector=ET.fromstring(p.read_bytes());nodes=list(vector.iter())
     assert len(nodes)==9 and all(nodes[i].get('fill')=='#FFFFFF' for i in (1,2,3,4,7))
     preserved={i:ET.tostring(nodes[i]) for i in (5,6,8)}
     for i in (1,2,3,4,7):nodes[i].set('fill','#000000')
     assert all(ET.tostring(nodes[i])==before for i,before in preserved.items())
     art=Image.open(io.BytesIO(cairosvg.svg2png(bytestring=ET.tostring(vector),output_width=800))).convert('RGBA');art=art.crop(art.getbbox());art.thumbnail((round(size[0]*192/220),round(size[1]*104/132)),Image.Resampling.LANCZOS)
    if mono and not opaque and style in ('white','black'):
     rgb=0 if style=='white' else 255
     art.putdata([(rgb,rgb,rgb,a) if a else (r,g,b,a) for r,g,b,a in art.getdata()])
    canvas.alpha_composite(art,((size[0]-art.width)//2,(size[1]-art.height)//2))
    path=R/'preview'/('%dx%d'%size)/style/row['picon_filename'];path.parent.mkdir(parents=True,exist_ok=True);canvas.save(path,compress_level=9)
    entry['files']['%dx%d/%s'%(*size,style)]={'path':str(path.relative_to(R)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
  unique.setdefault(src['sha256'],entry)
 except Exception as e:entry.update(status='SOURCE_ERROR',error=str(e))
 report.append(entry)
(R/'catalog/preview-review.json').write_text(json.dumps({'status':'review-only-not-published','input_sha256':hashlib.sha256((R/'catalog/refreshed-artwork-sources.json').read_bytes()).hexdigest(),'records':report,'master_sha256':expected},ensure_ascii=False,indent=2)+'\n')
items=list(unique.values())
for offset in range(0,len(items),18):
 chunk=items[offset:offset+18];sheet=Image.new('RGB',(720,len(chunk)*92),(38,49,66));d=ImageDraw.Draw(sheet)
 for i,r in enumerate(chunk):
  d.text((8,i*92+2),r['name'],fill='white')
  for c,s in enumerate(styles):
   p=R/r['files']['220x132/'+s]['path'];im=Image.open(p).convert('RGBA');im.thumbnail((125,75));sheet.paste(im,(300+c*140,i*92+8),im)
 sheet.save(R/'preview'/f'review-{offset//18+1:02d}.png')
print('Preview references',sum('files' in r and bool(r['files']) for r in report),'unique logos',len(unique),'statuses',{s:sum(r['status']==s for r in report) for s in {r['status'] for r in report}})
