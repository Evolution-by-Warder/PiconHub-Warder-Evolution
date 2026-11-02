"""Reproduce the authorized Warder import from immutable sources and reviewed masks.

Pillow 12.3.0. Developer tooling only; not included in receiver IPKs.
SVG originals are preserved beside their pinned, normalized canonical PNGs.
No colour threshold or component guessing runs during reproduction.
"""
from pathlib import Path
import hashlib,io,json
from PIL import Image

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
PLAN=json.loads((BASE/'publication-plan.json').read_text())
SHA=lambda b:hashlib.sha256(b).hexdigest()
def checked(entry):
    raw=(ROOT/entry['path']).read_bytes()
    assert SHA(raw)==entry['sha256'],entry['path']
    return raw
def protected_digest(pixels,mask):
    return SHA(bytes(c for pixel,selected in zip(pixels,mask) if not selected for c in pixel))
for style,digest in PLAN['template_sha256'].items():
    assert SHA((BASE.parents[1]/'templates/picons'/(style+'-sablona.png')).read_bytes())==digest
count=0
for item in PLAN['artwork']:
    if item['method']=='EXACT_EXISTING_WARDER_ARTWORK':
        outputs={style:checked(entry) for style,entry in item['sources'].items()}
    else:
        raw=checked(item['canonical_source'])
        original=Image.open(io.BytesIO(raw)).convert('RGBA')
        assert original.size==(220,132)
        pixels=list(original.get_flattened_data())
        outputs={'transparent':raw}
        for style in ('white','black'):
            foreground=original.copy()
            if style in item['contrast_masks']:
                entry=item['contrast_masks'][style]
                mask_image=Image.open(io.BytesIO(checked(entry))).convert('L')
                assert mask_image.size==original.size
                mask=list(mask_image.get_flattened_data())
                assert set(mask)<={0,255} and sum(bool(x) for x in mask)==entry['pixels']
                assert protected_digest(pixels,mask)==entry['protected_pixels_sha256']
                changed=[]
                for (r,g,b,a),selected in zip(pixels,mask):
                    assert not selected or a>0
                    if selected:
                        rgb=(255-r,255-g,255-b) if entry['operation']=='invert' else tuple(entry['colour'])
                        changed.append((*rgb,a))
                    else:changed.append((r,g,b,a))
                assert protected_digest(changed,mask)==entry['protected_pixels_sha256']
                assert all(a[3]==b[3] for a,b in zip(changed,pixels))
                foreground.putdata(changed)
            mark=foreground.crop(foreground.getchannel('A').getbbox())
            mark.thumbnail((204,116),Image.Resampling.LANCZOS)
            canvas=Image.open(BASE.parents[1]/'templates/picons'/(style+'-sablona.png')).convert('RGBA')
            canvas.alpha_composite(mark,((220-mark.width)//2,(132-mark.height)//2))
            output=io.BytesIO();canvas.save(output,format='PNG');outputs[style]=output.getvalue()
    for style,entry in item['outputs'].items():
        raw=outputs[style]
        assert SHA(raw)==entry['sha256'],(item['slug'],style)
        (ROOT/entry['path']).write_bytes(raw)
        count+=1
assert count==PLAN['artwork_count']==189
print('Reproduced and SHA256-verified 189 PNGs; all protected component pixels and source alpha preserved.')
