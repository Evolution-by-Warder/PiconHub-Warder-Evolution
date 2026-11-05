from pathlib import Path
from zipfile import ZipFile
from concurrent.futures import ThreadPoolExecutor
import json,hashlib,io,urllib.request
from PIL import Image
sha=lambda b:hashlib.sha256(b).hexdigest()
blob=lambda b:hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def produce(base,asset_index,subset,templates,master_ref):
 base.mkdir(parents=True,exist_ok=True);items=json.load(open(asset_index));z=ZipFile(subset);masters={s:Image.open(templates/(s+'-sablona.png')).convert('RGBA') for s in ('white','black')}
 for number,a in enumerate(items,1):
  if a['kind']=='SOURCE_GRAPHIC':
   raw=z.read(a['source_sha256']+'.png');assert sha(raw)==a['source_sha256'];src=Image.open(io.BytesIO(raw)).convert('RGBA');box=src.getchannel('A').getbbox();assert box;crop=src.crop(box);scale=min(196/crop.width,108/crop.height,1.0 if src.size==(220,132) else float('inf'));size=(max(1,round(crop.width*scale)),max(1,round(crop.height*scale)))
   if crop.size!=size:crop=crop.resize(size,Image.Resampling.LANCZOS)
   transparent=Image.new('RGBA',(220,132),(0,0,0,0));transparent.alpha_composite(crop,((220-crop.width)//2,(132-crop.height)//2));data={}
   for s in ('transparent','white','black'):
    out=io.BytesIO();(transparent if s=='transparent' else Image.alpha_composite(masters[s],transparent)).save(out,format='PNG');data[s]=out.getvalue()
  else:
   data={}
   for s,v in a['master_sources'].items():
    p=base/(v['sha']+'.png')
    if p.exists():b=p.read_bytes()
    else:b=urllib.request.urlopen('https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'+a.get('source_ref',master_ref)+'/'+v['path'],timeout=90).read()
    assert blob(b)==v['sha'];data[s]=b
  for s,b in data.items():assert sha(b)==a['outputs'][s]['sha256'],('Non-reproducible canonical PNG',a['asset_id'],s);(base/a['outputs'][s]['file']).write_bytes(b)
  if number%100==0:print('REPRODUCED',number,len(items),flush=True)
 print('ALL_CANONICAL_ASSETS_REPRODUCED',len(items),flush=True)
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--index',type=Path,required=True);p.add_argument('--subset',type=Path,required=True);p.add_argument('--templates',type=Path,required=True);p.add_argument('--master-ref',required=True);a=p.parse_args();produce(a.base,a.index,a.subset,a.templates,a.master_ref)
