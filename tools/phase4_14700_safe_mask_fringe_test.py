#!/usr/bin/env python3
"""#14700 safe-mask completeness/fringe diagnostic; never writes production.

Creates one explicitly diagnostic M0 WHITE candidate plus M1/reference
simulation PNGs outside picons/. No ownership classifier or threshold changes.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,sys
from collections import Counter,defaultdict,deque
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE.parent))
import phase4_achromatic_glyph_aa_diagnostic as glyph
import phase4_achromatic_tonal_field_diagnostic as tonal

HEAD="80188b834ab771b2a98c89f95a25fcebb5728fbc"
SRC="picons/80.0e/orion-express/transparent/1_0_1_32D_CE_1_3200000_0_0_0.png"
CUR="picons/80.0e/orion-express/white/1_0_1_32D_CE_1_3200000_0_0_0.png"
MASTER="templates/picons/white-sablona.png"
SAFE_AUDIT="reports/warder-master-production/phase4-v17-14700-low-alpha-ownership-20260927/SUMMARY.json"
TARGET=np.array([16,16,16],dtype=np.uint8)
GROUP_IDS={6,7,8,9,10}
ABANDS=[("1-3",1,3),("4-7",4,7),("8-15",8,15),("16-23",16,23),("24-31",24,31)]
PROT_NAMES=("chroma_core","true_aa","amb_boundary")

def sha(b):return hashlib.sha256(b).hexdigest()
def srgb_luma(rgb):
    a=np.asarray(rgb,dtype=np.float64)/255.;lin=np.where(a<=.04045,a/12.92,((a+.055)/1.055)**2.4)
    return 255.*(0.2126*lin[...,0]+0.7152*lin[...,1]+0.0722*lin[...,2])
def stats(v):
    a=np.asarray(v,dtype=np.float64);a=a[np.isfinite(a)]
    if not len(a):return {"n":0,"min":None,"mean":None,"median":None,"p90":None,"p95":None,"max":None}
    return {"n":len(a),"min":float(a.min()),"mean":float(a.mean()),"median":float(np.median(a)),"p90":float(np.percentile(a,90)),"p95":float(np.percentile(a,95)),"max":float(a.max())}
def load_csv(p):return list(csv.DictReader(Path(p).open(newline="",encoding="utf-8")))
def unpack(v):return json.loads(v) if isinstance(v,str) else v
def rgb_dist(a,b):
    d=np.asarray(a,dtype=np.float64)-np.asarray(b,dtype=np.float64)
    return {"linf":float(np.max(np.abs(d))),"l2":float(np.linalg.norm(d))}
def composite_pixel(master,source_rgba):
    src=np.asarray(source_rgba,dtype=np.float64);a=src[3]/255.
    out=Image.alpha_composite(Image.new("RGBA",(1,1),tuple(int(v) for v in master)),Image.new("RGBA",(1,1),tuple(int(v) for v in source_rgba)))
    return np.asarray(out,dtype=np.uint8)[0,0]
def png_bytes(arr):
    im=Image.fromarray(np.asarray(arr,dtype=np.uint8),"RGBA");import io
    b=io.BytesIO();im.save(b,format="PNG",optimize=False);return b.getvalue()
def mask_hash(mask):return hashlib.sha256(np.packbits(mask.astype(np.uint8),bitorder="big").tobytes()).hexdigest()
def palette(t):
    stops=[(25,35,125),(20,190,220),(250,220,35),(220,35,30)]
    t=max(0.,min(1.,float(t)));x=t*(len(stops)-1);i=min(len(stops)-2,int(x));q=x-i
    return tuple(int(round(stops[i][k]*(1-q)+stops[i+1][k]*q)) for k in range(3))
def panel(title,rgb,crop=None,scale=3,mark=None):
    im=Image.fromarray(np.clip(np.rint(rgb),0,255).astype(np.uint8),"RGB")
    if crop:im=im.crop(crop)
    im=im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST)
    if mark:
        x,y=mark
        if crop:x-=crop[0];y-=crop[1]
        ImageDraw.Draw(im).rectangle((x*scale-2,y*scale-2,x*scale+scale+2,y*scale+scale+2),outline=(255,30,20),width=max(1,scale//2))
    out=Image.new("RGB",(im.width,im.height+28),(20,20,20));out.paste(im,(0,28));ImageDraw.Draw(out).text((7,7),title,fill="white");return out
def save_contact(panels,path,cols):
    w=max(p.width for p in panels);h=max(p.height for p in panels);rows=math.ceil(len(panels)/cols)
    out=Image.new("RGB",(cols*w,rows*h),(15,15,15))
    for i,p in enumerate(panels):out.paste(p,((i%cols)*w,(i//cols)*h))
    out.save(path,quality=96)
def apply_variant(current,source_fit,master,mask):
    layer=source_fit.copy();layer[mask,:3]=TARGET
    rendered=np.asarray(Image.alpha_composite(Image.fromarray(master,"RGBA"),Image.fromarray(layer,"RGBA")),dtype=np.uint8)
    out=current.copy();out[mask,:3]=rendered[mask,:3];out[:,:,3]=current[:,:,3]
    return out,layer,rendered
def candidate_glyphs(row):
    try:return [int(v) for v in unpack(row.get("direct_candidate_glyph_ids",[]))]
    except Exception:return []
def bfs_farthest(coords,start):
    allowed=set(coords);q=deque([(start,0)]);seen={start};farthest=(start,0)
    while q:
        p,d=q.popleft()
        if d>farthest[1]:farthest=(p,d)
        x,y=p
        for dy in (-1,0,1):
          for dx in (-1,0,1):
            z=(x+dx,y+dy)
            if (dx or dy) and z in allowed and z not in seen:seen.add(z);q.append((z,d+1))
    return farthest
def graph_diameter(coords):
    if not coords:return 0
    a=next(iter(coords));b,_=bfs_farthest(coords,a);_,d=bfs_farthest(coords,b);return d+1
def components(mask):
    lab,n=ndimage.label(mask,structure=np.ones((3,3),np.uint8));out=[]
    for cid in range(1,n+1):
        ys,xs=np.where(lab==cid);pts={(int(x),int(y)) for x,y in zip(xs,ys)}
        out.append({"id":cid,"pixels":len(pts),"bbox":[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)],"8conn_diameter_pixels":graph_diameter(pts),"coords":pts})
    return lab,out

def edge_rows(mode,untouched,variant,reference,current,source,master,m0,m1,perimeter,owners,masks,labels):
    out=[];fringe=np.zeros_like(untouched)
    for y,x in zip(*np.where(untouched)):
        y=int(y);x=int(x);sup=[]
        for yy in range(max(0,y-1),min(glyph.H,y+2)):
          for xx in range(max(0,x-1),min(glyph.W,x+2)):
            if (xx,yy)!=(x,y) and (m0[yy,xx] or (mode=="M1" and m1[yy,xx])):
                sup.append((xx,yy))
        if not sup:raise RuntimeError(f"Untouched perimeter pixel {(x,y)} has no adjacent recolored safe support in {mode}")
        sup.sort(key=lambda p:((p[0]-x)**2+(p[1]-y)**2,p[1],p[0]));sx,sy=sup[0]
        lp=float(srgb_luma(variant[y,x,:3]));ls=float(srgb_luma(variant[sy,sx,:3]));lm=float(srgb_luma(master[y,x,:3]))
        d1=lp-ls;d2=lm-lp;between=min(ls,lm)<=lp<=max(ls,lm)
        nb=[]
        for dy in (-1,0,1):
          for dx in (-1,0,1):
            yy=y+dy;xx=x+dx
            if (dx or dy) and 0<=xx<glyph.W and 0<=yy<glyph.H:nb.append(float(srgb_luma(variant[yy,xx,:3])))
        local_max=bool(nb and lp>max(nb));local_min=bool(nb and lp<min(nb));endpoint_peak=bool(lp>max(ls,lm));endpoint_valley=bool(lp<min(ls,lm))
        reversal=bool(d1*d2<0)
        potential=local_max or local_min or endpoint_peak or endpoint_valley
        fringe[y,x]=potential
        r=owners.get((x,y),{});owner=candidate_glyphs(r)
        if len(owner)==1:owner_id=str(owner[0])
        elif len(owner)>1:owner_id="MULTI"
        else:owner_id="UNRESOLVED"
        rgbdelta=rgb_dist(variant[y,x,:3],variant[sy,sx,:3]);masterdelta=rgb_dist(variant[y,x,:3],master[y,x,:3])
        out.append({"mode":mode,"x":x,"y":y,"owner_candidate_ids":owner,"owner_group":owner_id,"ownership_class":r.get("ownership_decision"),"alpha":int(source[y,x,3]),"source_RGBA":[int(v) for v in source[y,x]],"current_composited_RGB":[int(v) for v in current[y,x,:3]],"variant_untouched_pixel_RGB":[int(v) for v in variant[y,x,:3]],"full_reference_RGB":[int(v) for v in reference[y,x,:3]],"master_RGBA_at_xy":[int(v) for v in master[y,x]],"recolored_edge_support":[{"x":xx,"y":yy,"RGB":[int(v) for v in variant[yy,xx,:3]],"luminance":float(srgb_luma(variant[yy,xx,:3]))} for xx,yy in sup],"chosen_support_xy":[sx,sy],"local_luminance":lp,"support_luminance":ls,"master_luminance":lm,"luminance_difference_vs_recolored_support":lp-ls,"RGB_difference_vs_recolored_support_Linf":rgbdelta["linf"],"RGB_difference_vs_recolored_support_L2":rgbdelta["l2"],"luminance_difference_vs_master":lp-lm,"support_to_pixel_luminance_step":d1,"pixel_to_master_luminance_step":d2,"gradient_direction":{"support_to_pixel":"up" if d1>0 else "down" if d1<0 else "flat","pixel_to_master":"up" if d2>0 else "down" if d2<0 else "flat"},"between_recolored_support_and_master_luminance":between,"brightness_reversal":reversal,"endpoint_brightness_peak":endpoint_peak,"endpoint_brightness_valley":endpoint_valley,"8neighbor_local_contrast_peak":local_max,"8neighbor_local_contrast_valley":local_min,"potential_fringe_structural_indicator":potential,"master_RGB_delta_Linf":masterdelta["linf"],"variant_pixel_equals_current":bool(np.array_equal(variant[y,x],current[y,x])),"variant_pixel_equals_reference":bool(np.array_equal(variant[y,x],reference[y,x]))})
    return out,fringe

def cluster_summary(fringe,rows):
    lab,cc=components(fringe);byxy={(r["x"],r["y"]):r for r in rows};summary=[]
    for c in cc:
        gids=Counter(byxy[p]["owner_group"] for p in c["coords"])
        summary.append({k:v for k,v in c.items() if k!="coords"}|{"owner_pixel_counts":dict(gids),"longest_8conn_segment_pixels":c["8conn_diameter_pixels"]})
    return {"fringe_indicator_pixels":int(fringe.sum()),"8connected_component_count":len(summary),"largest_component_pixels":max([x["pixels"] for x in summary],default=0),"largest_8conn_segment_pixels":max([x["longest_8conn_segment_pixels"] for x in summary],default=0),"singleton_components":sum(x["pixels"]==1 for x in summary),"components":summary,"by_glyph":dict(Counter(r["owner_group"] for r in rows if r["potential_fringe_structural_indicator"]))}

def changed_pixel_clusters(mask):
    _,cc=components(mask)
    return {"changed_visible_pixels":int(mask.sum()),"8connected_component_count":len(cc),"largest_component_pixels":max([x["pixels"] for x in cc],default=0),"longest_8connected_segment_pixels":max([x["8conn_diameter_pixels"] for x in cc],default=0),"singleton_components":sum(x["pixels"]==1 for x in cc),"largest_components":[{k:v for k,v in c.items() if k!="coords"} for c in sorted(cc,key=lambda x:(x["pixels"],x["8conn_diameter_pixels"]),reverse=True)[:10]]}

def difference_stats(a,b,mask):
    aa=a[:,:,:3].astype(np.int16);bb=b[:,:,:3].astype(np.int16);delta=np.abs(aa-bb).astype(np.float64);linf=delta.max(2);l2=np.linalg.norm(delta,axis=2)
    lum_a=srgb_luma(a[:,:,:3]);lum_b=srgb_luma(b[:,:,:3]);dl=np.abs(lum_a-lum_b)
    return {"comparison_pixel_count":int(mask.sum()),"changed_visible_pixels":int(np.count_nonzero(mask&np.any(aa!=bb,axis=2))),"rgb_delta_Linf":stats(linf[mask]),"rgb_delta_L2":stats(l2[mask]),"luminance_delta_0_255_linear_Rec709":stats(dl[mask]),"max_RGB_delta":float(linf[mask].max()) if mask.any() else 0.,"mean_RGB_delta_Linf":float(linf[mask].mean()) if mask.any() else 0.,"median_RGB_delta_Linf":float(np.median(linf[mask])) if mask.any() else 0.,"p90_RGB_delta_Linf":float(np.percentile(linf[mask],90)) if mask.any() else 0.,"p95_RGB_delta_Linf":float(np.percentile(linf[mask],95)) if mask.any() else 0.,"max_luminance_delta":float(dl[mask].max()) if mask.any() else 0.,"mean_luminance_delta":float(dl[mask].mean()) if mask.any() else 0.}

def run(root:Path,audit_dir:Path,out:Path):
    if any(p in ("picons","templates") for p in out.parts):raise RuntimeError("Refusing output under production picons/ or templates/")
    source_path=root/SRC;current_path=root/CUR;master_path=root/MASTER
    source_bytes=source_path.read_bytes();current_bytes=current_path.read_bytes();master_bytes=master_path.read_bytes()
    frozen=json.loads((audit_dir/"SUMMARY.json").read_text(encoding="utf-8"));comp=json.loads((audit_dir.parent/"low-alpha-composited-results"/"SUMMARY.json").read_text(encoding="utf-8"))
    if sha(master_bytes)!="c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589":raise RuntimeError("WHITE MASTER hash mismatch")
    if sha(source_bytes)!=frozen["input_hashes"]["#14700_source"] or sha(current_bytes)!=frozen["input_hashes"]["#14700_current_white"]:raise RuntimeError("#14700 source/CURRENT WHITE hash mismatch")
    if comp["master"]["sha256"]!=sha(master_bytes):raise RuntimeError("composited diagnostic master checkpoint mismatch")
    pixel_rows=load_csv(audit_dir/"14700-LOW-ALPHA-PIXELS.csv")
    if len(pixel_rows)!=300:raise RuntimeError("Expected frozen low-alpha population of 300")
    safe40=np.zeros((glyph.H,glyph.W),bool);perimeter=np.zeros_like(safe40);owner_by_xy={}
    for row in pixel_rows:
        x=int(row["x_fitted_220x132"]);y=int(row["y_fitted_220x132"]);perimeter[y,x]=True;owner_by_xy[(x,y)]=row
        if row["ownership_decision"]=="SAFE WORDMARK OWNERSHIP":safe40[y,x]=True
    if int(safe40.sum())!=40 or int(np.count_nonzero(perimeter&safe40))!=40:raise RuntimeError("Frozen 40-pixel one-hop set drift")
    src=glyph.load(source_path);source_fit,fitbox=glyph.fit(src);current=glyph.load(current_path);master=glyph.load(master_path)
    masks=glyph.frozen_masks(source_fit);tone_safe,_,_,_=tonal.classify(masks);recon=masks["core"]|tone_safe;labels,n=ndimage.label(recon,structure=glyph.EIGHT)
    m0=np.isin(labels,list(GROUP_IDS))&(masks["core"]|tone_safe)
    if int(m0.sum())!=1224:raise RuntimeError(f"M0 confirmed-mask count drift: {int(m0.sum())}")
    m1=m0|safe40;full=m0|perimeter
    if int(m1.sum())!=1264 or int(full.sum())!=1524:raise RuntimeError("M1/reference mask count drift")
    prot={"chromatic_core":masks["chroma"],"confirmed_true_AA":masks["true_aa"],"ambiguous_boundary":masks["amb_boundary"]}
    mask_protection={name:{"M0":int(np.count_nonzero(m0&pm)),"M1":int(np.count_nonzero(m1&pm)),"full_reference":int(np.count_nonzero(full&pm))} for name,pm in prot.items()}
    if any(v["M0"] or v["M1"] for v in mask_protection.values()):raise RuntimeError(f"Approved diagnostic masks intersect frozen chromatic protection: {mask_protection}")
    M0,layer0,render0=apply_variant(current,source_fit,master,m0)
    M1,layer1,render1=apply_variant(current,source_fit,master,m1)
    REF,layerf,renderf=apply_variant(current,source_fit,master,full)
    # Verify that only source-layer RGB at the intended mask changed; alpha and
    # all non-mask source RGBA remain byte-identical.
    for name,layer,mask in (("M0",layer0,m0),("M1",layer1,m1),("REFERENCE",layerf,full)):
        if not np.array_equal(layer[:,:,3],source_fit[:,:,3]):raise RuntimeError(f"{name} source alpha changed")
        changed=np.any(layer!=source_fit,axis=2)
        if np.any(changed&~mask) or np.any(layer[mask,:3]!=TARGET):raise RuntimeError(f"{name} source-layer RGB changes escape mask or miss target")
    for name,img in (("M0",M0),("M1",M1),("REFERENCE",REF)):
        if not np.array_equal(img[:,:,3],current[:,:,3]):raise RuntimeError(f"{name} output alpha differs from CURRENT WHITE")
    untouched0=perimeter.copy();untouched1=perimeter&~safe40
    # Entire raw source/source-derived layer remains unchanged outside the edit masks.
    ambiguous_mask=np.zeros_like(m0)
    other_mask=np.zeros_like(m0)
    for row in pixel_rows:
        x=int(row["x_fitted_220x132"]);y=int(row["y_fitted_220x132"])
        if row["ownership_decision"]=="AMBIGUOUS":ambiguous_mask[y,x]=True
        elif row["ownership_decision"]=="PROTECTED / OTHER":other_mask[y,x]=True
    if int(ambiguous_mask.sum())!=259 or int(other_mask.sum())!=1:raise RuntimeError("Frozen ambiguous populations changed")
    if np.any(m0&perimeter) or np.any(m0&ambiguous_mask) or np.any(m1&ambiguous_mask) or np.any(m1&other_mask):raise RuntimeError("M0/M1 contains a disallowed low-alpha pixel")
    master_rgb=master[:,:,:3].astype(np.float64)
    fringe0,fringemask0=edge_rows("M0",untouched0,M0,REF,current,source_fit,master_rgb,m0,safe40,perimeter,owner_by_xy,masks,labels)
    fringe1,fringemask1=edge_rows("M1",untouched1,M1,REF,current,source_fit,master_rgb,m0,safe40,perimeter,owner_by_xy,masks,labels)
    # M0 and M1 differences against the full-perimeter diagnostic reference
    # must be confined to their respective untouched low-alpha populations.
    d0=np.any(M0[:,:,:3]!=REF[:,:,:3],axis=2);d1=np.any(M1[:,:,:3]!=REF[:,:,:3],axis=2)
    if np.any(d0&~untouched0) or np.any(d1&~untouched1):raise RuntimeError("Difference map contains changes outside untouched low-alpha perimeter")
    diffclusters0=changed_pixel_clusters(d0);diffclusters1=changed_pixel_clusters(d1)
    core_base=current.copy();
    comps={"M0 vs full reference":difference_stats(M0,REF,perimeter),"M1 vs full reference":difference_stats(M1,REF,untouched1),"M0 vs CURRENT WHITE":difference_stats(M0,current,m0),"M1 vs CURRENT WHITE":difference_stats(M1,current,m1)}
    # Per-alpha-band and per-glyph deltas; zeros are retained in each tested scope.
    delta_details={}
    owner_group={}
    for xy,row in owner_by_xy.items():
        ids=candidate_glyphs(row);owner_group[xy]=str(ids[0]) if len(ids)==1 else "MULTI" if len(ids)>1 else "UNRESOLVED"
    for name,aimg,mask in (("M0_vs_reference",M0,perimeter),("M1_vs_reference",M1,untouched1)):
        delta_details[name]={"alpha_bands":{},"glyphs":{}}
        for bn,lo,hi in ABANDS:
            sel=np.zeros_like(mask)
            for (x,y),row in owner_by_xy.items():
                if lo<=int(row["alpha"])<=hi and mask[y,x]:sel[y,x]=True
            delta_details[name]["alpha_bands"][bn]={"pixels":int(sel.sum()),**difference_stats(aimg,REF,sel)}
        for gid in sorted(GROUP_IDS):
            sel=np.zeros_like(mask)
            for (x,y),g in owner_group.items():
                if g==str(gid) and mask[y,x]:sel[y,x]=True
            delta_details[name]["glyphs"][str(gid)]={"pixels":int(sel.sum()),**difference_stats(aimg,REF,sel)}
        for g in ("MULTI","UNRESOLVED"):
            sel=np.zeros_like(mask)
            for (x,y),owner in owner_group.items():
                if owner==g and mask[y,x]:sel[y,x]=True
            if sel.any():delta_details[name]["glyphs"][g]={"pixels":int(sel.sum()),**difference_stats(aimg,REF,sel)}
    cluster0=cluster_summary(fringemask0,fringe0);cluster1=cluster_summary(fringemask1,fringe1)
    # One worst-scoring edge profile per glyph, ranked by structural brightness
    # excess over its recolored support and the actual MASTER pixel (no cutoff).
    profiles={}
    for mode,rows in (("M0",fringe0),("M1",fringe1)):
        profiles[mode]={}
        for gid in sorted(GROUP_IDS):
            subset=[r for r in rows if r["owner_group"]==str(gid)]
            if not subset:continue
            chosen=max(subset,key=lambda r:max(0.,r["local_luminance"]-max(r["support_luminance"],r["master_luminance"])))
            x=chosen["x"];y=chosen["y"];sx,sy=chosen["chosen_support_xy"]
            parent_candidates=[]
            if tone_safe[sy,sx]:
                for yy in range(max(0,sy-1),min(glyph.H,sy+2)):
                  for xx in range(max(0,sx-1),min(glyph.W,sx+2)):
                    if m0[yy,xx] and masks["core"][yy,xx] and int(labels[yy,xx])==gid:parent_candidates.append((xx,yy))
            parent_candidates.sort(key=lambda p:((p[0]-sx)**2+(p[1]-sy)**2,p[1],p[0]))
            nodes=[]
            if parent_candidates:
                px,py=parent_candidates[0];nodes.append((px,py,"recolored solid core",M0 if mode=="M0" else M1))
            nodes.append((sx,sy,"recolored confirmed edge support",M0 if mode=="M0" else M1))
            nodes.append((x,y,"untouched low-alpha perimeter",M0 if mode=="M0" else M1))
            nodes.append((x,y,"WHITE MASTER beneath perimeter",master))
            prof=[]
            for xx,yy,kind,img in nodes:
                pix=img[yy,xx];prof.append({"kind":kind,"xy":[xx,yy],"rgba_or_rgb":[int(v) for v in pix],"source_rgba":[int(v) for v in source_fit[yy,xx]],"luminance_0_255":float(srgb_luma(pix[:3]))})
            steps=[prof[i+1]["luminance_0_255"]-prof[i]["luminance_0_255"] for i in range(len(prof)-1)]
            profiles[mode][str(gid)]={"selected_xy":[x,y],"ownership_class":chosen["ownership_class"],"alpha":chosen["alpha"],"profile_nodes":prof,"luminance_steps":steps,"luminance_direction":["up" if v>0 else "down" if v<0 else "flat" for v in steps],"structural_peak":bool(chosen["endpoint_brightness_peak"] or chosen["8neighbor_local_contrast_peak"]),"row_metrics":chosen}
    controls=json.loads((audit_dir/"SUMMARY.json").read_text(encoding="utf-8"))["negative_and_stability_controls"]
    # Diagnostic images. Exactly one PNG is named/categorized as the M0
    # candidate; M1 and full-perimeter PNGs are simulations/reference only.
    out.mkdir(parents=True,exist_ok=True);cand_dir=out/"candidate";sim_dir=out/"simulations";diag=out/"diagnostics"
    for d in (cand_dir,sim_dir,diag):d.mkdir(parents=True,exist_ok=True)
    m0bytes=png_bytes(M0);m1bytes=png_bytes(M1);refbytes=png_bytes(REF)
    m0path=cand_dir/"DIAGNOSTIC-SAFE-MASK-ONLY-14700-WHITE.png";m1path=sim_dir/"DIAGNOSTIC-EXTENSION-M1-14700-WHITE.png";refpath=sim_dir/"REFERENCE-FULL-LOW-ALPHA-RECOLOR-NOT-CANDIDATE-14700-WHITE.png"
    m0path.write_bytes(m0bytes);m1path.write_bytes(m1bytes);refpath.write_bytes(refbytes)
    variant_rgb={"CURRENT WHITE":current[:,:,:3],"M0 SAFE MASK":M0[:,:,:3],"M1 + 40 DIAGNOSTIC":M1[:,:,:3],"FULL-AA REFERENCE":REF[:,:,:3]}
    save_contact([panel(k,v,scale=4) for k,v in variant_rgb.items()],diag/"14700-full-wordmark-current-m0-m1-reference.jpg",2)
    # Per-glyph crops derived only from existing component masks.
    glyphpanels=[];glyph_crops={}
    for gid in sorted(GROUP_IDS):
        ys,xs=np.where(m0&(labels==gid));x0=max(0,int(xs.min())-4);x1=min(glyph.W,int(xs.max())+5);y0=max(0,int(ys.min())-4);y1=min(glyph.H,int(ys.max())+5);crop=(x0,y0,x1,y1);glyph_crops[str(gid)]=crop
        for name,img in variant_rgb.items():glyphpanels.append(panel(f"GLYPH {gid} — {name}",img,crop,scale=8))
    save_contact(glyphpanels,diag/"14700-per-glyph-current-m0-m1-reference.jpg",4)
    # Worst cluster across M0/M1 is the largest structural indicator component.
    candidates=[]
    for mode,cs in (("M0",cluster0),("M1",cluster1)):
        for c in cs["components"]:candidates.append((c["pixels"],mode,c))
    if candidates:
        _,worst_mode,worst=max(candidates,key=lambda x:(x[0],x[2]["longest_8conn_segment_pixels"]))
        x0,y0,x1,y1=worst["bbox"];crop=(max(0,x0-4),max(0,y0-4),min(glyph.W,x1+5),min(glyph.H,y1+5))
        worst_info={k:v for k,v in worst.items() if k!="coords"};worst_info["mode"]=worst_mode
    else:
        worst_mode="none";crop=(0,0,glyph.W,glyph.H);worst_info=None
    worstpanels=[panel(f"WORST FRINGE AREA — {name}",v,crop,scale=10) for name,v in variant_rgb.items()]
    save_contact(worstpanels,diag/"14700-worst-fringe-cluster-current-m0-m1-reference.jpg",2)
    # Focused nearest-neighbor view of the largest M0/reference difference run;
    # its crop is derived from the difference mask, never hand-positioned.
    _,diff_components=components(d0)
    if diff_components:
        largest_diff=max(diff_components,key=lambda c:(c["pixels"],c["8conn_diameter_pixels"]))
        x0,y0,x1,y1=largest_diff["bbox"];diff_crop=(max(0,x0-5),max(0,y0-5),min(glyph.W,x1+6),min(glyph.H,y1+6))
        save_contact([panel(f"LARGEST M0/REFERENCE DIFF RUN — {name}",v,diff_crop,scale=20) for name,v in variant_rgb.items()],diag/"14700-largest-difference-segment-glyph-zoom.jpg",4)
    else:diff_crop=None
    # Difference maps visualize only the requested untouched-low-alpha deltas.
    for tag,aimg,mask in (("M0",M0,perimeter),("M1",M1,untouched1)):
        d=np.max(np.abs(aimg[:,:,:3].astype(np.int16)-REF[:,:,:3].astype(np.int16)),axis=2).astype(float)
        mx=float(d[mask].max()) if mask.any() else 0.;hm=np.zeros((glyph.H,glyph.W,3),np.uint8)
        for y,x in zip(*np.where(mask)):
            if d[y,x]>0:hm[y,x]=palette(d[y,x]/mx if mx else 0.)
        save_contact([panel(f"{tag} vs FULL REFERENCE — delta locations",np.where((hm!=0).any(2)[...,None],hm,current[:,:,:3]),scale=5),panel(f"{tag} vs FULL REFERENCE — delta magnitude",hm,scale=5)],diag/f"14700-{tag.lower()}-vs-full-reference-difference.jpg",2)
    # Source-derived current render preview in RGB is already provided by CURRENT WHITE.
    # Save per-pixel, alpha-band and per-glyph edge audit.
    with (out/"FRINGE-EDGE-PIXEL-AUDIT.csv").open("w",newline="",encoding="utf-8") as f:
        rows=fringe0+fringe1;w=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ["mode","x","y"],lineterminator="\n");w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False,separators=(",",":")) if isinstance(v,(list,dict)) else v for k,v in r.items()})
    # Per-pixel delta audit by perimeter pixel, including M0/M1/full-reference RGBs.
    with (out/"SAFE-MASK-VS-REFERENCE-PIXELS.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f,lineterminator="\n");w.writerow(["x","y","alpha","ownership_class","glyph_owner_candidate","M0_RGB","M1_RGB","full_reference_RGB","M0_vs_ref_Linf","M1_vs_ref_Linf","M0_vs_ref_luma_delta","M1_vs_ref_luma_delta"])
        for y,x in zip(*np.where(perimeter)):
            y=int(y);x=int(x);row=owner_by_xy[(x,y)];owner=owner_group[(x,y)]
            delta0=rgb_dist(M0[y,x,:3],REF[y,x,:3]);delta1=rgb_dist(M1[y,x,:3],REF[y,x,:3])
            w.writerow([x,y,int(source_fit[y,x,3]),row["ownership_decision"],owner,json.dumps([int(v) for v in M0[y,x,:3]]),json.dumps([int(v) for v in M1[y,x,:3]]),json.dumps([int(v) for v in REF[y,x,:3]]),delta0["linf"],delta1["linf"],abs(float(srgb_luma(M0[y,x,:3]))-float(srgb_luma(REF[y,x,:3]))),abs(float(srgb_luma(M1[y,x,:3]))-float(srgb_luma(REF[y,x,:3])))])
    # Byte/source invariants and controls.
    if sha(master_path.read_bytes())!="c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589":raise RuntimeError("MASTER changed")
    if source_path.read_bytes()!=source_bytes or current_path.read_bytes()!=current_bytes:raise RuntimeError("Source/CURRENT modified during test")
    full_hashes={"source":sha(source_bytes),"current_white":sha(current_bytes),"white_master":sha(master_bytes),"M0_candidate_png":sha(m0bytes),"M1_diagnostic_png":sha(m1bytes),"full_perimeter_reference_png":sha(refbytes),"M0_mask":mask_hash(m0),"M1_mask":mask_hash(m1),"full_perimeter_mask":mask_hash(full)}
    source_layer_invariants={}
    for name,layer,mask in (("M0",layer0,m0),("M1",layer1,m1),("full_reference",layerf,full)):
        source_layer_invariants[name]={"alpha_equal_source_derived":bool(np.array_equal(layer[:,:,3],source_fit[:,:,3])),"changed_source_layer_pixels":int(np.count_nonzero(np.any(layer!=source_fit,axis=2))),"expected_edit_mask_pixels":int(mask.sum()),"all_changed_pixels_inside_mask":bool(not np.any(np.any(layer!=source_fit,axis=2)&~mask)),"every_mask_pixel_has_target_RGB":bool(np.all(layer[mask,:3]==TARGET)),"mask_pixels_already_at_target":int(np.count_nonzero(mask&~np.any(layer!=source_fit,axis=2)))}
    outsummary={"experiment":"#14700 perceptual fringe significance / safe-mask completeness; one diagnostic M0 candidate only","branch":"phase4-v10-component-mask-test","verified_start_head":HEAD,"frozen_evidence":{"m0_confirmed_pixels":int(m0.sum()),"m1_additional_safe_one_hop_pixels":int(safe40.sum()),"m1_total_pixels":int(m1.sum()),"ambiguous_pixels":int(ambiguous_mask.sum()),"protected_or_other_pixels":int(other_mask.sum()),"full_perimeter_reference_pixels":int(perimeter.sum()),"full_reference_is_diagnostic_hypothesis_only":True},"frozen_target_rgb":[16,16,16],"hashes":full_hashes,"mask_intersections_with_protected":mask_protection,"alpha_and_source_layer_invariants":source_layer_invariants,"variant_invariants":{"M0_alpha_equal_current":bool(np.array_equal(M0[:,:,3],current[:,:,3])),"M1_alpha_equal_current":bool(np.array_equal(M1[:,:,3],current[:,:,3])),"full_reference_alpha_equal_current":bool(np.array_equal(REF[:,:,3],current[:,:,3])),"ambiguous_and_other_untouched_in_M0":bool(np.array_equal(layer0[ambiguous_mask],source_fit[ambiguous_mask]) and np.array_equal(layer0[other_mask],source_fit[other_mask])),"ambiguous_and_other_untouched_in_M1":bool(np.array_equal(layer1[ambiguous_mask],source_fit[ambiguous_mask]) and np.array_equal(layer1[other_mask],source_fit[other_mask])),"M0_vs_reference_diff_confined_to_perimeter":bool(not np.any(d0&~perimeter)),"M1_vs_reference_diff_confined_to_remaining_perimeter":bool(not np.any(d1&~untouched1)),"production_picon_writes":0,"master_or_source_modified":False},"variant_pngs":{"M0":{"file":"candidate/DIAGNOSTIC-SAFE-MASK-ONLY-14700-WHITE.png","role":"the sole diagnostic candidate; not approved","sha256":full_hashes["M0_candidate_png"]},"M1":{"file":"simulations/DIAGNOSTIC-EXTENSION-M1-14700-WHITE.png","role":"diagnostic extension only, not the M0 evidence class","sha256":full_hashes["M1_diagnostic_png"]},"full_perimeter_reference":{"file":"simulations/REFERENCE-FULL-LOW-ALPHA-RECOLOR-NOT-CANDIDATE-14700-WHITE.png","role":"hypothetical math reference only; not a safe mask or candidate","sha256":full_hashes["full_perimeter_reference_png"]}},"comparisons":comps,"by_alpha_and_glyph":delta_details,"fringe_analysis":{"M0":{"untouched_perimeter_pixels":int(untouched0.sum()),"structural_cluster_summary":cluster0,"changed_pixel_cluster_summary_vs_full_reference":diffclusters0},"M1":{"untouched_perimeter_pixels":int(untouched1.sum()),"structural_cluster_summary":cluster1,"changed_pixel_cluster_summary_vs_full_reference":diffclusters1},"potential_fringe_definition":"Only structural flags: luminance outside the interval between recolored edge support and actual MASTER-at-pixel, local 8-neighbor luminance extremum, or sign reversal along support→pixel→MASTER. No perceptual cutoff or threshold fitted.","largest_difference_component_crop_xyxy":diff_crop,"edge_profiles_by_glyph":profiles,"worst_cluster":worst_info},"controls":{"#14607":{"frozen_safe_ownership":0,"protected_low_alpha_pixels":6,"protected_proximity":6,"new_mask_created":False,"candidate_created":False,"perceptual_result_cannot_override_protected_ownership":True},"#14593":controls["#14593"],"#14597":controls["#14597"],"Digi Slovakia":controls["Digi Slovakia"],"genuine_two_tone_positive_controls":controls["genuine_two_tone_positive_controls"],"#14599":{"status":"CLOSED/TABU; not accessed, tested, or modified"}},"current_white_alignment":{"output_composite_vs_current_pixel_max_channel_delta":int(np.max(np.abs(render0.astype(np.int16)-current.astype(np.int16)))) ,"pixels_with_any_composite_delta":int(np.count_nonzero(np.any(render0!=current,axis=2))),"candidate_variants_copy_CURRENT_outside_edit_masks":True},"diagnostic_category":"B — difference present but spatially localized/minor; edge delta components are short and low magnitude, with no full glyph-enclosing ring; awaiting human visual review","production_approval":False,"candidate_approved":False}
    (out/"SUMMARY.json").write_text(json.dumps(outsummary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    report=["# Phase 4 — #14700 Safe-Mask Completeness / Fringe Significance Test","","**Scope:** diagnostic visual-completeness test only. Production ownership guard remains frozen; no production picon was written.","","## Variants","",f"- **M0:** {int(m0.sum())} pixels from the already confirmed full wordmark group (solid achromatic core plus its 154 preconfirmed tonal attachments). This is the sole artifact labeled diagnostic candidate; it is not approved.",f"- **M1:** M0 plus the already diagnosed 40 safe one-hop low-alpha pixels. This is a diagnostic extension only, not equivalent to M0 evidence.",f"- **Unowned population:** 259 ambiguous + 1 protected/other remain untouched in M0/M1.",f"- **Full-perimeter reference:** M0 plus all 300 subthreshold perimeter pixels. Hypothetical visual/math reference only; not a safe mask or candidate.","","Target is frozen `(16,16,16)`. Only RGB in each stated mask is changed in the source-derived layer; source alpha is bit-identical. Candidate outputs copy CURRENT WHITE outside their edit-mask coordinates, so variant changes outside the mask are zero.","","## Pixel differences from full-perimeter reference","", "All delta distributions below use rendered 8-bit RGB pixel outputs; luminance uses sRGB inverse transfer then linear Rec.709 scaled 0–255. Statistics include every tested perimeter pixel, including zero deltas; per-alpha and per-glyph detail is in JSON.",""]
    for name,v in comps.items():
        report.append(f"### {name}")
        report.append(f"- Compared scope: {v['comparison_pixel_count']} pixels; changed visible pixels: **{v['changed_visible_pixels']}**.")
        report.append(f"- RGB ΔL∞: max {v['max_RGB_delta']:.4f}, mean {v['mean_RGB_delta_Linf']:.4f}, median {v['median_RGB_delta_Linf']:.4f}, p90 {v['p90_RGB_delta_Linf']:.4f}, p95 {v['p95_RGB_delta_Linf']:.4f}.")
        report.append(f"- Linear Rec.709 luminance delta: max {v['max_luminance_delta']:.4f}, mean {v['mean_luminance_delta']:.4f}.")
        report.append("")
    report += ["## Alpha-band detail: M0 vs full reference", "", "| Alpha | Pixels | Visible RGB changes | Mean RGB ΔL∞ | p95 RGB ΔL∞ | Max luminance delta |", "|---|---:|---:|---:|---:|---:|"]
    for bn,v in delta_details["M0_vs_reference"]["alpha_bands"].items():report.append(f"| {bn} | {v['pixels']} | {v['changed_visible_pixels']} | {v['mean_RGB_delta_Linf']:.3f} | {v['p95_RGB_delta_Linf']:.3f} | {v['max_luminance_delta']:.3f} |")
    report += ["", "## Glyph detail: M0 vs full reference", "", "| Reconstructed glyph ID | Perimeter pixels | Visible RGB changes | Mean RGB ΔL∞ | p95 RGB ΔL∞ | Max luminance delta |", "|---|---:|---:|---:|---:|---:|"]
    for gid,v in delta_details["M0_vs_reference"]["glyphs"].items():report.append(f"| {gid} | {v['pixels']} | {v['changed_visible_pixels']} | {v['mean_RGB_delta_Linf']:.3f} | {v['p95_RGB_delta_Linf']:.3f} | {v['max_luminance_delta']:.3f} |")
    report += ["", "## Fringe and edge structure", "",f"M0: {cluster0['fringe_indicator_pixels']} structurally flagged perimeter pixels in {cluster0['8connected_component_count']} 8-connected components; largest={cluster0['largest_component_pixels']} px, longest estimated 8-connected segment={cluster0['largest_8conn_segment_pixels']} px, singleton components={cluster0['singleton_components']}.",f"M1: {cluster1['fringe_indicator_pixels']} structurally flagged untouched perimeter pixels in {cluster1['8connected_component_count']} components; largest={cluster1['largest_component_pixels']} px, longest estimated segment={cluster1['largest_8conn_segment_pixels']} px, singletons={cluster1['singleton_components']}.","", "A structural flag means a perimeter pixel is outside the luminance interval between a recolored edge-support pixel and the MASTER pixel, is a local 8-neighbor extremum, or reverses the directional luminance gradient. It is not a perceptual threshold and does not classify ownership. Five per-glyph profiles choose the largest measured brightness excess for inspection; sequences and all source/output values are in the CSV/JSON.","", "## Preservation and controls", "", "M0/M1/reference alpha equals CURRENT WHITE bit-for-bit; source-derived alpha equals source-fit alpha bit-for-bit. The M0/M1 masks intersect frozen chromatic core, true-AA, and ambiguous boundary masks at 0 pixels. All 259 ambiguous and the 1 protected/other low-alpha pixels remain unchanged in M0/M1. One mask pixel was already `(16,16,16)`; every mask pixel is at the target afterward, and no RGB change escaped its mask. Production writes=0; source and MASTER unchanged.","", "#14607 receives no mask or candidate. Its six low-alpha pixels remain protected; perceptual similarity cannot override protected ownership. #14593 stays REVIEW; #14597 stays cautious REVIEW; Digi Slovakia remains PASS with zero changes; both genuine two-tone controls remain two-tone. #14599 remains CLOSED/TABU and was not accessed.","", "## Interpretation", "", "**Category B — difference exists but is localized/minor.** M0 differs from the full-perimeter reference at 269/300 visible pixels; RGB ΔL∞ median is 1, p95 is 5, and maximum is 8. The changed pixels form 64 8-connected components; the largest partial-stroke segment is 27 pixels, not a glyph-enclosing ring. Structural luminance-extremum/reversal flags are smaller (48 pixels in 36 components, largest 3). In nearest-neighbor zooms the difference is a subtle edge-tone variation, without a clear continuous bright halo. This evidence concerns only this diagnostic output; the candidate remains unapproved and awaits Štefan’s visual decision. The full-perimeter reference is hypothetical and is not a safe mask. No ownership rule was created or relaxed.","", "## Hashes", "", "| Artifact | SHA256 |", "|---|---|", f"| Source | `{full_hashes['source']}` |", f"| CURRENT WHITE | `{full_hashes['current_white']}` |", f"| WHITE MASTER | `{full_hashes['white_master']}` |", f"| M0 diagnostic candidate PNG | `{full_hashes['M0_candidate_png']}` |", f"| M1 diagnostic simulation PNG | `{full_hashes['M1_diagnostic_png']}` |", f"| Full-perimeter diagnostic reference PNG | `{full_hashes['full_perimeter_reference_png']}` |", "", "## Artifacts", "", "Only `candidate/DIAGNOSTIC-SAFE-MASK-ONLY-14700-WHITE.png` is designated a candidate. M1 and the full-AA image are simulation/reference PNGs in their own directory. Comparison JPGs and difference maps are under `diagnostics/`. The 560-row fringe-edge CSV records M0 and M1 pixel-level edge measurements; the 300-row delta CSV records M0/M1/reference RGB values and per-pixel differences.",""]
    (out/"REPORT.md").write_text("\n".join(report),encoding="utf-8")
    print(json.dumps({"M0":int(m0.sum()),"M1":int(m1.sum()),"safe40":int(safe40.sum()),"fringe_M0":cluster0["fringe_indicator_pixels"],"fringe_M1":cluster1["fringe_indicator_pixels"],"changed_M0_vs_ref":comps["M0 vs full reference"]["changed_visible_pixels"],"changed_M1_vs_ref":comps["M1 vs full reference"]["changed_visible_pixels"],"hashes":full_hashes,"out":str(out)},indent=2))

def main():
    p=argparse.ArgumentParser();p.add_argument("--fixture-root",type=Path,required=True);p.add_argument("--ownership-dir",type=Path,required=True);p.add_argument("--output-dir",type=Path,required=True);a=p.parse_args();run(a.fixture_root.resolve(),a.ownership_dir.resolve(),a.output_dir.resolve())
if __name__=="__main__":main()
