#!/usr/bin/env python3
"""Diagnostic-only exact mask geometry and shape experiment for saved auxiliary review scope.

Does not edit the production renderer or any candidate asset. It calls the existing
renderer in memory only to verify saved candidate SHA values, then derives geometry
from the exact transparent source alpha masks.
"""
from __future__ import annotations
import base64, gzip, hashlib, importlib.util, io, json, math, sys, zipfile, zlib
from collections import defaultdict
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
DIAG = ROOT / "reports/warder-master-production/auxiliary-component-diagnostics-2026-10-06"
OUT = ROOT / "reports/warder-master-production/auxiliary-mask-geometry-2026-10-07"
SAT_ZIP = Path("/tmp/aux-exp/satellite-transparent.zip")
HARMONIC_LOCAL = ROOT / "reports/warder-master-production/auxiliary-mask-geometry-2026-10-07/harmonic-source.png"
ENGINE_PATH = ROOT / "tools/rebuild_master_catalog.py"
MASTER_ROOT = ROOT.parent


def sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()
def load_engine():
    spec=importlib.util.spec_from_file_location("warder_mask_geometry_engine",ENGINE_PATH)
    mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod);return mod

def source_records():
    rows=[]
    for i in range(1,12):
        with gzip.open(DIAG/f"component-diagnostics-{i:02d}.jsonl.gz","rt",encoding="utf-8") as f:
            rows.extend(json.loads(x) for x in f if x.strip())
    return rows

def contour_chains(mask: np.ndarray):
    h,w=mask.shape; edges=[]
    for y,x in zip(*np.nonzero(mask)):
        if y==0 or not mask[y-1,x]: edges.append((int(x),int(y),0))
        if x==w-1 or not mask[y,x+1]: edges.append((int(x+1),int(y),1))
        if y==h-1 or not mask[y+1,x]: edges.append((int(x+1),int(y+1),2))
        if x==0 or not mask[y,x-1]: edges.append((int(x),int(y+1),3))
    remaining=set(edges); out=defaultdict(list)
    for x,y,d in edges: out[(x,y)].append(d)
    contours=[]
    while remaining:
        x0,y0,d0=min(remaining,key=lambda e:(e[1],e[0],e[2]))
        x,y,d=x0,y0,d0; chain=[]; safety=0
        while True:
            edge=(x,y,d)
            if edge not in remaining: break
            remaining.remove(edge);chain.append(str(d))
            if d==0: x,y=x+1,y
            elif d==1: x,y=x,y+1
            elif d==2: x,y=x-1,y
            else: x,y=x,y-1
            if (x,y)==(x0,y0): break
            avail=[nd for nd in out.get((x,y),[]) if (x,y,nd) in remaining]
            if not avail: break
            # Preserve foreground on the right; at diagonal vertices choose the tight turn.
            turn_priority={((d+1)%4):0,d:1,((d-1)%4):2,((d+2)%4):3}
            d=min(avail,key=lambda q:turn_priority[q]);safety+=1
            if safety>len(edges)+1: raise RuntimeError("contour tracing exceeded boundary edge count")
        contours.append({"start_xy": [x0,y0],"chain_4dir": "".join(chain),"closed": (x,y)==(x0,y0)})
    if any(not c["closed"] for c in contours): raise RuntimeError("open contour encountered")
    return contours,len(edges)

def geometry(mask: np.ndarray, expected_mask_sha: str):
    packed=np.packbits(mask.reshape(-1),bitorder="big").tobytes();msha=sha(packed)
    if msha!=expected_mask_sha: raise RuntimeError(f"mask SHA mismatch {msha} != {expected_mask_sha}")
    ys,xs=np.nonzero(mask);x0,x1=int(xs.min()),int(xs.max())+1;y0,y1=int(ys.min()),int(ys.max())+1
    crop=mask[y0:y1,x0:x1];area=int(mask.sum());height,width=crop.shape
    holes=ndimage.binary_fill_holes(crop,structure=np.array([[0,1,0],[1,1,1],[0,1,0]],dtype=bool)) & ~crop
    hole_count=int(ndimage.label(holes,structure=np.ones((3,3),dtype=np.uint8))[1])
    cross=np.array([[0,1,0],[1,1,1],[0,1,0]],dtype=np.uint8)
    four_subparts=int(ndimage.label(mask,structure=cross)[1])
    contours,perimeter=contour_chains(mask)
    return {
      "mask_dimensions_wh":[int(mask.shape[1]),int(mask.shape[0])],
      "mask_codec":"zlib+base64(packbits-C-order, bitorder=big)",
      "mask_packed_zlib_base64":base64.b64encode(zlib.compress(packed,9)).decode("ascii"),
      "mask_sha256":msha,"bbox_xyxy_exclusive":[x0,y0,x1,y1],"area_pixel_count":area,
      "perimeter_4edge":perimeter,"aspect_ratio_w_over_h":width/height,
      "fill_ratio_bbox":area/(width*height),
      "hole_count_4connected_background":hole_count,
      "centroid_xy_pixel_centres":[float(xs.mean()+0.5),float(ys.mean()+0.5)],
      "compactness_4piA_over_P2":(4*math.pi*area/(perimeter*perimeter)) if perimeter else 0,
      "horizontal_projection_per_x":[int(x) for x in mask.sum(axis=0)],
      "vertical_projection_per_y":[int(y) for y in mask.sum(axis=1)],
      "four_connected_subpart_count":four_subparts,"contours_pixel_edge_chaincodes":contours,
    }

def row_image_bytes(row, archive):
    if row["domain"]=="satellite-logo":
        _,member=row["source_path"].split(":",1)
        return archive.read(member)
    if row["auxiliary_identity"] in ("provider-logo::HARMONIC.png","provider-logo::HARMONIC - NT.png"):
        return HARMONIC_LOCAL.read_bytes()
    raise KeyError(row["auxiliary_identity"])

def shape_runs(components):
    # Name-free deterministic structural rule: 4+ isolated chromatic low-contrast
    # components with same representative RGB, common top/baseline and height, tight
    # horizontal gaps, wide combined run, and at least three distinct bbox aspect bins.
    by_domain_identity_variant=defaultdict(list)
    for c in components:
        if (c["component_class"]!="CHROMATIC" or c["low_contrast_pixel_count"]<=0
            or not c["mask_geometry_available"] or c["touches_another_component"]
            or c["overlaps_another_component"] or c["touches_protected_or_chromatic_component"]):
            continue
        by_domain_identity_variant[(c["auxiliary_identity"],c["variant"])].append(c)
    groups=[]
    for (identity,variant),items in by_domain_identity_variant.items():
        items=sorted(items,key=lambda c:(c["bbox_xyxy_exclusive"][0],c["component_id"]))
        for start in range(len(items)):
            run=[]
            for item in items[start:]:
                b=item["bbox_xyxy_exclusive"];rgb=item["representative_rgb_median"]
                if run:
                    prev=run[-1];pb=prev["bbox_xyxy_exclusive"]
                    h0=b[3]-b[1];hp=pb[3]-pb[1];gap=b[0]-pb[2]
                    if (rgb!=prev["representative_rgb_median"] or abs(b[3]-pb[3])>2
                        or abs(b[1]-pb[1])>3 or abs(h0-hp)>2 or gap<0 or gap>max(2,round(0.5*((h0+hp)/2)))):
                        break
                run.append(item)
                if len(run)<4: continue
                left=min(x["bbox_xyxy_exclusive"][0] for x in run);right=max(x["bbox_xyxy_exclusive"][2] for x in run)
                top=min(x["bbox_xyxy_exclusive"][1] for x in run);bottom=max(x["bbox_xyxy_exclusive"][3] for x in run)
                ratios={round((x["bbox_xyxy_exclusive"][2]-x["bbox_xyxy_exclusive"][0])/(x["bbox_xyxy_exclusive"][3]-x["bbox_xyxy_exclusive"][1]),2) for x in run}
                heights=[x["bbox_xyxy_exclusive"][3]-x["bbox_xyxy_exclusive"][1] for x in run]
                if (right-left)/(bottom-top)>=3.0 and len(ratios)>=3 and max(heights)-min(heights)<=2:
                    ids=[x["component_id"] for x in run]
                    groups.append({"auxiliary_identity":identity,"variant":variant,"component_ids":ids,
                      "mask_signatures":[x["mask_signature"] for x in run],"rule":"HORIZONTAL_GLYPH_RUN_V1",
                      "bbox_xyxy_exclusive_union":[left,top,right,bottom],"component_count":len(run),
                      "distinct_component_bbox_aspect_bins":len(ratios),"shared_baseline_spread_px":max(x["bbox_xyxy_exclusive"][3] for x in run)-min(x["bbox_xyxy_exclusive"][3] for x in run),
                      "shared_top_spread_px":max(x["bbox_xyxy_exclusive"][1] for x in run)-min(x["bbox_xyxy_exclusive"][1] for x in run)})
    # Keep maximal non-subset groups to avoid counting the same glyph run repeatedly.
    maximal=[]
    for g in groups:
        s=set(g["component_ids"])
        if not any(g["auxiliary_identity"]==h["auxiliary_identity"] and g["variant"]==h["variant"] and s<set(h["component_ids"]) for h in groups): maximal.append(g)
    return maximal

def main():
    import argparse
    global SAT_ZIP, HARMONIC_LOCAL
    ap=argparse.ArgumentParser()
    ap.add_argument("--satellite-archive",type=Path,default=SAT_ZIP)
    ap.add_argument("--harmonic-source",type=Path,default=HARMONIC_LOCAL)
    args=ap.parse_args();SAT_ZIP=args.satellite_archive;HARMONIC_LOCAL=args.harmonic_source
    if not SAT_ZIP.is_file(): raise RuntimeError(f"satellite input archive unavailable: {SAT_ZIP}")
    rows=source_records(); families={r["family_id"] for r in rows if r["source_qc_status"]=="PASS" and r["domain"]=="satellite-logo"}
    # HELLASAT is intentionally included as an already-known geometry sentinel.
    selected=[r for r in rows if r["source_qc_status"]=="PASS" and (r["domain"]=="satellite-logo" or r["auxiliary_identity"] in ("provider-logo::HARMONIC.png","provider-logo::HARMONIC - NT.png"))]
    sha_doc=json.load(gzip.open(DIAG/"sha-regression.json.gz","rt",encoding="utf-8"))
    expected={(x["identity"],x["variant"]):x for x in sha_doc["results"]}
    engine=load_engine();masters={s:Image.open(MASTER_ROOT/f"templates/picons/{s.lower()}-sablona.png").convert("RGBA") for s in ("BLACK","WHITE")}
    comp_geometry=[];regression=[];current_images={};sources={};row_meta={}
    with zipfile.ZipFile(SAT_ZIP) as archive:
      for row in selected:
        ib=row_image_bytes(row,archive); actual=sha(ib)
        if actual!=row["source_sha256"]: raise RuntimeError(f"source SHA mismatch {row['auxiliary_identity']} {actual} != {row['source_sha256']}")
        with Image.open(io.BytesIO(ib)) as im: src=im.convert("RGBA").copy()
        if src.size!=(220,132): raise RuntimeError(f"unexpected dimensions {row['auxiliary_identity']} {src.size}")
        sources[row["auxiliary_identity"]]=src;row_meta[row["auxiliary_identity"]]=row
        for variant in ("BLACK","WHITE"):
          detail=[];result=engine.classify_and_render(src,masters[variant],variant.lower(),component_diagnostics=detail)
          buf=io.BytesIO();result.image.save(buf,format="PNG",compress_level=9);out_bytes=buf.getvalue();out_sha=sha(out_bytes)
          ex=expected.get((row["auxiliary_identity"],variant))
          if not ex or out_sha!=ex["expected_sha256"]: raise RuntimeError(f"PNG SHA regression failed: {row['auxiliary_identity']} {variant} {out_sha}")
          if result.status!=row["variants"][variant]["engine_status"] or result.reason!=row["variants"][variant]["engine_reason"]: raise RuntimeError(f"status/reason mismatch {row['auxiliary_identity']} {variant}")
          current_images[(row["auxiliary_identity"],variant)]=result.image.copy()
          regression.append({"identity":row["auxiliary_identity"],"variant":variant,"source_sha256":actual,"saved_candidate_sha256":ex["expected_sha256"],"replayed_sha256":out_sha,"result":"PASS"})
          labels,n=ndimage.label(np.asarray(src)[:,:,3]>0,structure=np.ones((3,3),dtype=np.uint8))
          if len(detail)!=n: raise RuntimeError(f"component count mismatch {row['auxiliary_identity']} {variant}")
          for d in detail:
            mask=labels==d["component_id"]
            g=geometry(mask,d["mask_sha256"])
            if g["bbox_xyxy_exclusive"]!=d["bbox_xyxy_exclusive"] or g["area_pixel_count"]!=d["pixel_count"]: raise RuntimeError("geometry mismatch to existing component diagnostics")
            rec={"family_id":row["family_id"],"auxiliary_identity":row["auxiliary_identity"],"source_sha256":actual,"source_path":row["source_path"],"variant":variant,"component_id":d["component_id"],"component_class":d["component_class"],"mask_signature":d["mask_signature"],"low_contrast_pixel_count":d["low_contrast_pixel_count"],"low_contrast_percentage":d["low_contrast_percentage"],"representative_rgb_median":d["representative_rgb_median"],"touches_another_component":d["touches_another_8_connected_component"],"touches_protected_or_chromatic_component":d["touches_protected_or_chromatic_component"],"overlaps_another_component":d["overlaps_another_component"],"engine_status":result.status,"engine_reason":result.reason,"mask_geometry_available":True,**g}
            comp_geometry.append(rec)
    groups=shape_runs(comp_geometry)
    strong_keys={(g["auxiliary_identity"],g["variant"],i) for g in groups for i in g["component_ids"]}
    for c in comp_geometry:
      c["shape_decision"]="STRONG SHAPE CANDIDATE" if (c["auxiliary_identity"],c["variant"],c["component_id"]) in strong_keys else ("TWO-TONE / MIXED" if c["component_class"].startswith("TWO_TONE") else ("AMBIGUOUS CHROMATIC" if c["component_class"]=="CHROMATIC" and c["low_contrast_pixel_count"] else "NOT A LOW-CONTRAST CHROMATIC CANDIDATE"))
    # Recollect minimal masks in memory for approved experimental edits.
    experiment_outputs={};experiment_qc=[]
    for g in groups:
      identity=g["auxiliary_identity"];variant=g["variant"]
      src=sources[identity]; current=current_images[(identity,variant)]
      labels,n=ndimage.label(np.asarray(src)[:,:,3]>0,structure=np.ones((3,3),dtype=np.uint8))
      out=np.array(current,dtype=np.uint8).copy();master=np.array(masters[variant],dtype=np.uint8);srca=np.asarray(src,dtype=np.uint8)
      combined=np.zeros((132,220),dtype=bool)
      for cid in g["component_ids"]: combined |= labels==cid
      # Re-composite only the selected glyph-like masks over their native master.
      target=np.array([240,240,240] if variant=="BLACK" else [16,16,16],dtype=np.float32)
      ma=master[:,:,3:4].astype(np.float32)/255.0
      bg_rgb=master[:,:,:3].astype(np.float32)
      base_a=srca[:,:,3:4].astype(np.float32)/255.0
      # Existing candidate already includes the source over the master. Compute corrected pixel RGB by alpha-compositing the experimental glyph over master.
      new_alpha=base_a+ma*(1-base_a)
      corrected_rgb=np.zeros_like(bg_rgb); nz=new_alpha[:,:,0]>0
      corrected_rgb[nz]=np.rint((target*base_a[nz]+bg_rgb[nz]*ma[nz]*(1-base_a[nz]))/new_alpha[nz]).astype(np.uint8)
      out[:,:,:3][combined]=corrected_rgb[combined]
      img=Image.fromarray(out,"RGBA")
      changed=np.any(np.array(img)!=np.array(current),axis=2)
      if np.any(changed & ~combined): raise RuntimeError("experiment changed pixels outside the candidate mask")
      if img.size!=(220,132) or img.mode!="RGBA" or not changed.any(): raise RuntimeError("experiment output validity failure")
      # Contrast validation uses the unchanged renderer's ratio and threshold.
      solid=combined & (srca[:,:,3]>=engine.OPAQUE_ALPHA)
      if not solid.any(): solid=combined
      contrast=engine.contrast_ratio(np.broadcast_to(target,(int(solid.sum()),3)),engine.master_rgb_under(master,solid).reshape((-1,3)))
      low_pct=100*float(np.count_nonzero(contrast<engine.ACHROMATIC_CONTRAST_RATIO))/max(1,len(contrast))
      if low_pct>=engine.MATERIAL_FRACTION*100: raise RuntimeError(f"experiment contrast QC failed: {low_pct:.2f}%")
      b=io.BytesIO();img.save(b,format="PNG",compress_level=9);data=b.getvalue()
      experiment_outputs[(identity,variant)]=data
      experiment_qc.append({"identity":identity,"family_id":row_meta[identity]["family_id"],"variant":variant,"component_ids":g["component_ids"],"mask_signatures":g["mask_signatures"],"dimensions":[220,132],"mode":"RGBA","changed_pixels":int(changed.sum()),"changed_pixels_outside_mask":0,"low_contrast_percentage_after":low_pct,"output_sha256":sha(data),"status":"PASS"})
    OUT.mkdir(parents=True,exist_ok=True)
    with gzip.open(OUT/"mask-geometry.jsonl.gz","wt",encoding="utf-8") as f:
      for x in comp_geometry:f.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n")
    with (OUT/"shape-experiment-manifest.jsonl").open("w",encoding="utf-8") as f:
      for g in groups:
        row=row_meta[g["auxiliary_identity"]]
        f.write(json.dumps({**g,"family_id":row["family_id"],"source_sha256":row["source_sha256"],"decision":"STRONG SHAPE CANDIDATE","rule_name_free":True},ensure_ascii=False,sort_keys=True)+"\n")
    (OUT/"sha-regression.json").write_text(json.dumps({"scope":"satellite review scope + HARMONIC duplicate sentinel identities","variant_renders_checked":len(regression),"candidate_pngs_changed":0,"all_in_memory_sha_matches":all(x["result"]=="PASS" for x in regression),"result":"PASS FOR PROCESSED SCOPE","results":regression},indent=2,ensure_ascii=False)+"\n")
    (OUT/"experiment-output-qc.json").write_text(json.dumps({"candidate_count":len(experiment_qc),"results":experiment_qc},indent=2,ensure_ascii=False)+"\n")
    candidate_dir=OUT/"experiment-candidates";candidate_dir.mkdir(parents=True,exist_ok=True)
    for (identity,variant),data in experiment_outputs.items():
      stem=hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
      (candidate_dir/f"{stem}-{variant.lower()}.png").write_bytes(data)
    # HARMONIC sentinel report with exact evidence.
    harmonic=[c for c in comp_geometry if c["auxiliary_identity"]=="provider-logo::HARMONIC.png" and ((c["variant"]=="BLACK" and c["component_id"] in range(2,10)) or (c["variant"]=="WHITE" and c["component_id"]==1))]
    hdecision={"family_id":"AUX-RF-0301","identity":"provider-logo::HARMONIC.png","decision":"BLACK components 3-9 are STRONG SHAPE CANDIDATES; component 2 is AMBIGUOUS CHROMATIC; WHITE component 1 remains AMBIGUOUS CHROMATIC","black_candidate_component_ids":[3,4,5,6,7,8,9],"black_ambiguous_component_ids":[2],"white_low_contrast_review_component_ids":[1],"machine_rule":"HORIZONTAL_GLYPH_RUN_V1; common RGB, height +/-2px, baseline +/-2px, top +/-3px, gaps <= half median height, >=4 pieces, union aspect >=3, >=3 distinct bbox aspect bins.","evidence":harmonic,"geometry_scope":"HARMONIC pair only; exact same source SHA verified for both names."}
    (OUT/"harmonic-evidence.json").write_text(json.dumps(hdecision,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    # Build proposed review sheet only when candidates exist, capped at 20 families.
    families_with_groups=defaultdict(list)
    for g in groups: families_with_groups[row_meta[g["auxiliary_identity"]]["family_id"]].append(g)
    selected_families=sorted(families_with_groups)[:20]
    if selected_families:
      sheet=Image.new("RGB",(2000,1200*len(selected_families)),(20,26,38));draw=ImageDraw.Draw(sheet)
      try: title=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",22); font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",14)
      except: title=font=ImageFont.load_default()
      for fi,fid in enumerate(selected_families):
        gs=families_with_groups[fid];identity=gs[0]["auxiliary_identity"];row=row_meta[identity];sy=fi*1200
        draw.text((20,sy+10),f"{fid} | {identity} | strong components: {[(g['variant'],g['component_ids']) for g in gs]}",font=title,fill="white")
        labels=["SOURCE","CURRENT BLACK","PROPOSED BLACK","CURRENT WHITE","PROPOSED WHITE","MASK OVERLAY","CONTOUR OVERLAY"]
        for j,label in enumerate(labels):draw.text((20+j*280,sy+52),label,font=font,fill=(220,230,245))
        src=sources[identity]
        imgs=[src,current_images[(identity,"BLACK")],Image.open(io.BytesIO(experiment_outputs[(identity,"BLACK")])).convert("RGBA") if (identity,"BLACK") in experiment_outputs else None,current_images[(identity,"WHITE")],Image.open(io.BytesIO(experiment_outputs[(identity,"WHITE")])).convert("RGBA") if (identity,"WHITE") in experiment_outputs else None]
        # Source, existing output, and proposals; absent variants are explicitly not proposed.
        for j,img in enumerate(imgs):
          x=20+j*280;y=sy+78
          if img is None:
            draw.rectangle((x,y,x+260,y+156),fill=(43,49,62),outline=(105,120,145),width=2);draw.text((x+62,y+65),"NO PROPOSED CHANGE",font=font,fill=(235,190,90));continue
          im=img.resize((260,156),Image.Resampling.NEAREST).convert("RGBA");bg=Image.new("RGBA",im.size,(32,38,50,255));bg.alpha_composite(im);sheet.paste(bg.convert("RGB"),(x,y));draw.rectangle((x,y,x+259,y+155),outline=(115,130,155),width=2)
        # Combine selected mask overlays; contours use edge pixel coordinates translated to canvas.
        if row["domain"]=="provider-logo":
          source_mask=ndimage.label(np.asarray(src)[:,:,3]>0,structure=np.ones((3,3),dtype=np.uint8))[0]
        else: source_mask=ndimage.label(np.asarray(src)[:,:,3]>0,structure=np.ones((3,3),dtype=np.uint8))[0]
        target=np.zeros((132,220),bool)
        for g in gs:
          for cid in g["component_ids"]:target |= source_mask==cid
        maskimg=Image.new("RGBA",(220,132),(0,0,0,0));arr=np.zeros((132,220,4),dtype=np.uint8);arr[target]=[255,0,200,180];maskimg=Image.fromarray(arr,"RGBA").resize((260,156),Image.Resampling.NEAREST)
        x=20+5*280;y=sy+78;bg=Image.new("RGBA",(260,156),(32,38,50,255));bg.alpha_composite(src.resize((260,156),Image.Resampling.NEAREST));bg.alpha_composite(maskimg);sheet.paste(bg.convert("RGB"),(x,y))
        # Contour overlay extracted from the exact binary mask.
        contours,_=contour_chains(target);x=20+6*280;y=sy+78;im=src.resize((260,156),Image.Resampling.NEAREST).convert("RGBA");bg=Image.new("RGBA",im.size,(32,38,50,255));bg.alpha_composite(im);dr=ImageDraw.Draw(bg)
        for c in contours:
          px,py=c["start_xy"];pts=[(int(px*260/220),int(py*156/132))]
          for d in c["chain_4dir"]:
            if d=="0":px+=1
            elif d=="1":py+=1
            elif d=="2":px-=1
            else:py-=1
            pts.append((int(px*260/220),int(py*156/132)))
          if len(pts)>1:dr.line(pts,fill=(255,0,200,255),width=2)
        sheet.paste(bg.convert("RGB"),(x,y))
        draw.text((20,sy+255),"Shape rule: same RGB; >=4 pieces; aligned top/baseline; height +/-2 px; tight gaps; wide run; >=3 aspect bins. Proposal changes only mask pixels.",font=font,fill=(225,230,240))
      sheet.save(OUT/"shape-review-sheet.png",optimize=True)
    summary={"status":"PARTIAL — provider transparent source archive could not be retrieved through the connected GitHub file API (>1 MB blob returns empty); no global 900-family claim.","checkpoint":"38e58657e8bed714b6a99922ddaf2d4d16ac5701","requested_human_review_families":900,"families_with_full_mask_geometry_in_processed_scope":len({c["family_id"] for c in comp_geometry}),"identities_with_full_mask_geometry_in_processed_scope":len({c["auxiliary_identity"] for c in comp_geometry}),"component_geometry_records_in_processed_scope":len(comp_geometry),"strong_shape_candidate_components_in_processed_scope":sum(len(g["component_ids"]) for g in groups),"families_with_strong_shape_candidates_in_processed_scope":len(families_with_groups),"fully_resolvable_families_in_processed_scope":0,"partially_improvable_families_in_processed_scope":len(families_with_groups),"still_human_review_families_in_requested_scope":900,"source_qc_families":3,"source_qc_identities":4,"provider_review_families_missing_source":832,"scope_processed":{"satellite_review_families":len(families),"harmonic_family":1},"shape_rule":"HORIZONTAL_GLYPH_RUN_V1 (see README)","png_sha_regression":{"checked_variant_renders":len(regression),"changed_png":0,"result":"PASS FOR PROCESSED SCOPE; FULL PROVIDER SCOPE NOT VERIFIED"},"experiment_outputs":len(experiment_qc),"experiment_output_qc":"PASS" if all(x["status"]=="PASS" for x in experiment_qc) else "FAIL","human_review_sheet_families":selected_families,"production_renderer_changed":False,"policy_promoted":False,"full_scope_complete":False,"full_scope_strong_candidate_count":None,"full_scope_fully_resolvable_count":None,"full_scope_partially_improvable_count":None,"test202_built":False}
    (OUT/"summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    print(json.dumps(summary,indent=2,ensure_ascii=False,sort_keys=True))
if __name__=="__main__":main()
