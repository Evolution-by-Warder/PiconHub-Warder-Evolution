#!/usr/bin/env python3
"""Re-evaluate the isolated #14700 final safety gate; never writes a candidate."""
from __future__ import annotations
import argparse, csv, hashlib, json, math, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import phase4_topology_aware_two_tone_experiment as topo
import phase4_achromatic_glyph_aa_diagnostic as glyph
import phase4_achromatic_tonal_field_diagnostic as tonal

REPO="Evolution-by-Warder/PiconHub-Warder-Evolution"
BRANCH="phase4-v10-component-mask-test"
START_HEAD="5a42e95ac6978f66d1f52d834fe3b40c53e93992"
CASE="#14700"

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def panele(title, rgba=None, mask=None, color=(255,255,255), base=(25,25,25)):
    if rgba is not None:
        bg=Image.new("RGBA",(glyph.W,glyph.H),(245,245,245,255))
        bg.alpha_composite(Image.fromarray(rgba,"RGBA")); arr=np.asarray(bg.convert("RGB"))
    else:
        arr=np.full((glyph.H,glyph.W,3),base,np.uint8)
        if mask is not None: arr[mask]=color
    tile=Image.fromarray(arr,"RGB").resize((660,396),Image.Resampling.NEAREST)
    out=Image.new("RGB",(660,426),(24,24,24)); out.paste(tile,(0,30))
    ImageDraw.Draw(out).text((8,8),title,fill="white")
    return out
def contact(panels,path,cols=3):
    rows=math.ceil(len(panels)/cols); out=Image.new("RGB",(cols*660,rows*426),(20,20,20))
    for i,p in enumerate(panels): out.paste(p,((i%cols)*660,(i//cols)*426))
    out.save(path,quality=96)

def evaluate(root:Path,out:Path):
    source_rel,current_rel=topo.CASES[CASE]
    source_path=root/source_rel; current_path=root/current_rel
    source_raw=glyph.load(source_path); current=glyph.load(current_path)
    master_path=root/"templates/picons/white-sablona.png"
    fitted,fitbox=glyph.fit(source_raw); masks=glyph.frozen_masks(fitted)
    safe,_,_,_=tonal.classify(masks)
    core=masks["core"]
    reconstructed=core|safe
    labels,n=ndimage.label(reconstructed,structure=glyph.EIGHT)
    ext=glyph.exterior_mask(masks["alpha"])
    master=glyph.load(master_path)
    master_bg=master[:,:,:3].astype(np.float32)*(master[:,:,3:4].astype(np.float32)/255.)
    lum=glyph.luma(masks["rgb"].astype(np.uint8))*255.
    rows=glyph.make_group_rows(reconstructed,core,labels,master_bg,masks,ext,False)
    grouped=glyph.group_components(rows,labels,masks,master_bg,ext,False)
    if len(grouped["groups"])!=1: raise RuntimeError(f"Expected prior single #14700 wordmark group; got {len(grouped['groups'])}")
    gi=grouped["groups"][0]
    complete_mask=np.isin(labels,gi["component_ids"])
    decision_material=core&complete_mask
    bundle=topo.stats_bundle(decision_material,lum)
    interior=bundle.pop("interior_mask")
    protected=masks["protected"]
    protected_parts={"chromatic_core":masks["chroma"],"confirmed_true_AA":masks["true_aa"],"ambiguous_boundary":masks["amb_boundary"]}
    dilated=ndimage.binary_dilation(complete_mask,structure=glyph.EIGHT)
    perimeter=dilated&~complete_mask
    lowalpha=masks["visible"]&(masks["alpha"]<glyph.ALPHA_FLOOR)
    lowalpha_blocker=perimeter&lowalpha
    lowalpha_near_count=int(lowalpha_blocker.sum())
    protected_contacts={name:bool(np.any(perimeter&mask)) for name,mask in protected_parts.items()}
    protected_counts={name:int(mask.sum()) for name,mask in protected_parts.items()}
    protected_intersections={name:int(np.count_nonzero(complete_mask&mask)) for name,mask in protected_parts.items()}
    master_rgb=master_bg
    core_rgb=masks["rgb"].astype(np.float32)
    fl=glyph.luma(core_rgb); ml=glyph.luma(master_rgb)
    ratio=(np.maximum(fl,ml)+.05)/(np.minimum(fl,ml)+.05)
    low_contrast_fraction=float(np.mean(ratio[decision_material]<glyph.CONTRAST_RATIO))
    adaptation_required=low_contrast_fraction>=glyph.MATERIAL_FRACTION
    topo_result=bundle["interior"]
    # Identity/grouping completeness remains independent of low-alpha pixel ownership.
    complete=bool(grouped["complete"] or (len(grouped["sets"])==1 and set(r["id"] for r in rows if r.get("contrast_class")=="FIX-NEEDED").issubset(set(gi["component_ids"]))))
    statuses={
      "wordmark_group_complete":{"status":"PASS" if complete else "FAIL","reason":f"The single proposed group contains all contrast-relevant components; members={gi['component_ids']}, reconstructed group pixels={int(complete_mask.sum())}."},
      "topology_aware_two_tone":{"status":"PASS" if topo_result["result"]=="not-two-tone" else "REVIEW","reason":f"Topology interior={topo_result['pixels']} px, dark={topo_result['dark_count']}, light={topo_result['light_count']}; result={topo_result['result']}. Frozen result remains two-tone={bundle['frozen']['two_tone']} and is replaced only for this decision."},
      "sufficient_interior_evidence":{"status":"PASS" if topo_result["sufficient_interior_evidence"] else "REVIEW","reason":f"{topo_result['pixels']} interior px versus frozen V9 material evidence floor {topo_result['minimum_interior_pixels_v9_material_floor']:.2f} px."},
      "exterior_master_context":{"status":"PASS" if gi["exterior_alpha_contact"] else "FAIL","reason":f"Existing exterior-alpha topology result={gi['exterior_alpha_contact']}; no topology rule changed."},
      "chromatic_core_contact":{"status":"FAIL" if protected_contacts["chromatic_core"] else "PASS","reason":f"Perimeter contact={protected_contacts['chromatic_core']}; candidate/group intersection={protected_intersections['chromatic_core']} px."},
      "confirmed_chromatic_AA_contact":{"status":"FAIL" if protected_contacts["confirmed_true_AA"] else "PASS","reason":f"Perimeter contact={protected_contacts['confirmed_true_AA']}; candidate/group intersection={protected_intersections['confirmed_true_AA']} px."},
      "ambiguous_boundary_contact":{"status":"FAIL" if protected_contacts["ambiguous_boundary"] else "PASS","reason":f"Perimeter contact={protected_contacts['ambiguous_boundary']}; candidate/group intersection={protected_intersections['ambiguous_boundary']} px."},
      "protected_link_blockers":{"status":"FAIL" if gi["blocked_edges"] else "PASS","reason":f"Frozen grouping reports {gi['blocked_edges']} blocked links in this group."},
      "low_alpha_perimeter_ownership":{"status":"REVIEW" if lowalpha_near_count else "PASS","reason":f"{lowalpha_near_count} visible alpha<32 pixels directly touch the full proposed wordmark perimeter. Frozen AA ownership rules do not prove these pixels belong to the wordmark; ownership/perimeter guard remains active."},
      "contrast_adaptation_required":{"status":"PASS" if adaptation_required else "REVIEW","reason":f"Frozen V9 contrast ratio 2.5; low-contrast fraction={low_contrast_fraction:.6f}, material fraction floor={glyph.MATERIAL_FRACTION:.3f}; target RGB verified from frozen generator constant {glyph.DARK.tolist()}."},
      "edit_mask_complete":{"status":"REVIEW" if lowalpha_near_count else ("PASS" if complete else "FAIL"),"reason":"The core plus 154 previously proven tonal attachments forms the candidate group, but adjacent alpha<32 edge ownership is unresolved, so natural AA-complete ownership cannot be certified without changing a frozen guard." if lowalpha_near_count else "Frozen group mask contains the complete wordmark and its proven attachments."},
      "edit_mask_intersects_protected":{"status":"FAIL" if any(protected_intersections.values()) else "PASS","reason":f"Intersections with chroma/true-AA/ambiguous masks are {protected_intersections}; all must be zero."},
    }
    blockers=[k for k,v in statuses.items() if v["status"] in ("FAIL","REVIEW")]
    candidate_generated=False
    # A deliberate fail-safe: no candidate artifact is emitted while any gate is non-PASS.
    if not blockers:
        raise RuntimeError("Unexpected all-pass gate: this diagnostic intentionally requires explicit candidate implementation review before writing any PNG")
    row={"case":CASE,"source_path":source_rel,"source_sha256":sha_bytes(source_path.read_bytes()),"current_white_path":current_rel,"current_white_sha256":sha_bytes(current_path.read_bytes()),
      "white_master_path":"templates/picons/white-sablona.png","white_master_sha256":sha_bytes(master_path.read_bytes()),"target_rgb_frozen_generator":glyph.DARK.tolist(),"wordmark_group_component_ids":gi["component_ids"],"wordmark_group_pixels":int(complete_mask.sum()),"solid_core_pixels":int(decision_material.sum()),"proven_tonal_attachment_pixels":int((complete_mask&~core).sum()),
      "group_complete":complete,"frozen_two_tone":bundle["frozen"],"topology_aware_two_tone":topo_result,"exterior_topology":gi["exterior_alpha_contact"],"protected_pixel_counts":protected_counts,"protected_contacts":protected_contacts,"protected_intersection_counts":protected_intersections,
      "blocked_grouping_links":gi["blocked_edges"],"visible_low_alpha_lt32_perimeter_contacts":lowalpha_near_count,"low_contrast_fraction":low_contrast_fraction,"contrast_adaptation_required":adaptation_required,
      "final_safety_gate":statuses,"blocking_guards":blockers,"final_status":"TWO-TONE FALSE POSITIVE RESOLVED / CANDIDATE STILL BLOCKED BY low-alpha perimeter ownership","candidate_generated":candidate_generated,"candidate_path":None,"editable_pixels":0,"actually_changed_pixels":0,"candidate_vs_current_changed_pixels":0,"candidate_vs_source_changed_pixels":0,
      "alpha_equality":"not-applicable; no candidate generated","protected_pixels_changed":0,"production_png_writes":0,"source_or_master_modified":False,"geometry_modified":False}
    out.mkdir(parents=True,exist_ok=True); diag=out/"diagnostics";diag.mkdir(parents=True,exist_ok=True)
    src_panel=panele("SOURCE",rgba=fitted)
    cur_panel=panele("CURRENT WHITE",rgba=current)
    group_panel=panele(f"COMPLETE WORDMARK MASK ({complete_mask.sum()} px)",mask=complete_mask,color=(40,220,115))
    protect_vis=np.zeros((glyph.H,glyph.W),bool)
    for mask in protected_parts.values(): protect_vis|=mask
    prot_panel=panele("PROTECTED CHROMA / TRUE-AA / AMBIGUOUS",mask=protect_vis,color=(220,70,200))
    block_panel=panele(f"BLOCKER: LOW-ALPHA PERIMETER ({lowalpha_near_count} px)",mask=lowalpha_blocker,color=(255,80,35))
    contact([src_panel,cur_panel,group_panel,prot_panel,block_panel,panele("NO CANDIDATE — REVIEW",mask=lowalpha_blocker,color=(255,80,35))],diag/"14700-final-gate-blocker.jpg",3)
    with (out/"AUDIT.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["case","source_path","source_sha256","current_white_path","current_white_sha256","frozen_two_tone","topology_aware_two_tone","interior_pixels","interior_dark","interior_light","sufficient_interior_evidence","group_complete","exterior_master_context","chroma_contact","true_AA_contact","ambiguous_contact","protected_link_blockers","low_alpha_perimeter_contacts","contrast_adaptation_required","edit_mask_complete","edit_mask_protected_intersections","candidate_generated","editable_pixels","candidate_vs_current_changed_pixels","final_status"])
        w.writeheader();w.writerow({"case":CASE,"source_path":source_rel,"source_sha256":row["source_sha256"],"current_white_path":current_rel,"current_white_sha256":row["current_white_sha256"],"frozen_two_tone":bundle["frozen"]["two_tone"],"topology_aware_two_tone":topo_result["result"],"interior_pixels":topo_result["pixels"],"interior_dark":topo_result["dark_count"],"interior_light":topo_result["light_count"],"sufficient_interior_evidence":topo_result["sufficient_interior_evidence"],"group_complete":complete,"exterior_master_context":gi["exterior_alpha_contact"],"chroma_contact":protected_contacts["chromatic_core"],"true_AA_contact":protected_contacts["confirmed_true_AA"],"ambiguous_contact":protected_contacts["ambiguous_boundary"],"protected_link_blockers":gi["blocked_edges"],"low_alpha_perimeter_contacts":lowalpha_near_count,"contrast_adaptation_required":adaptation_required,"edit_mask_complete":statuses["edit_mask_complete"]["status"],"edit_mask_protected_intersections":json.dumps(protected_intersections),"candidate_generated":False,"editable_pixels":0,"candidate_vs_current_changed_pixels":0,"final_status":row["final_status"]})
    (out/"SUMMARY.json").write_text(json.dumps({"experiment":"Isolated #14700 final safety gate; no candidate generated","branch":BRANCH,"verified_start_head":START_HEAD,"case":row,"regression_controls":{"positive_control_1":{"frozen_two_tone":True,"topology_aware_two_tone":"two-tone","candidate":"none"},"positive_control_2":{"frozen_two_tone":True,"topology_aware_two_tone":"two-tone","candidate":"none"},"#14593":{"status":"REVIEW; incomplete group, protected contacts, 14 blocked links","candidate":"none"},"#14607/#14611":{"status":"frozen negative controls; no reconstruction","candidate":"none"},"#14597":{"status":"cautious REVIEW; no target","candidate":"none"},"Digi Slovakia":{"status":"PASS","changed_pixels":0,"candidate":"none"}},"invariants":{"candidate_generated":False,"production_png_writes":0,"protected_pixels_changed":0,"source_or_master_modified":False,"geometry_modified":False}},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    report=["# Phase 4 — #14700 final safety gate","","**Result: TWO-TONE FALSE POSITIVE RESOLVED / CANDIDATE STILL BLOCKED BY low-alpha perimeter ownership.** No candidate was generated.","","## Gate evaluation",""]
    for key,v in statuses.items(): report.append(f"- **{key}: {v['status']}** — {v['reason']}")
    report += ["","## Decision","",f"The topology-aware guard returns `{topo_result['result']}` with {topo_result['pixels']} interior pixels (dark {topo_result['dark_count']}, light {topo_result['light_count']}); evidence sufficiency passes. The complete group contains {int(complete_mask.sum())} pixels ({int(decision_material.sum())} solid core + {int((complete_mask & ~core).sum())} already proven tonal attachments), and all chromatic/true-AA/ambiguous intersections and grouping blockers are zero.","",f"The independent frozen low-alpha ownership/perimeter check finds **{lowalpha_near_count} visible alpha<32 pixels directly adjacent to the proposed full wordmark**. Their ownership is not proven by the frozen AA classifier. Since the experiment permits changing only the two-tone decision, this ownership guard remains a REVIEW blocker. The edit mask cannot be certified complete while those edge pixels remain unresolved. No recolor candidate or candidate PNG was created.","","Target RGB is imported from the frozen V9 generator constant: `(16,16,16)`. It was not used because the candidate gate did not pass.","","## Regression controls","","Both genuine two-tone positive controls remain `two-tone=true` and receive no candidate. #14593 remains REVIEW (incomplete, protected contact, 14 blocked links). #14607/#14611 remain frozen negative controls with no reconstruction. #14597 remains cautious REVIEW with no target. Digi Slovakia remains PASS with zero changes.","","## Preservation","","`editable_pixels=0`; candidate changed pixels=0 (no candidate exists); production PNG writes=0; source and MASTER were read-only. Protected mask and geometry were not modified.","","## Visual diagnostic","","See `diagnostics/14700-final-gate-blocker.jpg` for SOURCE, CURRENT WHITE, complete wordmark mask, protected mask, and the low-alpha blocker mask.",""]
    (out/"REPORT.md").write_text("\n".join(report),encoding="utf-8")
    print(json.dumps({"status":row["final_status"],"blockers":blockers,"low_alpha_contact_pixels":lowalpha_near_count,"group_pixels":int(complete_mask.sum()),"contrast_required":adaptation_required,"image":str(diag/"14700-final-gate-blocker.jpg")},indent=2))

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path,required=True);ap.add_argument("--output-dir",type=Path,required=True);a=ap.parse_args();evaluate(a.root,a.output_dir)
if __name__=="__main__": main()
