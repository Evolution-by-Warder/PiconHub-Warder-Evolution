#!/usr/bin/env python3
"""Diagnostic-only straight-alpha composition audit for #14700 low-alpha pixels.

Reads the frozen ownership pixel audits and existing source-derived fixtures.
It does not change thresholds/classification, construct an edit mask, or write
any candidate/production image. Composites are numeric diagnostic arrays only.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE.parent))
import phase4_achromatic_glyph_aa_diagnostic as glyph
import phase4_achromatic_tonal_field_diagnostic as tonal

EXPECTED_HEAD="4e84d3ddb370c89addb5b39258d5f718c8d7618a"
MASTER_SHA="c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589"
SOURCE14700="picons/80.0e/orion-express/transparent/1_0_1_32D_CE_1_3200000_0_0_0.png"
CURRENT14700="picons/80.0e/orion-express/white/1_0_1_32D_CE_1_3200000_0_0_0.png"
SOURCE14607="picons/80.0e/orion-express/transparent/1_0_1_2C8_CD_1_3200000_0_0_0.png"
CURRENT14607="picons/80.0e/orion-express/white/1_0_1_2C8_CD_1_3200000_0_0_0.png"
WHITE_MASTER="templates/picons/white-sablona.png"
GROUP_IDS={6,7,8,9,10}
ALPHA_BANDS=[("1-3",1,3),("4-7",4,7),("8-15",8,15),("16-23",16,23),("24-31",24,31)]

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def json_loads(v): return json.loads(v) if isinstance(v,str) else v
def fnum(v): return float(v) if v not in (None,"", "None") else None

def srgb_luma(rgb):
    x=np.asarray(rgb,dtype=np.float64)/255.0
    lin=np.where(x<=0.04045,x/12.92,((x+0.055)/1.055)**2.4)
    return float(255.0*(0.2126*lin[...,0]+0.7152*lin[...,1]+0.0722*lin[...,2]))

def composite(rgb,alpha,bg):
    a=float(alpha)/255.0
    return np.asarray(rgb,dtype=np.float64)*a+np.asarray(bg,dtype=np.float64)*(1.0-a)

def dist(a,b):
    d=np.asarray(a,dtype=np.float64)-np.asarray(b,dtype=np.float64)
    return {"linf":float(np.max(np.abs(d))),"l2":float(np.linalg.norm(d))}

def stats(values):
    a=np.asarray([v for v in values if v is not None and np.isfinite(v)],dtype=np.float64)
    if not len(a): return {"n":0,"min":None,"median":None,"mean":None,"p75":None,"p90":None,"p95":None,"max":None}
    return {"n":int(len(a)),"min":float(a.min()),"median":float(np.median(a)),"mean":float(a.mean()),"p75":float(np.percentile(a,75)),"p90":float(np.percentile(a,90)),"p95":float(np.percentile(a,95)),"max":float(a.max())}

def load_ownership(path,case):
    rows=list(csv.DictReader(path.open(newline="",encoding="utf-8")))
    if case=="#14700":
        if len(rows)!=300: raise RuntimeError(f"#14700 ownership audit expected 300 records, got {len(rows)}")
        counts=Counter(r["ownership_decision"] for r in rows)
        if counts.get("SAFE WORDMARK OWNERSHIP")!=40 or counts.get("AMBIGUOUS")!=259 or counts.get("PROTECTED / OTHER")!=1:
            raise RuntimeError(f"Frozen ownership evidence changed: {dict(counts)}")
    else:
        if len(rows)!=6: raise RuntimeError(f"#14607 expected six protected low-alpha controls, got {len(rows)}")
        if any(r.get("protected_within_8_neighbors")!="True" or r.get("decision")!="AMBIGUOUS/REVIEW" for r in rows):
            raise RuntimeError("#14607 protected negative-control evidence changed")
    return rows

def sample_rgba(img,x,y): return [int(v) for v in img[int(y),int(x)]]

def make_record(row,case,source_fit,master_rgba,confirmed,labels,tonal_safe,core,protected):
    if case=="#14700":
        x=int(row["x_fitted_220x132"]);y=int(row["y_fitted_220x132"])
        category=row["ownership_decision"]
        owner_ids=json_loads(row["direct_candidate_glyph_ids"])
        protected_near=row["protected_neighborhood_present"]=="True"
    else:
        x=int(row["x"]);y=int(row["y"]);category="PROTECTED NEGATIVE CONTROL"
        owner_ids=[];protected_near=row["protected_within_8_neighbors"]=="True"
    rgba=sample_rgba(source_fit,x,y);rgb=np.asarray(rgba[:3],dtype=np.float64);alpha=rgba[3]
    if not (1<=alpha<=31): raise RuntimeError(f"Unexpected alpha {alpha} at {case} {(x,y)}")
    master_rgb=master_rgba[:,:,:3].astype(np.float64)
    bg=master_rgb[y,x]
    out=composite(rgb,alpha,bg);lraw=srgb_luma(rgb);lcomp=srgb_luma(out)
    premul=rgb*(alpha/255.0)
    raw_support=[];composited_support=[];support_rows=[]
    for yy in range(max(0,y-1),min(glyph.H,y+2)):
      for xx in range(max(0,x-1),min(glyph.W,x+2)):
        if (xx,yy)==(x,y) or not confirmed[yy,xx]: continue
        gid=int(labels[yy,xx])
        if case=="#14700" and owner_ids and gid not in owner_ids: continue
        srgb=source_fit[yy,xx,:3].astype(np.float64);sa=int(source_fit[yy,xx,3]);sbg=master_rgb[yy,xx]
        sout=composite(srgb,sa,sbg)
        dr=dist(rgb,srgb);dc=dist(out,sout);dp=dist(premul,srgb*(sa/255.0))
        cls="proven_tonal_attachment" if tonal_safe[yy,xx] else "solid_achromatic_core" if core[yy,xx] else "confirmed_group_other"
        support={"x":xx,"y":yy,"glyph_id":gid,"class":cls,"rgba":[int(v) for v in source_fit[yy,xx]],"master_rgb":[float(v) for v in sbg],"master_rgba":[int(v) for v in master_rgba[yy,xx]],"raw_RGB_distance":{"linf":dr["linf"],"l2":dr["l2"]},"composited_RGB_distance":{"linf":dc["linf"],"l2":dc["l2"]},"premultiplied_RGB_distance_l2":dp["l2"],"composited_rgb":[float(v) for v in sout],"composited_luminance_0_255":srgb_luma(sout)}
        raw_support.append(dr);composited_support.append(dc);support_rows.append(support)
    # Fixed reference is the spatially nearest direct support, tie-broken by y,x.
    support_rows.sort(key=lambda q:((q["x"]-x)**2+(q["y"]-y)**2,q["y"],q["x"]))
    fixed=support_rows[0] if support_rows else None
    raw_min_linf=min((q["raw_RGB_distance"]["linf"] for q in support_rows),default=None)
    comp_min_linf=min((q["composited_RGB_distance"]["linf"] for q in support_rows),default=None)
    comp_min_l2=min((q["composited_RGB_distance"]["l2"] for q in support_rows),default=None)
    if fixed:
        fixed_raw_linf=fixed["raw_RGB_distance"]["linf"];fixed_comp_linf=fixed["composited_RGB_distance"]["linf"]
        fixed_comp_l2=fixed["composited_RGB_distance"]["l2"]
        comp_luma_diff=abs(lcomp-fixed["composited_luminance_0_255"])
        premul_dist=fixed["premultiplied_RGB_distance_l2"]
    else:
        fixed_raw_linf=fixed_comp_linf=fixed_comp_l2=comp_luma_diff=premul_dist=None
    dark=composite(np.array([16.,16.,16.]),alpha,bg);dark_delta=dist(out,dark)
    row_out={"case":case,"x_fitted_220x132":x,"y_fitted_220x132":y,"raw_source_xy_float":json_loads(row.get("raw_source_xy_float")) if case=="#14700" else None,"raw_source_xy_nearest":json_loads(row.get("raw_source_xy_nearest")) if case=="#14700" else None,"source_RGBA_fitted":rgba,"alpha":alpha,"channel_spread":int(max(rgba[:3])-min(rgba[:3])),"ownership_diagnostic_category":category,"candidate_glyph_owner_ids":owner_ids,"protected_neighborhood":protected_near,"local_support_pixels":support_rows,"fixed_spatial_nearest_support":fixed,"white_master_RGBA_at_pixel":[int(v) for v in master_rgba[y,x]],"raw_RGB_luminance_0_255":lraw,"composited_RGB_on_white_master":[float(v) for v in out],"composited_luminance_0_255":lcomp,"premultiplied_RGB":[float(v) for v in premul],"premultiplied_RGB_magnitude_l2":float(np.linalg.norm(premul)),"raw_distance_to_local_support_min_Linf":raw_min_linf,"raw_distance_to_fixed_nearest_support_Linf":fixed_raw_linf,"composited_distance_to_fixed_nearest_support_Linf":fixed_comp_linf,"composited_distance_to_fixed_nearest_support_L2":fixed_comp_l2,"composited_distance_min_over_direct_support_Linf":comp_min_linf,"composited_distance_min_over_direct_support_L2":comp_min_l2,"composited_luminance_difference_to_fixed_support":comp_luma_diff,"distance_reduction_fixed_support_Linf":(fixed_raw_linf-fixed_comp_linf) if fixed_raw_linf is not None and fixed_comp_linf is not None else None,"premultiplied_distance_to_fixed_support_L2":premul_dist,"hypothetical_dark_target_RGB":[16,16,16],"hypothetical_dark_target_composite":[float(v) for v in dark],"hypothetical_dark_target_visible_RGB_delta_Linf":dark_delta["linf"],"hypothetical_dark_target_visible_RGB_delta_L2":dark_delta["l2"],"hypothetical_dark_target_visible_luminance_delta":abs(srgb_luma(dark)-lcomp),"aa_gradient_path":None}
    return row_out

def add_gradient_paths(records,source_fit,master_rgb,confirmed,labels,tonal_safe,core):
    for r in records:
        if r["case"]!="#14700" or len(r["candidate_glyph_owner_ids"])!=1: continue
        x=r["x_fitted_220x132"];y=r["y_fitted_220x132"];gid=r["candidate_glyph_owner_ids"][0]
        fixed=r["fixed_spatial_nearest_support"]
        if not fixed: continue
        ax,ay=fixed["x"],fixed["y"];path=[]
        if tonal_safe[ay,ax]:
            parents=[]
            for yy in range(max(0,ay-1),min(glyph.H,ay+2)):
              for xx in range(max(0,ax-1),min(glyph.W,ax+2)):
                if core[yy,xx] and int(labels[yy,xx])==gid: parents.append((xx,yy))
            parents.sort(key=lambda q:((q[0]-ax)**2+(q[1]-ay)**2,q[1],q[0]))
            if parents:
                px,py=parents[0];path.append((px,py,"solid_core"))
            path.append((ax,ay,"confirmed_tonal_attachment"))
        else:
            path.append((ax,ay,"confirmed_support"))
        path.append((x,y,"low_alpha_perimeter"))
        nodes=[]
        for xx,yy,kind in path:
            pix=source_fit[yy,xx];a=int(pix[3]);raw=pix[:3].astype(np.float64);bg=master_rgb[yy,xx].astype(np.float64);co=composite(raw,a,bg)
            nodes.append({"x":xx,"y":yy,"kind":kind,"rgba":[int(v) for v in pix],"alpha":a,"raw_luminance_0_255":srgb_luma(raw),"master_rgb":[float(v) for v in bg],"composited_rgb":[float(v) for v in co],"composited_luminance_0_255":srgb_luma(co)})
        raw_steps=[];comp_steps=[];luma_steps=[]
        for a,b in zip(nodes,nodes[1:]):
            raw_steps.append(dist(a["rgba"][:3],b["rgba"][:3])["l2"])
            comp_steps.append(dist(a["composited_rgb"],b["composited_rgb"])["l2"])
            luma_steps.append(b["composited_luminance_0_255"]-a["composited_luminance_0_255"])
        r["aa_gradient_path"]={"nodes":nodes,"raw_RGB_step_L2":raw_steps,"composited_RGB_step_L2":comp_steps,"composited_luminance_steps":luma_steps,"composited_luminance_monotonic":bool(all(v>=0 for v in luma_steps) or all(v<=0 for v in luma_steps)) if luma_steps else None}

def rgb_canvas(source_fit,master_rgb):
    alpha=source_fit[:,:,3].astype(np.float64)[...,None]/255.0
    vis=source_fit[:,:,:3].astype(np.float64)*alpha+master_rgb.astype(np.float64)*(1-alpha)
    return np.clip(np.rint(vis),0,255).astype(np.uint8)

def palette_value(v,lo,hi):
    t=0. if hi<=lo else min(1.,max(0.,(float(v)-lo)/(hi-lo)))
    # compact blue -> cyan -> yellow -> red heat palette
    stops=[(32,32,128),(32,180,220),(240,220,40),(220,45,35)]
    u=t*(len(stops)-1);i=min(len(stops)-2,int(u));q=u-i
    return tuple(int(round(stops[i][k]*(1-q)+stops[i+1][k]*q)) for k in range(3))

def mask_panel(title,base,mask,color):
    im=Image.fromarray(base,"RGB").resize((660,396),Image.Resampling.NEAREST)
    arr=np.asarray(im).copy();small=np.asarray(Image.fromarray(mask.astype(np.uint8)*255).resize((660,396),Image.Resampling.NEAREST))>0;arr[small]=color
    out=Image.new("RGB",(660,426),(20,20,20));out.paste(Image.fromarray(arr),(0,30));ImageDraw.Draw(out).text((8,8),title,fill="white");return out

def plain_panel(title,arr,crop=None,mark=None):
    im=Image.fromarray(np.clip(np.rint(arr),0,255).astype(np.uint8),"RGB")
    if crop:im=im.crop(crop)
    im=im.resize((660,396),Image.Resampling.NEAREST)
    if mark:
        x,y=mark
        # mark is in full-image coordinates, adjusted for crop.
        if crop:x-=crop[0];y-=crop[1]
        sx=660/max(1,(crop[2]-crop[0])) if crop else 3.;sy=396/max(1,(crop[3]-crop[1])) if crop else 3.
        xx=int((x+.5)*sx);yy=int((y+.5)*sy)
        ImageDraw.Draw(im).rectangle((xx-8,yy-8,xx+8,yy+8),outline=(255,45,25),width=3)
    out=Image.new("RGB",(660,426),(20,20,20));out.paste(im,(0,30));ImageDraw.Draw(out).text((8,8),title,fill="white");return out

def contact(panels,path,cols):
    rows=math.ceil(len(panels)/cols);out=Image.new("RGB",(cols*660,rows*426),(18,18,18))
    for i,p in enumerate(panels):out.paste(p,((i%cols)*660,(i//cols)*426))
    out.save(path,quality=95)

def run(root:Path,ownership_dir:Path,out:Path):
    if "picons" in out.parts or "templates" in out.parts: raise RuntimeError("Refuse diagnostic output under production picons/ or templates/")
    master_path=root/WHITE_MASTER;master_bytes=master_path.read_bytes()
    if sha_bytes(master_bytes)!=MASTER_SHA: raise RuntimeError("WHITE MASTER SHA mismatch; stopped before experiment output")
    source_bytes=(root/SOURCE14700).read_bytes();current_bytes=(root/CURRENT14700).read_bytes();neg_bytes=(root/SOURCE14607).read_bytes();negcur_bytes=(root/CURRENT14607).read_bytes()
    ownership_summary=json.loads((ownership_dir/"SUMMARY.json").read_text(encoding="utf-8"))
    expected_inputs=ownership_summary["input_hashes"]
    if sha_bytes((root/SOURCE14700).read_bytes())!=expected_inputs["#14700_source"]: raise RuntimeError("#14700 source hash differs from frozen ownership experiment")
    if sha_bytes((root/CURRENT14700).read_bytes())!=expected_inputs["#14700_current_white"]: raise RuntimeError("#14700 CURRENT WHITE hash differs from frozen ownership experiment")
    if sha_bytes((root/WHITE_MASTER).read_bytes())!=expected_inputs["white_master"]: raise RuntimeError("WHITE MASTER hash differs from frozen ownership experiment")
    neg_saved=ownership_summary["negative_and_stability_controls"]["#14607/#14611"]
    if sha_bytes((root/SOURCE14607).read_bytes())!=neg_saved["source_sha256"] or sha_bytes((root/CURRENT14607).read_bytes())!=neg_saved["current_white_sha256"]: raise RuntimeError("#14607 source/CURRENT hash differs from frozen negative control")
    ownership=load_ownership(ownership_dir/"14700-LOW-ALPHA-PIXELS.csv","#14700")
    negative=load_ownership(ownership_dir/"14607-LOW-ALPHA-NEGATIVE-CONTROL.csv","#14607")
    source_raw=glyph.load(root/SOURCE14700);source_fit,fitbox=glyph.fit(source_raw)
    neg_raw=glyph.load(root/SOURCE14607);neg_fit,_=glyph.fit(neg_raw)
    master_rgba=glyph.load(master_path);master_rgb=master_rgba[:,:,:3].astype(np.float64)
    masks=glyph.frozen_masks(source_fit);tonal_safe,tonal_labels,_,_=tonal.classify(masks)
    reconstructed=masks["core"]|tonal_safe;labels,n=ndimage.label(reconstructed,structure=glyph.EIGHT)
    confirmed=np.isin(labels,list(GROUP_IDS));protected=masks["protected"]
    if int(confirmed.sum())!=1224: raise RuntimeError(f"#14700 confirmed group drift: {int(confirmed.sum())}")
    recs=[make_record(r,"#14700",source_fit,master_rgba,confirmed,labels,tonal_safe,masks["core"],protected) for r in ownership]
    n_masks=glyph.frozen_masks(neg_fit);n_tone,_,_,_=tonal.classify(n_masks);n_rec=n_masks["core"]|n_tone;n_labels,nn=ndimage.label(n_rec,structure=glyph.EIGHT)
    n_confirmed=np.isin(n_labels,[i for i in range(1,nn+1)])
    # Negative low-alpha candidates remain protected by the frozen mask even
    # when their composite colors look close; this status is never changed.
    neg_recs=[make_record(r,"#14607",neg_fit,master_rgba,n_confirmed,n_labels,n_tone,n_masks["core"],n_masks["protected"]) for r in negative]
    add_gradient_paths(recs,source_fit,master_rgb,confirmed,labels,tonal_safe,masks["core"])
    all_records=recs+neg_recs
    if sum(r["ownership_diagnostic_category"]=="AMBIGUOUS" and r["raw_distance_to_local_support_min_Linf"] is not None and r["raw_distance_to_local_support_min_Linf"]>18 for r in recs)!=252: raise RuntimeError("Frozen #14700 RGB-rejected population no longer equals 252")
    if any(not r["protected_neighborhood"] for r in neg_recs): raise RuntimeError("#14607 control lost protected status")
    if (root/WHITE_MASTER).read_bytes()!=master_bytes: raise RuntimeError("WHITE MASTER changed during read-only diagnostic")
    base=rgb_canvas(source_fit,master_rgb);no=rgb_canvas(neg_fit,master_rgb)
    xys=[(r["x_fitted_220x132"],r["y_fitted_220x132"]) for r in recs if r["ownership_diagnostic_category"]=="AMBIGUOUS" and r["raw_distance_to_local_support_min_Linf"] is not None and r["raw_distance_to_local_support_min_Linf"]>18]
    rgb_rej=np.zeros((glyph.H,glyph.W),bool)
    for x,y in xys:rgb_rej[y,x]=True
    safe_mask=np.zeros_like(rgb_rej);other_mask=np.zeros_like(rgb_rej);neg_mask=np.zeros_like(rgb_rej)
    for r in recs:
        x=r["x_fitted_220x132"];y=r["y_fitted_220x132"]
        if r["ownership_diagnostic_category"]=="SAFE WORDMARK OWNERSHIP":safe_mask[y,x]=True
        elif not rgb_rej[y,x]:other_mask[y,x]=True
    for r in neg_recs:neg_mask[r["y_fitted_220x132"],r["x_fitted_220x132"]]=True
    d_raw=np.full((glyph.H,glyph.W),np.nan);d_comp=np.full_like(d_raw,np.nan)
    for r in recs:
        x=r["x_fitted_220x132"];y=r["y_fitted_220x132"]
        if r["raw_distance_to_local_support_min_Linf"] is not None:d_raw[y,x]=r["raw_distance_to_local_support_min_Linf"]
        if r["composited_distance_min_over_direct_support_Linf"] is not None:d_comp[y,x]=r["composited_distance_min_over_direct_support_Linf"]
    def heat(values,mask):
        outimg=np.full((glyph.H,glyph.W,3),24,np.uint8);vv=values[mask];lo=float(np.nanmin(vv)) if vv.size else 0.;hi=float(np.nanpercentile(vv,95)) if vv.size else 1.
        for y,x in zip(*np.where(mask)):
            v=values[y,x]
            if np.isfinite(v):outimg[y,x]=palette_value(v,lo,hi)
        return outimg
    heat_raw=heat(d_raw,rgb_rej);heat_comp=heat(d_comp,rgb_rej)
    out.mkdir(parents=True,exist_ok=True);diag=out/"diagnostics";diag.mkdir(parents=True,exist_ok=True)
    contact([plain_panel("SOURCE ON WHITE MASTER",base),mask_panel("LOW-ALPHA RGB-REJECTED (252)",base,rgb_rej,(245,145,35)),plain_panel("RAW RGB DISTANCE (Linf)",heat_raw),plain_panel("COMPOSITED DISTANCE (Linf)",heat_comp)],diag/"14700-raw-vs-composited.jpg",2)
    contact([plain_panel("SOURCE ON WHITE MASTER",base),mask_panel("40 SAFE OWNERSHIP",base,safe_mask,(50,230,90)),mask_panel("252 RGB-REJECTED",base,rgb_rej,(245,145,35)),mask_panel("OTHER AMBIGUOUS / OUTLIER",base,other_mask,(210,65,220))],diag/"14700-population-classes.jpg",2)
    # One source-derived representative low-alpha RGB-rejected pixel per glyph,
    # chosen nearest alpha 15, then nearest interior-to-edge pixel by row/col.
    representatives=[]
    for gid in sorted(GROUP_IDS):
        group=[r for r in recs if r["ownership_diagnostic_category"]=="AMBIGUOUS" and r["raw_distance_to_local_support_min_Linf"] is not None and r["raw_distance_to_local_support_min_Linf"]>18 and gid in r["candidate_glyph_owner_ids"]]
        if not group: continue
        q=min(group,key=lambda r:(abs(r["alpha"]-15),r["y_fitted_220x132"],r["x_fitted_220x132"]))
        representatives.append((gid,q))
    # A three-column sheet per representative: same crop/scale and pixel center.
    panels=[];crop_records=[]
    for gid,r in representatives:
        x=r["x_fitted_220x132"];y=r["y_fitted_220x132"];rad=5
        crop=(max(0,x-rad),max(0,y-rad),min(glyph.W,x+rad+1),min(glyph.H,y+rad+1))
        dark_canvas=base.copy()
        # Change only this one low-alpha diagnostic pixel in memory. It is
        # neither an edit mask nor a saved candidate artifact.
        dark_canvas[y,x]=np.clip(np.rint(composite([16,16,16],int(source_fit[y,x,3]),master_rgb[y,x])),0,255).astype(np.uint8)
        panels.extend([plain_panel(f"GLYPH {gid} RAW SOURCE ({x},{y}) a={r['alpha']}",source_fit[:,:,:3],crop,(x,y)),plain_panel(f"GLYPH {gid} COMPOSITED ON MASTER",base,crop,(x,y)),plain_panel(f"GLYPH {gid} HYPOTHETICAL DARK RGB",dark_canvas,crop,(x,y))])
        crop_records.append({"glyph_id":gid,"x":x,"y":y,"alpha":r["alpha"],"crop":crop,"category":r["ownership_diagnostic_category"]})
    contact(panels,diag/"14700-aa-edge-representatives.jpg",3)
    # Pixel-level output includes all 300 #14700 low-alpha pixels and the six
    # protected #14607 controls. Nested support and gradient records preserve
    # each intermediate value needed to recompute the listed distances.
    with (out/"LOW-ALPHA-COMPOSITED-PIXELS.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(all_records[0]),lineterminator="\n");w.writeheader()
        for r in all_records:
            compact=dict(r)
            compact["local_support_pixels"]=[{"xy":[q["x"],q["y"]],"glyph_id":q["glyph_id"],"class":q["class"],"rgba":q["rgba"],"master_rgba":q["master_rgba"]} for q in r["local_support_pixels"]]
            q=r["fixed_spatial_nearest_support"]
            compact["fixed_spatial_nearest_support"]={"xy":[q["x"],q["y"]],"glyph_id":q["glyph_id"],"class":q["class"]} if q else None
            w.writerow({k:json.dumps(v,ensure_ascii=False,separators=(",",":")) if isinstance(v,(list,dict)) else v for k,v in compact.items()})
    categories={"#14700 SAFE REFERENCE":[r for r in recs if r["ownership_diagnostic_category"]=="SAFE WORDMARK OWNERSHIP"],"#14700 RGB REJECTED":[r for r in recs if r["ownership_diagnostic_category"]=="AMBIGUOUS" and r["raw_distance_to_local_support_min_Linf"] is not None and r["raw_distance_to_local_support_min_Linf"]>18],"#14700 OTHER AMBIGUOUS":[r for r in recs if r["ownership_diagnostic_category"]=="AMBIGUOUS" and (r["raw_distance_to_local_support_min_Linf"] is None or r["raw_distance_to_local_support_min_Linf"]<=18)],"#14700 PROTECTED / OTHER":[r for r in recs if r["ownership_diagnostic_category"]=="PROTECTED / OTHER"],"#14607 PROTECTED NEGATIVE CONTROL":neg_recs}
    metric_names=["raw_distance_to_local_support_min_Linf","raw_distance_to_fixed_nearest_support_Linf","composited_distance_to_fixed_nearest_support_Linf","composited_distance_min_over_direct_support_Linf","composited_distance_min_over_direct_support_L2","composited_luminance_difference_to_fixed_support","distance_reduction_fixed_support_Linf","premultiplied_RGB_magnitude_l2","premultiplied_distance_to_fixed_support_L2","hypothetical_dark_target_visible_RGB_delta_Linf","hypothetical_dark_target_visible_RGB_delta_L2","hypothetical_dark_target_visible_luminance_delta"]
    distributions={}
    for name,subset in categories.items():
        distributions[name]={"n":len(subset),"metrics":{m:stats([r[m] for r in subset]) for m in metric_names},"alpha":stats([r["alpha"] for r in subset])}
    bands={}
    for b,lo,hi in ALPHA_BANDS:
        bands[b]={}
        for name,subset in categories.items():
            pick=[r for r in subset if lo<=r["alpha"]<=hi]
            bands[b][name]={"count":len(pick),"metrics":{m:stats([r[m] for r in pick]) for m in metric_names}}
    grad_records=[r for r in recs if r["aa_gradient_path"] is not None]
    smooth_counts={"n_paths":len(grad_records),"monotone_composited_luma":sum(r["aa_gradient_path"]["composited_luminance_monotonic"] is True for r in grad_records),"not_monotone":sum(r["aa_gradient_path"]["composited_luminance_monotonic"] is False for r in grad_records),"missing":sum(r["aa_gradient_path"]["composited_luminance_monotonic"] is None for r in grad_records)}
    raw_comp_current=[]
    current=glyph.load(root/CURRENT14700);pred=rgb_canvas(source_fit,master_rgb)
    output_diff=np.max(np.abs(pred.astype(np.int16)-current[:,:,:3].astype(np.int16)),axis=2)
    summary={"experiment":"Straight-alpha low-alpha raw RGB vs WHITE MASTER composited evidence; diagnostics only","branch":"phase4-v10-component-mask-test","verified_start_head":EXPECTED_HEAD,"master":{"path":WHITE_MASTER,"sha256":sha_bytes(master_bytes),"hash_verified":sha_bytes(master_bytes)==MASTER_SHA,"size":[glyph.W,glyph.H],"RGB_is_sampled_at_each_fitted_pixel_coordinate":True,"RGBA_alpha_range":[int(master_rgba[:,:,3].min()),int(master_rgba[:,:,3].max())],"sampled_target_master_alpha_histogram":dict(Counter(str(int(master_rgba[r['y_fitted_220x132'],r['x_fitted_220x132'],3])) for r in recs))},"inputs":{"#14700_source_sha256":sha_bytes(source_bytes),"#14700_current_white_sha256":sha_bytes(current_bytes),"#14607_source_sha256":sha_bytes(neg_bytes),"#14607_current_white_sha256":sha_bytes(negcur_bytes),"ownership_pixel_rows":len(ownership),"negative_control_rows":len(negative),"confirmed_wordmark_group_pixels":int(confirmed.sum())},"frozen_ownership_evidence":{"14700":{"safe":40,"rgb_rejected":252,"other_ambiguous":7,"protected_or_other":1,"total":300,"ownership_complete":False,"classifier_changed":False},"14607":{"protected_low_alpha_pixels":6,"protected_proximity":6,"safe_ownership":0}},"compositing_model":"C_out = (alpha/255)*C_source + (1-alpha/255)*C_WHITE_MASTER_RGB; float64; no intermediate rounding. MASTER uses its actual RGB at each pixel coordinate, including non-255 textured values.","metrics":{"raw_luminance":"sRGB inverse companding then linear Rec.709, scaled 0..255","composited_luminance":"same metric on floating RGB composite without early quantization","distance":"RGB L-infinity and L2 in 0..255 space","fixed_local_support":"nearest in 8-neighbor support set by squared pixel distance, then y,x; distributions also report minimum over all direct confirmed support pixels","premultiplied_RGB":"(alpha/255)*source RGB; magnitude and distance to same spatial-nearest support","hypothetical_dark_target":"diagnostic math only: target RGB 16,16,16 at unchanged source alpha, composited on same master RGB","alpha_bands":[{"range":b,"inclusive":[lo,hi]} for b,lo,hi in ALPHA_BANDS]},"category_distributions":distributions,"alpha_band_distributions":bands,"aa_gradient_paths":{"definition":"Existing unique-owner direct support only; if support is a previously accepted tonal attachment, add its adjacent frozen solid-core parent. No new pixel is used as support and no ownership is propagated.","summary":smooth_counts},"source_fit_vs_current_WHITE_render":{"comparison":"Diagnostic composite with actual MASTER RGB compared to CURRENT WHITE RGB; no writes","pixel_count_max_channel_delta_gt_1":int(np.count_nonzero(output_diff>1)),"max_channel_delta":int(output_diff.max()),"median_channel_delta":float(np.median(output_diff)),"p95_channel_delta":float(np.percentile(output_diff,95))},"negative_control":{"case":"#14607","all_six_remain_protected":all(r["protected_neighborhood"] for r in neg_recs),"status_unchanged":True,"category_counts":dict(Counter(r["ownership_diagnostic_category"] for r in neg_recs))},"visualizations":{"A":"diagnostics/14700-raw-vs-composited.jpg","B":"diagnostics/14700-population-classes.jpg","C":"diagnostics/14700-aa-edge-representatives.jpg","representative_pixels":crop_records},"outcome":"MIXED — composited and premultiplied evidence are diagnostic only; frozen classifier and protected status unchanged; no candidate; #14700 remains REVIEW","invariants":{"classifier_changed":False,"thresholds_changed":False,"protected_classes_changed":False,"ownership_mask_changed":False,"candidate_generated":False,"production_png_writes":0,"source_or_master_modified":False}}
    (out/"SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    report=["# Phase 4 — #14700 Low-Alpha Composited-Color Diagnostic","","**Scope: measurement only. No classifier, threshold, mask, or candidate was changed.**","",f"## Integrity checks","",f"- Branch checkpoint recorded: `{EXPECTED_HEAD}`.",f"- WHITE MASTER SHA256: `{summary['master']['sha256']}` — {'PASS' if summary['master']['hash_verified'] else 'FAIL'}.",f"- Frozen #14700 ownership population: 300 px (40 safe reference, 252 raw-RGB rejected, 7 other ambiguous, 1 protected/other).",f"- #14607 negative control: 6/6 still within a frozen protected neighborhood; safe ownership remains 0.","","## Composition and measurements","",summary["compositing_model"],"Raw pixel RGB is compared to directly adjacent preconfirmed group support. For a fixed-pair comparison, support is selected by spatial distance (then y/x tie-break) independent of color. The CSV also stores every direct support pair, the minimum RGB/composited distance across that set, source/master values, and the alpha/composited values needed to recompute the results. Luminance uses inverse sRGB companding and linear Rec.709; distances use float64, with no pre-rounding.","","Premultiplied RGB is recorded as `alpha/255 * source RGB` and is not used as an ownership test. Hypothetical dark-target values apply `(16,16,16)` at unchanged alpha only in numeric arrays; no candidate PNG is emitted.","","## Distributions","", "The following metrics are descriptive, not fitted thresholds. See `SUMMARY.json` for min/median/mean/p75/p90/p95/max and all alpha-band breakdowns.",""]
    for name,values in distributions.items():
        report.append(f"### {name} (n={values['n']})")
        for metric in ["raw_distance_to_local_support_min_Linf","raw_distance_to_fixed_nearest_support_Linf","composited_distance_to_fixed_nearest_support_Linf","composited_distance_min_over_direct_support_Linf","distance_reduction_fixed_support_Linf","composited_luminance_difference_to_fixed_support","premultiplied_RGB_magnitude_l2","premultiplied_distance_to_fixed_support_L2","hypothetical_dark_target_visible_RGB_delta_Linf","hypothetical_dark_target_visible_luminance_delta"]:
            report.append(f"- `{metric}`: `{json.dumps(values['metrics'][metric],separators=(',',':'))}`")
        report.append("")
    report += ["## Alpha-gradient evidence", "",f"Unique-owner paths analyzed: {smooth_counts['n_paths']}; composited luminance monotone: {smooth_counts['monotone_composited_luma']}; non-monotone: {smooth_counts['not_monotone']}; no measurable path: {smooth_counts['missing']}. Each row's path records core/attachment/perimeter RGBA, alpha, actual master RGB, raw and composited luminance, and per-step RGB/luminance changes. This is source-topology inspection only; no chaining was used.","",f"The source-fit composite was compared numerically with CURRENT WHITE: max channel delta {summary['source_fit_vs_current_WHITE_render']['max_channel_delta']:.4f}, median {summary['source_fit_vs_current_WHITE_render']['median_channel_delta']:.4f}, p95 {summary['source_fit_vs_current_WHITE_render']['p95_channel_delta']:.4f}. This checks alignment of the source-derived fitted grid and the master pixel coordinates.","","## Negative control and conclusion","", "#14607’s six low-alpha pixels retain protected proximity in every row, regardless of their composited values. The classifier’s protected precedence is unchanged.","", "**Diagnostic category: `MIXED`.** Compare the fixed-pair and best-direct-support distributions for the 252 raw-RGB rejects against the 40 safe reference and six #14607 protected controls. Any improved composited continuity is descriptive evidence only. No threshold or status was altered; all 252 remain rejected, the 40 remain reference-only, ambiguous groups stay ambiguous, #14607 remains protected, and #14700 remains REVIEW. Candidate = none; production writes = 0.","","## Visualizations","", "- A: `diagnostics/14700-raw-vs-composited.jpg` — source on WHITE MASTER, raw-RGB rejects, raw distance and composited distance.","- B: `diagnostics/14700-population-classes.jpg` — safe reference, 252 rejected, other ambiguous/outlier.","- C: `diagnostics/14700-aa-edge-representatives.jpg` — representative edge crops: source RGB, composited on MASTER, hypothetical dark-target composite.",""]
    (out/"REPORT.md").write_text("\n".join(report),encoding="utf-8")
    print(json.dumps({"master_sha256":summary["master"]["sha256"],"categories":{k:v["n"] for k,v in distributions.items()},"gradient":smooth_counts,"current_composite_max_delta":summary["source_fit_vs_current_WHITE_render"]["max_channel_delta"],"outcome":summary["outcome"],"out":str(out)},indent=2))

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--fixture-root",type=Path,required=True);ap.add_argument("--ownership-dir",type=Path,required=True);ap.add_argument("--output-dir",type=Path,required=True);a=ap.parse_args();run(a.fixture_root.resolve(),a.ownership_dir.resolve(),a.output_dir.resolve())
if __name__=="__main__":main()
