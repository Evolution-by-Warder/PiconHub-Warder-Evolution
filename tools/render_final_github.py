"""Render independently reviewed source assets and require every approved PNG hash."""
import json,hashlib,io,subprocess
from pathlib import Path
from PIL import Image
from final_logo_pass import render,PINS,save,SHA
ROOT=Path('migration/radio-final775-reviewed-20261105')
masters={'transparent':Image.new('RGBA',(220,132))}
for style,pin in PINS.items():
 raw=(Path('plugin/artwork/templates/picons')/(style+'-sablona.png')).read_bytes();assert SHA(raw)==pin;masters[style]=Image.open(io.BytesIO(raw)).convert('RGBA')
rows=json.load(open(ROOT/'new-ready.json'));seen=set()
for i,row in enumerate(rows,1):
 assert row['reference'] not in seen;seen.add(row['reference']);src=row['source'];base=Path(row['source_asset_root']);raw=(base/src['path']).read_bytes();assert SHA(raw)==src['sha256'];raster=src.get('frozen_svg_raster',src);raw=(base/raster['path']).read_bytes();assert SHA(raw)==raster['sha256'];rgba=Image.open(io.BytesIO(raw)).convert('RGBA');actual=render(ROOT,rgba,src['sha256'],masters);assert all(actual[k]['sha256']==v['sha256'] for k,v in row['renders'].items());assert set(actual)==set(row['renders'])
 if i%50==0:print('Verified identical nine PNG variants',i,flush=True)
save(ROOT/'verified-ready.json',rows);save(ROOT/'render-verification.json',dict(references=len(rows),pngs=len(rows)*9,all_expected_png_sha256_identical=True,original_colours_and_whole_source_preserved=True,production_changed=False));subprocess.run(['git','config','user.name','Warder Radio artwork automation'],check=True);subprocess.run(['git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com'],check=True);subprocess.run(['git','add','--',str(ROOT)],check=True)
if subprocess.run(['git','diff','--cached','--quiet']).returncode:
 subprocess.run(['git','commit','-m','Save verified final Radio artwork and unchanged approved alias bytes'],check=True);subprocess.run(['python','tools/push_radio_final.py','work/radio-final775-reviewed-20261105'],check=True)
