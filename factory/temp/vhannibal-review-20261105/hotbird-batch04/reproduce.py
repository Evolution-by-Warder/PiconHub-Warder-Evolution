"""Reproduce this review batch in an explicit empty output directory.
Needs Pillow, NumPy and SciPy. Does not edit sources or grant approval.
"""
from pathlib import Path
import sys, json, hashlib, io, argparse, zipfile
from PIL import Image
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'renderer'))
from auxiliary_renderer import fit_logo
from warder_visual_qc import fit_geometry_mask, center_rgba_layer
p=argparse.ArgumentParser()
p.add_argument('--masters',type=Path,required=True,help='Directory containing frozen white-sablona.png and black-sablona.png')
p.add_argument('--out',type=Path,required=True)
a=p.parse_args()
if a.out.exists() and any(a.out.iterdir()):raise SystemExit('Output directory must be empty')
a.out.mkdir(parents=True,exist_ok=True)
m=json.loads((HERE/'review-manifest.json').read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()
for name,h in m['helper_sha256'].items():assert sha((HERE/'renderer'/name).read_bytes())==h
masters={}
for s,h in m['template_sha256'].items():
 path=a.masters/(s+'-sablona.png');assert sha(path.read_bytes())==h
 masters[s]=Image.open(path).convert('RGBA')
with zipfile.ZipFile(HERE/'source-originals.zip') as z:
 for art in m['artworks']:
  r=art['references'][0]
  data=z.read(f"{art['review_number']:02}/"+Path(r['source_member']).name)
  assert sha(data)==art['original_sha256']
  src=Image.open(io.BytesIO(data)).convert('RGBA')
  fit,scale,box=fit_logo(src)
  centered=center_rgba_layer(fit,geometry_mask=fit_geometry_mask(src,box,scale))
  assert centered.safe_area and centered.centered and not centered.clipped
  for s,spec in art['outputs'].items():
   im=centered.image if s=='transparent' else Image.alpha_composite(masters[s],centered.image)
   path=a.out/spec['path'];path.parent.mkdir(parents=True,exist_ok=True);im.save(path)
   assert sha(path.read_bytes())==spec['sha256'],str(path)
print('PASS: 72 exact review PNG hashes; owner approval remains pending')
