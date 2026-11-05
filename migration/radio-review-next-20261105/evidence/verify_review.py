"""Verify this review bundle offline. New PNG hashes require Pillow 13.0.0.

Run: python evidence/verify_review.py
This performs no production writes or network calls.
"""
from pathlib import Path
import gzip, hashlib, io, json
from PIL import Image

root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'manifest.json').read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()
assert manifest['production_changed'] is False
masters={'transparent':Image.new('RGBA',(220,132),(0,0,0,0))}
for style,pin in manifest['master_sha256'].items():
 raw=(root/'evidence/masters'/(style+'-sablona.png')).read_bytes()
 assert sha(raw)==pin
 masters[style]=Image.open(io.BytesIO(raw)).convert('RGBA')
expected={f'{w}x{h}/{s}' for w,h in [(50,30),(220,132),(400,240)] for s in masters}
count=0;regenerated=0
for row in manifest['stations']:
 assert row['production_approved'] is False
 refs=json.loads(gzip.decompress(next((root/'evidence/catalogues'/row['country']).glob('*.gz')).read_bytes()))
 assert any(r['reference']==row['reference'] and r['name']==row['name'] and r['url']==row['stream_url'] for r in refs)
 original=(root/row['original_path']).read_bytes();assert sha(original)==row['source_sha256']
 assert set(row['renders'])==expected
 for key,meta in row['renders'].items():
  path=root/meta['path'];raw=path.read_bytes()
  assert path.name==row['reference'].replace(':','_')+'.png'
  assert sha(raw)==meta['sha256'] and len(raw)==meta['bytes']
  dims,style=key.split('/');size=tuple(map(int,dims.split('x')))
  with Image.open(io.BytesIO(raw)) as im:
   assert im.mode=='RGBA' and im.size==size
   im.verify()
  if row['newly_rendered']:
   assert Image.__version__==manifest['pillow_new_renders']
   mark=Image.open(io.BytesIO(original)).convert('RGBA')
   mark.thumbnail((192,104),Image.Resampling.LANCZOS)
   assert sha(mark.tobytes())==row['fitted_rgba_sha256']
   canvas=masters[style].copy()
   canvas.alpha_composite(mark,((220-mark.width)//2,(132-mark.height)//2))
   if size!=(220,132):canvas=canvas.resize(size,Image.Resampling.LANCZOS)
   buf=io.BytesIO();canvas.save(buf,'PNG');assert buf.getvalue()==raw
   regenerated+=1
  count+=1
assert count==45 and regenerated==27
assert len(list((root/'kontrola').rglob('*.png')))==45
print('PASS: 45 decoded PNGs, source/master hashes, exact catalogue identities; 27 byte-exact regenerations, 18 preserved review PNGs; no production writes.')
