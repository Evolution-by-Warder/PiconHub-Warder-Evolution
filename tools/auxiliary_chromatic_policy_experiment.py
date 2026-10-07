#!/usr/bin/env python3
"""Conservative evidence-only policy experiment for saved auxiliary diagnostics.

Does not import or call the production renderer, does not alter production PNGs,
and does not emit corrected PNGs.  Existing diagnostics contain mask hashes but
not mask pixels/contours, so no chromatic component can satisfy the independent
wordmark/glyph geometry proof required by this experiment.
"""
from __future__ import annotations
import gzip, json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports/warder-master-production/auxiliary-component-diagnostics-2026-10-06"
OUT = ROOT / "reports/warder-master-production/chromatic-policy-experiment-2026-10-07"


def read_jsonl_gz(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def main():
    families = {}
    eligible, rejected = [], []
    component_counts = Counter()
    family_components = defaultdict(list)
    source_qc_families = set()
    rows = list(read_jsonl_gz(SOURCE / "component-diagnostics-01.jsonl.gz"))
    for n in range(2, 12):
        rows.extend(read_jsonl_gz(SOURCE / f"component-diagnostics-{n:02d}.jsonl.gz"))
    for row in rows:
        fid = row["family_id"]
        families.setdefault(fid, {"family_id": fid, "domain": row["domain"],
            "member_identities": [], "source_qc_statuses": set(),
            "geometry_statuses": set(), "review_variants": set(), "component_count": 0})
        fam = families[fid]
        if row["auxiliary_identity"] not in fam["member_identities"]:
            fam["member_identities"].append(row["auxiliary_identity"])
        fam["source_qc_statuses"].add(row["source_qc_status"])
        fam["geometry_statuses"].add(row["geometry_status"])
        if row["source_qc_status"] != "PASS":
            source_qc_families.add(fid)
        for variant, v in row["variants"].items():
            fam["component_count"] += len(v.get("components", []))
            if v.get("engine_status") == "REVIEW":
                fam["review_variants"].add(variant)
            for c in v.get("components", []):
                low = int(c.get("low_contrast_pixel_count", 0)) > 0
                if not low:
                    continue
                cls = c.get("component_class", "UNKNOWN")
                if cls not in ("CHROMATIC", "TWO_TONE_CHROMATIC", "TWO_TONE_ACHROMATIC"):
                    continue
                component_counts[cls] += 1
                record = {
                    "family_id": fid, "auxiliary_identity": row["auxiliary_identity"],
                    "domain": row["domain"], "source_path": row["source_path"],
                    "source_sha256": row["source_sha256"], "source_qc_status": row["source_qc_status"],
                    "geometry_status": row["geometry_status"], "variant": variant,
                    "component_id": c["component_id"], "component_class": cls,
                    "bbox_xyxy_exclusive": c["bbox_xyxy_exclusive"],
                    "pixel_count": c["pixel_count"], "representative_rgb_median": c["representative_rgb_median"],
                    "low_contrast_pixel_count": c["low_contrast_pixel_count"],
                    "low_contrast_percentage": c["low_contrast_percentage"],
                    "touches_another_component": c.get("touches_another_8_connected_component"),
                    "touches_protected_or_chromatic_component": c.get("touches_protected_or_chromatic_component"),
                    "overlaps_another_component": c.get("overlaps_another_component"),
                    "mask_signature": c.get("mask_signature"),
                    "engine_status": c.get("engine_status"),
                    "engine_reason": c.get("engine_reason"),
                    "recolour_refusal_reason": c.get("recolour_refusal_reason"),
                }
                if row["source_qc_status"] != "PASS":
                    category, reason = "SOURCE-QC", "source QC is not PASS"
                elif row["geometry_status"] != "PRESERVED_NATIVE_CANVAS":
                    category, reason = "PROTECTED / UNSAFE", "source geometry is not a preserved native canvas"
                elif cls.startswith("TWO_TONE"):
                    category, reason = "TWO-TONE / MIXED", "two-tone chromatic/achromatic components remain excluded by default"
                elif (not record["mask_signature"] or record["touches_another_component"]
                      or record["touches_protected_or_chromatic_component"]
                      or record["overlaps_another_component"]):
                    category, reason = "PROTECTED / UNSAFE", "required isolated-mask evidence is absent or unsafe"
                else:
                    # A hash identifies a mask but cannot disclose its contour or glyph structure.
                    category, reason = "AMBIGUOUS CHROMATIC", (
                        "isolation and low contrast are recorded, but diagnostics contain only a mask hash/bbox; "
                        "no pixel-mask geometry or contour evidence establishes a simple wordmark/glyph rather than a brand symbol"
                    )
                record.update({"classification": category, "decision": "REJECTED_FROM_STRONG_SET",
                               "exact_experiment_reason": reason,
                               "strong_experiment_candidate": False})
                rejected.append(record)
                family_components[fid].append(record)
    for fam in families.values():
        fam["source_qc_statuses"] = sorted(fam["source_qc_statuses"])
        fam["geometry_statuses"] = sorted(fam["geometry_statuses"])
        fam["review_variants"] = sorted(fam["review_variants"])
        fam["strong_candidate_components"] = 0
        fam["strong_candidate_component_ids"] = []
        fam["experiment_decision"] = "HUMAN-REVIEW" if fam["family_id"] not in source_qc_families else "SOURCE-QC"
        fam["fully_resolvable_if_rule_approved"] = False
        fam["partially_improvable"] = False
        fam["reason"] = "No component passed the semantic geometry gate; recorded mask signatures cannot establish glyph-like shape."
    summary = {
        "status": "PROPOSED POLICY EXPERIMENT — NO POLICY PROMOTION",
        "input_checkpoint": "17dfbd0a23d4a6073aed9ab5846a3fd45e3d35c4",
        "total_review_families": len(families),
        "review_families_with_component_evidence": len(families) - len(source_qc_families),
        "source_qc_families": len(source_qc_families),
        "source_qc_identities": sum(1 for r in rows if r["source_qc_status"] != "PASS"),
        "chromatic_low_contrast_component_instances": component_counts["CHROMATIC"],
        "two_tone_low_contrast_component_instances": component_counts["TWO_TONE_CHROMATIC"] + component_counts["TWO_TONE_ACHROMATIC"],
        "strong_experiment_candidate_components": 0,
        "families_with_strong_candidates": 0,
        "fully_resolvable_families": 0,
        "partially_improvable_families": 0,
        "still_human_review_families": len(families) - len(source_qc_families),
        "source_qc_families_still_blocked": len(source_qc_families),
        "experiment_png_count": 0,
        "experiment_output_qc": "NOT APPLICABLE — no strong candidate passed the semantic geometry gate",
        "scope_note": "The 320 SOURCE-UNRESOLVED families are excluded; this run reads only the saved 903 engine-review family diagnostics.",
        "semantic_gate": "Requires deterministic pixel-mask/contour evidence for simple glyph-like wordmark structure. Existing diagnostics store mask SHA signatures and bounding boxes, not mask geometry. No OCR/name-based inference used.",
        "low_contrast_class_counts": dict(component_counts),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT / "component-eligibility.jsonl.gz", "wt", encoding="utf-8") as f:
        for x in eligible: f.write(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n")
    with gzip.open(OUT / "component-rejections.jsonl.gz", "wt", encoding="utf-8") as f:
        for x in rejected: f.write(json.dumps(x, ensure_ascii=False, sort_keys=True) + "\n")
    with gzip.open(OUT / "family-experiment-summary.jsonl.gz", "wt", encoding="utf-8") as f:
        for fid in sorted(families): f.write(json.dumps(families[fid], ensure_ascii=False, sort_keys=True) + "\n")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    harmonic = json.loads((SOURCE / "harmonic-evidence.json").read_text(encoding="utf-8"))
    harmonic_out = {"decision": "AMBIGUOUS CHROMATIC", "family_id": "AUX-RF-0301",
       "engine_refusal": harmonic["exact_refusal"],
       "machine_evidence": "8-connected component IDs 2–9 are CHROMATIC, have no touching/overlap, share recorded median RGB [0,39,78], and have low-contrast values 76.4% (component 2) / 100% (3–9). The saved diagnostics include bbox and mask SHA, but no component contour/mask pixels; they cannot establish whether the larger first component is a glyph or protected brand symbol.",
       "strong_candidate_component_ids": [], "experiment_pngs": [],
       "source_unmodified": True, "production_status_unchanged": True}
    (OUT / "harmonic-decision.json").write_text(json.dumps(harmonic_out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__": main()
