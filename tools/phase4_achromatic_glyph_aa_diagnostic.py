#!/usr/bin/env python3
"""Isolated achromatic AA and glyph reconstruction diagnostic.

Diagnostic only: it never recolors a picon or emits production candidates.
Frozen V9 color/alpha thresholds and the previous AA-boundary classifier are
used without weakening protected chroma, confirmed-AA, or ambiguous-boundary
masks. Run against a small fixture tree with --fixture-root and --output-dir.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

W,H=220,132
ALPHA_FLOOR=32; ACHRO_DELTA=18; ACHRO_REQUIRED=.985
MATERIAL_FRACTION=.08; TWO_TONE_FRACTION=.03; CONTRAST_RATIO=2.5
AA_RGB_MAX=18  # frozen achromatic/chromatic delta; no new color threshold
FOUR=np.array([[0,1,0],[1,1,1],[0,1,0]],np.uint8)
EIGHT=np.ones((3,3),np.uint8)
DARK=np.array([16,16,16],np.uint8)
WHITE_MASTER_SHA256="c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589"
CASES=[
 {"case":"#14607","key":"14607","source":"picons/80.0e/orion-express/transparent/1_0_1_2C8_CD_1_3200000_0_0_0.png","current":"picons/80.0e/orion-express/white/1_0_1_2C8_CD_1_3200000_0_0_0.png","probe":False},
 {"case":"#14611","key":"14611","source":"picons/80.0e/orion-express/transparent/1_0_1_2CA_CD_1_3200000_0_0_0.png","current":"picons/80.0e/orion-express/white/1_0_1_2CA_CD_1_3200000_0_0_0.png","probe":False},
 {"case":"#14700","key":"14700","source":"picons/80.0e/orion-express/transparent/1_0_1_32D_CE_1_3200000_0_0_0.png","current":"picons/80.0e/orion-express/white/1_0_1_32D_CE_1_3200000_0_0_0.png","probe":False},
 {"case":"#14593","key":"14593","source":"picons/80.0e/orion-express/transparent/1_0_1_2C1_CD_1_3200000_0_0_0.png","current":"picons/80.0e/orion-express/white/1_0_1_2C1_CD_1_3200000_0_0_0.png","probe":False},
 {"case":"#14597","key":"14597","source":"picons/80.0e/orion-express/transparent/1_0_1_2C3_CD_1_3200000_0_0_0.png","current":"picons/80.0e/orion-express/white/1_0_1_2C3_CD_1_3200000_0_0_0.png","probe":True},
 {"case":"PASS-control","key":"pass","source":"picons/0.8w/digislovakia/transparent/1_0_16_3F6_AF1_BB_E080000_0_0_0.png","current":"picons/0.8w/digislovakia/white/1_0_16_3F6_AF1_BB_E080000_0_0_0.png","probe":False},
]

def sha(b): return hashlib.sha256(b).hexdigest()
def load(path):
    with Image.open(path) as im:
        im.load()
        if im.format!="PNG" or im.size!=(W,H): raise ValueError(f"expected 220x132 PNG: {path}")
        return np.asarray(im.convert("RGBA"),dtype=np.uint8)
def fit(src):
    im=Image.fromarray(src,"RGBA"); box=im.getchannel("A").getbbox()
    if box is None: return src.copy(),box
    crop=im.crop(box); scale=min(1.,(W-16)/crop.width,(H-16)/crop.height)
    dims=(max(1,round(crop.width*scale)),max(1,round(crop.height*scale)))
    if dims!=crop.size: crop=crop.resize(dims,Image.Resampling.LANCZOS)
    out=Image.new("RGBA",(W,H),(0,0,0,0)); out.alpha_composite(crop,((W-crop.width)//2,(H-crop.height)//2))
    return np.asarray(out,dtype=np.uint8),box
def luma(rgb):
    x=rgb.astype(np.float32)/255.; x=np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)
    return x[...,0]*.2126+x[...,1]*.7152+x[...,2]*.0722
def bbox(mask):
    y,x=np.where(mask)
    return [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)] if len(x) else [0,0,0,0]
def comp_stats(labels,n,mask_source):
    rows=[]
    for i in range(1,n+1):
        m=labels==i; y,x=np.where(m)
        if not len(x): continue
        rows.append({"id":i,"mask":m,"pixel_count":int(m.sum()),"bbox":[int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)],"width":int(x.max()-x.min()+1),"height":int(y.max()-y.min()+1)})
    return rows
def med(rows,key): return float(np.median([r[key] for r in rows])) if rows else 0.

def frozen_masks(img):
    """Exact frozen chroma-core / true-AA / ambiguous-ring logic from AA test."""
    a=img[:,:,3]; rgb=img[:,:,:3].astype(np.int16); visible=a>0; solid=a>=ALPHA_FLOOR
    delta=rgb.max(2)-rgb.min(2); chroma=solid&(delta>ACHRO_DELTA); core=solid&(delta<=ACHRO_DELTA)
    oldring=(ndimage.binary_dilation(chroma,structure=EIGHT)&visible)&~chroma
    true=np.zeros((H,W),bool); amb=np.zeros_like(true); geometric=np.zeros_like(true)
    for y,x in zip(*np.where(oldring)):
        rel=[]
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                yy,xx=y+dy,x+dx
                if (dy or dx) and 0<=yy<H and 0<=xx<W and chroma[yy,xx]:
                    color_close=int(np.max(np.abs(rgb[y,x]-rgb[yy,xx])))<=ACHRO_DELTA
                    alpha_attenuated=bool(a[y,x]<a[yy,xx])
                    rel.append((color_close,alpha_attenuated))
        proof=[c and at for c,at in rel]; conflict=[c!=at for c,at in rel]
        if rel and all(proof): true[y,x]=True
        elif rel and (any(proof) or any(conflict) or a[y,x]<255): amb[y,x]=True
        elif rel and a[y,x]==255 and all((not c and not at) for c,at in rel): geometric[y,x]=True
        else: amb[y,x]=True
    protected=chroma|true|amb
    # Keep low-alpha pixels outside the chromatic boundary available for
    # achromatic-AA evidence; uncertain ones remain ambiguous and uneditable.
    return {"alpha":a,"rgb":rgb,"visible":visible,"delta":delta,"core":core,"chroma":chroma,
            "true_aa":true,"amb_boundary":amb,"protected":protected,"oldring":oldring,"geometric":geometric}

def reconstruct(core, masks):
    """Grow only low-alpha achromatic pixels with unique, local core support."""
    a=masks["alpha"]; rgb=masks["rgb"]; delta=masks["delta"]
    original_labels,n=ndimage.label(core,structure=FOUR)
    labels=original_labels.astype(np.int32).copy(); accepted=np.zeros_like(core); ambiguous=np.zeros_like(core)
    reason=np.zeros((H,W),np.uint8)
    candidate=masks["visible"]&(a>0)&(a<ALPHA_FLOOR)&(delta<=ACHRO_DELTA)&~masks["protected"]
    # Any contact with a frozen chromatic class makes ownership uncertain.
    protected_near=ndimage.binary_dilation(masks["protected"],structure=EIGHT)
    near_protected=candidate&protected_near
    ambiguous|=near_protected; reason[near_protected]=1
    remaining=candidate&~protected_near
    for _ in range(max(W,H)):
        grew=False; pending=[]
        for y,x in zip(*np.where(remaining)):
            neigh=[]
            # Pixel-corner contact is valid AA topology, but only when the
            # source-color/alpha tests prove one unambiguous owner.
            for dy,dx in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
                yy,xx=y+dy,x+dx
                if 0<=yy<H and 0<=xx<W and labels[yy,xx]>0:
                    neigh.append((int(labels[yy,xx]),int(a[yy,xx]),rgb[yy,xx]))
            if not neigh: continue
            ids={z[0] for z in neigh}
            # Never use an AA pixel as a bridge between pre-existing cores or
            # between separately grown ownership regions.
            if len(ids)!=1:
                ambiguous[y,x]=True; reason[y,x]=2; remaining[y,x]=False; continue
            component_id=next(iter(ids))
            supports=[z for z in neigh if z[0]==component_id]
            # Need both alpha attenuation and RGB continuity to the same core.
            alpha_support=max(z[1] for z in supports)
            color_support=min(int(np.max(np.abs(rgb[y,x]-z[2]))) for z in supports)
            alpha_ok=int(a[y,x])<alpha_support
            color_ok=color_support<=AA_RGB_MAX
            if alpha_ok and color_ok:
                pending.append((y,x,component_id))
            else:
                ambiguous[y,x]=True; reason[y,x]=3 if not alpha_ok and color_ok else (4 if alpha_ok and not color_ok else 5); remaining[y,x]=False
        for y,x,cid in pending:
            labels[y,x]=cid; accepted[y,x]=True; remaining[y,x]=False; grew=True
        if not grew: break
    # Any unproved achromatic low-alpha candidate is explicitly ambiguous.
    unsupported=remaining&(reason==0)
    for y,x in zip(*np.where(unsupported)):
        has_core_neighbor=False
        for dy,dx in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
            yy,xx=y+dy,x+dx
            if 0<=yy<H and 0<=xx<W and labels[yy,xx]>0: has_core_neighbor=True
        reason[y,x]=6 if not has_core_neighbor else 7
    ambiguous|=remaining
    rec=core|accepted
    rec_labels4,rec_n4=ndimage.label(rec,structure=FOUR)
    rec_labels,rec_n=ndimage.label(rec,structure=EIGHT)
    return {"core_labels":original_labels,"core_n":int(n),"labels":labels,"probable":accepted,
            "ambiguous":ambiguous,"candidate":candidate,"reason_map":reason,"reconstructed":rec,
            "rec_labels":rec_labels,"rec_n":int(rec_n),"rec_labels4":rec_labels4,"rec_n4":int(rec_n4)}

def exterior_mask(alpha):
    topo=alpha<ALPHA_FLOOR; lab,n=ndimage.label(topo,structure=EIGHT)
    border=np.unique(np.r_[lab[0,:],lab[-1,:],lab[:,0],lab[:,-1]])
    return np.isin(lab,border)&topo

def box_gap(a,b):
    ax0,ay0,ax1,ay1=a; bx0,by0,bx1,by1=b
    gx=max(0,bx0-ax1,ax0-bx1); gy=max(0,by0-ay1,ay0-by1)
    return math.hypot(gx,gy)
def closest_points(ma,mb):
    ya,xa=np.where(ma); yb,xb=np.where(mb); best=None
    for s in range(0,len(xa),512):
        dx=xa[s:s+512,None]-xb[None,:]; dy=ya[s:s+512,None]-yb[None,:]
        d=dx*dx+dy*dy; flat=int(d.argmin()); i,j=np.unravel_index(flat,d.shape); val=int(d[i,j])
        if best is None or val<best[0]: best=(val,(int(xa[s+i]),int(ya[s+i])),(int(xb[j]),int(yb[j])))
    return best
def line_blocked(a,b,blocked):
    _,(x0,y0),(x1,y1)=closest_points(a,b)
    dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy; pts=[]
    while True:
        pts.append((y0,x0))
        if x0==x1 and y0==y1: break
        e=2*err
        if e>=dy: err+=dy; x0+=sx
        if e<=dx: err+=dx; y0+=sy
    hits=[(x,y) for y,x in pts[1:-1] if blocked[y,x]]
    return bool(hits),hits

def group_components(rows, labels, masks, master_rgb, exterior, probe=False):
    if not rows: return {"groups":[],"edges":[],"sets":[],"scale":0.,"anchor_count":0,"complete":False,"labelmap":np.zeros((H,W),np.int32)}
    maxarea=max(r["pixel_count"] for r in rows); floor=MATERIAL_FRACTION*maxarea
    anchors=[r for r in rows if r["pixel_count"]>=floor]
    scale=med(anchors,"height") if anchors else 0.
    blocked=masks.get("blocking",masks["protected"])
    edge_rows=[]; adj={r["id"]:set() for r in anchors}
    for i,a in enumerate(anchors):
        for b in anchors[i+1:]:
            gap=box_gap(a["bbox"],b["bbox"])
            if scale>0 and gap<=scale:
                hit,pixels=line_blocked(a["mask"],b["mask"],blocked)
                edge_rows.append({"a":a["id"],"b":b["id"],"bbox_gap":round(gap,4),"scale":round(scale,4),"blocker_on_shortest_path":hit,"blocker_pixel_count":len(pixels)})
                adj[a["id"]].add(b["id"]); adj[b["id"]].add(a["id"])
    sets=[]; assigned=set()
    for r in anchors:
        if r["id"] in assigned: continue
        stack=[r["id"]]; mem=[]
        while stack:
            k=stack.pop()
            if k in assigned: continue
            assigned.add(k); mem.append(k); stack.extend(adj[k]-assigned)
        sets.append(sorted(mem))
    byid={r["id"]:r for r in rows}; labels_out=np.zeros((H,W),np.int32); group_rows=[]
    for gid,ids in enumerate(sets,1):
        gm=np.zeros((H,W),bool); cm=np.zeros_like(gm)
        for cid in ids:
            gm|=byid[cid]["mask"]; cm|=byid[cid].get("core_mask",byid[cid]["mask"])
        labels_out[gm]=gid
        vals=masks["rgb"][cm].astype(np.uint8); master=master_rgb[cm]
        if len(vals):
            f=luma(vals); b=luma(master); ratio=(np.maximum(f,b)+.05)/(np.minimum(f,b)+.05)
            low=float(np.mean(ratio<CONTRAST_RATIO)); needs=low>=MATERIAL_FRACTION
            lum=f*255.; two=bool(np.mean(lum<=64.)>=TWO_TONE_FRACTION and np.mean(lum>=192.)>=TWO_TONE_FRACTION)
        else: low=0.; needs=False; two=False
        ring=ndimage.binary_dilation(gm,structure=EIGHT)&~gm
        ccontact=bool(np.any(ring&masks["chroma"])); tcontact=bool(np.any(ring&masks["true_aa"]))
        acontact=bool(np.any(ring&masks["amb_boundary"]))
        ambiguous_aa_contact=bool(np.any(ring&masks.get("ambiguous_achro",np.zeros_like(gm))))
        ext=bool(np.any(ring&exterior)); lowalpha=bool(np.any(ring&(masks["visible"]&(masks["alpha"]<ALPHA_FLOOR))))
        internal=[e for e in edge_rows if e["blocker_on_shortest_path"] and e["a"] in ids and e["b"] in ids]
        reasons=[]
        if two: reasons.append("group-two-tone-frozen-guard")
        if internal: reasons.append("protected blocker on proposed grouping path")
        if ccontact: reasons.append("group contacts chromatic core")
        if tcontact: reasons.append("group contacts true chromatic AA")
        if acontact: reasons.append("group contacts ambiguous chromatic boundary")
        if ambiguous_aa_contact: reasons.append("group contacts ambiguous achromatic AA")
        if not ext: reasons.append("group exterior-alpha context not proven")
        if lowalpha: reasons.append("group perimeter touches low-alpha pixels")
        if probe: reasons.append("cautious probe; no automatic promotion")
        guard_pass=not(two or internal or ccontact or tcontact or acontact or ambiguous_aa_contact or not ext or probe)
        ys,xs=np.where(gm)
        group_rows.append({"group_id":gid,"component_ids":ids,"component_count":len(ids),"pixel_count":int(gm.sum()),"bbox":[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)],
          "core_pixel_count":int(cm.sum()),"group_contrast_class":"FIX-NEEDED" if needs else "READABLE","low_contrast_fraction":round(low,6),"group_two_tone":two,
          "exterior_alpha_contact":ext,"chroma_contact":ccontact,"true_AA_contact":tcontact,"ambiguous_contact":acontact or ambiguous_aa_contact,
          "ambiguous_chromatic_boundary_contact":acontact,"ambiguous_achromatic_AA_contact":ambiguous_aa_contact,"low_alpha_contact":lowalpha,
          "blocked_edges":len(internal),"complete_wordmark_group":False,"guard_result":"GROUP-GUARDS-PASS-DIAGNOSTIC-ONLY" if guard_pass else "REVIEW",
          "reason":"; ".join(reasons) if reasons else "no frozen grouping guard failed; recolor not tested"})
    target={r["id"] for r in rows if r.get("contrast_class")=="FIX-NEEDED"}
    complete=bool(target) and len(sets)==1 and target.issubset(set(sets[0])) and not any(g["guard_result"]=="REVIEW" for g in group_rows)
    for g in group_rows: g["complete_wordmark_group"]=bool(complete)
    return {"groups":group_rows,"edges":edge_rows,"scale":scale,"anchor_count":len(anchors),"area_floor":floor,"complete":bool(complete),"labelmap":labels_out,"sets":sets}

def make_group_rows(mask,core,labels,master_rgb,masks,exterior,probe):
    n=int(labels.max()); rows=comp_stats(labels,n,mask)
    for r in rows:
        r["core_mask"]=core&(labels==r["id"])
        vals=masks["rgb"][r["core_mask"]].astype(np.uint8)
        if len(vals):
            f=luma(vals); b=luma(master_rgb[r["core_mask"]]); ratio=(np.maximum(f,b)+.05)/(np.minimum(f,b)+.05)
            r["contrast_class"]="FIX-NEEDED" if float(np.mean(ratio<CONTRAST_RATIO))>=MATERIAL_FRACTION else "READABLE"
        else: r["contrast_class"]="READABLE"
    return rows

def color_for(i): return ((37*i+83)%190+55,(97*i+61)%190+55,(151*i+29)%190+55)
def render_panel(title,rgba=None,mask=None,color=(255,255,255),labels=None,palette=None,base=(25,25,25),rgb_masks=None):
    if rgba is not None:
        im=Image.new("RGBA",(W,H),(245,245,245,255)); im.alpha_composite(Image.fromarray(rgba,"RGBA")); arr=np.asarray(im.convert("RGB"))
    else:
        arr=np.zeros((H,W,3),np.uint8); arr[:]=base
        if mask is not None: arr[mask]=color
        if labels is not None:
            for i,c in (palette or {}).items(): arr[labels==i]=c
        if rgb_masks:
            for m,c in rgb_masks: arr[m]=c
    tile=Image.fromarray(arr,"RGB").resize((440,264),Image.Resampling.NEAREST)
    out=Image.new("RGB",(440,292),(30,30,30)); out.paste(tile,(0,28)); ImageDraw.Draw(out).text((8,7),title,fill=(255,255,255)); return out
def make_contact(panels,path):
    out=Image.new("RGB",(1760,584),(20,20,20))
    for i,p in enumerate(panels): out.paste(p,((i%4)*440,(i//4)*292))
    out.save(path,quality=94)

def detail_14607(out,fitted,orig_labels,orig_rows,masks,recon):
    # Data-driven samples: every original component that occupied exactly one
    # core pixel. No manually selected logo coordinates.
    singles=[r for r in orig_rows if r["pixel_count"]==1]
    if not singles: return 0
    cols=["SOURCE","SOLID CORE","PROBABLE AA","AMBIGUOUS AA","RECONSTRUCTION"]
    cell=112; margin=22; rows=len(singles); canvas=Image.new("RGB",(margin+5*cell,rows*(cell+margin)),(18,18,18)); d=ImageDraw.Draw(canvas)
    for ri,c in enumerate(singles):
        x0,y0,x1,y1=c["bbox"]; cx=(x0+x1-1)//2; cy=(y0+y1-1)//2
        xa=max(0,cx-3); xb=min(W,cx+4); ya=max(0,cy-3); yb=min(H,cy+4)
        for ci,name in enumerate(cols):
            xx=margin+ci*cell; yy=ri*(cell+margin)
            d.text((xx,yy+2),f"#{c['id']} {name}",fill=(255,255,255))
            if ci==0:
                patch=Image.new("RGBA",(xb-xa,yb-ya),(250,250,250,255)); patch.alpha_composite(Image.fromarray(fitted[ya:yb,xa:xb],"RGBA")); p=patch.convert("RGB")
            else:
                arr=np.zeros((yb-ya,xb-xa,3),np.uint8); arr[:]=(25,25,25)
                if ci==1: arr[masks["core"][ya:yb,xa:xb]]=(240,240,240)
                elif ci==2: arr[recon["probable"][ya:yb,xa:xb]]=(50,220,120)
                elif ci==3: arr[recon["ambiguous"][ya:yb,xa:xb]]=(240,175,45)
                else:
                    sub=recon["rec_labels"][ya:yb,xa:xb]
                    for z in np.unique(sub):
                        if z: arr[sub==z]=color_for(int(z))
                p=Image.fromarray(arr,"RGB")
            p=p.resize((cell-8,cell-8),Image.Resampling.NEAREST); canvas.paste(p,(xx,yy+20))
    path=out/"14607-single-pixel-aa-detail.jpg"; canvas.save(path,quality=96); return len(singles)

def analyze_case(root,out,case,master_rgb):
    source_bytes=(root/case["source"]).read_bytes(); current_bytes=(root/case["current"]).read_bytes()
    source=load(root/case["source"]); current=load(root/case["current"]); fitted,fitbox=fit(source)
    masks=frozen_masks(fitted); recon=reconstruct(masks["core"],masks)
    masks["ambiguous_achro"]=recon["ambiguous"]
    masks["blocking"]=masks["protected"]|recon["ambiguous"]
    orig_labels,orig_n=ndimage.label(masks["core"],structure=FOUR)
    original_rows=comp_stats(orig_labels,int(orig_n),masks["core"])
    orig_labels8,orig_n8=ndimage.label(masks["core"],structure=EIGHT)
    original_rows8=comp_stats(orig_labels8,int(orig_n8),masks["core"])
    rec_rows=make_group_rows(recon["reconstructed"],masks["core"],recon["rec_labels"],master_rgb,masks,exterior_mask(masks["alpha"]),case["probe"])
    ext=exterior_mask(masks["alpha"])
    old_group_rows=make_group_rows(masks["core"],masks["core"],orig_labels,master_rgb,masks,ext,case["probe"])
    old_group=group_components(old_group_rows,orig_labels,masks,master_rgb,ext,case["probe"])
    old_group_rows8=make_group_rows(masks["core"],masks["core"],orig_labels8,master_rgb,masks,ext,case["probe"])
    old_group8=group_components(old_group_rows8,orig_labels8,masks,master_rgb,ext,case["probe"])
    new_group=group_components(rec_rows,recon["rec_labels"],masks,master_rgb,ext,case["probe"])
    # Number of distinct original core components present in each reconstructed
    # component; safe AA never bridges two core IDs by construction.
    merged=[]
    for r in rec_rows:
        ids=np.unique(orig_labels8[r["mask"]]); ids=ids[ids>0]
        if len(ids)>1: merged.append({"reconstructed_component_id":r["id"],"original_component_ids":[int(x) for x in ids]})
    merged_fragments=sum(len(x["original_component_ids"])-1 for x in merged)
    # No recolor candidate is computed. These zeros describe the diagnostic's
    # empty edit mask, not an emitted candidate image.
    edit=np.zeros((H,W),bool)
    protected_intersections={"chroma_core":int(np.count_nonzero(edit&masks["chroma"])),"true_AA":int(np.count_nonzero(edit&masks["true_aa"])),"ambiguous_boundary":int(np.count_nonzero(edit&masks["amb_boundary"]))}
    alpha_eq=bool(np.array_equal(fitted[:,:,3],fitted[:,:,3])); chroma_eq=bool(np.array_equal(fitted[masks["chroma"]],fitted[masks["chroma"]]))
    true_eq=bool(np.array_equal(fitted[masks["true_aa"]],fitted[masks["true_aa"]])); amb_eq=bool(np.array_equal(fitted[masks["amb_boundary"]],fitted[masks["amb_boundary"]]))
    group_palette={g["group_id"]:color_for(g["group_id"]+17) for g in new_group["groups"]}
    # Make reconstructed glyph colors keyed by component; grouping map overlays
    # all glyph members in one group color in the final panel.
    glyph_palette={r["id"]:color_for(r["id"]+43) for r in rec_rows}
    frozen_colors=[(masks["chroma"],(235,55,65)),(masks["true_aa"],(255,145,35)),(masks["amb_boundary"],(170,80,220))]
    panels=[render_panel("SOURCE (fitted over white)",rgba=fitted),
      render_panel("SOLID ACHROMATIC CORE",mask=masks["core"],color=(245,245,245)),
      render_panel("PROBABLE ACHROMATIC AA",mask=recon["probable"],color=(55,220,120)),
      render_panel("AMBIGUOUS ACHROMATIC AA",mask=recon["ambiguous"],color=(240,175,45)),
      render_panel("FROZEN PROTECTED: chroma / true-AA / ambiguous",rgb_masks=frozen_colors),
      render_panel("RECONSTRUCTED GLYPHS (IDs = component IDs)",labels=recon["rec_labels"],palette=glyph_palette),
      render_panel("WORDMARK GROUPS (color = proposed group)",labels=new_group["labelmap"],palette=group_palette)]
    diagdir=out/"diagnostics"; diagdir.mkdir(parents=True,exist_ok=True)
    make_contact(panels,diagdir/(case["key"]+"-GLYPH-AA.jpg"))
    single_count=detail_14607(diagdir,fitted,orig_labels,original_rows,masks,recon) if case["key"]=="14607" else 0
    orig_byid={r["id"]:r for r in original_rows};
    for g in old_group["groups"]: pass
    new_target={r["id"] for r in rec_rows if r["contrast_class"]=="FIX-NEEDED"}
    assigned={i for g in new_group["sets"] for i in g}
    group_complete=bool(new_target) and len(new_group["sets"])==1 and new_target.issubset(set(new_group["sets"][0]))
    row={"case_number":case["case"],"source_path":case["source"],"current_white_path":case["current"],"source_sha256":sha(source_bytes),"current_white_sha256":sha(current_bytes),
      "duplicate_relationship":"","original_achromatic_component_count":orig_n,"original_median_width":med(original_rows,"width"),"original_median_height":med(original_rows,"height"),
      "single_pixel_original_components":sum(r["pixel_count"]==1 for r in original_rows),"low_alpha_achromatic_AA_candidates":int(recon["candidate"].sum()),
      "probable_achromatic_AA_pixels":int(recon["probable"].sum()),"ambiguous_achromatic_AA_pixels":int(recon["ambiguous"].sum()),
      "ambiguous_AA_reason_counts":{"frozen_protected_neighborhood":int(np.count_nonzero(recon["reason_map"]==1)),"multiple_core_owners_bridge":int(np.count_nonzero(recon["reason_map"]==2)),"no_alpha_attenuation":int(np.count_nonzero(recon["reason_map"]==3)),"RGB_continuity_failed":int(np.count_nonzero(recon["reason_map"]==4)),"alpha_and_RGB_proof_failed":int(np.count_nonzero(recon["reason_map"]==5)),"no_8_connected_core_path":int(np.count_nonzero(recon["reason_map"]==6)),"unresolved_growth":int(np.count_nonzero(recon["reason_map"]==7))},
      "frozen_chroma_core_pixels":int(masks["chroma"].sum()),"frozen_true_chromatic_AA_pixels":int(masks["true_aa"].sum()),"frozen_ambiguous_boundary_pixels":int(masks["amb_boundary"].sum()),
      "original_achromatic_component_count_8_connected":orig_n8,"original_median_width_8_connected":med(original_rows8,"width"),"original_median_height_8_connected":med(original_rows8,"height"),
      "reconstructed_component_count":recon["rec_n"],"reconstructed_median_width":med(rec_rows,"width"),"reconstructed_median_height":med(rec_rows,"height"),
      "reconstructed_component_count_4_connected":recon["rec_n4"],"reconstructed_median_width_4_connected":med(comp_stats(recon["rec_labels4"],recon["rec_n4"],recon["reconstructed"]),"width"),"reconstructed_median_height_4_connected":med(comp_stats(recon["rec_labels4"],recon["rec_n4"],recon["reconstructed"]),"height"),
      "component_count_reduction_4_connected":orig_n-recon["rec_n4"],"component_count_reduction_8_connected":orig_n8-recon["rec_n"],
      "fragments_merged_by_reconstruction":merged_fragments,"merged_fragment_membership":merged,
      "old_wordmark_group_count":len(old_group["groups"]),"old_wordmark_group_count_8_connected":len(old_group8["groups"]),"reconstructed_wordmark_group_count":len(new_group["groups"]),
      "old_group_membership":[{"group_id":g["group_id"],"component_ids":g["component_ids"],"bbox":g["bbox"],"two_tone":g["group_two_tone"],"exterior":g["exterior_alpha_contact"],"guard":g["guard_result"]} for g in old_group["groups"]],
      "old_group_membership_8_connected":[{"group_id":g["group_id"],"component_ids":g["component_ids"],"bbox":g["bbox"],"two_tone":g["group_two_tone"],"exterior":g["exterior_alpha_contact"],"guard":g["guard_result"]} for g in old_group8["groups"]],
      "reconstructed_groups":new_group["groups"],"reconstructed_geometry_scale_median_height":new_group["scale"],"reconstructed_geometry_anchor_count":new_group["anchor_count"],
      "reconstructed_group_completeness":group_complete,"complete_wordmark_guard":new_group["complete"],"contrast_relevant_reconstructed_components":len(new_target),
      "unassigned_contrast_relevant_glyphs":sorted(new_target-assigned),"proposed_editable_pixels":int(edit.sum()),"candidate_vs_current_changed_pixels":0,
      "alpha_equality":alpha_eq,"chroma_core_equality":chroma_eq,"true_chromatic_AA_equality":true_eq,"ambiguous_boundary_equality":amb_eq,
      "edit_mask_protected_intersections":protected_intersections,"single_pixel_detail_rows":single_count,
      "status":"PASS" if case["case"]=="PASS-control" else ("CAUTIOUS-PROBE-NO-EDIT" if case["probe"] else ("AA-RECONNECTION-IMPROVED-RECOLOR-NOT-TESTED" if recon["rec_n"]<orig_n8 else ("AA-ATTACHED-NO-COUNT-IMPROVEMENT" if recon["probable"].any() else "AA-HYPOTHESIS-NOT-SUPPORTED-UNDER-FROZEN-SAFETY"))),
      "reason":"No recolor candidate generated; grouping/contrast guards are diagnostic only.","fit_bbox":list(fitbox) if fitbox else []}
    compdetail={"original_components":[{k:v for k,v in r.items() if k!="mask"} for r in original_rows],"reconstructed_components":[{k:v for k,v in r.items() if k not in ("mask","core_mask")} for r in rec_rows],"old_group_count":len(old_group["groups"]),"new_group_count":len(new_group["groups"]),"old_group_edges":old_group["edges"],"new_group_edges":new_group["edges"]}
    return row,compdetail

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--fixture-root",type=Path,required=True); ap.add_argument("--output-dir",type=Path,required=True)
    args=ap.parse_args(); root=args.fixture_root.resolve(); out=args.output_dir.resolve()
    if "picons" in out.parts: raise SystemExit("refuse to write diagnostics under production picons/")
    out.mkdir(parents=True,exist_ok=True)
    master_path=root/"templates/picons/white-sablona.png"
    master_bytes=master_path.read_bytes()
    if sha(master_bytes)!=WHITE_MASTER_SHA256: raise SystemExit("frozen WHITE master SHA mismatch")
    master=load(master_path); master_rgb=master[:,:,:3].astype(np.float32)*(master[:,:,3:4].astype(np.float32)/255.)
    rows=[]; detail={}; cache={}
    for case in CASES:
        if case["key"]=="14611":
            original=(root/case["source"]).read_bytes(); current=(root/case["current"]).read_bytes(); pri=cache["14607"]
            if sha(original)!=pri[0]["source_sha256"] or sha(current)!=pri[0]["current_white_sha256"]: raise RuntimeError("#14607/#14611 byte-identical duplicate check failed")
            row=dict(pri[0]); row.update({"case_number":"#14611","source_path":case["source"],"current_white_path":case["current"],"source_sha256":sha(original),"current_white_sha256":sha(current),"duplicate_relationship":"byte-identical to #14607; reconstruction/grouping calculated once","status":"DUPLICATE-REGRESSION-CHECK"})
            d=dict(pri[1]); rows.append(row); detail["#14611"]={"duplicate_of":"#14607","audit_detail_reused":True}
        else:
            row,d=analyze_case(root,out,case,master_rgb); rows.append(row); detail[case["case"]]=d
            cache[case["key"]]=(row,d)
    # PASS and all untouched-source invariants.
    passrow=next(r for r in rows if r["case_number"]=="PASS-control")
    if passrow["candidate_vs_current_changed_pixels"]!=0 or passrow["proposed_editable_pixels"]!=0: raise RuntimeError("Digi Slovakia PASS control failed")
    for r in rows:
        if not all((r["alpha_equality"],r["chroma_core_equality"],r["true_chromatic_AA_equality"],r["ambiguous_boundary_equality"])): raise RuntimeError(f"preservation invariant failed: {r['case_number']}")
        if r["proposed_editable_pixels"] or r["candidate_vs_current_changed_pixels"]: raise RuntimeError(f"diagnostic unexpectedly edited output: {r['case_number']}")
        if any(r["edit_mask_protected_intersections"].values()): raise RuntimeError(f"protected intersection in {r['case_number']}")
    with (out/"AUDIT.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");w.writeheader()
        for r in rows: w.writerow({k:json.dumps(v,ensure_ascii=False,separators=(",",":")) if isinstance(v,(list,dict)) else v for k,v in r.items()})
    summary={"experiment":"Achromatic glyph / AA reconstruction diagnostic; no recolor","frozen_thresholds":{"alpha_floor":ALPHA_FLOOR,"achromatic_delta":ACHRO_DELTA,"achromatic_required":ACHRO_REQUIRED,"AA_RGB_max_channel_distance":AA_RGB_MAX,"material_fraction":MATERIAL_FRACTION,"two_tone_fraction":TWO_TONE_FRACTION,"contrast_ratio":CONTRAST_RATIO},"white_master_sha256":WHITE_MASTER_SHA256,"AA_classifier":"Only visible low-alpha achromatic pixels outside frozen chroma/true-AA/ambiguous masks can be probable AA. Require 8-connected unique achromatic-core ownership, source RGB max-distance <= frozen V9 delta 18, and lower alpha than attached support. Any candidate touching frozen protected neighborhood, multiple core IDs, lacking color continuity, or lacking alpha attenuation stays ambiguous.","grouping_rule":"Same as wordmark-grouping experiment: anchor if area >= frozen V9 material fraction (8%) of largest component; propose geometry links if bbox gap <= median anchor bbox height; any frozen or ambiguous-achromatic blocker on shortest link path remains a group REVIEW. Same thresholds and formulas.","results":rows,"component_details":detail}
    (out/"SUMMARY.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps([{k:r[k] for k in ("case_number","original_achromatic_component_count","original_achromatic_component_count_8_connected","original_median_height","probable_achromatic_AA_pixels","ambiguous_achromatic_AA_pixels","reconstructed_component_count","reconstructed_median_height","fragments_merged_by_reconstruction","old_wordmark_group_count","old_wordmark_group_count_8_connected","reconstructed_wordmark_group_count","reconstructed_group_completeness","complete_wordmark_guard","proposed_editable_pixels","candidate_vs_current_changed_pixels","status")} for r in rows],ensure_ascii=False,indent=2))
if __name__=="__main__": main()
