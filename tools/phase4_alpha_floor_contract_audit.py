#!/usr/bin/env python3
"""Read-only verifier for the pinned V21 alpha-floor contract evidence.

Run from a clone containing the pinned Git objects. Prints its checks as JSON.
It never modifies generator, picons, sources, templates, or masters.
"""
import json
import subprocess

PHASE3 = "e9b503d76eae3c3c7d7763df4909039a55d3edb8"
FIRST_GATE = "6b336f74a6d717a39ac04084b2f4399f92842ccb"
FOLLOWUP = "34dbb53a8291419c1061f602710dc36d263cef19"
CURRENT = "37d466f398b1fc1f518c68e50072fbdc9e36817f"

def show(rev, path):
    return subprocess.check_output(["git", "show", f"{rev}:{path}"], text=True, encoding="utf-8")

def main():
    source = show(PHASE3, "tools/rebuild_master_catalog.py")
    required = (
        "OPAQUE_ALPHA = 32",
        "visible = alpha > 0",
        "ndimage.label(visible, structure=np.ones((3, 3), dtype=np.uint8))",
        "solid = component & (alpha >= OPAQUE_ALPHA)",
        "if not solid.any():",
        "solid = component",
        "work[..., :3][component] = target",
        "protected |= component",
    )
    for token in required:
        if token not in source:
            raise SystemExit(f"Missing Phase 3 code evidence: {token}")

    plan = show(PHASE3, "docs/PICON-MASTER-QUALITY-PLAN.md")
    if any(token in plan for token in ("OPAQUE_ALPHA", "alpha<32", "alpha < 32")):
        raise SystemExit("Unexpected explicit alpha-floor ownership clause in Phase 3 plan")

    gate = show(FIRST_GATE, "tools/phase4_14700_final_candidate_gate.py")
    for token in ('lowalpha=masks["visible"]&(masks["alpha"]<glyph.ALPHA_FLOOR)',
                  "lowalpha_blocker=perimeter&lowalpha",
                  '"low_alpha_perimeter_ownership":{"status":"REVIEW"'):
        if token not in gate:
            raise SystemExit(f"Missing later low-alpha gate evidence: {token}")

    followup = show(FOLLOWUP, "tools/phase4_14700_low_alpha_ownership.py")
    if "SAFE WORDMARK OWNERSHIP" not in followup or "AMBIGUOUS" not in followup:
        raise SystemExit("Missing one-hop ownership follow-up evidence")

    print(json.dumps({
        "phase3": PHASE3,
        "current": CURRENT,
        "opaque_alpha": 32,
        "visible": "alpha > 0",
        "component_connectivity": "8-connected",
        "material": "alpha >= 32; fallback to whole component if none qualify",
        "edit_and_protected_unit": "whole visible connected component",
        "separate_low_alpha_ownership_classifier_in_v9": False,
        "first_explicit_low_alpha_ownership_gate": FIRST_GATE,
        "result": "A — V9 component inclusion; separate ownership proof is later",
    }, indent=2))

if __name__ == "__main__":
    main()
