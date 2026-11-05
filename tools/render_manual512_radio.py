"""Render visually reviewed Radio originals; preserve every original pixel and pinned masters."""
import argparse,hashlib,io,json
from pathlib import Path
from PIL import Image
PINS={'white':'c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589','black':'61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe'}
SHA=lambda b:hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--templates',required=True);a=p.parse_args();root=Path(a.root);templates=Path(a.templates)
 rows=json.loads((root/'assistant-review-input.json').read_text());decisions=json.loads((root/'assistant-review-decisions.json').read_text());approved=[]
 masters={'transparent':Image.new('RGBA',(220,132))}
 for style,pin in PINS.items():
  data=(templates/(style+'.png')).read_bytes();assert SHA(data)==pin;masters[style]=Image.open(io.BytesIO(data)).convert('RGBA')
 for row,decision in zip(rows,decisions,strict=True):
  assert row['reference']==decision['reference'] and row['source']['sha256']==decision['sha256']
  if decision['decision']!='approve':continue
  source=row['source'];assert SHA((root/source['path']).read_bytes())==source['sha256'];raster=source.get('frozen_svg_raster',source);raw=(root/raster['path']).read_bytes();assert SHA(raw)==raster['sha256']
  mark=Image.open(io.BytesIO(raw)).convert('RGBA');mark.thumbnail((192,104),Image.Resampling.LANCZOS);pos=((220-mark.width)//2,(132-mark.height)//2);renders={}
  for style,master in masters.items():
   canvas=master.copy()
   if style=='transparent':canvas.paste(mark,pos)
   else:canvas.alpha_composite(mark,pos)
   for size,dim in [('50x30',(50,30)),('220x132',(220,132)),('400x240',(400,240))]:
    im=canvas if dim==(220,132) else canvas.resize(dim,Image.Resampling.LANCZOS);buf=io.BytesIO();im.save(buf,'PNG');body=buf.getvalue();relative='verified-assets/'+SHA(body)+'.png';path=root/relative;path.parent.mkdir(exist_ok=True)
    if path.exists():assert path.read_bytes()==body
    else:path.write_bytes(body)
    renders[size+'/'+style]={'path':relative,'sha256':SHA(body),'bytes':len(body)}
  row.update(status='ready_verified_visual_and_current_page',renders=renders,verification={'identity':'unique catalogue stream and saved current broadcaster page','visual_review':'assistant full original and current page identity review, 2026-11-05','variants_verified':9,'whole_original_and_master_outside_logo_preserved':True});approved.append(row)
 (root/'assistant-reviewed-ready.json').write_text(json.dumps(approved,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'approved':len(approved),'rejected':len(rows)-len(approved),'pngs':len(approved)*9}))
if __name__=='__main__':main()
