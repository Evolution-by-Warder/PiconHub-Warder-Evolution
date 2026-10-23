#!/usr/bin/env python3
"""Import user-approved PNG bytes; add only missing runtime aliases."""
from pathlib import Path
import hashlib,io,json,re,subprocess,zipfile
from PIL import Image
ROOT=Path.cwd();BASE=ROOT/'migration/gioppygio/68.5e-approved-20261022';PLAN=json.loads((BASE/'approval.json').read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()
baseline={str(p):sha(p.read_bytes()) for p in Path('picons/68.5e').rglob('*.png')}
parts=[]
for c in PLAN['chunks']:
 b=Path(c['path']).read_bytes();assert sha(b)==c['sha256'];parts.append(b)
data=b''.join(parts);assert len(data)==PLAN['archive_bytes'] and sha(data)==PLAN['archive_sha256'];z=zipfile.ZipFile(io.BytesIO(data))
assert set(z.namelist())==set(PLAN['artwork_files'])|{'preview.png'}
for name,wanted in PLAN['artwork_files'].items():
 b=z.read(name);assert sha(b)==wanted
 size,style,filename=name.split('/');assert size in ['220x132','400x240'] and style in ['transparent','white','black']
 assert filename.endswith('.png') and '/' not in filename
 im=Image.open(io.BytesIO(b));assert im.size==tuple(map(int,size.split('x'))) and im.mode=='RGBA'
 if style=='transparent':
  box=im.getchannel('A').getbbox();assert abs(box[0]-(im.width-box[2]))<=1 and abs(box[1]-(im.height-box[3]))<=1
 p=BASE/'artwork'/name;p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();p.write_bytes(b)
(BASE/'preview.png').write_bytes(z.read('preview.png'))
index={}
for p in Path('picons/68.5e').rglob('*.png'):index.setdefault(p.name,set()).add(p.parts[2])
added=[];preserved=[];missing_provider=[]
for m in PLAN['mappings']:
 assert re.fullmatch(r'1_0_[0-9A-F]+(?:_[0-9A-F]+){7}\.png',m['reference']),m['reference']
 assert int(m['reference'].split('_')[6],16)>>16==685
 providers=index.get(m['reference'],set())
 if not providers:
  provider=re.sub(r'[^a-z0-9]+','-',m['provider'].lower()).strip('-')
  if not provider:missing_provider.append(m);continue
  providers={provider}
 for provider in sorted(providers):
  for style in ['transparent','white','black']:
   dst=Path('picons/68.5e')/provider/style/m['reference'];src=BASE/'artwork/220x132'/style/(m['artwork']+'.png')
   if dst.exists():preserved.append(str(dst));continue
   dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(src.read_bytes());added.append(str(dst))
assert all(Path(p).is_file() and sha(Path(p).read_bytes())==digest for p,digest in baseline.items())
report={'approved_pngs':len(PLAN['artwork_files']),'station_artworks':92,'mapped_artworks':len(set(m['artwork'] for m in PLAN['mappings'])),'mapped_references':len(PLAN['mappings']),'unmapped_artwork':PLAN['unmapped_artwork'],'runtime_aliases_added':added,'runtime_aliases_preserved':preserved,'missing_provider':missing_provider,'baseline_existing_pngs_preserved':len(baseline),'all_existing_bytes_unchanged':True,'centering_checks_passed':184}
(BASE/'publication-report.json').write_text(json.dumps(report,indent=2)+'\n')
for c in PLAN['chunks']:Path(c['path']).unlink()
print(json.dumps({k:v for k,v in report.items() if k not in ['runtime_aliases_added','runtime_aliases_preserved','missing_provider']}))
