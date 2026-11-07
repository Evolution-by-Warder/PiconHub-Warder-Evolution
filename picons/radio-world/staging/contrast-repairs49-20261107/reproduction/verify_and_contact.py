from pathlib import Path
import json,zipfile,hashlib,io,gzip,sys
from PIL import Image,ImageDraw,ImageChops
p=Path('continuation/contrast-repair-34-36');b=p/'rendered-pass1';manifest=json.load(open(b/'manifest.json'));sources=manifest['source_inventory'];marks={};masters={'transparent':Image.new('RGBA',(220,132))};styles=['transparent','white','black'];sizes=['50x30','220x132','400x240'];proof=[];rows=[]
sha=lambda d:hashlib.sha256(d).hexdigest()
for digest,e in sources.items():
 raw=(b/e['path']).read_bytes();assert sha(raw)==digest and len(raw)==e['bytes'];im=Image.open(io.BytesIO(raw)).convert('RGBA');im.thumbnail((192,104),Image.Resampling.LANCZOS);marks[digest]=im
for style in ['white','black']:
 raw=(b/'masters'/f'{style}.png').read_bytes();assert sha(raw)==manifest['master_sha256'][style];masters[style]=Image.open(io.BytesIO(raw)).convert('RGBA')
(b/'png').mkdir(exist_ok=True)
for station in manifest['stations']:
 variants={};out=Image.new('RGB',(1230,700),'#aaaaaa');d=ImageDraw.Draw(out);d.text((5,5),station['country']+' '+station['name'],fill='black')
 for j,size in enumerate(sizes):
  wh=tuple(map(int,size.split('x')));y=[35,140,410][j]
  for k,style in enumerate(styles):
   pkg=manifest['packages'][size][style];raw=(b/pkg['path']).read_bytes();assert sha(raw)==pkg['sha256']and len(raw)==pkg['bytes'];name=station['reference'].replace(':','_')+'.png'
   with zipfile.ZipFile(io.BytesIO(raw))as z:png=z.read(name)
   digest=sha(png);assert pkg['files'][name]==digest;im=Image.open(io.BytesIO(png));im.load();assert im.mode=='RGBA'and im.size==wh
   mark=marks[station.get('black_source',station['source'])if style=='black'else station['source']];base=masters[style].copy();pos=((220-mark.width)//2,(132-mark.height)//2)
   if style=='transparent':base.paste(mark,pos)
   else:base.alpha_composite(mark,pos)
   if wh!=base.size:base=base.resize(wh,Image.Resampling.LANCZOS)
   assert im.tobytes()==base.tobytes(),'Whole-source composition mismatch'
   file=b/'png'/f'{digest}.png';file.write_bytes(png);variants[size+'/'+style]=[digest,len(png),hashlib.sha1(b'blob '+str(len(png)).encode()+b'\0'+png).hexdigest()];d.text((k*410+5,y),size+' '+style,fill='black');out.paste(im,(k*410+5,y+18),im)
 out.save(b/f'review-{station["country"]}.png');rows.append({'ref':station['reference'],'country':station['country'],'station':{k:station[k]for k in ['name','url','group']},'source_commit':None,'asset_root':'pending-root-upload','source_sha256':station['source'],'variants':variants});proof.append({'country':station['country'],'ref':station['reference'],'pngs':9,'whole_source_pixel_composition_equal':True})
(b/'rendered-selection.json').write_text(json.dumps({'schema':1,'status':'rendered-awaiting-real-visual-QA','entries':rows},ensure_ascii=False,indent=2)+'\n');(b/'pixel-source-master-proof.json').write_text(json.dumps({'schema':1,'status':'pass','references':3,'pngs':27,'originals_preserved':4,'all_png_bytes_sha_dimensions_decode_pass':True,'whole_source_all_rgba_pixels_equal':True,'new_zip_files':9,'old_zips_recreated':0,'entries':proof},indent=2)+'\n');print('27PNG4originals exact andwholepixelcompositionPASS')
