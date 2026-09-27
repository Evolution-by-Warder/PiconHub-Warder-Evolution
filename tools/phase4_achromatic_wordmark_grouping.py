#!/usr/bin/env python3
"""Isolated, grouping-only experiment for frozen V9/AA-boundary fixtures.

The experiment forms geometric proposals from contrast-relevant achromatic
4-connected components. It never adds chroma, true-AA, or ambiguous pixels to a
group. Frozen AA classification is copied from the prior committed experiment;
it is not tuned here. Candidate output is written only when every group-level
and case-level guard passes, and always outside the production picons tree.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

SIZE=(220,132)
OPAQUE_ALPHA=32; ACHROMATIC_DELTA=18; ACHROMATIC_REQUIRED=.985
CONTRAST_RATIO=2.50; MATERIAL_FRACTION=.08; TWO_TONE_FRACTION=.03
DARK=np.array((16,16,16),dtype=np.uint8)
WHITE_MASTER_SHA256="c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589"
FOUR=np.array([[0,1,0],[1,1,1],[0,1,0]],dtype=np.uint8); EIGHT=np.ones((3,3),dtype=np.uint8)
CASES=[
 {"case":"#14607","key":"14607","source":"picons/80.0e/orion-express/transparent/1_0_1_2C8_CD_1_3200000_0_0_0.png","current":"picons/80.0e/orion-express/white/1_0_1_2C8_CD_1_3200000_0_0_0.png","duplicate":"","probe":False},
 {"case":"#14611","key":"14611","source":"picons/80.0e/orion-express/transparent/1_0_1_2CA_CD_1_3200000_0_0_0.png","current":"picons/80.0e/orion-express/white/1_0_1_2CA_CD_1_3200000_0_0_0.png","duplicate":"#14607; byte-identical source/current; primary grouping reused","probe":False},
 {"case":"#14700","key":"14700","source":"picons/80.0e/orion-express/transparent/1_0_1_32D_CE_1_3200000_0_0_0.png","current":"picons/80.0e/orion-express/white/1_0_1_32D_CE_1_3200000_0_0_0.png","duplicate":"","probe":False},
 {"case":"#14593","key":"14593","source":"picons/80.0e/orion-express/transparent/1_0_1_2C1_CD_1_3200000_0_0_0.png","current":"picons/80.0e/orion-express/white/1_0_1_2C1_CD_1_3200000_0_0_0.png","duplicate":"","probe":False},
 {"case":"#14597","key":"14597","source":"picons/80.0e/orion-express/transparent/1_0_1_2C3_CD_1_3200000_0_0_0.png","current":"picons/80.0e/orion-express/white/1_0_1_2C3_CD_1_3200000_0_0_0.png","duplicate":"","probe":True},
 {"case":"PASS-control","key":"pass","source":"picons/0.8w/digislovakia/transparent/1_0_16_3F6_AF1_BB_E080000_0_0_0.png","current":"picons/0.8w/digislovakia/white/1_0_16_3F6_AF1_BB_E080000_0_0_0.png","duplicate":"","probe":False},
]

def sha(data): return hashlib.sha256(data).hexdigest()
def load(path):
    with Image.open(path) as im:
        im.load()
        if im.format!="PNG" or im.size!=SIZE: raise ValueError(f"bad fixture: {path} {im.format}/{im.size}")
        return np.array(im.convert("RGBA"),dtype=np.uint8)
def fit(src):
    im=Image.fromarray(src,"RGBA"); box=im.getchannel("A").getbbox()
    if box is None: return src.copy(),box
    crop=im.crop(box); scale=min(1.,(220-16)/crop.width,(132-16)/crop.height)
    dims=(max(1,round(crop.width*scale)),max(1,round(crop.height*scale)))
    if dims!=crop.size: crop=crop.resize(dims,Image.Resampling.LANCZOS)
    out=Image.new("RGBA",SIZE,(0,0,0,0)); out.alpha_composite(crop,((220-crop.width)//2,(132-crop.height)//2))
    return np.array(out,dtype=np.uint8),box
def luma(rgb):
    x=rgb.astype(np.float32)/255.; x=np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)
    return x[...,0]*.2126+x[...,1]*.7152+x[...,2]*.0722

def frozen_masks(fitted):
    """Exact AA-boundary classification used in phase4_aa_boundary_classification.py."""
    alpha=fitted[:,:,3]; visible=alpha>0; solid=alpha>=OPAQUE_ALPHA
    rgb=fitted[:,:,:3].astype(np.int16); delta=rgb.max(2)-rgb.min(2)
    chroma=solid&(delta>ACHROMATIC_DELTA); achro=solid&(delta<=ACHROMATIC_DELTA)
    old_ring=(ndimage.binary_dilation(chroma,structure=EIGHT)&visible)&~chroma
    true_aa=np.zeros_like(chroma); aa_amb=np.zeros_like(chroma); geometric=np.zeros_like(chroma)
    for y,x in zip(*np.where(old_ring)):
        rel=[]
        for dy in (-1,0,1):
            for dx in (-1,0,1):
                yy,xx=y+dy,x+dx
                if (dy or dx) and 0<=yy<132 and 0<=xx<220 and chroma[yy,xx]:
                    close=int(np.max(np.abs(rgb[y,x]-rgb[yy,xx])))<=ACHROMATIC_DELTA
                    atten=alpha[y,x]<alpha[yy,xx]
                    rel.append((close,atten))
        proof=[c and a for c,a in rel]; conflict=[c!=a for c,a in rel]
        if rel and all(proof): true_aa[y,x]=True
        elif rel and (any(proof) or any(conflict) or alpha[y,x]<255): aa_amb[y,x]=True
        elif rel and alpha[y,x]==255 and all((not c and not a) for c,a in rel): geometric[y,x]=True
        else: aa_amb[y,x]=True
    lowalpha=visible&(alpha<OPAQUE_ALPHA)
    ambiguous=lowalpha|aa_amb
    return {"alpha":alpha,"visible":visible,"rgb":rgb,"achro":achro,"chroma":chroma,
            "old_ring":old_ring,"true_aa":true_aa,"aa_amb":aa_amb,
            "lowalpha":lowalpha,"ambiguous":ambiguous,"geometric":geometric}

def exterior_mask(alpha):
    # This is topology evidence, not a protected/editable class. Include
    # transparent alpha=0 as well as low-alpha pixels so the group can be
    # tested against the true exterior. The edit blocker mask remains frozen.
    topology=alpha<OPAQUE_ALPHA
    lab,n=ndimage.label(topology,structure=EIGHT)
    border=np.unique(np.r_[lab[0,:],lab[-1,:],lab[:,0],lab[:,-1]])
    return np.isin(lab,border)&topology

def comp_stats(k,mask,labels,rgb,bg,exterior,blocks):
    yy,xx=np.where(mask); vals=rgb[mask].astype(np.uint8)
    lf=luma(vals.reshape(-1,1,3)).reshape(-1); bf=luma(bg[mask].reshape(-1,1,3)).reshape(-1)
    ratios=(np.maximum(lf,bf)+.05)/(np.minimum(lf,bf)+.05)
    lowfrac=float(np.mean(ratios<CONTRAST_RATIO)); needs=lowfrac>=MATERIAL_FRACTION
    lum8=lf*255.
    two=bool(np.mean(lum8<=64.)>=TWO_TONE_FRACTION and np.mean(lum8>=192.)>=TWO_TONE_FRACTION)
    ring=ndimage.binary_dilation(mask,structure=EIGHT)&~mask
    return {"id":int(k),"pixel_count":int(mask.sum()),"bbox":[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)],
      "bbox_width":int(xx.max()-xx.min()+1),"bbox_height":int(yy.max()-yy.min()+1),
      "contrast_class":"FIX-NEEDED" if needs else "READABLE",
      "low_contrast_fraction":round(lowfrac,6),"median_luminance":round(float(np.median(lf)),6),
      "two_tone":two,"exterior_alpha_contact":bool(np.any(ring&exterior)),
      "chroma_contact":bool(np.any(ring&blocks["chroma"])),
      "true_AA_contact":bool(np.any(ring&blocks["true_aa"])),
      "ambiguous_boundary_contact":bool(np.any(ring&blocks["aa_amb"])),
      "low_alpha_contact":bool(np.any(ring&blocks["lowalpha"])),
      "mask":mask}

def bbox_gap(a,b):
    ax0,ay0,ax1,ay1=a; bx0,by0,bx1,by1=b
    gx=max(0,bx0-ax1,ax0-bx1); gy=max(0,by0-ay1,ay0-by1)
    return math.hypot(gx,gy),gx,gy

def line_points(p0,p1):
    x0,y0=p0; x1,y1=p1; dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        yield y0,x0
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

def closest_points(ma,mb):
    ya,xa=np.where(ma); yb,xb=np.where(mb)
    # Small masks (220x132). Integer squared distance avoids any new distance cutoff.
    best=None
    for start in range(0,len(xa),512):
        dx=xa[start:start+512,None]-xb[None,:]; dy=ya[start:start+512,None]-yb[None,:]
        d=dx*dx+dy*dy; flat=int(d.argmin()); i,j=np.unravel_index(flat,d.shape)
        val=int(d[i,j])
        if best is None or val<best[0]: best=(val,(int(xa[start+i]),int(ya[start+i])),(int(xb[j]),int(yb[j])))
    return best

def edge_blocker(a,b,blocked):
    _,p,q=closest_points(a,b)
    pts=list(line_points(p,q))
    # Endpoints are achromatic component pixels. Every intervening frozen
    # chroma/AA/ambiguous pixel blocks the geometric grouping edge.
    interior=pts[1:-1]
    return any(bool(blocked[y,x]) for y,x in interior),[(x,y) for y,x in interior]

def color_for(i):
    # Deterministic perceptually separated palette for diagnostic-only views.
    return ((37*i+83)%190+55,(97*i+61)%190+55,(151*i+29)%190+55)

def panel(title,rgba=None,mask=None,color=(255,255,255),labels=None,palette=None,base=(28,28,28),overlays=None):
    if rgba is not None:
        src=Image.fromarray(rgba,"RGBA"); bg=Image.new("RGBA",SIZE,(245,245,245,255)); bg.alpha_composite(src); arr=np.array(bg.convert("RGB"))
    elif labels is not None:
        arr=np.zeros((132,220,3),dtype=np.uint8); arr[:]=base
        for i,c in (palette or {}).items(): arr[labels==i]=c
    else:
        arr=np.zeros((132,220,3),dtype=np.uint8); arr[:]=base
        if mask is not None: arr[mask]=color
    if overlays:
        for m,c in overlays: arr[m]=c
    im=Image.fromarray(arr,"RGB").resize((440,264),Image.Resampling.NEAREST)
    out=Image.new("RGB",(440,292),(30,30,30)); out.paste(im,(0,28)); ImageDraw.Draw(out).text((8,7),title,fill=(255,255,255))
    return out

def contact(panels,path):
    out=Image.new("RGB",(1320,584),(20,20,20))
    for i,p in enumerate(panels): out.paste(p,((i%3)*440,(i//3)*292))
    out.save(path,quality=94)

def process_case(root,out,case,master):
    srcbytes=(root/case["source"]).read_bytes(); curbytes=(root/case["current"]).read_bytes()
    original=load(root/case["source"]); fitted,fitbox=fit(original); current=load(root/case["current"])
    masks=frozen_masks(fitted); alpha=masks["alpha"]; rgb=masks["rgb"]
    ach_labels,ach_n=ndimage.label(masks["achro"],structure=FOUR)
    masterrgb=master[:,:,:3].astype(np.float32)*(master[:,:,3:4].astype(np.float32)/255.)
    exterior=exterior_mask(alpha)
    blocked=masks["chroma"]|masks["true_aa"]|masks["ambiguous"]
    blockparts={"chroma":masks["chroma"],"true_aa":masks["true_aa"],"aa_amb":masks["aa_amb"],"lowalpha":masks["lowalpha"]}
    comps=[]
    for idx in range(1,ach_n+1):
        mask=ach_labels==idx
        s=comp_stats(idx,mask,ach_labels,rgb,masterrgb,exterior,blockparts)
        s["contrast_relevant"]=s["contrast_class"]=="FIX-NEEDED"
        comps.append(s)
    target=[c for c in comps if c["contrast_relevant"]]
    # Select geometry anchors with the frozen V9 material fraction, relative to
    # the largest achromatic component in this fixture. Every case uses the same
    # formula; sub-threshold components remain audited and block completeness.
    max_area=max((c["pixel_count"] for c in comps),default=0)
    anchor_floor=MATERIAL_FRACTION*max_area
    anchors=[c for c in comps if c["pixel_count"]>=anchor_floor] if max_area else []
    # One uniform geometry scale: median bbox height of these data-derived anchors.
    scale=float(np.median([c["bbox_height"] for c in anchors])) if anchors else 0.
    cand_edges=[]; adjacency={c["id"]:set() for c in anchors}; edge_rows=[]
    for i,a in enumerate(anchors):
        for b in anchors[i+1:]:
            gap,gx,gy=bbox_gap(a["bbox"],b["bbox"])
            if scale>0 and gap<=scale:
                barrier,points=edge_blocker(a["mask"],b["mask"],blocked)
                item={"a":a["id"],"b":b["id"],"bbox_gap":round(gap,4),"scale":round(scale,4),"blocker_on_shortest_path":bool(barrier),"blocker_path_pixels":points}
                edge_rows.append(item); cand_edges.append((a["id"],b["id"],barrier))
                adjacency[a["id"]].add(b["id"]); adjacency[b["id"]].add(a["id"])
    # Geometric connected sets are proposals; blockers are not group members.
    group_ids={}; groups=[]
    for c in anchors:
        if c["id"] in group_ids: continue
        stack=[c["id"]]; members=[]
        while stack:
            k=stack.pop()
            if k in group_ids: continue
            group_ids[k]=-1; members.append(k); stack.extend(adjacency[k]-set(group_ids))
        gid=len(groups)+1
        for k in members: group_ids[k]=gid
        groups.append(sorted(members))
    byid={c["id"]:c for c in comps}; group_details=[]; proposed_all=np.zeros((132,220),bool)
    accepted_union=np.zeros_like(proposed_all); component_labelmap=np.zeros((132,220),np.int32); group_labelmap=np.zeros_like(component_labelmap)
    for c in comps: component_labelmap[c["mask"]]=c["id"]
    for gid,member_ids in enumerate(groups,1):
        gm=np.zeros_like(proposed_all)
        for k in member_ids: gm|=byid[k]["mask"]
        proposed_all|=gm; group_labelmap[gm]=gid
        vals=rgb[gm].astype(np.uint8); fl=luma(vals.reshape(-1,1,3)).reshape(-1); bl=luma(masterrgb[gm].reshape(-1,1,3)).reshape(-1)
        ratio=(np.maximum(fl,bl)+.05)/(np.minimum(fl,bl)+.05); lowfrac=float(np.mean(ratio<CONTRAST_RATIO)); needs=lowfrac>=MATERIAL_FRACTION
        lum8=fl*255.; two=bool(np.mean(lum8<=64.)>=TWO_TONE_FRACTION and np.mean(lum8>=192.)>=TWO_TONE_FRACTION)
        ring=ndimage.binary_dilation(gm,structure=EIGHT)&~gm
        ext=bool(np.any(ring&exterior)); contacts={name:bool(np.any(ring&mask)) for name,mask in blockparts.items()}
        internal_block_edges=[e for e in edge_rows if e["blocker_on_shortest_path"] and e["a"] in member_ids and e["b"] in member_ids]
        reasons=[]
        if not needs: reasons.append("group-readable-under-frozen-V9-contrast")
        if two: reasons.append("group-two-tone-frozen-guard")
        if internal_block_edges: reasons.append("ambiguous/chroma blocker on grouping path")
        if contacts["chroma"]: reasons.append("group contacts chromatic core")
        if contacts["true_aa"]: reasons.append("group contacts true chromatic AA")
        if contacts["aa_amb"]: reasons.append("group contacts ambiguous chromatic boundary")
        if not ext: reasons.append("group exterior-alpha context not proven")
        if contacts["lowalpha"]: reasons.append("group perimeter touches low-alpha pixels; they remain excluded")
        if case["probe"]: reasons.append("cautious probe only; gold/brand not promoted")
        group_safe=(not internal_block_edges and not contacts["chroma"] and not contacts["true_aa"] and not contacts["aa_amb"] and ext and not case["probe"] and not (needs and two))
        edit_eligible=group_safe and needs and not two
        if edit_eligible: accepted_union|=gm
        ys,xs=np.where(gm); bbox=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
        group_details.append({"group_id":gid,"component_ids":member_ids,"component_count":len(member_ids),"pixel_count":int(gm.sum()),"bbox":bbox,
           "group_contrast_class":"FIX-NEEDED" if needs else "READABLE","group_low_contrast_fraction":round(lowfrac,6),"group_two_tone":two,
           "group_exterior_alpha_contact":ext,"chroma_core_contact":contacts["chroma"],"true_AA_contact":contacts["true_aa"],
           "ambiguous_boundary_contact":contacts["aa_amb"],"low_alpha_contact":contacts["lowalpha"],
           "blocking_geometry_edges":len(internal_block_edges),"status":"ACCEPTED-GROUP-EDIT-ELIGIBLE" if edit_eligible else ("ACCEPTED-READABLE-GROUP" if group_safe and not needs else "REVIEW"),
           "reason":"; ".join(reasons) if reasons else ("grouping accepted; readable under frozen contrast rule" if group_safe and not needs else ("all grouping and edit guards passed" if edit_eligible else "; ".join(reasons))),"mask":gm})
    # A wordmark-level edit would require every relevant component in one
    # unambiguously safe group. Grouping/classification alone never bypasses
    # any V9 contrast, two-tone, exterior, or boundary guard.
    all_component_ids={c["id"] for c in target}
    assigned={k for g in groups for k in g}
    case_complete=bool(target) and all_component_ids.issubset(assigned) and len(groups)==1 and len(group_details)==1 and group_details[0]["status"]=="ACCEPTED-GROUP-EDIT-ELIGIBLE" and not case["probe"]
    editmask=accepted_union if case_complete else np.zeros_like(proposed_all)
    intersect_chroma=int(np.count_nonzero(editmask&masks["chroma"]))
    intersect_aa=int(np.count_nonzero(editmask&masks["true_aa"]))
    intersect_amb=int(np.count_nonzero(editmask&masks["ambiguous"]))
    if intersect_chroma or intersect_aa or intersect_amb: raise RuntimeError(f"HARD FAIL edit/protected intersection in {case['case']}")
    outlayer=fitted.copy(); changes=editmask&np.any(outlayer[:,:,:3]!=DARK,axis=2); outlayer[:,:,:3][editmask]=DARK
    alphaeq=bool(np.array_equal(outlayer[:,:,3],fitted[:,:,3])); chromaeq=bool(np.array_equal(outlayer[masks["chroma"]],fitted[masks["chroma"]]))
    aaeq=bool(np.array_equal(outlayer[masks["true_aa"]],fitted[masks["true_aa"]]))
    if not(alphaeq and chromaeq and aaeq): raise RuntimeError(f"preservation invariant failed {case['case']}")
    candidate=None; candidate_diff=0; candidate_sha=""
    if int(changes.sum()):
        candidate=Image.alpha_composite(Image.fromarray(master,"RGBA"),Image.fromarray(outlayer,"RGBA"))
        p=out/"candidates"/(case["key"]+"-white.png"); p.parent.mkdir(parents=True,exist_ok=True); candidate.save(p)
        candidate_sha=sha(p.read_bytes()); currentpx=current
        candidate_diff=int(np.any(np.array(candidate.convert("RGBA"))!=currentpx,axis=2).sum())
        # Also emit only a comparison preview if a guard-safe candidate exists.
        comparison(out,fitted,current,np.array(candidate.convert("RGBA")),case["key"])
    if case["case"]=="PASS-control" and (int(changes.sum()) or candidate_diff): raise RuntimeError("PASS control changed")
    # If no accepted mask exists, mask diagnostic still shows candidate group
    # outlines/classification; no fake candidate PNG is generated.
    diag(out,case,fitted,component_labelmap,group_labelmap,group_details,masks,editmask)
    # Detailed per-component data preserves the original decisions for comparison.
    comp_rows=[]
    for c in comps:
        comp_rows.append({k:v for k,v in c.items() if k!="mask"})
    all_target_together=bool(target) and len(groups)==1 and all_component_ids.issubset(assigned)
    multi_target_groups=sum(g["component_count"]>1 and any(cid in all_component_ids for cid in g["component_ids"]) for g in group_details)
    row={"case_number":case["case"],"source_path":case["source"],"source_sha256":sha(srcbytes),"current_white_path":case["current"],
      "current_white_sha256":sha(curbytes),"candidate_sha256":candidate_sha or sha(curbytes),"duplicate_relationship":case["duplicate"],
      "achromatic_component_count":ach_n,"contrast_relevant_component_count":len(target),"geometry_anchor_component_count":len(anchors),
      "geometry_anchor_area_floor_pixels":anchor_floor,"unassigned_contrast_relevant_components":sorted(all_component_ids-assigned),"component_scale_median_bbox_height":scale,
      "proposed_wordmark_group_count":len(groups),"groups_containing_multiple_components_and_target_pixels":multi_target_groups,"all_target_components_in_one_group":all_target_together,
      "proposed_groups":[{k:v for k,v in g.items() if k!="mask"} for g in group_details],"component_decisions":comp_rows,
      "candidate_geometry_edge_count":len(edge_rows),"geometry_edges":edge_rows,"accepted_group_count":sum(g["status"].startswith("ACCEPTED") for g in group_details),
      "rejected_group_count":sum(g["status"]=="REVIEW" for g in group_details),"complete_wordmark_guard":case_complete,
      "proposed_editable_pixels":int(editmask.sum()),"changed_achromatic_pixels":int(changes.sum()),"candidate_vs_current_changed_pixels":candidate_diff,
      "alpha_equality":alphaeq,"chroma_core_equality":chromaeq,"true_AA_equality":aaeq,
      "edit_mask_chroma_intersection":intersect_chroma,"edit_mask_true_AA_intersection":intersect_aa,"edit_mask_ambiguous_intersection":intersect_amb,
      "status":("PASS" if case["case"]=="PASS-control" else ("CAUTIOUS-PROBE-NO-EDIT" if case["probe"] else ("AUTO-FIX-CANDIDATE" if case_complete else ("GROUPING-SUCCESS-EDIT-NOT-PROVEN-SAFE" if all_target_together and target else ("GROUPING-PARTIAL-REVIEW" if multi_target_groups else "REVIEW-GROUPING-NOT-PROVEN"))))),
      "reason":"; ".join(sorted({g["reason"] for g in group_details if g["status"]=="REVIEW"})) if group_details else ("no contrast-relevant achromatic components" if not case["probe"] else "cautious probe: no contrast-relevant components; no edits"),
      "fit_bbox":list(fitbox) if fitbox else []}
    return row

def diag(out,case,source,component_labels,group_labels,groups,m,m_edit):
    colors={i:color_for(i) for i in range(1,int(component_labels.max())+1)}
    gcolors={g["group_id"]:color_for(g["group_id"]+29) for g in groups}
    def labelnames(im,items,key):
        d=ImageDraw.Draw(im)
        for it in items:
            x0,y0,x1,y1=it[key]; d.text(((x0+x1)//2*2,(y0+y1)//2*2),str(it.get("group_id",it.get("id",""))),fill=(255,255,255),stroke_width=1,stroke_fill=(0,0,0))
    blockers=[(m["chroma"],(235,55,65)),(m["true_aa"],(255,151,38)),(m["ambiguous"],(166,80,220))]
    compimg=panel("ACHROMATIC COMPONENTS (label = component ID)",labels=component_labels,palette=colors)
    groupimg=panel("PROPOSED WORDMARK GROUPS (IDs in audit)",labels=group_labels,palette=gcolors)
    labelnames(groupimg,groups,"bbox")
    resultarr=np.zeros((132,220,3),dtype=np.uint8); resultarr[:]=(25,25,25)
    for g in groups:
        col=(64,210,105) if g["status"]=="ACCEPTED-GROUP" else (235,180,35)
        for cid in g["component_ids"]: resultarr[component_labels==cid]=col
    result=Image.fromarray(resultarr,"RGB").resize((440,264),Image.Resampling.NEAREST); resultpane=Image.new("RGB",(440,292),(30,30,30));resultpane.paste(result,(0,28));ImageDraw.Draw(resultpane).text((8,7),"GROUP CONTRAST / GUARD RESULT",fill="white")
    panes=[panel("SOURCE (fitted over white)",rgba=source),compimg,groupimg,
      panel("FROZEN CHROMA / TRUE-AA / AMBIGUOUS BLOCKERS",mask=None,overlays=blockers),resultpane,
      panel("PROPOSED EDITABLE GROUP (empty unless all guards pass)",mask=m_edit,color=(65,210,105))]
    dest=out/"grouping-masks"; dest.mkdir(parents=True,exist_ok=True); contact(panes,dest/(case["key"]+"-GROUPING.jpg"))

def comparison(out,source,current,candidate,key):
    panels=[]
    for name,data in (("SOURCE",source),("CURRENT WHITE",current),("GROUPED-TOPOLOGY CANDIDATE",candidate)):
        base=Image.new("RGB",(440,292),(255,255,255)); ImageDraw.Draw(base).text((8,7),f"{key} — {name}",fill=(0,0,0))
        im=Image.fromarray(data,"RGBA").resize((440,264),Image.Resampling.NEAREST);base.paste(im,(0,28),im);panels.append(base)
    outp=Image.new("RGB",(1320,292),(255,255,255))
    for i,p in enumerate(panels):outp.paste(p,(440*i,0))
    folder=out/"comparisons";folder.mkdir(parents=True,exist_ok=True);outp.save(folder/(key+"-GROUPED-CANDIDATE.jpg"),quality=95)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--fixture-root",type=Path,required=True);ap.add_argument("--output-dir",type=Path,required=True);a=ap.parse_args()
    root=a.fixture_root.resolve();out=a.output_dir.resolve()
    if "picons" in out.parts: raise SystemExit("refusing output under production picons/")
    mpath=root/"templates/picons/white-sablona.png"
    if sha(mpath.read_bytes())!=WHITE_MASTER_SHA256: raise SystemExit("WHITE MASTER hash mismatch")
    master=load(mpath)
    rows=[];cache={}
    for case in CASES:
        if case["key"]=="14611":
            src=(root/case["source"]).read_bytes();cur=(root/case["current"]).read_bytes();primary=cache["14607"]
            if sha(src)!=primary["source_sha256"] or sha(cur)!=primary["current_white_sha256"]: raise RuntimeError("duplicate mismatch #14607/#14611")
            row=dict(primary);row.update({"case_number":"#14611","source_path":case["source"],"source_sha256":sha(src),"current_white_path":case["current"],"current_white_sha256":sha(cur),"candidate_sha256":primary["candidate_sha256"],"duplicate_relationship":case["duplicate"],"status":"DUPLICATE-REGRESSION-CHECK","reason":"byte-identical #14607 fixture; grouping not recomputed"})
        else: row=process_case(root,out,case,master)
        cache[case["key"]]=row;rows.append(row)
    # PASS is an invariant and candidate output may not be generated from it.
    passrow=next(r for r in rows if r["case_number"]=="PASS-control")
    if passrow["proposed_editable_pixels"] or passrow["candidate_vs_current_changed_pixels"]: raise RuntimeError("PASS control changed")
    out.mkdir(parents=True,exist_ok=True)
    with (out/"AUDIT.csv").open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");writer.writeheader()
        for r in rows: writer.writerow({k:(json.dumps(v,ensure_ascii=False,separators=(",",":")) if isinstance(v,(list,dict)) else v) for k,v in r.items()})
    summary={"experiment":"achromatic wordmark grouping only; frozen AA/chroma/ambiguous masks","grouping_rule":"geometry anchors are components at least frozen V9 material fraction (8%) of largest achromatic component; candidate links when bbox gap <= median anchor bbox height in that fixture; same formula for every case, no logo-specific parameters","frozen_v9":{"alpha_floor":OPAQUE_ALPHA,"achromatic_delta":ACHROMATIC_DELTA,"achromatic_required":ACHROMATIC_REQUIRED,"contrast_ratio":CONTRAST_RATIO,"material_fraction":MATERIAL_FRACTION,"two_tone_fraction":TWO_TONE_FRACTION,"target_rgb":DARK.tolist()},"white_master_sha256":WHITE_MASTER_SHA256,"results":rows}
    (out/"SUMMARY.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps([{k:r[k] for k in ("case_number","achromatic_component_count","proposed_wordmark_group_count","accepted_group_count","rejected_group_count","proposed_editable_pixels","candidate_vs_current_changed_pixels","status","reason")} for r in rows],indent=2,ensure_ascii=False))
if __name__=="__main__":main()
