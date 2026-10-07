#!/usr/bin/env python3
"""Continue the existing auxiliary mask geometry experiment for provider scope only.

This imports the existing geometry, classifier replay, and HORIZONTAL_GLYPH_RUN_V1
implementation unchanged from auxiliary_mask_geometry_export.py. It does not edit the
production renderer or the previous satellite/HARMONIC results.
"""
from __future__ import annotations
import argparse, gzip, hashlib, importlib.util, io, json, sys, zipfile
from collections import defaultdict
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"reports/warder-master-production/auxiliary-mask-geometry-2026-10-07"
OUT=ROOT/"reports/warder-master-production/auxiliary-mask-geometry-provider-2026-10-07"
DIAG=ROOT/"reports/warder-master-production/auxiliary-component-diagnostics-2026-10-06"
ARCHIVE=Path("/tmp/aux-exp/provider-transparent.zip")
EXPECTED_SIZE=11481399
EXPECTED_SHA256="93ef555cf09d49a72188c477949d948feaf6416a0fcff047600d36b3a96e4b8f"
HARMONIC_IDS={"provider-logo::HARMONIC.png","provider-logo::HARMONIC - NT.png"}

def sha(b): return hashlib.sha256(b).hexdigest()
def load_exporter():
    spec=importlib.util.spec_from_file_location("existing_auxiliary_mask_geometry_export",ROOT/"tools/auxiliary_mask_geometry_export.py")
    mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod);return mod

def load_rows():
    rows=[]
    for i in range(1,12):
        with gzip.open(DIAG/f"component-diagnostics-{i:02d}.jsonl.gz","rt",encoding="utf-8") as f:
            rows.extend(json.loads(x) for x in f if x.strip())
    return rows

def main():
    global ARCHIVE
    ap=argparse.ArgumentParser()
    ap.add_argument("--archive",type=Path,default=ARCHIVE)
    ARCHIVE=ap.parse_args().archive
    if not ARCHIVE.is_file(): raise RuntimeError(f"pinned provider archive missing: {ARCHIVE}")
    data=ARCHIVE.read_bytes()
    if len(data)!=EXPECTED_SIZE: raise RuntimeError(f"provider ZIP size mismatch: {len(data)} != {EXPECTED_SIZE}")
    if sha(data)!=EXPECTED_SHA256: raise RuntimeError(f"provider ZIP SHA mismatch: {sha(data)} != {EXPECTED_SHA256}")
    exporter=load_exporter(); rows=load_rows()
    selected=[r for r in rows if r["domain"]=="provider-logo" and r["source_qc_status"]=="PASS" and r["auxiliary_identity"] not in HARMONIC_IDS]
    families={r["family_id"] for r in selected}
    if len(families)!=832: raise RuntimeError(f"expected 832 remaining provider families; found {len(families)}")
    if len(selected)!=967: raise RuntimeError(f"expected 967 provider identities in remaining review scope; found {len(selected)}")
    sha_doc=json.load(gzip.open(DIAG/"sha-regression.json.gz","rt",encoding="utf-8"))
    expected={(x["identity"],x["variant"]):x for x in sha_doc["results"]}
    engine=exporter.load_engine()
    masters={s:Image.open(ROOT/f"templates/picons/{s.lower()}-sablona.png").convert("RGBA") for s in ("BLACK","WHITE")}
    comp_geometry=[];regression=[];current_images={};sources={};row_meta={}
    with zipfile.ZipFile(ARCHIVE) as archive:
        bad=archive.testzip()
        if bad: raise RuntimeError(f"provider ZIP integrity failure at {bad}")
        for row in selected:
            prefix,member=row["source_path"].split(":",1)
            if prefix!="provider-transparent.zip": raise RuntimeError(f"unexpected provider source path: {row['source_path']}")
            try: ib=archive.read(member)
            except KeyError as e: raise RuntimeError(f"missing ZIP member: {member}") from e
            actual=sha(ib)
            if actual!=row["source_sha256"]: raise RuntimeError(f"source SHA mismatch {row['auxiliary_identity']}: {actual} != {row['source_sha256']}")
            with Image.open(io.BytesIO(ib)) as im: src=im.convert("RGBA").copy()
            if src.size!=(220,132): raise RuntimeError(f"unexpected dimensions {row['auxiliary_identity']}: {src.size}")
            sources[row["auxiliary_identity"]]=src;row_meta[row["auxiliary_identity"]]=row
            for variant in ("BLACK","WHITE"):
                detail=[]
                result=engine.classify_and_render(src,masters[variant],variant.lower(),component_diagnostics=detail)
                buf=io.BytesIO();result.image.save(buf,format="PNG",compress_level=9);out_bytes=buf.getvalue();out_sha=sha(out_bytes)
                ex=expected.get((row["auxiliary_identity"],variant))
                if not ex or out_sha!=ex["expected_sha256"]: raise RuntimeError(f"PNG SHA regression failed: {row['auxiliary_identity']} {variant} {out_sha}")
                if result.status!=row["variants"][variant]["engine_status"] or result.reason!=row["variants"][variant]["engine_reason"]:
                    raise RuntimeError(f"status/reason mismatch {row['auxiliary_identity']} {variant}")
                current_images[(row["auxiliary_identity"],variant)]=result.image.copy()
                regression.append({"identity":row["auxiliary_identity"],"family_id":row["family_id"],"variant":variant,"source_sha256":actual,"saved_candidate_sha256":ex["expected_sha256"],"replayed_sha256":out_sha,"status":result.status,"reason":result.reason,"result":"PASS"})
                labels,n=ndimage.label(np.asarray(src)[:,:,3]>0,structure=np.ones((3,3),dtype=np.uint8))
                if len(detail)!=n: raise RuntimeError(f"component count mismatch {row['auxiliary_identity']} {variant}")
                for d in detail:
                    mask=labels==d["component_id"]
                    g=exporter.geometry(mask,d["mask_sha256"])
                    if g["bbox_xyxy_exclusive"]!=d["bbox_xyxy_exclusive"] or g["area_pixel_count"]!=d["pixel_count"]: raise RuntimeError("geometry mismatch to saved diagnostics")
                    comp_geometry.append({"family_id":row["family_id"],"auxiliary_identity":row["auxiliary_identity"],"source_sha256":actual,"source_path":row["source_path"],"variant":variant,"component_id":d["component_id"],"component_class":d["component_class"],"mask_signature":d["mask_signature"],"low_contrast_pixel_count":d["low_contrast_pixel_count"],"low_contrast_percentage":d["low_contrast_percentage"],"representative_rgb_median":d["representative_rgb_median"],"touches_another_component":d["touches_another_8_connected_component"],"touches_protected_or_chromatic_component":d["touches_protected_or_chromatic_component"],"overlaps_another_component":d["overlaps_another_component"],"engine_status":result.status,"engine_reason":result.reason,"mask_geometry_available":True,**g})
    groups=exporter.shape_runs(comp_geometry)
    strong={(g["auxiliary_identity"],g["variant"],i) for g in groups for i in g["component_ids"]}
    for c in comp_geometry:
        c["shape_decision"]="STRONG SHAPE CANDIDATE" if (c["auxiliary_identity"],c["variant"],c["component_id"]) in strong else ("TWO-TONE / MIXED" if c["component_class"].startswith("TWO_TONE") else ("AMBIGUOUS CHROMATIC" if c["component_class"]=="CHROMATIC" and c["low_contrast_pixel_count"] else "NOT A LOW-CONTRAST CHROMATIC CANDIDATE"))
    experiment_outputs={};experiment_qc=[]
    for g in groups:
        identity=g["auxiliary_identity"];variant=g["variant"];src=sources[identity];current=current_images[(identity,variant)]
        labels,_=ndimage.label(np.asarray(src)[:,:,3]>0,structure=np.ones((3,3),dtype=np.uint8))
        out=np.array(current,dtype=np.uint8).copy();master=np.array(masters[variant],dtype=np.uint8);srca=np.asarray(src,dtype=np.uint8);combined=np.zeros((132,220),dtype=bool)
        for cid in g["component_ids"]: combined |= labels==cid
        target=np.array([240,240,240] if variant=="BLACK" else [16,16,16],dtype=np.float32)
        ma=master[:,:,3:4].astype(np.float32)/255.0;bg=master[:,:,:3].astype(np.float32);base_a=srca[:,:,3:4].astype(np.float32)/255.0
        new_a=base_a+ma*(1-base_a);corrected=np.zeros_like(bg);nz=new_a[:,:,0]>0
        corrected[nz]=np.rint((target*base_a[nz]+bg[nz]*ma[nz]*(1-base_a[nz]))/new_a[nz]).astype(np.uint8)
        out[:,:,:3][combined]=corrected[combined];img=Image.fromarray(out,"RGBA")
        changed=np.any(np.asarray(img)!=np.asarray(current),axis=2)
        if np.any(changed & ~combined): raise RuntimeError("experiment changed pixels outside exact candidate mask")
        if img.size!=(220,132) or img.mode!="RGBA" or not changed.any(): raise RuntimeError("experiment output validation failure")
        if not np.array_equal(np.asarray(img)[:,:,3],np.asarray(current)[:,:,3]): raise RuntimeError("experiment changed alpha/geometry")
        solid=combined & (srca[:,:,3]>=engine.OPAQUE_ALPHA)
        if not solid.any(): solid=combined
        ratios=engine.contrast_ratio(np.broadcast_to(target,(int(solid.sum()),3)),engine.master_rgb_under(master,solid).reshape((-1,3)))
        low=100*float(np.count_nonzero(ratios<engine.ACHROMATIC_CONTRAST_RATIO))/max(1,len(ratios))
        if low>=engine.MATERIAL_FRACTION*100: raise RuntimeError(f"experiment contrast QC failed: {low:.2f}%")
        b=io.BytesIO();img.save(b,format="PNG",compress_level=9);png=b.getvalue();experiment_outputs[(identity,variant)]=png
        experiment_qc.append({"identity":identity,"family_id":row_meta[identity]["family_id"],"variant":variant,"component_ids":g["component_ids"],"mask_signatures":g["mask_signatures"],"dimensions":[220,132],"mode":"RGBA","changed_pixels":int(changed.sum()),"changed_pixels_outside_mask":0,"alpha_geometry_unchanged":True,"low_contrast_percentage_after":low,"output_sha256":sha(png),"status":"PASS"})
    OUT.mkdir(parents=True,exist_ok=True);(OUT/"experiment-candidates").mkdir(exist_ok=True)
    with gzip.open(OUT/"provider-mask-geometry.jsonl.gz","wt",encoding="utf-8") as f:
        for x in comp_geometry:f.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n")
    with (OUT/"provider-shape-experiment-manifest.jsonl").open("w",encoding="utf-8") as f:
        for g in groups:
            row=row_meta[g["auxiliary_identity"]];f.write(json.dumps({**g,"family_id":row["family_id"],"source_sha256":row["source_sha256"],"decision":"STRONG SHAPE CANDIDATE","rule_name_free":True},ensure_ascii=False,sort_keys=True)+"\n")
    (OUT/"provider-source-verification.json").write_text(json.dumps({"url":"https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/main/assets/warder/downloads/picons/providers/220x132/piconProv_220x132.zip","archive":"piconProv_220x132.zip","size_bytes":len(data),"sha256":sha(data),"expected_size_bytes":EXPECTED_SIZE,"expected_sha256":EXPECTED_SHA256,"zip_test":"PASS","member_png_count":sum(n.lower().endswith('.png') for n in zipfile.ZipFile(ARCHIVE).namelist()),"result":"PASS"},indent=2)+"\n")
    (OUT/"provider-sha-regression.json").write_text(json.dumps({"scope":"remaining 832 provider review families; HARMONIC excluded and preserved from accepted checkpoint","variant_renders_checked":len(regression),"candidate_pngs_changed":0,"all_sha_status_reason_matches":True,"result":"PASS","results":regression},ensure_ascii=False,indent=2)+"\n")
    (OUT/"provider-experiment-output-qc.json").write_text(json.dumps({"candidate_count":len(experiment_qc),"results":experiment_qc},ensure_ascii=False,indent=2)+"\n")
    for (identity,variant),png in experiment_outputs.items():
        stem=hashlib.sha256(identity.encode()).hexdigest()[:12]
        (OUT/"experiment-candidates"/f"{stem}-{variant.lower()}.png").write_bytes(png)
    # Per-family readiness is evidence-only; a family is fully resolvable only when
    # every low-contrast chromatic component across both variants belongs to a run.
    groups_by_family=defaultdict(list)
    for g in groups: groups_by_family[row_meta[g["auxiliary_identity"]]["family_id"]].append(g)
    comps_by_family=defaultdict(list)
    for c in comp_geometry: comps_by_family[c["family_id"]].append(c)
    fully=[];partial=[]
    for fid in families:
        comps=comps_by_family[fid]; marks={(g["auxiliary_identity"],g["variant"],cid) for g in groups_by_family.get(fid,[]) for cid in g["component_ids"]}
        low=[c for c in comps if c["component_class"]=="CHROMATIC" and c["low_contrast_pixel_count"]>0]
        if not low: continue
        if all((c["auxiliary_identity"],c["variant"],c["component_id"]) in marks for c in low): fully.append(fid)
        else: partial.append(fid)
    summary={"checkpoint":"79c801ade4d51bc9e1ea7c8d7db1f4cab26586ee","source_checkpoint":"38e58657e8bed714b6a99922ddaf2d4d16ac5701","scope":"provider only; remaining 832 review families; no satellite rerun; HARMONIC preserved","provider_families_expected":832,"provider_families_processed":len(families),"provider_identities_processed":len(selected),"total_component_records":len(comp_geometry),"variant_renders_checked":len(regression),"strong_shape_candidate_components":sum(len(g["component_ids"]) for g in groups),"shape_candidate_groups":len(groups),"families_with_strong_candidates":len(groups_by_family),"fully_resolvable_families_by_candidate_coverage":len(fully),"partially_improvable_families":len(partial),"source_qc_families_not_in_render_scope":3,"source_qc_identities_not_in_render_scope":4,"experiment_outputs":len(experiment_qc),"experiment_output_qc":"PASS","png_sha_regression":"PASS; 0 existing PNG changed; status+reason match","shape_rule":"HORIZONTAL_GLYPH_RUN_V1 imported unchanged from tools/auxiliary_mask_geometry_export.py","production_renderer_changed":False,"production_policy_changed":False,"test202_built":False}
    (OUT/"provider-summary.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps(summary,indent=2))
if __name__=="__main__": main()
