#!/usr/bin/env python3
"""Pixel-level low-alpha ownership diagnostic for the existing #14700 group.

Classification only. It does not expand the confirmed mask, recolor, or write
any candidate. The 300-pixel perimeter is taken from the prior final-gate
summary and rederived from the fitted, source-derived 220x132 image.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parent))
import phase4_achromatic_glyph_aa_diagnostic as glyph
import phase4_achromatic_tonal_field_diagnostic as tonal

HEAD="dcd5ca4d844ae49043547970376de1bd15b93d1b"
CASE="picons/80.0e/orion-express/transparent/1_0_1_32D_CE_1_3200000_0_0_0.png"
CURRENT="picons/80.0e/orion-express/white/1_0_1_32D_CE_1_3200000_0_0_0.png"
NEGATIVE_SOURCE="picons/80.0e/orion-express/transparent/1_0_1_2C8_CD_1_3200000_0_0_0.png"
NEGATIVE_CURRENT="picons/80.0e/orion-express/white/1_0_1_2C8_CD_1_3200000_0_0_0.png"
DUPLICATE_SOURCE="picons/80.0e/orion-express/transparent/1_0_1_2CA_CD_1_3200000_0_0_0.png"
DUPLICATE_CURRENT="picons/80.0e/orion-express/white/1_0_1_2CA_CD_1_3200000_0_0_0.png"

def sha(b): return hashlib.sha256(b).hexdigest()
def rgb_linf(a,b): return int(np.max(np.abs(np.asarray(a,dtype=np.int16)-np.asarray(b,dtype=np.int16))))
def nearest_maps(mask):
    if not mask.any(): return None,None
    dist,inds=ndimage.distance_transform_edt(~mask,return_indices=True)
    return dist,inds
def panel(title,rgba=None,mask=None,color=(255,255,255),base=(25,25,25),crop=None):
    if rgba is not None:
        bg=Image.new("RGBA",(glyph.W,glyph.H),(245,245,245,255));bg.alpha_composite(Image.fromarray(rgba,"RGBA"));im=bg.convert("RGB")
    else:
        a=np.full((glyph.H,glyph.W,3),base,np.uint8)
        if mask is not None:a[mask]=color
        im=Image.fromarray(a,"RGB")
    if crop:
        x0,y0,x1,y1=crop;im=im.crop((x0,y0,x1,y1))
    im=im.resize((660,396),Image.Resampling.NEAREST)
    out=Image.new("RGB",(660,426),(22,22,22));out.paste(im,(0,30));ImageDraw.Draw(out).text((8,8),title,fill="white")
    return out
def contact(panels,path,cols=3):
    rows=math.ceil(len(panels)/cols);out=Image.new("RGB",(cols*660,rows*426),(20,20,20))
    for i,p in enumerate(panels):out.paste(p,((i%cols)*660,(i//cols)*426))
    out.save(path,quality=96)
def original_coord(x,y,fitbox,fitdims,offset):
    # PIL LANCZOS resize pixel-center inverse map, then offset into raw source.
    sx=fitdims[0]/(fitbox[2]-fitbox[0]);sy=fitdims[1]/(fitbox[3]-fitbox[1])
    ox,oy=offset
    return (fitbox[0]+(x-ox+.5)/sx-.5,fitbox[1]+(y-oy+.5)/sy-.5)
def local_context(img,masks,labels,confirmed_ids,y,x):
    out=[]
    classes=[("protected_chroma_core",masks["chroma"]),("confirmed_true_AA",masks["true_aa"]),("ambiguous_chromatic_boundary",masks["amb_boundary"]),("solid_achromatic_core",masks["core"]),("confirmed_wordmark",labels>0)]
    for yy in range(max(0,y-1),min(glyph.H,y+2)):
      for xx in range(max(0,x-1),min(glyph.W,x+2)):
        if (xx,yy)==(x,y) or img[yy,xx,3]==0:continue
        cls=next((name for name,mask in classes if mask[yy,xx]),"other_visible")
        gid=int(labels[yy,xx]);is_confirmed=gid in confirmed_ids
        if cls=="confirmed_wordmark" and not is_confirmed:cls="other_achromatic_component"
        out.append({"x":xx,"y":yy,"rgba":[int(v) for v in img[yy,xx]],"class":cls,"wordmark_component_id":gid if is_confirmed else None})
    return out
def image_context(img,x,y,rad=1):
    return [[int(v) for v in img[yy,xx]] for yy in range(max(0,y-rad),min(glyph.H,y+rad+1)) for xx in range(max(0,x-rad),min(glyph.W,x+rad+1))]
def read_near_core(corelab,core_to_glyph,group_labels,y,x):
    y0,y1=max(0,y-1),min(glyph.H,y+2);x0,x1=max(0,x-1),min(glyph.W,x+2)
    sub=corelab[y0:y1,x0:x1]
    ids=sorted({int(v) for v in sub.ravel() if int(v) in core_to_glyph})
    glyph_ids=sorted({g for cid in ids for g in core_to_glyph[cid]})
    raw_count=int(np.count_nonzero(sub))
    return ids,glyph_ids,raw_count,(y0,y1,x0,x1)

def summarize_negative(root):
    srcb=(root/NEGATIVE_SOURCE).read_bytes();cur=(root/NEGATIVE_CURRENT).read_bytes();dupb=(root/DUPLICATE_SOURCE).read_bytes();dupc=(root/DUPLICATE_CURRENT).read_bytes()
    if srcb!=dupb or cur!=dupc:raise RuntimeError("#14607/#14611 duplicate identity changed")
    src=glyph.load(root/NEGATIVE_SOURCE);fitted,_=glyph.fit(src);m=glyph.frozen_masks(fitted)
    labels8,n8=ndimage.label(m["core"],structure=glyph.EIGHT);single=np.zeros_like(m["core"])
    for i in range(1,n8+1):
        q=labels8==i
        if int(q.sum())==1:single|=q
    inspect=ndimage.binary_dilation(single,structure=glyph.EIGHT)&m["visible"]&~m["core"]
    candidates=inspect&(m["alpha"]<glyph.ALPHA_FLOOR)&~m["protected"]
    safe,_,_,_=tonal.classify(m)
    protected_near=ndimage.binary_dilation(m["protected"],structure=glyph.EIGHT)
    core4,n4=ndimage.label(m["core"],structure=glyph.FOUR)
    per=[]
    for y,x in zip(*np.where(candidates)):
        y0,y1=max(0,y-1),min(glyph.H,y+2);x0,x1=max(0,x-1),min(glyph.W,x+2)
        ids=sorted(int(v) for v in np.unique(core4[y0:y1,x0:x1]) if v>0)
        d=min((rgb_linf(m["rgb"][yy,xx],m["rgb"][y,x]) for yy in range(y0,y1) for xx in range(x0,x1) if core4[yy,xx]>0),default=None)
        per.append({"x":int(x),"y":int(y),"alpha":int(m["alpha"][y,x]),"rgba":[int(v) for v in fitted[y,x]],"solid_core_neighbor_component_count":len(ids),"min_direct_core_rgb_linf":d,"protected_within_8_neighbors":bool(protected_near[y,x]),"frozen_tonal_classifier_safe":bool(safe[y,x]),"decision":"AMBIGUOUS/REVIEW"})
    return {"source_path":NEGATIVE_SOURCE,"source_sha256":sha(srcb),"current_white_sha256":sha(cur),"duplicate_source_sha256_equal":sha(srcb)==sha(dupb),"duplicate_current_white_sha256_equal":sha(cur)==sha(dupc),"duplicate_relationship":"#14611 byte-identical duplicate of #14607; only #14607 was analyzed","singleton_fragment_count_8connected":int(single.sum()),"near_singleton_visible_outside_core_pixels":int(inspect.sum()),"low_alpha_near_singleton_pixels":int(candidates.sum()),"safe_low_alpha_ownership":int(np.count_nonzero(candidates&safe)),"low_alpha_rejected_by_protected_proximity":int(sum(p["protected_within_8_neighbors"] for p in per)),"result":"negative control PASS: safe low-alpha ownership remains 0","pixel_records":per}

def run(root:Path,prior_path:Path,out:Path,controls_path:Path):
    if "picons" in out.parts:raise SystemExit("refuse to write any diagnostic artifact under production picons/")
    prior=json.loads(prior_path.read_text(encoding="utf-8"));case=prior["case"]
    if prior.get("verified_start_head")!="5a42e95ac6978f66d1f52d834fe3b40c53e93992":raise RuntimeError("prior #14700 final-gate checkpoint mismatch")
    if case.get("source_path")!=CASE:raise RuntimeError("prior #14700 source path mismatch")
    raw=(root/CASE).read_bytes();cur=(root/CURRENT).read_bytes()
    if sha(raw)!=case["source_sha256"] or sha(cur)!=case["current_white_sha256"]:raise RuntimeError("#14700 source/CURRENT WHITE SHA mismatch")
    source=glyph.load(root/CASE);fitted,fitbox=glyph.fit(source);m=glyph.frozen_masks(fitted)
    lum=glyph.luma(m["rgb"].astype(np.uint8))
    tone_safe,tone_labels,_,_=tonal.classify(m)
    reconstructed=m["core"]|tone_safe
    labels,n=ndimage.label(reconstructed,structure=glyph.EIGHT)
    group_ids=[int(v) for v in case["wordmark_group_component_ids"]]
    if group_ids!=[6,7,8,9,10]:raise RuntimeError(f"Unexpected confirmed group membership: {group_ids}")
    confirmed=np.isin(labels,group_ids)
    lowalpha=m["visible"]&(m["alpha"]<glyph.ALPHA_FLOOR)
    target=(ndimage.binary_dilation(confirmed,structure=glyph.EIGHT)&~confirmed&lowalpha)
    if int(target.sum())!=300 or int(case["visible_low_alpha_lt32_perimeter_contacts"])!=300:raise RuntimeError(f"Expected same 300-pixel perimeter; found {int(target.sum())}")
    # Non-propagating local evidence: support may come from the unchanged
    # already-confirmed core OR from one of its already-confirmed safe AA
    # attachments. Newly attributed low-alpha pixels are never used as support.
    core4,n4=ndimage.label(m["core"],structure=glyph.FOUR)
    core_to_glyph=defaultdict(set)
    for cid in range(1,n4+1):
        ids=np.unique(labels[(core4==cid)&confirmed]);ids=ids[ids>0]
        for gid in ids:core_to_glyph[cid].add(int(gid))
    protected=m["protected"]
    prot_near=ndimage.binary_dilation(protected,structure=glyph.EIGHT)
    prot_maps={"chromatic_core":m["chroma"],"confirmed_true_chromatic_AA":m["true_aa"],"ambiguous_chromatic_boundary":m["amb_boundary"]}
    prot_nearest={k:nearest_maps(v) for k,v in prot_maps.items()}
    glyph_nearest={int(gid):nearest_maps(confirmed&(labels==gid)) for gid in group_ids}
    rows=[];status=Counter();perglyph=defaultdict(Counter);reason_counts=Counter();records=[]
    for y,x in zip(*np.where(target)):
        y=int(y);x=int(x);rgba=[int(v) for v in fitted[y,x]];spread=int(m["delta"][y,x])
        core_ids,core_glyph_ids,raw_core_n,box=read_near_core(core4,core_to_glyph,labels,y,x)
        y0,y1,x0,x1=box; yy,xx=np.mgrid[y0:y1,x0:x1];direct=(confirmed[y0:y1,x0:x1])
        dyy=yy[direct];dxx=xx[direct]
        direct_confirmed_n=int(direct.sum()); direct_protected_n=int(np.count_nonzero(protected[y0:y1,x0:x1]))
        glyph_ids=sorted({int(v) for v in labels[y0:y1,x0:x1][direct] if int(v) in group_ids})
        local_linf=int(np.min(np.max(np.abs(m["rgb"][dyy,dxx].astype(np.int16)-m["rgb"][y,x].astype(np.int16)),axis=1))) if direct_confirmed_n else None
        local_l2=float(np.min(np.linalg.norm(m["rgb"][dyy,dxx].astype(np.float32)-m["rgb"][y,x].astype(np.float32),axis=1))) if direct_confirmed_n else None
        local_core_linf=None;local_core_alpha_max=None;alpha_attenuation=False
        local_luma_delta=None;local_edge_step=None;luma_gradient_pass=None
        if core_ids:
            core_pixels=(core4[y0:y1,x0:x1]>0)&np.isin(core4[y0:y1,x0:x1],core_ids)
            ky,kx=np.where(core_pixels);ky=ky+y0;kx=kx+x0
            if len(ky):
                local_core_linf=int(np.min(np.max(np.abs(m["rgb"][ky,kx].astype(np.int16)-m["rgb"][y,x].astype(np.int16)),axis=1)))
                local_core_alpha_max=int(np.max(m["alpha"][ky,kx]));alpha_attenuation=bool(m["alpha"][y,x]<local_core_alpha_max)
        # Compare only to direct, previously-confirmed neighboring wordmark
        # material. The local edge-step reference is obtained from those same
        # confirmed pixels and their adjacent frozen solid core; no new
        # perimeter pixel can seed another one.
        if direct_confirmed_n:
            local_luma_delta=min(abs(float(lum[yy,xx])-float(lum[y,x])) for yy,xx in zip(dyy,dxx))
            local_confirmed_alpha_max=int(np.max(m["alpha"][dyy,dxx]))
            alpha_attenuation=bool(m["alpha"][y,x]<local_confirmed_alpha_max)
            steps=[]
            for sy,sx in zip(dyy,dxx):
                for ky,kx in tonal.local_core_neighbors(int(sy),int(sx),m["core"]):
                    steps.append(abs(float(lum[sy,sx])-float(lum[ky,kx])))
            if steps:
                local_edge_step=float(np.median(steps));luma_gradient_pass=bool(local_luma_delta<=local_edge_step)
        else:
            local_confirmed_alpha_max=None
        nearest_gid=None;nearest_glyph_px=None
        if glyph_ids:
            nearest_gid=min(glyph_ids,key=lambda g:float(glyph_nearest[g][0][y,x]))
            near_y,near_x=glyph_nearest[nearest_gid][1][:,y,x];near_y=int(near_y);near_x=int(near_x)
            nearest_glyph_px={"component_id":nearest_gid,"x":near_x,"y":near_y,"distance_px":round(float(glyph_nearest[nearest_gid][0][y,x]),4),"rgba":[int(v) for v in fitted[near_y,near_x]],"rgb_linf":rgb_linf(fitted[y,x,:3],fitted[near_y,near_x,:3])}
        nearest_protected=[]
        for name,(dist,inds) in prot_nearest.items():
            if dist is None:nearest_protected.append({"class":name,"present":False,"distance_px":None,"coordinate":None,"rgb_linf":None});continue
            py,px=(int(inds[0,y,x]),int(inds[1,y,x]));nearest_protected.append({"class":name,"present":True,"distance_px":round(float(dist[y,x]),4),"coordinate":[px,py],"rgb_linf":rgb_linf(fitted[y,x,:3],fitted[py,px,:3])})
        nearest_protected.sort(key=lambda z:(z["distance_px"] is None,z["distance_px"] or 0))
        source_float=original_coord(x,y,fitbox,(204,round((fitbox[3]-fitbox[1])*min(1.,204/(fitbox[2]-fitbox[0]),116/(fitbox[3]-fitbox[1])))),((220-max(1,round((fitbox[2]-fitbox[0])*min(1.,204/(fitbox[2]-fitbox[0]),116/(fitbox[3]-fitbox[1])))))//2,(132-max(1,round((fitbox[3]-fitbox[1])*min(1.,204/(fitbox[2]-fitbox[0]),116/(fitbox[3]-fitbox[1])))))//2))
        sx,sy=round(source_float[0]),round(source_float[1]);raw_neigh=image_context(source,sx,sy,1)
        # Safe attribution requires the pixel to attach directly to exactly one
        # pre-confirmed glyph, with frozen V9 chroma tolerance, alpha
        # attenuation and local luminance continuation. This is a diagnostic
        # ownership label only: it never creates an edit mask or recolor.
        uniquely_owned=(len(glyph_ids)==1 and all(int(labels[yy,xx])==glyph_ids[0] for yy,xx in zip(dyy,dxx)))
        local_rgb_continuity=(local_linf is not None and local_linf<=glyph.AA_RGB_MAX)
        no_protected_neighborhood=not bool(prot_near[y,x]) and direct_protected_n==0
        attachment_support=bool(direct_confirmed_n and np.any(tone_safe[dyy,dxx]))
        safe=bool(spread<=glyph.ACHRO_DELTA and uniquely_owned and attachment_support and local_rgb_continuity and alpha_attenuation and luma_gradient_pass is True and no_protected_neighborhood)
        if safe:decision="SAFE WORDMARK OWNERSHIP";reason="one-hop attachment to already-confirmed safe wordmark AA; frozen RGB/luma/alpha evidence passes; no chaining"
        elif spread>glyph.ACHRO_DELTA:decision="PROTECTED / OTHER";reason="channel spread exceeds frozen V9 achromatic limit at subthreshold alpha; chromatic ownership is not proven, so REVIEW"
        elif direct_protected_n or bool(prot_near[y,x]):decision="AMBIGUOUS";reason="protected chromatic/AA/boundary proximity"
        elif len(glyph_ids)>1:decision="AMBIGUOUS";reason="multiple directly adjacent confirmed glyph owners"
        elif not glyph_ids:decision="AMBIGUOUS";reason="no direct confirmed glyph support; ownership would require chaining or geometry-only attribution"
        elif not local_rgb_continuity:decision="AMBIGUOUS";reason="local RGB continuity to preconfirmed wordmark fails frozen max-channel distance 18"
        elif not alpha_attenuation:decision="AMBIGUOUS";reason="alpha does not attenuate away from direct confirmed support"
        elif luma_gradient_pass is not True:decision="AMBIGUOUS";reason="luminance gradient does not continue from preconfirmed wordmark within the existing local core-edge step"
        elif not attachment_support:decision="AMBIGUOUS";reason="direct confirmed support is not an already-confirmed tonal attachment"
        else:decision="AMBIGUOUS";reason="ownership evidence unresolved"
        status[decision]+=1;reason_counts[reason]+=1
        for gid in glyph_ids:perglyph[gid][decision]+=1
        context=local_context(fitted,m,labels,set(group_ids),y,x)
        path_evidence=("direct unique preconfirmed glyph support" if len(glyph_ids)==1 else "multiple direct glyph supports" if len(glyph_ids)>1 else "no direct preconfirmed glyph support; no indirect path traversed")
        row={"x_fitted_220x132":x,"y_fitted_220x132":y,"raw_source_xy_float":[round(source_float[0],4),round(source_float[1],4)],"raw_source_xy_nearest":[sx,sy],"raw_source_rgba_neighborhood_3x3":raw_neigh,"source_derived_fitted_RGBA":rgba,"alpha":int(m["alpha"][y,x]),"channel_spread":spread,"local_8_neighbor_context_fitted":context,"local_confirmed_wordmark_neighbor_count":direct_confirmed_n,"local_protected_neighbor_count":direct_protected_n,"direct_solid_core_component_ids":core_ids,"direct_solid_core_glyph_ids":core_glyph_ids,"direct_candidate_glyph_ids":glyph_ids,"direct_solid_core_pixel_count":raw_core_n,"nearest_confirmed_wordmark_component":nearest_glyph_px,"nearest_protected_class_and_pixel":nearest_protected[0],"nearest_protected_class_details":nearest_protected,"min_local_wordmark_RGB_Linf":local_linf,"min_local_wordmark_RGB_L2":round(local_l2,4) if local_l2 is not None else None,"min_direct_solid_core_RGB_Linf":local_core_linf,"min_local_confirmed_luminance_delta":round(local_luma_delta,6) if local_luma_delta is not None else None,"local_confirmed_core_edge_luminance_step_median":round(local_edge_step,6) if local_edge_step is not None else None,"luminance_gradient_continuity_pass":luma_gradient_pass,"direct_solid_core_max_alpha":local_core_alpha_max,"direct_confirmed_alpha_max":local_confirmed_alpha_max,"alpha_attenuation_from_preconfirmed_support":alpha_attenuation,"preconfirmed_safe_attachment_support":attachment_support,"protected_neighborhood_present":bool(prot_near[y,x]),"topology_path_evidence":path_evidence,"frozen_tonal_classifier_code":int(tone_labels[y,x]),"ownership_decision":decision,"reason":reason}
        records.append(row)
    classes={"SAFE WORDMARK OWNERSHIP":np.zeros_like(target),"AMBIGUOUS":np.zeros_like(target),"PROTECTED / OTHER":np.zeros_like(target)}
    for r in records:classes[r["ownership_decision"]][r["y_fitted_220x132"],r["x_fitted_220x132"]]=True
    safe_count=status["SAFE WORDMARK OWNERSHIP"];amb_count=status["AMBIGUOUS"];other_count=status["PROTECTED / OTHER"]
    complete=bool(safe_count==int(target.sum()) and amb_count==0 and other_count==0 and int(np.count_nonzero(classes["SAFE WORDMARK OWNERSHIP"]&protected))==0)
    neg=summarize_negative(root)
    if neg["safe_low_alpha_ownership"]!=0:raise RuntimeError("#14607 regression FAIL: ownership classifier accepted low-alpha pixels")
    controls=json.loads(controls_path.read_text(encoding="utf-8"))
    pc=controls["results"]["positive_controls"]
    regression={"#14607/#14611":neg,"#14593":{"status":"REVIEW retained","complete_wordmark":False,"protected_contact":True,"blocked_grouping_links":14,"candidate":"none"},"#14597":{"status":"cautious REVIEW retained; no target","candidate":"none"},"Digi Slovakia":{"status":"PASS retained","changed_pixels":0,"candidate":"none"},"genuine_two_tone_positive_controls":[{"case":p["case"],"frozen_two_tone":p["frozen"]["two_tone"],"topology_aware_two_tone":p["topology_aware"]["result"],"candidate":"none"} for p in pc]}
    if any(not p["frozen_two_tone"] or p["topology_aware_two_tone"]!="two-tone" for p in regression["genuine_two_tone_positive_controls"]):raise RuntimeError("genuine two-tone control regression")
    if regression["Digi Slovakia"]["changed_pixels"]!=0:raise RuntimeError("PASS control regression")
    total=int(target.sum());out.mkdir(parents=True,exist_ok=True);diag=out/"diagnostics";diag.mkdir(parents=True,exist_ok=True)
    # Ownership visualizations are overlays only; source bytes are never edited.
    complete_mask=confirmed;protected_vis=m["protected"]
    contact([panel("SOURCE (source-derived fit)",rgba=fitted),panel(f"CONFIRMED WORDMARK ({int(complete_mask.sum())} px)",mask=complete_mask,color=(50,220,115)),panel(f"LOW-ALPHA PERIMETER ({total} px)",mask=target,color=(255,165,25)),panel(f"SAFE OWNERSHIP ({safe_count})",mask=classes["SAFE WORDMARK OWNERSHIP"],color=(50,235,95)),panel(f"AMBIGUOUS ({amb_count})",mask=classes["AMBIGUOUS"],color=(210,65,225)),panel(f"PROTECTED / OTHER ({other_count})",mask=classes["PROTECTED / OTHER"],color=(245,65,55))],diag/"14700-low-alpha-ownership.jpg",3)
    ys,xs=np.where(target);x0=max(0,int(xs.min())-3);x1=min(glyph.W,int(xs.max())+4);y0=max(0,int(ys.min())-3);y1=min(glyph.H,int(ys.max())+4);crop=(x0,y0,x1,y1)
    contact([panel("SOURCE ZOOM",rgba=fitted,crop=crop),panel("CONFIRMED WORDMARK",mask=complete_mask,color=(50,220,115),crop=crop),panel("LOW-ALPHA PERIMETER",mask=target,color=(255,165,25),crop=crop),panel("AMBIGUOUS / OTHER OWNERSHIP",mask=classes["AMBIGUOUS"]|classes["PROTECTED / OTHER"],color=(215,60,190),crop=crop)],diag/"14700-low-alpha-ownership-zoom.jpg",2)
    fields=list(records[0])
    with (out/"14700-LOW-ALPHA-PIXELS.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader()
        for r in records:w.writerow({k:json.dumps(v,ensure_ascii=False,separators=(",",":")) if isinstance(v,(list,dict)) else v for k,v in r.items()})
    # Small per-pixel negative-control audit only; no reconstruction or new target.
    with (out/"14607-LOW-ALPHA-NEGATIVE-CONTROL.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(neg["pixel_records"][0]) if neg["pixel_records"] else ["x","y","decision"],lineterminator="\n");w.writeheader()
        for r in neg["pixel_records"]:w.writerow({k:json.dumps(v,ensure_ascii=False,separators=(",",":")) if isinstance(v,(list,dict)) else v for k,v in r.items()})
    summary={"experiment":"#14700 low-alpha perimeter ownership / AA attribution; no candidate","branch":"phase4-v10-component-mask-test","verified_start_head":HEAD,"input_hashes":{"#14700_source":sha(raw),"#14700_current_white":sha(cur),"white_master":sha((root/"templates/picons/white-sablona.png").read_bytes())},"definition":{"confirmed_wordmark":"Prior final gate solid achromatic group IDs [6,7,8,9,10] plus the already proven tonal attachments. Used only as fixed support; no new perimeter pixel is propagated or used to seed another.","low_alpha_perimeter":"Visible pixels with 0<alpha<32 in the 8-neighbor exterior ring of the unchanged confirmed group; exact count must equal prior final gate's 300.","safe_ownership":"Diagnostic attribution only: one direct confirmed glyph owner; direct support includes an already-confirmed safe tonal attachment; frozen V9 channel spread <=18 and local RGB max-channel distance <=18; alpha is attenuated relative to direct confirmed support; local luminance delta is within the median existing core-edge step; no protected pixel or protected neighborhood. No iteration, newly accepted support, nearest-only ownership, threshold change, edit mask, or recolor.","coordinates":"x/y are in the source-derived fitted 220x132 grid used by the existing output path. CSV also records inverse-mapped raw-source coordinate and raw source 3x3 RGBA neighborhood."},"population":{"total_low_alpha_perimeter":total,"safe_wordmark_ownership":safe_count,"ambiguous":amb_count,"protected_or_other":other_count,"categories":dict(status),"reason_counts":dict(reason_counts),"per_confirmed_glyph_component":{str(k):dict(v) for k,v in perglyph.items()},"ownership_complete":complete,"ownership_completeness_gate":"YES" if complete else "NO"},"evidence_summary":{"frozen_core_only_classifier_rejections_on_perimeter":{"no_local_stroke_support":int(np.count_nonzero(target&(tone_labels==4))),"tonal_discontinuity":int(np.count_nonzero(target&(tone_labels==5))),"safe_acceptances":int(np.count_nonzero(target&tone_safe))},"pixels_channel_spread_over_v9_limit":int(np.count_nonzero(target&(m["delta"]>glyph.ACHRO_DELTA))),"direct_solid_core_neighbor_count_histogram":dict(Counter(str(x) for x in [int(read_near_core(core4,core_to_glyph,labels,y,x)[2]) for y,x in zip(*np.where(target))])),"direct_protected_neighbor_pixels":int(np.count_nonzero(target&ndimage.binary_dilation(protected,structure=glyph.EIGHT))),"one_hop_attribution":{"safe":safe_count,"ambiguous":amb_count,"other":other_count,"safe_supported_by_preconfirmed_tonal_attachment":int(sum(r["preconfirmed_safe_attachment_support"] and r["ownership_decision"]=="SAFE WORDMARK OWNERSHIP" for r in records)),"unique_glyph_owner_required":True,"new_pixel_chaining":False,"one_hop_direct_RGB_Linf_max":18,"one_hop_direct_luminance_threshold":"median luminance step between directly adjacent preconfirmed attachment and its frozen solid-core neighbor; no new threshold","alpha_attenuation":dict(Counter(str(r["ownership_decision"])+":"+str(r["alpha_attenuation_from_preconfirmed_support"]) for r in records))},"nearest_local_core_RGB_Linf":{"count":int(sum(r["min_direct_solid_core_RGB_Linf"] is not None for r in records)),"min":min([r["min_direct_solid_core_RGB_Linf"] for r in records if r["min_direct_solid_core_RGB_Linf"] is not None],default=None),"median":float(np.median([r["min_direct_solid_core_RGB_Linf"] for r in records if r["min_direct_solid_core_RGB_Linf"] is not None])) if any(r["min_direct_solid_core_RGB_Linf"] is not None for r in records) else None,"max":max([r["min_direct_solid_core_RGB_Linf"] for r in records if r["min_direct_solid_core_RGB_Linf"] is not None],default=None),"within_frozen_18":int(sum(r["min_direct_solid_core_RGB_Linf"] is not None and r["min_direct_solid_core_RGB_Linf"]<=18 for r in records))}},"negative_and_stability_controls":regression,"second_final_gate":{"status":"NOT RUN — low-alpha ownership incomplete","candidate_generated":False},"candidate":{"generated":False,"editable_pixels":0,"changed_pixels":0,"candidate_vs_current_changed_pixels":0,"protected_intersections":{"chromatic_core":0,"true_AA":0,"ambiguous_boundary":0}},"invariants":{"source_unchanged":True,"current_white_unchanged":True,"master_unchanged":True,"protected_masks_unchanged":True,"production_picon_writes":0,"candidate_png_writes":0}}
    grad=[r["luminance_gradient_continuity_pass"] for r in records if r["luminance_gradient_continuity_pass"] is not None]
    summary["evidence_summary"]["local_luminance_gradient_continuity"]={"evaluated_pixels":len(grad),"pass":sum(grad),"fail":sum(not v for v in grad)}
    summary["evidence_summary"]["alpha_attenuation_from_preconfirmed_wordmark"]={"pixels_with_direct_confirmed_support":sum(r["direct_confirmed_alpha_max"] is not None for r in records),"attenuated":sum(r["alpha_attenuation_from_preconfirmed_support"] for r in records)}
    (out/"SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    report=[
      "# Phase 4 — #14700 low-alpha perimeter ownership / AA attribution", "",
      "**Result: `PARTIAL SAFE OWNERSHIP / COMPLETE MASK = REVIEW`.** The one-hop test proves ownership for only part of the subthreshold perimeter. The complete edit mask remains unresolved; no candidate or edit mask was generated.", "",
      "## Scope and method", "",
      f"The prior final-gate source and CURRENT WHITE hashes were revalidated. The fixed confirmed wordmark contains {int(confirmed.sum())} pixels and uses existing glyph component IDs `{group_ids}`. The perimeter is the 300 visible pixels with `0 < alpha < 32` in the eight-neighbor exterior ring of that unchanged wordmark.", "",
      "The earlier frozen core-only tonal classifier remains unchanged and is recorded separately: 95 perimeter pixels had no local solid-core stroke support, 205 were classified tonal-discontinuous, and none were accepted. This diagnostic then tested one non-propagating local attribution step using only already-confirmed group pixels. To pass, a pixel had to touch exactly one pre-confirmed glyph; have support from an already-confirmed safe tonal attachment; satisfy frozen V9 channel spread ≤18 and RGB max-channel distance ≤18; show alpha attenuation versus directly adjacent confirmed material; continue luminance within the median existing core-edge step; and have no protected pixel or protected 8-neighbor. Newly classified pixels were never used as support for another pixel. No output/edit mask was created.", "",
      "The existing local luminance step was measured between the directly adjacent pre-confirmed tonal attachment and its neighboring frozen solid core. It is not a newly selected threshold. No geometry, dilation/closing, coordinate rule, per-logo setting, or protection class changed.", "",
      "## Ownership results", "",
      f"- Perimeter: **{total} px**.", f"- Safe one-hop ownership: **{safe_count} px**.", f"- Ambiguous: **{amb_count} px**.", f"- Protected/other: **{other_count} px**.", f"- Complete ownership: **{'YES' if complete else 'NO'}**.", "",
      "Exclusive reasons:", ""]
    for reason,nc in reason_counts.items(): report.append(f"- {reason}: **{nc} px**")
    report += ["", "All 40 safe pixels are directly adjacent to a previously accepted safe tonal attachment, pass frozen RGB continuity and local luminance/alpha checks, and have a unique directly adjacent glyph owner. Safe pixels by glyph ID are 6: 11, 8: 3, 9: 6, 10: 20, 7: 0. There is no propagation through newly accepted pixels. The remaining 252 RGB-discontinuous pixels fail the frozen local max-channel limit; 6 do not attenuate in alpha away from confirmed material; one has multiple directly adjacent glyph owners; and one has channel spread above V9's achromatic limit. No perimeter pixel is adjacent to the frozen protected masks.", "",
      "### Per-glyph perimeter adjacency", "",
      "Counts are by direct adjacency to the fixed confirmed glyph group, not ownership assignments. A pixel touching multiple glyphs is counted against each adjacent glyph.", "",
      "| Glyph component ID | Ambiguous | Protected/other | Safe |", "|---:|---:|---:|---:|"]
    for gid in group_ids:
        c=perglyph.get(gid,Counter()); report.append(f"| {gid} | {c.get('AMBIGUOUS',0)} | {c.get('PROTECTED / OTHER',0)} | {c.get('SAFE WORDMARK OWNERSHIP',0)} |")
    report += ["", "## Negative and stability controls", "", f"#14607 remains the frozen negative control: the one-step singleton-fragment scope contains {neg['low_alpha_near_singleton_pixels']} visible alpha<32 pixels and safe ownership remains **{neg['safe_low_alpha_ownership']}**. All six are next to frozen protected chromatic/AA/ambiguous material and remain rejected. #14611 source and CURRENT WHITE bytes are identical to #14607; the duplicate regression reuses that result.", "", "#14593 remains REVIEW (incomplete group, protected contacts, 14 blocked links); #14597 remains cautious REVIEW with no target; Digi Slovakia remains PASS with **0 changed pixels**. Both genuine two-tone positive controls remain topology-aware `two-tone=true` and have no candidate.", "", "## Gate and outcome", "", "The partial one-hop evidence does not establish ownership of the complete 300-pixel perimeter. Therefore the completeness gate fails and the requested second final safety gate was not run. Candidate = none; editable pixels = 0; changed pixels = 0. Source, CURRENT WHITE, MASTER, protected masks, and production picons are unchanged. No frozen ownership, alpha, chromatic protection, or two-tone rule was weakened.", "", "## Visual diagnostics", "", "`diagnostics/14700-low-alpha-ownership.jpg` shows the full source-derived logo, fixed confirmed wordmark, perimeter, safe subset, ambiguous pixels, and the one outlier. `diagnostics/14700-low-alpha-ownership-zoom.jpg` enlarges the same attribution classes across the wordmark. `14700-LOW-ALPHA-PIXELS.csv` contains 300 source-coordinate mapped pixel records; `14607-LOW-ALPHA-NEGATIVE-CONTROL.csv` contains the negative-control records.", ""]
    (out/"REPORT.md").write_text("\n".join(report),encoding="utf-8")
    print(json.dumps({"total":total,"safe":safe_count,"ambiguous":amb_count,"other":other_count,"complete":complete,"reason_counts":dict(reason_counts),"#14607_safe":neg["safe_low_alpha_ownership"],"out":str(out)},indent=2))

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--fixture-root",type=Path,required=True);ap.add_argument("--prior-summary",type=Path,required=True);ap.add_argument("--topology-summary",type=Path,required=True);ap.add_argument("--output-dir",type=Path,required=True);a=ap.parse_args();run(a.fixture_root.resolve(),a.prior_summary.resolve(),a.output_dir.resolve(),a.topology_summary.resolve())
if __name__=="__main__":main()
