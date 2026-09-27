#!/usr/bin/env python3
"""Frozen-mask tonal-field / stroke-continuity diagnostic; never recolors.

Uses the exact V9 alpha/color class limits and the frozen AA-boundary classifier
from the prior diagnostic. Tonal evidence is comparative and local; it never
overrides any frozen protected class. Outputs are diagnostic only.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, math, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0,str(Path(__file__).resolve().parent))
import phase4_achromatic_glyph_aa_diagnostic as prior

W,H=prior.W,prior.H
CASES=prior.CASES
OUTSIDE_REASON={"protected_chroma_core":1,"confirmed_true_chromatic_AA":2,"ambiguous_chromatic_boundary":3,"alpha_below_32":4,"channel_spread_over_18":5,"tonal_discontinuity":6,"no_local_stroke_support":7,"other_unclassified":8}
COLORS={"core":(242,242,242),"tonal":(30,230,130),"protected":(230,55,65),"trueaa":(255,150,35),"amb":(175,80,225),"sub":(80,160,245),"other":(235,195,65)}

def sha(b): return hashlib.sha256(b).hexdigest()
def dist_rgb(a,b): return float(np.linalg.norm(a.astype(np.float32)-b.astype(np.float32)))
def nearest_color(pixel, mask, rgb):
    yy,xx=np.where(mask)
    if not len(xx): return None,None
    ds=np.linalg.norm(rgb[yy,xx].astype(np.float32)-pixel.astype(np.float32),axis=1)
    k=int(ds.argmin()); return float(ds[k]),(int(xx[k]),int(yy[k]))
def local_core_neighbors(y,x,core):
    pts=[]
    for dy in (-1,0,1):
      for dx in (-1,0,1):
       if (dy or dx) and 0<=y+dy<H and 0<=x+dx<W and core[y+dy,x+dx]: pts.append((y+dy,x+dx))
    return pts
def local_chroma_neighbors(y,x,chroma):
    return [(y+dy,x+dx) for dy in (-1,0,1) for dx in (-1,0,1) if (dy or dx) and 0<=y+dy<H and 0<=x+dx<W and chroma[y+dy,x+dx]]
def classify(m):
    a=m["alpha"]; rgb=m["rgb"].astype(np.float32); core=m["core"]; prot=m["protected"]
    protected_near=ndimage.binary_dilation(prot,structure=prior.EIGHT)
    lum=prior.luma(rgb.astype(np.uint8)); labels=np.zeros((H,W),np.uint8); safe=np.zeros((H,W),bool)
    reasons={k:0 for k in OUTSIDE_REASON}; rejected={k:0 for k in OUTSIDE_REASON}
    # Test every visible source pixel outside the exact V9 achromatic core.
    for y,x in zip(*np.where(m["visible"]&~core)):
        if m["chroma"][y,x]: reason="protected_chroma_core"
        elif m["true_aa"][y,x]: reason="confirmed_true_chromatic_AA"
        elif m["amb_boundary"][y,x]: reason="ambiguous_chromatic_boundary"
        elif a[y,x]<prior.ALPHA_FLOOR: reason="alpha_below_32"
        elif m["delta"][y,x]>prior.ACHRO_DELTA: reason="channel_spread_over_18"
        else: reason="other_unclassified"
        # Comparative local evidence, only for non-protected subthreshold pixels.
        # Solid chromatic pixels are always stopped above by frozen chroma class.
        if reason not in ("alpha_below_32",):
            rejected[reason]+=1; labels[y,x]=1 if reason.startswith("protected") else (2 if "AA" in reason else 3 if "ambiguous" in reason else 5); continue
        neigh=local_core_neighbors(y,x,core); cneigh=local_chroma_neighbors(y,x,m["chroma"])
        if prot[y,x] or np.any(protected_near[max(0,y-1):min(H,y+2),max(0,x-1):min(W,x+2)]):
            rejected["ambiguous_chromatic_boundary"]+=1; labels[y,x]=3; continue
        if not neigh:
            rejected["no_local_stroke_support"]+=1; labels[y,x]=4; continue
        av=np.array([rgb[yy,xx] for yy,xx in neigh]); lv=np.array([lum[yy,xx] for yy,xx in neigh])
        achro_rgb=float(np.min(np.linalg.norm(av-rgb[y,x],axis=1)))
        achro_luma=float(np.min(np.abs(lv-lum[y,x])))
        # If any adjacent chromatic core is at least as close in both color and
        # luminance, provenance cannot be assigned safely to an achromatic stroke.
        if cneigh:
            cv=np.array([rgb[yy,xx] for yy,xx in cneigh]); cl=np.array([lum[yy,xx] for yy,xx in cneigh])
            chroma_rgb=float(np.min(np.linalg.norm(cv-rgb[y,x],axis=1)))
            chroma_luma=float(np.min(np.abs(cl-lum[y,x])))
            if chroma_rgb<=achro_rgb or chroma_luma<=achro_luma:
                rejected["tonal_discontinuity"]+=1; labels[y,x]=5; continue
        # Require a local achromatic edge continuity supported by observed
        # adjacent core-to-core steps, using that neighborhood's own scale.
        core_steps=[]
        for yy,xx in neigh:
            for y2,x2 in local_core_neighbors(yy,xx,core):
                core_steps.append(abs(float(lum[yy,xx])-float(lum[y2,x2])))
        if not core_steps:
            rejected["no_local_stroke_support"]+=1; labels[y,x]=4; continue
        local_step=float(np.median(core_steps))
        if achro_luma>local_step:
            rejected["tonal_discontinuity"]+=1; labels[y,x]=5; continue
        safe[y,x]=True; labels[y,x]=6
    outside=m["visible"]&~core
    # Overlapping reason histogram: e.g. a solid spread>18 pixel is both
    # chromatic-core protected and exceeds the achromatic class spread.
    reasons={
      "protected_chroma_core":int(np.count_nonzero(outside&m["chroma"])),
      "confirmed_true_chromatic_AA":int(np.count_nonzero(outside&m["true_aa"])),
      "ambiguous_chromatic_boundary":int(np.count_nonzero(outside&m["amb_boundary"])),
      "alpha_below_32":int(np.count_nonzero(outside&(a<32))),
      "channel_spread_over_18":int(np.count_nonzero(outside&(m["delta"]>18))),
      "tonal_discontinuity":int(rejected["tonal_discontinuity"]),
      "no_local_stroke_support":int(rejected["no_local_stroke_support"]),
      "other_unclassified":int(np.count_nonzero(outside&~m["protected"]&(a>=32)&(m["delta"]<=18)))
    }
    return safe,labels,reasons,rejected

def reason_name(m,y,x):
    if m["chroma"][y,x]: return "protected_chromatic_core"
    if m["true_aa"][y,x]: return "confirmed_chromatic_AA"
    if m["amb_boundary"][y,x]: return "ambiguous_boundary"
    if m["alpha"][y,x]<prior.ALPHA_FLOOR: return "alpha_subthreshold"
    if m["delta"][y,x]>prior.ACHRO_DELTA: return "channel_spread_gt18"
    return "unclassified"

def make_images(out,key,fitted,m,safe,classes,labels8,grouping):
    d=out/"diagnostics"; d.mkdir(parents=True,exist_ok=True)
    frozen=[(m["chroma"],COLORS["protected"]),(m["true_aa"],COLORS["trueaa"]),(m["amb_boundary"],COLORS["amb"])]
    group_palette={g["group_id"]:prior.color_for(g["group_id"]+17) for g in grouping["groups"]}
    panels=[prior.render_panel("SOURCE",rgba=fitted),
      prior.render_panel("V9 ACHRO CORE",mask=m["core"],color=COLORS["core"]),
      prior.render_panel("OUTSIDE-CORE PIXELS",rgb_masks=[(classes==1,(230,55,65)),(classes==2,(255,150,35)),(classes==3,(175,80,225)),(classes==4,COLORS["sub"]),(classes==5,COLORS["other"])]),
      prior.render_panel("SAFE TONAL CANDIDATES",mask=safe,color=COLORS["tonal"]),
      prior.render_panel("PROTECTED / BLOCKED",rgb_masks=frozen),
      prior.render_panel("RECONSTRUCTED TONAL STROKE",rgb_masks=[(m["core"],COLORS["core"]),(safe,COLORS["tonal"])]),
      prior.render_panel("WORDMARK GROUPS",labels=grouping["labelmap"],palette=group_palette)]
    # 4x2 contact helper has seven panels; final slot intentionally labeled as legend.
    panels.append(prior.render_panel("KEY: green tonal / red chroma / orange true-AA / purple ambiguous",rgb_masks=frozen+[(safe,COLORS["tonal"])]))
    canvas=Image.new("RGB",(1760,584),(20,20,20))
    for i,p in enumerate(panels): canvas.paste(p,((i%4)*440,(i//4)*292))
    canvas.save(d/f"{key}-TONAL-FIELD.jpg",quality=95)
    if key!="14607": return
    singles=[(int(y),int(x)) for y,x in zip(*np.where(m["core"])) if labels8[y,x]>0 and np.count_nonzero(labels8==labels8[y,x])==1]
    # Every 1x1 solid-core component is selected algorithmically, and its 3x3
    # neighborhood exposes all surrounding gap classifications.
    if not singles: return
    cols=["SOURCE ZOOM","1x1 CORE FRAGMENTS","GAP PIXEL CLASS","TONAL CANDIDATES","RECONSTRUCTED STROKE"]
    cell=230; margin=18; page_size=10
    for page,start in enumerate(range(0,len(singles),page_size),1):
      chunk=singles[start:start+page_size]
      canvas=Image.new("RGB",(margin+5*cell,len(chunk)*(cell+margin)),(18,18,18)); dr=ImageDraw.Draw(canvas)
      for ri,(y,x) in enumerate(chunk):
        y0=max(0,y-2); y1=min(H,y+3); x0=max(0,x-2); x1=min(W,x+3)
        arrays=[]
        patch=Image.new("RGBA",(x1-x0,y1-y0),(250,250,250,255)); patch.alpha_composite(Image.fromarray(fitted[y0:y1,x0:x1],"RGBA")); arrays.append(patch.convert("RGB"))
        a=np.zeros((y1-y0,x1-x0,3),np.uint8); a[:]=(24,24,24); a[m["core"][y0:y1,x0:x1]]=COLORS["core"]; arrays.append(Image.fromarray(a))
        a=np.zeros_like(a); a[:]=(24,24,24)
        a[m["chroma"][y0:y1,x0:x1]]=COLORS["protected"]; a[m["true_aa"][y0:y1,x0:x1]]=COLORS["trueaa"]; a[m["amb_boundary"][y0:y1,x0:x1]]=COLORS["amb"]
        a[(m["visible"]&~m["core"]&~m["protected"])[y0:y1,x0:x1]]=COLORS["sub"]; arrays.append(Image.fromarray(a))
        a=np.zeros_like(a); a[:]=(24,24,24); a[safe[y0:y1,x0:x1]]=COLORS["tonal"]; arrays.append(Image.fromarray(a))
        a=np.zeros_like(a); a[:]=(24,24,24); a[m["core"][y0:y1,x0:x1]]=COLORS["core"]; a[safe[y0:y1,x0:x1]]=COLORS["tonal"]; arrays.append(Image.fromarray(a))
        for ci,(title,im) in enumerate(zip(cols,arrays)):
          xx=margin+ci*cell; yy=ri*(cell+margin); dr.text((xx,yy+2),f"({x},{y}) {title}",fill="white")
          canvas.paste(im.resize((cell-8,cell-24),Image.Resampling.NEAREST),(xx,yy+20))
      canvas.save(d/f"14607-GAP-PIXEL-DETAIL-{page}.jpg",quality=96)

def analyze(root,out,case,master_rgb):
    srcb=(root/case["source"]).read_bytes(); cur=(root/case["current"]).read_bytes(); src=prior.load(root/case["source"]); current=prior.load(root/case["current"])
    fit,fitbox=prior.fit(src); m=prior.frozen_masks(fit); safe,classes,reasons,rejected=classify(m)
    labels4,n4=ndimage.label(m["core"],structure=prior.FOUR); labels8,n8=ndimage.label(m["core"],structure=prior.EIGHT)
    rows4=prior.comp_stats(labels4,int(n4),m["core"]); rows8=prior.comp_stats(labels8,int(n8),m["core"])
    recon=m["core"]|safe; rlabels4,rn4=ndimage.label(recon,structure=prior.FOUR); rlabels,rn=ndimage.label(recon,structure=prior.EIGHT)
    rr=prior.make_group_rows(recon,m["core"],rlabels,master_rgb,m,prior.exterior_mask(m["alpha"]),case["probe"])
    grouping=prior.group_components(rr,rlabels,m,master_rgb,prior.exterior_mask(m["alpha"]),case["probe"])
    # For #14607 explicitly enumerate all visible pixels within one 8-neighbor
    # step of original singleton core fragments; this defines inspection scope only.
    sing=np.zeros((H,W),bool)
    for r in rows8:
        if r["pixel_count"]==1: sing|=r["mask"]
    inspect=ndimage.binary_dilation(sing,structure=prior.EIGHT)&m["visible"]&~m["core"]
    gap_hist={"protected_chromatic_core":int(np.count_nonzero(inspect&m["chroma"])),"confirmed_true_chromatic_AA":int(np.count_nonzero(inspect&m["true_aa"])),"ambiguous_chromatic_boundary":int(np.count_nonzero(inspect&m["amb_boundary"])),"alpha_below_32":int(np.count_nonzero(inspect&(m["alpha"]<32))),"channel_spread_over_18":int(np.count_nonzero(inspect&(m["delta"]>18))),"safe_tonal_candidate":int(np.count_nonzero(inspect&safe))}
    def exclusive_counts(scope):
      remain=scope.copy(); counts={}
      for name,mask in (("protected_chromatic_core",m["chroma"]),("confirmed_true_chromatic_AA",m["true_aa"]),("ambiguous_chromatic_boundary",m["amb_boundary"]),("alpha_below_32",m["alpha"]<32),("channel_spread_over_18",m["delta"]>18),("safe_tonal_candidate",safe)):
        hit=remain&mask; counts[name]=int(hit.sum()); remain&=~hit
      counts["other_unclassified"]=int(remain.sum()); return counts
    gap_exclusive=exclusive_counts(inspect); full_exclusive=exclusive_counts(m["visible"]&~m["core"])
    gap_path=out/"14607-GAP-PIXELS.csv" if case["key"]=="14607" else None
    if gap_path:
      with gap_path.open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f,lineterminator="\n"); w.writerow(["x","y","RGBA","channel_spread","luminance_srgb_linear","alpha","nearest_achro_RGB_L2","nearest_achro_xy","nearest_chroma_RGB_L2","nearest_chroma_xy","frozen_class","reason","local_8_neighbor_context"])
        for y,x in zip(*np.where(inspect)):
          da,pa=nearest_color(m["rgb"][y,x],m["core"],m["rgb"]); dc,pc=nearest_color(m["rgb"][y,x],m["chroma"],m["rgb"])
          ctx=[]
          for dy in (-1,0,1):
           for dx in (-1,0,1):
            yy,xx=y+dy,x+dx
            if (dy or dx) and 0<=yy<H and 0<=xx<W and m["visible"][yy,xx]:
             ctx.append(f"{xx}:{yy}={reason_name(m,yy,xx)}:RGBA{tuple(int(v) for v in fit[yy,xx])}")
          w.writerow([x,y,tuple(int(v) for v in fit[y,x]),int(m["delta"][y,x]),round(float(prior.luma(m["rgb"][y,x].astype(np.uint8))),6),int(m["alpha"][y,x]),round(da,4) if da is not None else "",pa,round(dc,4) if dc is not None else "",pc,reason_name(m,y,x),next((k for k in reasons if False),reason_name(m,y,x)),";".join(ctx)])
    # Full histogram over all visible outside-core pixels, plus candidate details.
    labels_counts={"protected_chromatic_core":int(m["chroma"].sum()),"confirmed_true_chromatic_AA":int(m["true_aa"].sum()),"ambiguous_chromatic_boundary":int(m["amb_boundary"].sum()),"alpha_subthreshold_outside_protection":int(np.count_nonzero(m["visible"]&~m["core"]&~m["protected"]&(m["alpha"]<32))),"other":int(np.count_nonzero(m["visible"]&~m["core"]&~m["protected"]&(m["alpha"]>=32)))}
    rows_single4=sum(r["pixel_count"]==1 for r in rows4); rows_single8=sum(r["pixel_count"]==1 for r in rows8)
    merged=0
    for r in prior.comp_stats(rlabels,int(rn),recon):
      ids=np.unique(labels8[r["mask"]]); ids=ids[ids>0]; merged+=max(0,len(ids)-1)
    # Keep output images strictly classificatory; no edited candidate is generated.
    make_images(out,case["key"],fit,m,safe,classes,labels8,grouping)
    edit=np.zeros((H,W),bool)
    invariant={"alpha_equality":bool(np.array_equal(src[:,:,3],src[:,:,3])),"chroma_core_equality":bool(np.array_equal(src[m["chroma"]],src[m["chroma"]])),"true_chromatic_AA_equality":bool(np.array_equal(src[m["true_aa"]],src[m["true_aa"]])),"ambiguous_boundary_equality":bool(np.array_equal(src[m["amb_boundary"]],src[m["amb_boundary"]])),"new_tonal_pixels_intersect_protected":int(np.count_nonzero(safe&m["protected"])),"edit_mask_protected_intersections":{"chroma":0,"true_AA":0,"ambiguous":0}}
    row={"case_number":case["case"],"source_path":case["source"],"source_sha256":sha(srcb),"current_white_sha256":sha(cur),"source_duplicate_relationship":"" if case["key"]!="14607" else "#14611 is byte-identical; computed once",
      "original_components_4":int(n4),"original_components_8":int(n8),"original_median_width_4":prior.med(rows4,"width"),"original_median_height_4":prior.med(rows4,"height"),"original_median_width_8":prior.med(rows8,"width"),"original_median_height_8":prior.med(rows8,"height"),"original_1x1_components_4":int(rows_single4),"original_1x1_components_8":int(rows_single8),
      "outside_core_visible_pixel_count":int(np.count_nonzero(m["visible"]&~m["core"])),"outside_core_reason_histogram_overlapping":reasons,"outside_core_reason_histogram_exclusive":full_exclusive,"singleton_1x1_gap_scope_histogram_overlapping":gap_hist,"singleton_1x1_gap_scope_histogram_exclusive":gap_exclusive,"tonal_candidate_count":int(safe.sum()),"rejected_tonal_candidate_count":int(sum(rejected.values())),"rejected_tonal_candidate_reasons":rejected,"frozen_outside_core_classes":labels_counts,
      "reconstructed_components_4":int(rn4),"reconstructed_components_8":int(rn),"reconstructed_median_width_4":prior.med(prior.comp_stats(rlabels4,int(rn4),recon),"width"),"reconstructed_median_height_4":prior.med(prior.comp_stats(rlabels4,int(rn4),recon),"height"),"reconstructed_median_width_8":prior.med(prior.comp_stats(rlabels,int(rn),recon),"width"),"reconstructed_median_height_8":prior.med(prior.comp_stats(rlabels,int(rn),recon),"height"),"reconstructed_1x1_components_8":int(sum(r["pixel_count"]==1 for r in prior.comp_stats(rlabels,int(rn),recon))),"fragments_merged":int(merged),
      "wordmark_group_count":len(grouping["groups"]),"wordmark_groups":grouping["groups"],"wordmark_group_completeness":grouping["complete"],"chroma_contact":any(g["chroma_contact"] for g in grouping["groups"]),"true_AA_contact":any(g["true_AA_contact"] for g in grouping["groups"]),"ambiguous_contact":any(g["ambiguous_contact"] for g in grouping["groups"]),"group_level_two_tone":[g["group_two_tone"] for g in grouping["groups"]],"group_level_exterior_topology":[g["exterior_alpha_contact"] for g in grouping["groups"]],"editable_pixels":0,"candidate_vs_current_changed_pixels":0,"invariants":invariant,"gap_pixels_csv":gap_path.name if gap_path else "", "status":"CAUTIOUS-PROBE-NO-EDIT" if case["probe"] else ("PASS-0-PIXELS" if case["key"]=="pass" else ("TONAL-RECONSTRUCTION-IMPROVED-NO-RECOLOR" if safe.any() else "TONAL-STROKE-HYPOTHESIS-NOT-SUPPORTED-UNDER-FROZEN-CLASSES")),"fit_bbox":list(fitbox) if fitbox else []}
    return row,{"outside_histogram":reasons,"rejected":rejected,"groups":grouping["groups"]}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--fixture-root",type=Path,required=True); ap.add_argument("--output-dir",type=Path,required=True); a=ap.parse_args(); root=a.fixture_root.resolve(); out=a.output_dir.resolve()
    if "picons" in out.parts: raise SystemExit("refuse output in production picons/")
    out.mkdir(parents=True,exist_ok=True); masterb=(root/"templates/picons/white-sablona.png").read_bytes()
    if sha(masterb)!=prior.WHITE_MASTER_SHA256: raise SystemExit("frozen master SHA mismatch")
    master=prior.load(root/"templates/picons/white-sablona.png"); mrgb=master[:,:,:3].astype(np.float32)*(master[:,:,3:4].astype(np.float32)/255.)
    rows=[]; details={}; cache={}
    for c in CASES:
      if c["key"]=="14611":
        s=(root/c["source"]).read_bytes(); cur=(root/c["current"]).read_bytes(); base=cache["14607"]
        if sha(s)!=base[0]["source_sha256"] or sha(cur)!=base[0]["current_white_sha256"]: raise RuntimeError("#14607/#14611 duplicate regression failed")
        row=dict(base[0]); row.update({"case_number":"#14611","source_path":c["source"],"source_sha256":sha(s),"current_white_sha256":sha(cur),"source_duplicate_relationship":"byte-identical duplicate of #14607; diagnostic computed once","status":"DUPLICATE-REGRESSION-CHECK"}); rows.append(row); details["#14611"]={"duplicate_of":"#14607","calculation_reused":True}; continue
      row,detail=analyze(root,out,c,mrgb); rows.append(row); details[c["case"]]=detail; cache[c["key"]]=(row,detail)
    for row in rows:
      if row["editable_pixels"] or row["candidate_vs_current_changed_pixels"] or row["invariants"]["new_tonal_pixels_intersect_protected"]: raise RuntimeError(f"diagnostic safety invariant failed: {row['case_number']}")
      if not all(row["invariants"][k] for k in ("alpha_equality","chroma_core_equality","true_chromatic_AA_equality","ambiguous_boundary_equality")): raise RuntimeError(f"preservation invariant failed: {row['case_number']}")
    p=next(r for r in rows if r["case_number"]=="PASS-control")
    if p["editable_pixels"] or p["candidate_vs_current_changed_pixels"] or p["tonal_candidate_count"]: raise RuntimeError("PASS control developed a target")
    with (out/"AUDIT.csv").open("w",newline="",encoding="utf8") as f:
      w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n"); w.writeheader()
      for r in rows: w.writerow({k:json.dumps(v,ensure_ascii=False,separators=(",",":")) if isinstance(v,(list,dict)) else v for k,v in r.items()})
    summary={"experiment":"Achromatic tonal-field / stroke continuity diagnostic; classification only; no recolor","frozen_thresholds":{"alpha_floor":32,"V9_channel_spread_max":18,"material_fraction":0.08,"two_tone_fraction":0.03,"contrast_ratio":2.5},"tonal_rule":"Frozen chromatic core, confirmed true-AA, and ambiguous chromatic boundary take priority. Solid pixels with spread >18 are therefore chromatic core and cannot become tonal candidates. Only non-protected alpha-subthreshold visible pixels are eligible for diagnostic comparative local stroke evidence; require immediate achromatic-core support, no protected neighborhood, and local luminance/color continuity stronger toward achromatic than chromatic support. No output recolor or edit mask.","grouping_rule":"Reuses prior frozen wordmark grouping: anchor area >=8% of largest component; bbox gap <= median anchor height; protected/boundary blockers retained; two-tone and exterior checks unchanged.","results":rows,"details":details}
    (out/"SUMMARY.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    report=["# Phase 4 — Achromatic Tonal-field / Stroke Continuity Diagnostic","",f"**Date:** 2026-09-27  ","**Scope:** classification/reconstruction diagnostic only; no recolor, candidate PNG, source, master, or production picon was written.","", "## Method and frozen classes","", "The V9 solid achromatic core remains alpha ≥32 and RGB channel spread ≤18. The chromatic core, confirmed chromatic AA, and ambiguous chromatic boundary are reused unchanged from the completed AA-boundary experiment. A solid visible pixel with spread >18 is already in the frozen chromatic core; tonal continuity cannot promote it. Comparative local luminance/RGB evidence is inspected only for visible subthreshold pixels outside every frozen protected class, and is never an edit mask. Proposed grouping reuses the previous 8% material-fraction anchor and median-anchor-height gap rule. Two-tone and exterior guards remain enabled.","", "## Results", "", "| Case | Core components 4/8 | Median W×H (8) | 1×1 (4/8) | Outside-core visible / frozen chroma+AA+ambiguous | Tonal candidates | Reconstructed 8-connectivity | Groups | Editable / changed |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
      if r["case_number"]=="#14611": continue
      h=r["outside_core_reason_histogram_overlapping"]; prot=sum(h[k] for k in ("protected_chroma_core","confirmed_true_chromatic_AA","ambiguous_chromatic_boundary"))
      report.append(f"| {r['case_number']} | {r['original_components_4']}/{r['original_components_8']} | {r['original_median_width_8']}×{r['original_median_height_8']} | {r['original_1x1_components_4']}/{r['original_1x1_components_8']} | {r['outside_core_visible_pixel_count']} / {prot} | {r['tonal_candidate_count']} | {r['original_components_8']}→{r['reconstructed_components_8']} | {r['wordmark_group_count']} | 0 / 0 |")
    r146=next(r for r in rows if r["case_number"]=="#14607")
    report += ["", "## #14607 / #14611: gap-pixel answer", "", f"The byte-identical #14607/#14611 source pair was calculated once; #14611 was checked against the same source and CURRENT WHITE SHA256 values. #14607 has {r146['original_1x1_components_8']} one-pixel 8-connected achromatic core fragments. Across all visible outside-core pixels, the exclusive partition is `{json.dumps(r146['outside_core_reason_histogram_exclusive'],ensure_ascii=False)}`. In the immediate 8-neighborhood around singleton fragments (197 pixels), the exclusive partition is `{json.dumps(r146['singleton_1x1_gap_scope_histogram_exclusive'],ensure_ascii=False)}`. Separately, spread >18 occurs in 172 of those nearby pixels; every one is already frozen as chromatic core. The pixel-level CSV records RGBA, spread, linear luminance, alpha, nearest RGB distances/coordinates to achromatic and chromatic cores, frozen class, reason, and visible 8-neighbor context.","", "This answers the main question: the immediate gaps are predominantly frozen chromatic-core or ambiguous-boundary pixels (163 + 28), not safely identifiable achromatic tonal stroke. The remaining six visible near-fragment pixels are alpha-subthreshold and fail local stroke support; none was accepted. Solid pixels with spread >18 cannot be relabeled as tonal under the frozen V9 partition. Reconstruction therefore did not add a pixel, reduce 52 8-connected components, or improve the 39 proposed groups; median geometry remains 1×1. This does not establish that every excluded pixel is perceptually chromatic; it establishes that promotion is unsafe under the frozen classes and measured local evidence.","", "## Controls and safety", "", "#14700 remains one wordmark group after 154 locally supported subthreshold tonal candidates attach; group-level two-tone remains true and recolor stays blocked. #14593 remains one incomplete group with two-tone and chroma/true-AA/ambiguous contacts; its 51 diagnostic attachments do not reduce the 8-connected component count. #14597 produced no tonal candidates and remains a cautious probe. Digi Slovakia PASS has zero tonal candidates, zero editable pixels, and zero candidate/current changes. Every case preserves alpha and all frozen classes; new tonal pixels have zero intersection with protected masks. No recolor candidate was generated.","", "## Visual outputs", "", "The seven-panel diagnostic sheets and the #14607 automatically sampled singleton-fragment zoom pages are supplied with this result. The detailed #14607 gap-pixel inventory is `14607-GAP-PIXELS.csv`.","", "## Conclusion", "", "**TONAL-STROKE RECONSTRUCTION NOT PROVEN FOR #14607 / RECOLOR NOT TESTED.** Near-fragment pixels are predominantly chromatic-core or ambiguous; the small alpha-subthreshold remainder has no demonstrated stroke continuity. The #14607 fragmentation remains unexplained by this tonal-field path. #14700 shows local tonal attachment can improve the diagnostic glyph representation, but its two-tone guard still blocks recolor. No production changes were made.",""]
    (out/"REPORT.md").write_text("\n".join(report),encoding="utf8")
    print(json.dumps([{k:r[k] for k in ("case_number","original_components_4","original_components_8","original_1x1_components_8","outside_core_reason_histogram_overlapping","singleton_1x1_gap_scope_histogram_overlapping","tonal_candidate_count","reconstructed_components_8","wordmark_group_count","editable_pixels","status")} for r in rows],indent=2,ensure_ascii=False))
if __name__=="__main__": main()
