"""Pinned alpha-component wordmark contrast, retaining protected brand badges."""
from PIL import Image
import hashlib
import base64
import io
import cairosvg
from xml.etree import ElementTree as ET

def components(image):
    pixels=list(image.getdata());w,h=image.size;seen=bytearray(w*h);groups=[]
    for first,p in enumerate(pixels):
        if seen[first] or not p[3]:continue
        seen[first]=1;todo=[first];group=[]
        while todo:
            i=todo.pop();group.append(i);x,y=i%w,i//w
            neighbours=([i-1] if x else [])+([i+1] if x+1<w else [])+([i-w] if y else [])+([i+w] if y+1<h else [])
            for j in neighbours:
                if not seen[j] and pixels[j][3]:seen[j]=1;todo.append(j)
        groups.append(group)
    return pixels,groups

def negative_wordmark(path, spec):
    assert hashlib.sha256(path.read_bytes()).hexdigest()==spec['source_sha256']
    if spec.get('embedded_png'):
        root=ET.fromstring(path.read_bytes());nodes=list(root.iter())
        assert not any(n.tag.split('}')[-1] in ('path','polygon','rect','circle') for n in nodes)
        images=[n for n in nodes if n.tag.split('}')[-1]=='image'];assert len(images)==1
        node=images[0];href=next(v for k,v in node.attrib.items() if k.endswith('href'))
        assert href.startswith('data:image/png;base64,') and node.get('x','0')=='0' and node.get('y','0')=='0'
        image=Image.open(io.BytesIO(base64.b64decode(href.split(',',1)[1]))).convert('RGBA')
        original=image.copy();box=image.getbbox()
    else:
        image=Image.open(path).convert('RGBA')
    image=image.crop(image.getbbox())
    before,groups=components(image)
    assert [len(g) for g in groups]==spec['component_sizes']
    after=list(before)
    colour=tuple(spec.get('target_rgb',(255,255,255)))
    for identity in spec['wordmark_components']:
        for i in groups[identity]:after[i]=colour+(before[i][3],)
    for identity in spec['protected_components']:
        assert all(after[i]==before[i] for i in groups[identity])
    image.putdata(after)
    assert bytes(p[3] for p in after)==bytes(p[3] for p in before)
    if spec.get('embedded_png'):
        # Keep the source SVG's original image dimensions and transforms. Some
        # wrappers deliberately scale their bitmap; replacing only its pixels
        # preserves that exact composition in the negative variant too.
        original.paste(image,box[:2]);buffer=io.BytesIO();original.save(buffer,format='PNG')
        key=next(k for k in node.attrib if k.endswith('href'))
        node.set(key,'data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode('ascii'))
        image=Image.open(io.BytesIO(cairosvg.svg2png(bytestring=ET.tostring(root),output_width=800))).convert('RGBA')
    return image
