"""Reproduce the authorized derivatives from preserved original PNGs.

Build dependency: Pillow 12.3.0 (PNG encodings are verified by the plan).
This developer tool is not installed on receivers.
"""
from pathlib import Path
import hashlib,io,json
from PIL import Image

BASE=Path(__file__).resolve().parent
PLAN=json.loads((BASE/'publication-plan.json').read_text())
TEMPLATES=BASE.parents[1]/'templates/picons'
SHA=lambda b:hashlib.sha256(b).hexdigest()
for style,digest in PLAN['template_sha256'].items():
    assert SHA((TEMPLATES/(style+'-sablona.png')).read_bytes())==digest
for item in PLAN['artwork']:
    raw=(BASE/'source'/(item['slug']+'.png')).read_bytes()
    assert SHA(raw)==item['source_sha256']
    image=Image.open(io.BytesIO(raw)).convert('RGBA')
    mark=image.crop(image.getchannel('A').getbbox())
    mark.thumbnail((204,116),Image.Resampling.LANCZOS)
    for style,entry in item['outputs'].items():
        if style=='transparent' and image.size==(220,132):output=raw
        else:
            foreground=mark.copy()
            if style=='white' and item['slug'] in ('tvge-internacional','disney-cinema','tv5-monde-info','klan-nostalgji','aurora-tv'):
                foreground.putdata([(20,20,20,a) if min(r,g,b)>220 and a>0 else (r,g,b,a) for r,g,b,a in foreground.get_flattened_data()])
            canvas=Image.new('RGBA',(220,132)) if style=='transparent' else Image.open(TEMPLATES/(style+'-sablona.png')).convert('RGBA')
            canvas.alpha_composite(foreground,((220-foreground.width)//2,(132-foreground.height)//2))
            stream=io.BytesIO();canvas.save(stream,format='PNG');output=stream.getvalue()
        assert SHA(output)==entry['sha256'],(item['slug'],style)
        (BASE/'artwork'/style/(item['slug']+'.png')).write_bytes(output)
print('Verified and reproduced 30 authorized PNGs')
