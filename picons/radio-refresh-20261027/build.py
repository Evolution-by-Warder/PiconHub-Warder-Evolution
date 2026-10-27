#!/usr/bin/env python3
"""Exact approved regional radio replacements; no invented logo variants."""
from pathlib import Path
import hashlib,io,json,shutil
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent
SIZES=('50x30','220x132','400x240');STYLES=('transparent','white','black')
MASTERS=ROOT.parents[1]/'plugin/artwork/templates/picons'
HASHES={'white':'c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589','black':'61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe'}
ROWS=[('Fun Radio Z','135D','fun'),('Fun Radio S','135E','fun'),('Fun Radio V','135F','fun'),('Melody Z','1345','melody'),('Melody S','1346','melody'),('Melody V','1347','melody'),('ReginaBA','133A','ReginaBA'),('ReginaBB','133B','ReginaBB'),('ReginaKE','133C','ReginaKE')]
def sha(b):return hashlib.sha256(b).hexdigest()
def resize(im,size):
 return im.convert('RGBA').convert('RGBa').resize(size,Image.Resampling.LANCZOS).convert('RGBA')
def encode(im):
 f=io.BytesIO();im.save(f,format='PNG',compress_level=9);return f.getvalue()
def build():
 masters={}
 for style,digest in HASHES.items():
  raw=(MASTERS/(style+'-sablona.png')).read_bytes();assert sha(raw)==digest;masters[style]=Image.open(io.BytesIO(raw)).convert('RGBA')
 art={};mappings=[];source_hashes={}
 for name,sid,key in ROWS:
  reference='1_0_2_'+sid+'_CA2_3_EB0000_0_0_0.png';record={'station':name,'reference':reference,'position_tenths':235,'artwork':{}}
  for size in SIZES:
   dims=tuple(map(int,size.split('x')))
   for style in STYLES:
    if key in ('fun','melody'):
     p=ROOT/'sources'/key/(style+'.png');raw=p.read_bytes();source_hashes[str(p.relative_to(ROOT))]=sha(raw)
     output=raw if size=='220x132' else encode(resize(Image.open(io.BytesIO(raw)),dims))
    else:
     p=ROOT/'sources'/(key+'.png');raw=p.read_bytes();source_hashes[str(p.relative_to(ROOT))]=sha(raw)
     original=Image.open(io.BytesIO(raw)).convert('RGBA');logo=original.crop(original.getbbox());logo.thumbnail((round(192*dims[0]/220),round(104*dims[1]/132)),Image.Resampling.LANCZOS)
     frame=Image.new('RGBA',dims) if style=='transparent' else (masters[style].copy() if size=='220x132' else resize(masters[style],dims))
     result=frame.copy();x,y=(dims[0]-logo.width)//2,(dims[1]-logo.height)//2;result.alpha_composite(logo,(x,y))
     for box in ((0,0,dims[0],y),(0,y+logo.height,dims[0],dims[1]),(0,y,x,y+logo.height),(x+logo.width,y,dims[0],y+logo.height)):
      assert result.crop(box).tobytes()==frame.crop(box).tobytes()
     output=encode(result)
    path='artwork/'+size+'/'+style+'/'+reference;dest=ROOT/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(output);assert Image.open(dest).size==dims
    art[path]=sha(output);record['artwork'].setdefault(size,{})[style]={'path':'picons/radio-refresh-20261027/'+path,'sha256':sha(output)}
  mappings.append(record)
 for prefix in ('Fun Radio','Melody'):
  rows=[m for m in mappings if m['station'].startswith(prefix)]
  for size in SIZES:
   for style in STYLES:assert len({m['artwork'][size][style]['sha256'] for m in rows})==1
 report={'schema':1,'status':'owner-authorized','date':'2026-10-27','owner_instruction':'Fun Radio S/V must match Fun Radio Z; Melody S must match Melody V/Z; use attached ReginaBA/BB/KE originals for all three backgrounds and supported sizes. Publish independently and record all changes.','sizes':list(SIZES),'styles':list(STYLES),'mappings':mappings,'artwork_files':art,'source_sha256':source_hashes,'master_sha256':HASHES,'technical_reference_source':'https://en.kingofsat.tv/radio-23.5E','technical_reference_checked':'2026-10-27','policy':'Preserve original colours and identity. Exact approved full 220x132 Fun/Melody PNGs copied; other sizes resized proportionally. Regina uses original supplied high-resolution artwork and frozen Warder backgrounds. No guessed DAB or terrestrial aliases.'}
 (ROOT/'approval.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 sheet=Image.new('RGB',(660,5*155),(30,40,53));d=ImageDraw.Draw(sheet)
 for row,key in enumerate(('Fun Radio Z','Melody Z','ReginaBA','ReginaBB','ReginaKE')):
  m=next(m for m in mappings if m['station']==key)
  for col,style in enumerate(STYLES):
   im=Image.open(ROOT/'artwork/220x132'/style/m['reference']).convert('RGBA');sheet.paste(im,(col*220,row*155),im)
  d.text((5,row*155+134),key,fill='white')
 sheet.save(ROOT/'review.png');print('Verified',len(mappings),'references;',len(art),'PNG variants; originals and frozen masters preserved')
 return report
if __name__=='__main__':build()
