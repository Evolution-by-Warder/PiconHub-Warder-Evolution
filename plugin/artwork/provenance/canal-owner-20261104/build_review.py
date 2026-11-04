from pathlib import Path
import sys,json,hashlib,io,shutil
import numpy as np
from scipy import ndimage
from PIL import Image,ImageDraw,ImageFont
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--renderer-tools',type=Path,required=True);args=parser.parse_args()
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
sys.path[:0]=[str(args.renderer_tools),str(ROOT/'tools')]
import auxiliary_renderer as renderer
from warder_brand_guard import classify_and_render_guarded
# BASE is the directory containing this review script.
for d in ['originals','cleaned-proposals','review-only/220x132','review-only/50x30','review-only/400x240']:(BASE/d).mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
masters={s:Image.open(ROOT/'plugin/artwork/templates/picons'/(s+'-sablona.png')).convert('RGBA') for s in ['black','white']}
report={'status':'CLEANED_SOURCE_REVIEW_REQUIRED','production_changed':False,'templates':{s:sha((ROOT/'plugin/artwork/templates/picons'/(s+'-sablona.png')).read_bytes()) for s in masters},'engine_sha256':sha(Path(renderer.__file__).read_bytes()),'artwork':[]}
for slug in ['action','classics','crime','drama']:
 p=BASE/'originals'/(slug+'.png');original=Image.open(p).convert('RGBA');a=np.array(original);rgb=a[:,:,:3].astype(float);alpha=a[:,:,3].astype(float)
 # Full monochrome source proposal, without redrawing or substituting text.
 # Remove the near-black rectangular matte from Classics/Crime/Drama.
 # Keep Action's supplied alpha; RGB luminance only suppresses dark debris.
 gray=np.dot(rgb,[.2126,.7152,.0722]);mask=np.rint(np.clip((gray-8)/247,0,1)*alpha).astype(np.uint8)
 # Remove isolated scan/alpha debris without changing any glyph contour.
 labels,count=ndimage.label(mask>=32,np.ones((3,3)));areas=np.bincount(labels.ravel());keep=areas>=12;keep[0]=False
 for component, region in enumerate(ndimage.find_objects(labels), 1):
  if region is not None and (region[0].stop-region[0].start<=3 or region[1].stop-region[1].start<=2):keep[component]=False
 support=ndimage.binary_dilation(keep[labels],iterations=2);mask[~support]=0
 clean=np.zeros_like(a);clean[:,:,:3]=255;clean[:,:,3]=mask;clean[mask==0,:3]=0
 src=Image.fromarray(clean,'RGBA');src.save(BASE/'cleaned-proposals'/(slug+'.png'))
 f,scale,box=renderer.fit_logo(src);geometry=renderer.fit_geometry_mask(src,box,scale);aligned=renderer.center_rgba_layer(f,geometry_mask=geometry)
 assert aligned.centered and aligned.safe_area and not aligned.clipped
 row={'slug':slug,'original_sha256':sha(p.read_bytes()),'cleaned_source_sha256':sha((BASE/'cleaned-proposals'/(slug+'.png')).read_bytes()),'cleanup':'Whole monochrome glyph extraction; near-black matte to alpha, chromatic compression noise to monochrome, isolated alpha debris removal; no text redraw or font substitution. Requires owner review of this new source.','source_bbox':box,'scale':scale,'outputs':{},'original_preflight':{}}
 for style in ['transparent','white','black']:
  if style=='transparent':image=aligned.image;status='GEOMETRY_PASS';reason='Preserved cleaned source geometry'
  else:
   result=classify_and_render_guarded(renderer,f,masters[style],style,centering_mask=geometry,original_source=src)
   image=result.image;status=result.status;reason=result.reason
   assert status in ['PASS','AUTO-FIXED'],(slug,style,status,reason)
  for size in ['220x132','50x30','400x240']:
   dest=BASE/'review-only'/size/style/(slug+'.png');dest.parent.mkdir(exist_ok=True)
   rendered=image if size=='220x132' else image.convert('RGBa').resize(tuple(map(int,size.split('x'))),Image.Resampling.LANCZOS).convert('RGBA')
   rendered.save(dest,optimize=True)
   row['outputs'][size+'/'+style]={'path':str(dest.relative_to(BASE)),'sha256':sha(dest.read_bytes()),'status':status,'reason':reason}
 # Retain exact raw-source failure evidence separately from normalized proposals.
 of,oscale,obox=renderer.fit_logo(original);og=renderer.fit_geometry_mask(original,obox,oscale)
 for style in ['white','black']:
  try:
   res=classify_and_render_guarded(renderer,of,masters[style],style,centering_mask=og,original_source=original);row['original_preflight'][style]={'status':res.status,'reason':res.reason}
  except Exception as ex:row['original_preflight'][style]={'status':'BLOCKED','reason':str(ex)}
 report['artwork'].append(row)
(BASE/'review-manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
font='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
F=lambda n:ImageFont.truetype(font,n)
sheet=Image.new('RGB',(1100,900),'#17202c');d=ImageDraw.Draw(sheet)
d.text((30,18),'CANAL+ · Warder MASTER · návrhy na kontrolu',font=F(26),fill='white')
d.text((30,56),'220 × 132 · finálne veľkosti aj 50 × 30 / 400 × 240',font=F(17),fill='#c4cfdd')
for j,s in enumerate(['transparent','white','black']):d.text((230+j*290,100),s.upper(),font=F(18),fill='white')
for i,row in enumerate(report['artwork']):
 y=148+i*175;d.text((28,y+48),'+'+row['slug'].upper(),font=F(18),fill='white')
 for j,s in enumerate(['transparent','white','black']):
  im=Image.open(BASE/row['outputs']['220x132/'+s]['path']).convert('RGBA');tile=Image.new('RGBA',im.size,'#526174' if s=='transparent' else '#c6ced8');tile.alpha_composite(im);sheet.paste(tile,(230+j*290,y))
d.text((30,858),'Pôvodné šablóny zachované. Vyčistené zdroje čakajú na schválenie; produkcia nezmenená.',font=F(15),fill='#c4cfdd')
sheet.save(BASE/'Warder-Canal-kontrola.png')
print(json.dumps({'artwork':4,'variants':sum(len(x['outputs']) for x in report['artwork']),'templates':report['templates'],'output':str(BASE)},indent=2))
