"""Pinned alpha-component wordmark contrast, retaining protected brand badges."""
from PIL import Image
import hashlib

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
    image=Image.open(path).convert('RGBA');image=image.crop(image.getbbox())
    before,groups=components(image)
    assert [len(g) for g in groups]==spec['component_sizes']
    after=list(before)
    for identity in spec['wordmark_components']:
        for i in groups[identity]:after[i]=(255,255,255,before[i][3])
    for identity in spec['protected_components']:
        assert all(after[i]==before[i] for i in groups[identity])
    image.putdata(after)
    assert bytes(p[3] for p in after)==bytes(p[3] for p in before)
    return image
