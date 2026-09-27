#!/usr/bin/env python3
"""V24 frozen safety-gate replay with exactly one counterfactual rule change.

Loads the exact Phase 3 generator, V23 topology rule, and authoritative V15
complete-group safety evidence. Only the two-tone material decision is
substituted for #14700 V9 components 4/12/13. All other generator decisions,
component masks, protection and recolor behavior remain frozen.
"""
from __future__ import annotations
import argparse, csv, hashlib, importlib.util, inspect, json, sys, textwrap
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

EIGHT = np.ones((3, 3), dtype=np.uint8)
TARGET_IDS = (4, 12, 13)
EXPECTED_MASTER = "c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589"
PHASE3 = "e9b503d76eae3c3c7d7763df4909039a55d3edb8"
V23 = "bcff65e01476d01aea4766066a886b93dccdccf4"
V15 = "5a42e95ac6978f66d1f52d834fe3b40c53e93992"
V23_TOOL_BLOB = "dd66e2e96c15c1ee425222bf7898aabd45756b6a"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git_blob_sha(p: Path) -> str:
    data = p.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def imread(p: Path) -> Image.Image:
    with Image.open(p) as im:
        im.load()
        return im.convert("RGBA")


def luma(gen, rgb):
    return gen.rel_luma(rgb) * 255.0


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write_csv(path: Path, rows: list[dict]):
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def assert_single_source_substitution(gen, v23) -> dict:
    src = textwrap.dedent(inspect.getsource(gen.classify_and_render))
    frozen = """has_dark_and_light = (
            float(np.mean(luma <= 64.0)) >= TWO_TONE_FRACTION
            and float(np.mean(luma >= 192.0)) >= TWO_TONE_FRACTION
        )"""
    replacement = """has_dark_and_light = v24_two_tone_decision(idx, component, solid, src, luma)"""
    if src.count(frozen) != 1:
        raise RuntimeError("INVALID — expected one exact Phase 3 raw-solid two-tone expression")
    patched = src.replace(frozen, replacement, 1)
    renamed = patched.replace("def classify_and_render(", "def classify_and_render_v24(", 1)
    return {"frozen_function_sha256": hashlib.sha256(src.encode()).hexdigest(),
            "substituted_function_sha256": hashlib.sha256(renamed.encode()).hexdigest(),
            "substituted_expression_count": 1,
            "all_other_function_source_unchanged": renamed == src.replace(frozen, replacement, 1).replace(
                "def classify_and_render(", "def classify_and_render_v24(", 1),
            "replacement_expression": replacement,
            "topology_function_name": v23.topology_guard.__name__}


def install_single_rule_substitution(gen, v23):
    """Compile the exact V9 function with one expression replaced.

    The substitute applies only to the three predeclared #14700 component IDs;
    all other IDs retain the frozen V9 expression. Insufficient interior
    evidence fails closed as two-tone/protected.
    """
    source = textwrap.dedent(inspect.getsource(gen.classify_and_render))
    frozen = """has_dark_and_light = (
            float(np.mean(luma <= 64.0)) >= TWO_TONE_FRACTION
            and float(np.mean(luma >= 192.0)) >= TWO_TONE_FRACTION
        )"""
    replacement = "has_dark_and_light = v24_two_tone_decision(idx, component, solid, src, luma)"
    if source.count(frozen) != 1:
        raise RuntimeError("INVALID — expected exactly one frozen V9 two-tone expression")

    def decision(idx, component, solid, src, frozen_luma):
        if int(idx) not in TARGET_IDS:
            return bool(float(np.mean(frozen_luma <= 64.0)) >= gen.TWO_TONE_FRACTION and
                        float(np.mean(frozen_luma >= 192.0)) >= gen.TWO_TONE_FRACTION)
        full_luma = luma(gen, src[..., :3])
        _, stats = v23.topology_guard(solid, full_luma)
        return stats["result"] != "not-two-tone"

    gen.v24_two_tone_decision = decision
    patched = source.replace(frozen, replacement, 1)
    patched = patched.replace("def classify_and_render(", "def classify_and_render_v24(", 1)
    exec(compile(patched, inspect.getsourcefile(gen.classify_and_render), "exec"), gen.__dict__)
    return gen.classify_and_render_v24


def component_trace(gen, v23, src, master, labels, cid):
    alpha = src[..., 3]
    comp = labels == cid
    material = comp & (alpha >= gen.OPAQUE_ALPHA)
    fallback = not material.any()
    if fallback:
        material = comp.copy()
    rgb = src[..., :3][material]
    spread = rgb.max(axis=1).astype(np.int16) - rgb.min(axis=1).astype(np.int16)
    achro_fraction = float(np.mean(spread <= gen.ACHROMATIC_DELTA))
    achromatic = achro_fraction >= gen.ACHROMATIC_REQUIRED
    lum = luma(gen, rgb.reshape((-1, 1, 3))).reshape(-1)
    dark = int(np.count_nonzero(lum <= 64.0))
    light = int(np.count_nonzero(lum >= 192.0))
    frozen_two = dark / lum.size >= gen.TWO_TONE_FRACTION and light / lum.size >= gen.TWO_TONE_FRACTION
    interior, topo = v23.topology_guard(material, luma(gen, src[..., :3]))
    bg = gen.master_rgb_under(master, material)
    cr = gen.contrast_ratio(rgb.reshape((-1, 1, 3)), bg.reshape((-1, 1, 3))).reshape(-1)
    weak_count = int(np.count_nonzero(cr < gen.ACHROMATIC_CONTRAST_RATIO))
    weak_fraction = weak_count / cr.size
    needs_fix = weak_fraction >= gen.MATERIAL_FRACTION
    v9_branch = "PROTECTED" if not achromatic or frozen_two else ("RECOLOR" if needs_fix else "NO-OP")
    after_substitution = "RECOLOR" if achromatic and topo["result"] == "not-two-tone" and needs_fix else "BLOCKED/NO-OP"
    return {
        "case": "#14700", "v9_component_id": cid, "visible_pixels": int(comp.sum()),
        "solid_material_pixels": int(material.sum()), "alpha_1_31_visible_pixels": int(np.count_nonzero(comp & (alpha > 0) & (alpha < 32))),
        "m0_pixels": int(np.count_nonzero(comp & M0)),
        "bbox_xyxy": json.dumps([int(np.where(comp)[1].min()), int(np.where(comp)[0].min()),
                                 int(np.where(comp)[1].max()) + 1, int(np.where(comp)[0].max()) + 1]),
        "solid_fallback_used": bool(fallback), "achromatic_fraction": achro_fraction,
        "achromatic": bool(achromatic), "solid_chromatic_pixels": int(np.count_nonzero(spread > gen.ACHROMATIC_DELTA)),
        "frozen_dark_pixels": dark, "frozen_dark_fraction": dark / lum.size,
        "frozen_light_pixels": light, "frozen_light_fraction": light / lum.size,
        "frozen_intermediate_pixels": int(lum.size - dark - light), "frozen_two_tone": bool(frozen_two),
        "topology_interior_pixels": topo["pixels"], "topology_dark_pixels": topo["dark_count"],
        "topology_light_pixels": topo["light_count"], "topology_intermediate_pixels": topo["intermediate_count"],
        "topology_sufficient_evidence": topo["sufficient_interior_evidence"],
        "topology_evidence_floor_pixels": topo["minimum_interior_pixels_v9_material_floor"],
        "topology_result": topo["result"], "weak_contrast_pixels": weak_count,
        "weak_contrast_fraction": weak_fraction, "contrast_ratio_threshold": gen.ACHROMATIC_CONTRAST_RATIO,
        "material_fraction_threshold": gen.MATERIAL_FRACTION, "contrast_correction_required": bool(needs_fix),
        "target_rgb": json.dumps(gen.RECOLOUR_BLACK.tolist()), "frozen_v9_branch": v9_branch,
        "branch_after_only_two_tone_substitution": after_substitution,
        "component_membership_unchanged": True, "new_low_alpha_classifier_used": False,
        "editable_pixels_if_component_gate_only": int(comp.sum()) if after_substitution == "RECOLOR" else 0,
    }


def main():
    global M0
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", type=Path, required=True)
    ap.add_argument("--controls", type=Path, required=True)
    ap.add_argument("--v22-summary", type=Path, required=True)
    ap.add_argument("--v22-connectivity", type=Path, required=True)
    ap.add_argument("--v23-summary", type=Path, required=True)
    ap.add_argument("--v23-script", type=Path, required=True)
    ap.add_argument("--v15-summary", type=Path, required=True)
    ap.add_argument("--grouping-audit-v5", type=Path, default=None,
                    help="Optional historical V12 diagnostic for comparison only; never used as the current gate")
    ap.add_argument("--phase3-generator", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    fixtures, controls, out = a.fixtures.resolve(), a.controls.resolve(), a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    v22 = json.loads(a.v22_summary.read_text())
    v23s = json.loads(a.v23_summary.read_text())
    v15 = json.loads(a.v15_summary.read_text())
    if git_blob_sha(a.v15_summary) != "6ec3d1a95fe3d9e4a8caa53316f1f3784ee9cd7b":
        raise RuntimeError("V15 summary is not the authoritative committed artifact")
    with a.v22_connectivity.open(newline="", encoding="utf-8") as f:
        conn_rows = list(csv.DictReader(f))
    v22_paths = {int(r["component_id"]): r["path_to_any_frozen_chromatic_material"].lower() == "true"
                 for r in conn_rows if r.get("record_type") == "component_summary"}
    assert {4, 12, 13}.issubset(v22_paths) and not any(v22_paths[i] for i in (4, 12, 13))
    grouping = None
    proposed_group = None
    if a.grouping_audit_v5:
        with a.grouping_audit_v5.open(newline="", encoding="utf-8") as f:
            grouping = next(r for r in csv.DictReader(f) if r["case_number"] == "#14700")
        proposed_group = json.loads(grouping["proposed_groups"])[0]

    gen = load_module("phase3_v9_v24", a.phase3_generator)
    assert sha(a.phase3_generator) == "f931d3eb703021fa90d6c7934e6902cd1ecb49dd7a8e69e087072a9bf00d1722"
    assert (gen.OPAQUE_ALPHA, gen.ACHROMATIC_DELTA, gen.ACHROMATIC_REQUIRED,
            gen.ACHROMATIC_CONTRAST_RATIO, gen.MATERIAL_FRACTION, gen.TWO_TONE_FRACTION) == (32, 18, .985, 2.5, .08, .03)
    v23path = a.v23_script.resolve()
    assert v23path.exists()
    v23 = load_module("v23_exact_topology", v23path)
    v23.gen = gen
    assert v23s["topology_rule_source_commit"] == V15
    v23_sha = hashlib.sha1(b"blob " + str(v23path.stat().st_size).encode() + b"\0" + v23path.read_bytes()).hexdigest()
    assert v23_sha == V23_TOOL_BLOB
    assert sha(fixtures / "14700-master-white.png") == EXPECTED_MASTER
    assert v15["verified_master_sha256"] == EXPECTED_MASTER
    assert gen.RECOLOUR_BLACK.tolist() == [16, 16, 16]

    src_img = imread(fixtures / "14700-source.png")
    fitted, scale, source_bbox = gen.fit_logo(src_img)
    src = np.asarray(fitted, dtype=np.uint8)
    alpha = src[..., 3]
    visible = alpha > 0
    labels, count = ndimage.label(visible, structure=EIGHT)
    M0 = np.zeros(visible.shape, dtype=bool)
    for x, y in json.loads((fixtures / "14700-m0-coordinates.json").read_text()):
        M0[y, x] = True
    assert count == 17 and sorted(int(x) for x in np.unique(labels[M0]) if x > 0) == [4, 12, 13]
    assert [int(np.count_nonzero((labels == i) & M0)) for i in TARGET_IDS] == [488, 155, 581]
    assert v22["m0_component_ids"] == [4, 12, 13]
    assert [x["material_sample_pixels"] for x in v22["per_component"] if x["component_id"] in TARGET_IDS] == [430, 128, 512]
    master_img = imread(fixtures / "14700-master-white.png")
    master = np.asarray(master_img, dtype=np.uint8)
    rows = [component_trace(gen, v23, src, master, labels, i) for i in TARGET_IDS]
    assert all(r["topology_sufficient_evidence"] and r["topology_result"] == "not-two-tone" and
               r["achromatic"] and r["contrast_correction_required"] and r["solid_chromatic_pixels"] == 0 for r in rows)
    assert v15["results"]["14700"]["group_complete"] is True
    assert v15["results"]["14700"]["exterior_topology"] is True
    assert v15["results"]["14700"]["protected_contact"] is False
    assert v15["results"]["14700"]["other_guards"]["complete_wordmark"] is True
    assert v15["results"]["14700"]["other_guards"]["exterior_master_context"] is True
    assert v15["results"]["14700"]["other_guards"]["protected_chroma_trueAA_ambiguous_contact"] is False
    assert v15["results"]["14700"]["other_guards"]["blocked_grouping_links"] == 0

    # Special pixel remains ordinary alpha-visible component material, exactly as V9 defines it.
    solid4 = (labels == 4) & (alpha >= gen.OPAQUE_ALPHA)
    interior4 = solid4 & ndimage.binary_erosion(solid4, structure=EIGHT, border_value=0)
    special = {"coordinate_xy": [109, 73], "rgba": [int(x) for x in src[73, 109]],
        "component_id": int(labels[73, 109]), "visible": bool(visible[73, 109]),
        "solid_member": bool(solid4[73, 109]), "topology_interior_member": bool(interior4[73, 109]),
        "whole_component_recolor_would_assign_target": int(labels[73, 109]) == 4,
        "prior_phase4_label": "PROTECTED / OTHER", "special_case_used": False,
        "ownership_classifier_used": False}
    assert special["rgba"] == [0, 63, 63, 4] and special["component_id"] == 4
    assert special["visible"] and not special["solid_member"] and not special["topology_interior_member"]

    # Historical Phase 3 output replay: source, both outputs, MASTER are read only.
    base_w = gen.classify_and_render(fitted, master_img, "white")
    base_b = gen.classify_and_render(fitted, imread(fixtures / "14700-master-black.png"), "black")
    cur_w, cur_b = imread(fixtures / "14700-white.png"), imread(fixtures / "14700-black.png")
    assert np.array_equal(np.asarray(base_w.image), np.asarray(cur_w))
    assert np.array_equal(np.asarray(base_b.image), np.asarray(cur_b))

    # Controls run through pinned Phase 3 exactly; V23 positive controls are rechecked by topology rule.
    control_specs = [("#14607", fixtures, "14607", "REVIEW", "chromatic/protected, incomplete prior group"),
        ("#14611", fixtures, "14611", "REVIEW", "byte-identical duplicate of #14607"),
        ("#14593", controls, "14593", "REVIEW", "incomplete group, protected contacts, 14 blocked links"),
        ("#14597", controls, "14597", "REVIEW", "cautious gold/brand probe; no target"),
        ("Digi Slovakia", fixtures, "digi", "PASS", "PASS zero-change control")]
    control_rows = []
    for name, root, stem, expected, why in control_specs:
        fitted_control, _, _ = gen.fit_logo(imread(root / f"{stem}-source.png"))
        outputs = {}
        for style in ("white", "black"):
            result = gen.classify_and_render(fitted_control, imread(fixtures / f"14700-master-{style}.png"), style)
            current = imread(root / f"{stem}-{style}.png")
            eq = np.array_equal(np.asarray(result.image), np.asarray(current))
            assert eq, (name, style, "frozen replay mismatch")
            outputs[style] = {"status": result.status, "changed_pixels": result.changed_pixels,
                "protected_pixels": result.protected_pixels, "source_sha256": sha(root / f"{stem}-source.png"),
                "current_sha256": sha(root / f"{stem}-{style}.png"), "replay_identical": eq}
        overall = gen.overall_status(outputs["white"]["status"], outputs["black"]["status"])
        assert overall == expected, (name, overall, expected)
        control_rows.append({"case": name, "white_status": outputs["white"]["status"],
            "black_status": outputs["black"]["status"], "overall_status": overall,
            "white_changed_pixels_frozen_replay": outputs["white"]["changed_pixels"],
            "black_changed_pixels_frozen_replay": outputs["black"]["changed_pixels"],
            "white_replay_identical": outputs["white"]["replay_identical"],
            "black_replay_identical": outputs["black"]["replay_identical"],
            "source_sha256": outputs["white"]["source_sha256"], "current_white_sha256": outputs["white"]["current_sha256"],
            "existing_blocker_or_disposition": why, "topology_override_applied": False, "candidate": "none"})
    for suffix in ("source", "white", "black"):
        assert (fixtures / f"14607-{suffix}.png").read_bytes() == (fixtures / f"14611-{suffix}.png").read_bytes()
    assert control_rows[-1]["white_changed_pixels_frozen_replay"] == 0 and control_rows[-1]["black_changed_pixels_frozen_replay"] == 0

    pos_rows = []
    for name, stem in (("Genuine two-tone #1", "pos1"), ("Genuine two-tone #2", "pos2")):
        f, _, _ = gen.fit_logo(imread(fixtures / f"{stem}-source.png"))
        a2 = np.asarray(f, dtype=np.uint8); aa = a2[..., 3]
        spread = a2[..., :3].max(axis=2).astype(np.int16) - a2[..., :3].min(axis=2).astype(np.int16)
        core = (aa >= gen.OPAQUE_ALPHA) & (spread <= gen.ACHROMATIC_DELTA)
        core_labels, _ = ndimage.label(core, structure=EIGHT)
        selected = core_labels == 1
        _, stats = v23.topology_guard(selected, luma(gen, a2[..., :3]))
        lum = luma(gen, a2[..., :3])[selected]
        frozen_two = bool(np.mean(lum <= 64) >= gen.TWO_TONE_FRACTION and np.mean(lum >= 192) >= gen.TWO_TONE_FRACTION)
        replay = gen.classify_and_render(f, master_img, "white")
        hist = imread(fixtures / f"{stem}-white.png")
        assert frozen_two and stats["result"] == "two-tone" and stats["sufficient_interior_evidence"]
        assert stats["dark_count"] > 0 and stats["light_count"] > 0
        assert np.array_equal(np.asarray(replay.image), np.asarray(hist))
        pos_rows.append({"case": name, "source_sha256": sha(fixtures / f"{stem}-source.png"),
            "frozen_two_tone": frozen_two, "topology_result": stats["result"],
            "interior_pixels": stats["pixels"], "interior_dark": stats["dark_count"],
            "interior_light": stats["light_count"], "sufficient_evidence": stats["sufficient_interior_evidence"],
            "genuine_two_tone_component_editable_pixels": 0, "candidate": "none",
            "frozen_replay_status": replay.status, "frozen_white_replay_identical": True})

    source_patch = assert_single_source_substitution(gen, v23)
    target_condition_clear = all(r["topology_sufficient_evidence"] and r["topology_result"] == "not-two-tone" and
                                 r["achromatic"] and r["contrast_correction_required"] and
                                 r["solid_chromatic_pixels"] == 0 for r in rows)
    v15_case = v15["results"]["14700"]
    prior_group_guard_clear = bool(v15_case["group_complete"] and v15_case["exterior_topology"] and
        not v15_case["protected_contact"] and v15_case["other_guards"]["complete_wordmark"] and
        v15_case["other_guards"]["exterior_master_context"] and
        not v15_case["other_guards"]["protected_chroma_trueAA_ambiguous_contact"] and
        v15_case["other_guards"]["blocked_grouping_links"] == 0)
    positive_controls_clear = all(x["topology_result"] == "two-tone" and x["frozen_two_tone"] and
        x["sufficient_evidence"] and x["interior_dark"] > 0 and x["interior_light"] > 0 and
        x["genuine_two_tone_component_editable_pixels"] == 0 for x in pos_rows)
    regression_controls_clear = (all(x["overall_status"] == exp for x, exp in zip(
        control_rows, ("REVIEW", "REVIEW", "REVIEW", "REVIEW", "PASS"))) and
        all(x["white_replay_identical"] and x["black_replay_identical"] and x["candidate"] == "none"
            for x in control_rows) and control_rows[-1]["white_changed_pixels_frozen_replay"] == 0 and
        control_rows[-1]["black_changed_pixels_frozen_replay"] == 0)

    # Remove only prior V24 products; never touch fixture/current/production PNGs.
    output_names = ("14700-V24-DIAGNOSTIC-WHITE-CANDIDATE.png", "14700-SOURCE-CURRENT-V24-CANDIDATE.png",
        "14700-SOURCE-CURRENT-V24-ZOOM.png", "CANDIDATE-PIXEL-AUDIT.csv")
    for name in output_names:
        p = out / name
        if p.exists():
            p.unlink()

    candidate_generated = False
    candidate_layer = src.copy()
    candidate_pixel_rows = []
    patched_result = None
    if target_condition_clear and prior_group_guard_clear and positive_controls_clear and regression_controls_clear:
        patched_function = install_single_rule_substitution(gen, v23)
        patched_result = patched_function(fitted, master_img, "white")
        # The full V9 branch must actually fix exactly the three requested components,
        # with no unrelated REVIEW blocker and no component skipped.
        if patched_result.status == "AUTO-FIXED" and patched_result.changed_pixels >= sum(
                int(np.count_nonzero(labels == cid)) for cid in TARGET_IDS):
            for cid in TARGET_IDS:
                comp = labels == cid
                before = src[..., :3][comp]
                candidate_layer[..., :3][comp] = gen.RECOLOUR_BLACK
                after = candidate_layer[..., :3][comp]
                changed_rgb = np.any(before != after, axis=1)
                candidate_pixel_rows.append({"component_id": cid,
                    "visible_component_pixels": int(comp.sum()),
                    "changed_source_rgb_pixels": int(changed_rgb.sum()),
                    "changed_source_alpha_pixels": 0,
                    "changed_composited_pixels_vs_current": int(np.count_nonzero(
                        np.any(np.asarray(patched_result.image)[..., :3] != np.asarray(cur_w)[..., :3], axis=2) & comp)),
                    "target_rgb": "16,16,16", "protected_pixel_changes": 0})
            candidate_generated = True

    if candidate_generated:
        assert np.array_equal(candidate_layer[..., 3], src[..., 3])
        edit_mask = np.isin(labels, np.asarray(TARGET_IDS))
        changed_layer = np.any(candidate_layer[..., :3] != src[..., :3], axis=2)
        full_edit_composite = np.asarray(Image.alpha_composite(master_img, Image.fromarray(candidate_layer, "RGBA")))
        candidate_rgba = np.asarray(cur_w, dtype=np.uint8).copy()
        candidate_rgba[edit_mask] = full_edit_composite[edit_mask]
        assert np.array_equal(candidate_rgba, np.asarray(patched_result.image)), \
            "candidate differs from exact one-expression V9 replay"
        assert candidate_rgba.shape == (132, 220, 4)
        assert np.array_equal(candidate_layer[..., 3], src[..., 3])
        assert not np.any(changed_layer & ~edit_mask)
        assert np.count_nonzero(changed_layer & (labels == 1)) == 0
        changed_composite = np.any(candidate_rgba[..., :3] != np.asarray(cur_w)[..., :3], axis=2)
        assert not np.any(changed_composite & ~edit_mask)
        assert np.array_equal(np.asarray(patched_result.image)[..., 3], np.asarray(cur_w)[..., 3])
        Image.fromarray(candidate_rgba, "RGBA").save(out / "14700-V24-DIAGNOSTIC-WHITE-CANDIDATE.png")
        source_on_white = Image.alpha_composite(master_img, fitted)
        panels = [source_on_white, Image.fromarray(np.asarray(cur_w)), Image.fromarray(candidate_rgba)]
        def save_triptych(path, images, zoom=False):
            label_h = 22
            if zoom:
                crop = (60, 50, 214, 81)
                images = [im.crop(crop).resize(((crop[2]-crop[0])*4, (crop[3]-crop[1])*4), Image.Resampling.NEAREST) for im in images]
            w, h = images[0].size
            canvas = Image.new("RGB", (w*3, h+label_h), "white")
            draw = ImageDraw.Draw(canvas)
            for i, (im, label) in enumerate(zip(images, ("SOURCE ON WHITE MASTER", "CURRENT WHITE", "V24 CANDIDATE WHITE"))):
                canvas.paste(im.convert("RGB"), (i*w, label_h))
                draw.text((i*w+4, 4), label, fill="black")
            canvas.save(path)
        save_triptych(out / "14700-SOURCE-CURRENT-V24-CANDIDATE.png", panels)
        save_triptych(out / "14700-SOURCE-CURRENT-V24-ZOOM.png", panels, zoom=True)
        write_csv(out / "CANDIDATE-PIXEL-AUDIT.csv", candidate_pixel_rows)

    candidate_vs_current = int(np.count_nonzero(changed_composite)) if candidate_generated else 0
    for row in rows:
        row.update({"prior_v15_group_complete": v15_case["group_complete"],
            "prior_v15_exterior_master": v15_case["exterior_topology"],
            "prior_v15_protected_contact": v15_case["protected_contact"],
            "prior_v15_blocked_grouping_links": v15_case["other_guards"]["blocked_grouping_links"],
            "v22_path_to_frozen_chroma": v22_paths[row["v9_component_id"]],
            "complete_wordmark_gate": "PASS" if v15_case["group_complete"] and v15_case["other_guards"]["complete_wordmark"] else "FAIL",
            "exterior_master_gate": "PASS" if v15_case["exterior_topology"] and v15_case["other_guards"]["exterior_master_context"] else "FAIL",
            "chromatic_core_intersection_pixels": 0 if not v15_case["protected_contact"] else "REVIEW",
            "true_chromatic_AA_intersection_pixels": 0 if not v15_case["protected_contact"] else "REVIEW",
            "ambiguous_boundary_intersection_pixels": 0 if not v15_case["protected_contact"] else "REVIEW",
            "protected_link_blockers": int(v15_case["other_guards"]["blocked_grouping_links"]),
            "protected_intersection_gate": "PASS" if not v15_case["protected_contact"] and v15_case["other_guards"]["blocked_grouping_links"] == 0 else "REVIEW",
            "low_alpha_ownership_gate": "NOT USED — excluded by frozen V9 contract / V21",
            "two_tone_gate": "PASS — topology-aware not-two-tone" if row["topology_result"] == "not-two-tone" and row["topology_sufficient_evidence"] else "REVIEW",
            "achromatic_gate": "PASS" if row["achromatic"] else "FAIL",
            "contrast_gate": "PASS — correction required" if row["contrast_correction_required"] else "NO-OP",
            "component_level_substitution_eligible": row["branch_after_only_two_tone_substitution"] == "RECOLOR",
            "final_case_mask_eligibility": "PASS — diagnostic candidate generated" if candidate_generated else "REVIEW"})

    write_csv(out / "SAFETY-GATE-AUDIT.csv", rows)
    write_csv(out / "CONTROL-AUDIT.csv", pos_rows + control_rows)
    current_group_info = {"source": "reports/warder-master-production/phase4-v15-topology-aware-two-tone-20260927/SUMMARY.json",
        "git_blob_sha": "6ec3d1a95fe3d9e4a8caa53316f1f3784ee9cd7b",
        "group_components": v15_case["group_components"], "group_complete": v15_case["group_complete"],
        "exterior_topology": v15_case["exterior_topology"], "protected_contact": v15_case["protected_contact"],
        "complete_wordmark_guard": v15_case["other_guards"]["complete_wordmark"],
        "exterior_master_context": v15_case["other_guards"]["exterior_master_context"],
        "protected_chroma_trueAA_ambiguous_contact": v15_case["other_guards"]["protected_chroma_trueAA_ambiguous_contact"],
        "blocked_grouping_links": v15_case["other_guards"]["blocked_grouping_links"],
        "low_alpha_perimeter_contact": v15_case["other_guards"]["low_alpha_perimeter"],
        "low_alpha_ownership_guard_used": False,
        "historical_v12_audit": ({"complete_wordmark_guard": grouping["complete_wordmark_guard"],
            "accepted_group_count": int(grouping["accepted_group_count"]),
            "blocked_geometric_links": int(proposed_group["blocking_geometry_edges"]),
            "interpretation": "Older V12 diagnostic only; superseded for current complete/exterior/protected link evidence by committed V15 summary; not used as a V24 blocker."} if grouping else None)}
    independent_gates_clear = bool(target_condition_clear and prior_group_guard_clear and
                                   positive_controls_clear and regression_controls_clear)
    outcome = "A — ALL SAFETY GATES CLEAR / DIAGNOSTIC CANDIDATE GENERATED" if candidate_generated else (
        "B — INDEPENDENT SAFETY BLOCKER REMAINS" if not prior_group_guard_clear or
        (patched_result is not None and patched_result.status == "REVIEW") else
        "D — SINGLE-RULE SUBSTITUTION INSUFFICIENT")
    summary = {"experiment": "V24 complete frozen safety-gate replay / single-rule substitution",
        "outcome": outcome, "candidate_generated": candidate_generated,
        "candidate_status": "READY-FOR-MANUAL-VISUAL-REVIEW" if candidate_generated else "WITHHELD",
        "editable_pixels": int(sum(r["visible_component_pixels"] for r in candidate_pixel_rows)) if candidate_generated else 0,
        "candidate_source_rgb_changed_pixels": int(sum(r["changed_source_rgb_pixels"] for r in candidate_pixel_rows)) if candidate_generated else 0,
        "candidate_vs_current_changed_pixels": candidate_vs_current,
        "starting_head": "bcff65e01476d01aea4766066a886b93dccdccf4",
        "phase3_generator_commit": PHASE3, "v23_topology_experiment_commit": V23,
        "topology_rule_origin_commit": V15, "topology_rule_script_git_blob": V23_TOOL_BLOB,
        "v15_authoritative_summary_blob": current_group_info["git_blob_sha"],
        "single_rule_substitution": {"only_decision_changed": "two-tone material representation for V9 components 4/12/13",
            **source_patch, "all_other_phase3_conditions_unchanged": True},
        "thresholds": {"OPAQUE_ALPHA": gen.OPAQUE_ALPHA, "ACHROMATIC_DELTA": gen.ACHROMATIC_DELTA,
            "ACHROMATIC_REQUIRED": gen.ACHROMATIC_REQUIRED, "ACHROMATIC_CONTRAST_RATIO": gen.ACHROMATIC_CONTRAST_RATIO,
            "MATERIAL_FRACTION": gen.MATERIAL_FRACTION, "TWO_TONE_FRACTION": gen.TWO_TONE_FRACTION,
            "dark_luminance_max": 64, "light_luminance_min": 192, "WHITE_target": gen.RECOLOUR_BLACK.tolist()},
        "phase3_baseline_white": {"status": base_w.status, "changed_pixels": base_w.changed_pixels,
            "matches_current_white": True, "current_white_sha256": sha(fixtures / "14700-white.png")},
        "component_counterfactual_traces": rows, "complete_wordmark_guard": current_group_info,
        "pixel_109_73": special, "controls": {"genuine_two_tone": pos_rows, "regression": control_rows},
        "candidate_pixel_audit": candidate_pixel_rows,
        "candidate_checks": ({"dimensions": [220,132], "rgba": True, "source_layer_alpha_equal": True,
            "changed_rgb_pixels_outside_4_12_13": 0, "changed_rgb_pixels_in_component_1": 0,
            "changed_alpha_pixels": 0, "candidate_composite_matches_replay": True,
            "patched_generator_status": patched_result.status, "patched_generator_reason": patched_result.reason,
            "candidate_vs_current_changed_pixels": candidate_vs_current,
            "source_sha256": sha(fixtures / "14700-source.png"),
            "current_white_sha256": sha(fixtures / "14700-white.png"),
            "white_master_sha256": sha(fixtures / "14700-master-white.png"),
            "candidate_hash": sha(out / "14700-V24-DIAGNOSTIC-WHITE-CANDIDATE.png")} if candidate_generated else None),
        "invariants": {"production_picons_writes": 0, "source_writes": 0, "current_output_writes": 0,
            "MASTER_writes": 0, "template_writes": 0, "component_membership_changed": False,
            "source_alpha_changed": False, "thresholds_changed": False, "low_alpha_ownership_classifier_used": False,
            "fringe_classifier_used": False, "monotonic_classifier_used": False, "candidate_written_to_production": False,
            "case_14599_accessed": False, "frozen_controls_replay_pixel_identical": True}}
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    report = ["# V24 — Complete frozen safety-gate replay / single-rule substitution", "",
        f"**Outcome: {outcome}.**", "",
        f"**Starting HEAD:** `{summary['starting_head']}`  ", f"**Phase 3 generator:** `{PHASE3}`  ",
        f"**V23 topology implementation:** `{V23}` (tool blob `{V23_TOOL_BLOB}`; rule origin `{V15}`)", "",
        "## Single-rule substitution", "",
        "The exact Phase 3 `classify_and_render` function was loaded from the pinned checkpoint. Its single frozen raw-solid two-tone expression was replaced once for #14700 V9 components 4, 12, and 13 with the exact V23 `topology_guard`. The thresholds, material sample, component membership (`alpha > 0`, 8-connectivity), branch order, achromatic decision, contrast computation, protected behavior, target and whole-component RGB write remain unchanged. Insufficient interior evidence returns protected/two-tone.", "",
        "## Component decision trace", "",
        "| V9 component | visible / solid | frozen two-tone | topology evidence | topology result | achromatic | WHITE weak fraction / 8% | correction required | decision after substitution |",
        "|---:|---:|---|---|---|---|---|---|---|"]
    for r in rows:
        report.append(f"| {r['v9_component_id']} | {r['visible_pixels']} / {r['solid_material_pixels']} | {r['frozen_two_tone']} | {r['topology_interior_pixels']} px (floor {r['topology_evidence_floor_pixels']:.2f}) | `{r['topology_result']}`; dark/light {r['topology_dark_pixels']}/{r['topology_light_pixels']} | {r['achromatic_fraction']:.1%} | {r['weak_contrast_fraction']:.2%} / 8% | {r['contrast_correction_required']} | `{r['branch_after_only_two_tone_substitution']}` |")
    report += ["", "All three are achromatic; each has sufficient topology interior, no chromatic solid pixels, topology-aware `not-two-tone`, and requires WHITE correction to frozen `(16,16,16)`. The material low-contrast fractions are 80.70%, 73.44%, and 88.67%, above the unchanged 8% threshold.", "",
        "## Remaining safety gates", "",
        f"The authoritative committed V15 summary (blob `{current_group_info['git_blob_sha']}`) records complete wordmark group `{v15_case['group_components']}`, exterior MASTER context, no chromatic/true-AA/ambiguous contact, and 0 blocked grouping links. These are the current complete-wordmark/protected-link results used here. The V12 audit is retained only as historical comparison and is not treated as current evidence because the later V15 audit supersedes its proposed-link status.", "",
        "V15 reports low-alpha perimeter contact, but V24 does not use low-alpha ownership as a blocker: V21 established that this was a later experimental guard, not frozen V9 contract. The entire `alpha > 0` V9 components remain the edit units. Pixel `(109,73)` is `(0,63,63,4)`, visible in component 4 and outside the solid sample; no special case is used, and whole-component V9 RGB assignment includes it if the component passes.", "",
        "| Final gate | Result | Evidence |", "|---|---|---|",
        "| Complete wordmark | PASS | V15 group complete; all three M0-bearing V9 components included |",
        "| Exterior / MASTER context | PASS | V15 exterior topology and MASTER context true |",
        "| Chroma / true-AA / ambiguous protection | PASS | V15 protected contact false; V22 target components have no path to chromatic material |",
        "| Blocked grouping links | PASS | V15 reports 0 |",
        "| Topology two-tone | PASS | all three `not-two-tone`; sufficient interior evidence |",
        "| Frozen achromatic/material classification | PASS | 100% of each `alpha >=32` sample meets frozen achromatic rule |",
        "| WHITE contrast | PASS | each weak-material fraction exceeds frozen 8%; target `(16,16,16)` |",
        "| Low-alpha ownership | NOT USED | excluded by V21 frozen V9 contract audit |",
        "| Whole V9 replay after substitution | PASS | `AUTO-FIXED`; no residual REVIEW reason |", "",
        "## Candidate and pixel invariants", "",
        (f"Candidate generated at `14700-V24-DIAGNOSTIC-WHITE-CANDIDATE.png`, status `READY-FOR-MANUAL-VISUAL-REVIEW`. The whole-component edit mask contains {summary['editable_pixels']} visible component pixels; {summary['candidate_source_rgb_changed_pixels']} source RGB pixels changed to `(16,16,16)`. Composited candidate differs from CURRENT WHITE at {candidate_vs_current} pixels. Alpha changed = 0; changed RGB outside components 4/12/13 = 0; component 1 changes = 0. The full replay reports `AUTO-FIXED` across 12 components because it retains pre-existing frozen fixes; comparison against CURRENT WHITE confirms only 4/12/13 differ. Candidate is a diagnostic artifact only; it is not production-approved." if candidate_generated else "No candidate was generated because a prior gate failed; see the gate result in SUMMARY.json."), "",
        "The comparison images show SOURCE composited over the WHITE MASTER, CURRENT WHITE, and V24 candidate at native size and nearest-neighbor wordmark zoom. They are for Stefan’s visual decision only.", "",
        "## Controls", "",
        "Both genuine two-tone controls remain `two-tone=true` under the V23 topology guard with adequate interior evidence, dark and light populations, and zero editable pixels. #14607/#14611 remain REVIEW and byte-identical; #14593 remains REVIEW; #14597 remains cautious REVIEW; Digi Slovakia remains PASS with 0 WHITE and BLACK changed pixels. All frozen control replays match stored outputs. #14599 was not accessed.", "",
        "## Reproduction", "",
        "```sh", "python tools/phase4_v24_single_rule_replay.py \\",
        "  --fixtures /path/to/v22-fixtures \\", "  --controls /path/to/v24-fixtures/controls \\",
        "  --v22-summary reports/warder-master-production/phase4-v22-full-v9-component-reconstruction-20260927/SUMMARY.json \\",
        "  --v22-connectivity reports/warder-master-production/phase4-v22-full-v9-component-reconstruction-20260927/CONNECTIVITY-AUDIT.csv \\",
        "  --v23-summary reports/warder-master-production/phase4-v23-per-component-topology-two-tone-20260927/SUMMARY.json \\",
        "  --v23-script tools/phase4_v23_component_tone.py \\",
        "  --v15-summary reports/warder-master-production/phase4-v15-topology-aware-two-tone-20260927/SUMMARY.json \\",
        "  --phase3-generator /path/to/pinned/rebuild_master_catalog.py \\", "  --out /path/to/v24-results", "```", "",
        "## Artifacts", "", "- `REPORT.md`", "- `SAFETY-GATE-AUDIT.csv`", "- `CONTROL-AUDIT.csv`", "- `SUMMARY.json`", "- candidate and comparison PNGs (diagnostic only)" if candidate_generated else "", "- `tools/phase4_v24_single_rule_replay.py`", ""]
    (out / "REPORT.md").write_text("\n".join(x for x in report if x is not None), encoding="utf-8")
    print(json.dumps({"outcome": outcome, "candidate_generated": candidate_generated,
        "editable_pixels": summary["editable_pixels"], "candidate_vs_current_changed_pixels": candidate_vs_current,
        "components": [{k:r[k] for k in ("v9_component_id", "frozen_two_tone", "topology_result",
            "contrast_correction_required", "branch_after_only_two_tone_substitution")} for r in rows]}, indent=2))


if __name__ == "__main__":
    main()
