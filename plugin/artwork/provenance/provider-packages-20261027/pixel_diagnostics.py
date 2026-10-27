import json,io,zipfile,urllib.request
from pathlib import Path
from PIL import Image
R=Path(__file__).resolve().parent;d=json.loads((R/'comparison.json').read_text());ref=d['skin_commit'];base='https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/'+ref+'/assets/warder/downloads/picons/channels/';doc=json.load(urllib.request.urlopen(base+'manifest.json',timeout=30));meta={p['filename']:p for p in doc['parts']}
frames={}
for s in ('white','black'):
 raw=urllib.request.urlopen('https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/90d088e13f95ddc36df4369d0be4fdb0698a8ec2/plugin/artwork/templates/picons/'+s+'-sablona.png',timeout=30).read();frames[s]=Image.open(io.BytesIO(raw)).convert('RGBA')
boxes=[(0,0,12,12),(208,0,220,12),(0,120,12,132),(208,120,220,132)]
stats=[];details=[]
for p in doc['packages']:
 if p['selector_id'] not in ('SKYLINK','CANALPLUS_SK','CANALPLUS_CZ') or p['resolution']!='220x132':continue
 s=p['family'].removeprefix('channel-');raw=b''.join((R/'parts'/meta[u.rsplit('/',1)[-1]]['sha256']).read_bytes() for u in p['parts']);blank=[];corner_matches=0
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  for n in z.namelist():
   im=Image.open(io.BytesIO(z.read(n))).convert('RGBA');alpha=im.getchannel('A');bbox=alpha.getbbox()
   if bbox is None:blank.append(n)
   if s in frames and im.size==(220,132) and all(im.crop(b).convert('RGBa').tobytes()==frames[s].crop(b).convert('RGBa').tobytes() for b in boxes):corner_matches+=1
   if '_1B03_3FE_1_C00000_' in n or '_1F4B_CA1_' in n or '_3C30_C90_' in n:details.append({'selector':p['selector_id'],'style':s,'filename':n,'size':list(im.size),'alpha_extrema':list(alpha.getextrema()),'visible_bbox':bbox})
 stats.append({'selector':p['selector_id'],'style':s,'files':len(z.namelist()),'fully_transparent_pngs':blank,'frozen_master_four_corners_exact':corner_matches if s in frames else None})
out={'packages':stats,'selected_details':details,'corner_test':'Compare visible premultiplied RGBA pixels in four 12x12 corner regions against the frozen 220x132 Warder masters. This detects framing differences, not broadcast/entitlement differences.'};(R/'pixel-diagnostics.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
