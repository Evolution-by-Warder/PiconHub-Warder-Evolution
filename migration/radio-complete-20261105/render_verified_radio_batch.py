"""Render only assistant-checked official Radio originals; preserve frozen masters."""
from pathlib import Path
from PIL import Image,ImageChops,ImageDraw
from collections import defaultdict,Counter
import argparse, gzip, hashlib, io, json, shutil, zipfile

SHA=lambda b:hashlib.sha256(b).hexdigest()
PINS={'white':'c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589','black':'61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe'}
SIZES=('50x30','220x132','400x240');STYLES=('transparent','white','black')
def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('workspace',type=Path);args=ap.parse_args();root=args.workspace.resolve();out=root/'batch05';out.mkdir(exist_ok=True)
 source_root=root/'remote-sources/migration/radio-complete-20261105';state=json.loads((source_root/'source-acquisition.json').read_text());decisions=json.loads((root/'qa/decisions.json').read_text())
 masters={'transparent':Image.new('RGBA',(220,132))}
 for style,pin in PINS.items():
  p=root/f'restored/Warder_Radio_Davka04_164_grafik_164_referencii_1476_PNG/reprodukcia/masters/{style}-sablona.png';raw=p.read_bytes();assert SHA(raw)==pin
  masters[style]=Image.open(io.BytesIO(raw)).convert('RGBA');(out/'masters').mkdir(exist_ok=True);shutil.copyfile(p,out/'masters'/p.name)
 catalogue=json.load(gzip.open(root/'piconhub/picons/IPTV-SK-CZ/catalog/global/world-radio.receiver.json.gz'));byref={s['reference']:s for s in catalogue}
 previous=json.loads((root/'checkpoint/ready-manifest.json').read_text());ready={r['reference'] for r in previous}
 canonical=json.load(gzip.open(root/'piconhub/picons/IPTV-SK-CZ/catalog/global/world-radio.json.gz'));countries={s['group']:s.get('countrycode') or 'WORLD' for s in canonical}
 candidates=[s for s in state['stations'].values() if s.get('status')=='candidate_assistant_visual_check' and decisions.get(s['source']['sha256'],{}).get('decision')=='approve']
 cache={};records=[]
 for station in candidates:
  ref=station['reference'];assert ref in byref and ref not in ready
  exact=byref[ref];assert exact['url']==station['url'] and exact['name']==station['name']
  source=station['source'];digest=source['sha256'];raw=(source_root/source['path']).read_bytes();assert SHA(raw)==digest and len(raw)==source['bytes']
  if digest not in cache:
   original=Image.open(io.BytesIO(raw)).convert('RGBA');assert list(original.size)==source['dimensions'];mark=original.copy();mark.thumbnail((192,104),Image.Resampling.LANCZOS)
   pos=((220-mark.width)//2,(132-mark.height)//2);box=(*pos,pos[0]+mark.width,pos[1]+mark.height);variants={}
   for style in STYLES:
    canvas=masters[style].copy()
    if style=='transparent':canvas.paste(mark,pos)
    else:canvas.alpha_composite(mark,pos)
    expected=mark if style=='transparent' else Image.alpha_composite(masters[style].crop(box),mark)
    assert canvas.crop(box).tobytes()==expected.tobytes()
    outside=canvas.copy();background=masters[style].copy()
    for image in [outside,background]:ImageDraw.Draw(image).rectangle((box[0],box[1],box[2]-1,box[3]-1),fill=(0,0,0,0))
    assert outside.tobytes()==background.tobytes()
    for size in SIZES:
     final=canvas if size=='220x132' else canvas.resize(tuple(map(int,size.split('x'))),Image.Resampling.LANCZOS);buffer=io.BytesIO();final.save(buffer,'PNG');body=buffer.getvalue()
     with Image.open(io.BytesIO(body)) as checked:assert checked.size==tuple(map(int,size.split('x'))) and checked.mode=='RGBA';checked.verify()
     p=out/'assets'/(SHA(body)+'.png');p.parent.mkdir(exist_ok=True);p.write_bytes(body)
     variants[size+'/'+style]=dict(path=str(p.relative_to(out)),bytes=len(body),sha256=SHA(body))
   p=out/'originals'/(digest+'.img');p.parent.mkdir(exist_ok=True);p.write_bytes(raw);cache[digest]=variants
  row=dict(reference=ref,country=countries.get(station['group'],'WORLD'),station=station,status='ready_verified_owner_approved',origins=['Radio batch05 / official laut.fm registry / assistant visual verification'],renders=cache[digest]);records.append(row);ready.add(ref)
 assert len(records)==len({r['reference'] for r in records})
 dump(out/'ready-manifest.json',records);dump(out/'assistant-visual-decisions.json',decisions)
 dump(out/'source-provenance.json',candidates)
 stats=dict(schema=1,date='2026-11-05',project='Radio plugin',batch='05',status='verified_and_owner_approved',new_references=len(records),new_pngs=len(records)*9,new_unique_originals=len(cache),master_sha256=PINS,pillow=Image.__version__,total_ready_references=len(ready),total_ready_pngs=len(ready)*9,total_ready_catalogue_references=len(ready&set(byref)),remaining_catalogue_references=len(set(byref)-ready),production_published=False)
 dump(out/'summary.json',stats)
 packages=[]
 for start in range(0,len(records),200):
  chunk=records[start:start+200];p=out/f'Warder_Radio_Davka05_cast{start//200+1:02d}_{len(chunk)}_ref_{len(chunk)*9}_PNG.zip'
  with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
   z.writestr('README.txt','Warder Radio: approved batch05, original whole broadcaster logos. Three sizes x three backgrounds. See provenance and hashes.\n')
   z.writestr('manifest.json',json.dumps(chunk,ensure_ascii=False,indent=2))
   for row in chunk:
    for variant,item in row['renders'].items():z.writestr('picons/'+variant+'/'+row['reference'].replace(':','_')+'.png',(out/item['path']).read_bytes())
  with zipfile.ZipFile(p) as z:
   assert z.testzip() is None
   for row in chunk:
    for variant,item in row['renders'].items():assert SHA(z.read('picons/'+variant+'/'+row['reference'].replace(':','_')+'.png'))==item['sha256']
  packages.append(dict(name=p.name,bytes=p.stat().st_size,sha256=SHA(p.read_bytes()),references=len(chunk),pngs=len(chunk)*9))
 dump(out/'packages.json',packages)
 old=json.loads((root/'checkpoint/coverage.json').read_text())
 for row in old:
  if row['reference'] in ready:row['status']='ready';row.pop('reason',None)
 dump(out/'coverage.json',old);dump(out/'ready-references.json',sorted(ready));dump(out/'complete-ready-manifest.json',previous+records)
 print(json.dumps(stats),flush=True);print(json.dumps(packages),flush=True)

if __name__=='__main__':main()
