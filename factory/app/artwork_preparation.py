"""Conservative artwork extraction. Never alter the source image on disk."""
from PIL import Image, ImageChops


def extract_flat_edge_background(source):
    """Remove a solid edge-connected matte only if foreground is unambiguous.

    Ambiguous, photographic, gradient, or brand-colored backgrounds are kept.
    Returns (RGBA image, extracted flag). The caller can route ambiguous art to QA.
    """
    im = source.convert('RGBA')
    w, h = im.size
    if w < 16 or h < 16:
        return im, False
    px = im.load()
    # A matte must be opaque at every corner and nearly uniform across the border.
    corners = [px[0,0],px[w-1,0],px[0,h-1],px[w-1,h-1]]
    if any(c[3] < 250 for c in corners):
        return im, False
    matte = tuple(round(sum(c[k] for c in corners)/4) for k in range(3))
    if max(max(abs(c[k]-matte[k]) for k in range(3)) for c in corners)>7:
        return im, False
    # Saturated edge fields can be an intentional brand plaque, not disposable matte.
    # Never auto-erase them; keep the original for artwork QA.
    if max(matte)-min(matte)>38:
        return im, False
    border = [px[x,0] for x in range(w)] + [px[x,h-1] for x in range(w)] + [px[0,y] for y in range(h)] + [px[w-1,y] for y in range(h)]
    if sum(c[3]>=250 and max(abs(c[k]-matte[k]) for k in range(3))<=10 for c in border)/len(border)<0.98:
        return im, False
    # Flood-fill ONLY the edge-connected matte; holes and internal brand elements survive.
    from collections import deque
    seen = bytearray(w*h)
    q = deque([(0,0)])
    count = 0
    while q:
        x,y=q.popleft()
        i=y*w+x
        if seen[i]:continue
        seen[i]=1
        c=px[x,y]
        if c[3]<240 or max(abs(c[k]-matte[k]) for k in range(3))>18:continue
        count+=1
        if x:q.append((x-1,y))
        if x+1<w:q.append((x+1,y))
        if y:q.append((x,y-1))
        if y+1<h:q.append((x,y+1))
    # Reject nearly empty and overwhelmingly matte images; do not erase intentional plaques.
    if not (0.12 <= count/(w*h) <= 0.85):
        return im, False
    out=im.copy()
    op=out.load()
    # Recompute connected component for transparency without retaining a giant coordinate set.
    visited=bytearray(w*h)
    q=deque([(0,0)])
    while q:
        x,y=q.popleft()
        i=y*w+x
        if visited[i]:continue
        visited[i]=1
        c=px[x,y]
        if c[3]<240 or max(abs(c[k]-matte[k]) for k in range(3))>18:continue
        op[x,y]=(c[0],c[1],c[2],0)
        if x:q.append((x-1,y))
        if x+1<w:q.append((x+1,y))
        if y:q.append((x,y-1))
        if y+1<h:q.append((x,y+1))
    return out, True
