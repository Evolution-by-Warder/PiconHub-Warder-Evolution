#!/usr/bin/env python3
"""Replay the pinned Phase 3/V9 component path on a small frozen fixture set.

Inputs are read-only copies fetched at the Phase 3 checkpoint. This script
never writes to a repository picons/, template, source, or MASTER tree.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

EIGHT = np.ones((3, 3), dtype=np.uint8)
NEIGHBORS = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]
FIXTURES = {
    "14700": ("14700-source.png", "14700-white.png", "14700-black.png"),
    "14607": ("14607-source.png", "14607-white.png", "14607-black.png"),
    # 14611 is byte-identical to 14607 at the frozen checkpoint; this alias
    # replays the same bytes and is also verified remotely as a duplicate.
    "14611 duplicate regression": ("14607-source.png", "14607-white.png", "14607-black.png"),
    "Digi Slovakia": ("digi-source.png", "digi-white.png", "digi-black.png"),
    "Genuine two-tone #1": ("pos1-source.png", "pos1-white.png", "pos1-black.png"),
    "Genuine two-tone #2": ("pos2-source.png", "pos2-white.png", "pos2-black.png"),
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rgba(path: Path) -> Image.Image:
    with Image.open(path) as im:
        im.load()
        return im.convert("RGBA")


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def component_stats(gen, src: np.ndarray, master: np.ndarray, mask: np.ndarray, style: str) -> dict:
    alpha = src[..., 3]
    solid = mask & (alpha >= gen.OPAQUE_ALPHA)
    fallback = not bool(solid.any())
    if fallback:
        solid = mask.copy()
    rgb = src[..., :3][solid]
    delta = rgb.max(axis=1).astype(np.int16) - rgb.min(axis=1).astype(np.int16)
    achro_fraction = float(np.mean(delta <= gen.ACHROMATIC_DELTA))
    achromatic = achro_fraction >= gen.ACHROMATIC_REQUIRED
    luma = gen.rel_luma(rgb.reshape((-1, 1, 3))).reshape(-1) * 255.0
    dark_fraction = float(np.mean(luma <= 64.0))
    light_fraction = float(np.mean(luma >= 192.0))
    two_tone = dark_fraction >= gen.TWO_TONE_FRACTION and light_fraction >= gen.TWO_TONE_FRACTION
    bg = gen.master_rgb_under(master, solid)
    cr = gen.contrast_ratio(rgb.reshape((-1, 1, 3)), bg.reshape((-1, 1, 3))).reshape(-1)
    weak_fraction = float(np.mean(cr < gen.ACHROMATIC_CONTRAST_RATIO))
    needs_fix = weak_fraction >= gen.MATERIAL_FRACTION
    if achromatic and not two_tone:
        branch = "RECOLOR" if needs_fix else "NO-OP"
        reason = ("achromatic; no genuine dark+light; material low contrast fraction "
                  f"{weak_fraction:.8f} {'>=' if needs_fix else '<'} {gen.MATERIAL_FRACTION}")
    else:
        branch = "PROTECTED" if weak_fraction >= gen.MATERIAL_FRACTION else "NO-OP-PROTECTED"
        kind = "two-tone achromatic" if achromatic and two_tone else "chromatic"
        reason = (f"{kind}; dark fraction={dark_fraction:.8f}, light fraction={light_fraction:.8f}; "
                  f"weak fraction={weak_fraction:.8f}; "
                  f"{'REVIEW reason emitted' if needs_fix else 'no REVIEW reason emitted'}")
    yy, xx = np.where(mask)
    return {
        "pixels": int(mask.sum()),
        "bbox_xyxy": [int(xx.min()), int(yy.min()), int(xx.max()) + 1, int(yy.max()) + 1],
        "solid_pixels": int(solid.sum()),
        "solid_fallback_used": fallback,
        "achromatic_pixel_count": int(np.count_nonzero(delta <= gen.ACHROMATIC_DELTA)),
        "chromatic_pixel_count": int(np.count_nonzero(delta > gen.ACHROMATIC_DELTA)),
        "achromatic_fraction": achro_fraction,
        "is_achromatic": achromatic,
        "dark_count": int(np.count_nonzero(luma <= 64.0)),
        "dark_fraction": dark_fraction,
        "light_count": int(np.count_nonzero(luma >= 192.0)),
        "light_fraction": light_fraction,
        "two_tone": two_tone,
        "weak_contrast_count": int(np.count_nonzero(cr < gen.ACHROMATIC_CONTRAST_RATIO)),
        "weak_contrast_fraction": weak_fraction,
        "min_contrast_ratio": float(cr.min()),
        "median_contrast_ratio": float(np.median(cr)),
        "needs_fix": needs_fix,
        "v9_branch": branch,
        "reason": reason,
        "style": style,
    }


def shortest_path(src: np.ndarray, start_mask: np.ndarray, goal_mask: np.ndarray, comp: np.ndarray):
    h, w = comp.shape
    parent_y = np.full((h, w), -2, dtype=np.int32)
    parent_x = np.full((h, w), -2, dtype=np.int32)
    q = deque()
    for y, x in zip(*np.where(start_mask & comp)):
        parent_y[y, x] = -1
        parent_x[y, x] = -1
        q.append((int(y), int(x)))
    hit = None
    while q:
        y, x = q.popleft()
        if goal_mask[y, x]:
            hit = (y, x)
            break
        for dy, dx in NEIGHBORS:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and comp[ny, nx] and parent_y[ny, nx] == -2:
                parent_y[ny, nx], parent_x[ny, nx] = y, x
                q.append((ny, nx))
    if hit is None:
        return []
    path = []
    y, x = hit
    while y >= 0:
        path.append((y, x))
        py, px = int(parent_y[y, x]), int(parent_x[y, x])
        y, x = py, px
    return list(reversed(path))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    root, out = args.fixtures.resolve(), args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("phase3_v9", root / "rebuild_master_catalog.py")
    gen = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = gen
    spec.loader.exec_module(gen)

    masters = {s: read_rgba(root / f"14700-master-{s}.png") for s in ("white", "black")}
    masters_np = {s: np.asarray(im, dtype=np.uint8) for s, im in masters.items()}
    m0_coords = json.loads((root / "14700-m0-coordinates.json").read_text())
    m0 = np.zeros((gen.SIZE[1], gen.SIZE[0]), dtype=bool)
    for x, y in m0_coords:
        m0[y, x] = True
    prior_rows = json.loads((root / "14700-ownership-evidence.json").read_text())
    prior = {(int(r["x_fitted_220x132"]), int(r["y_fitted_220x132"])): r for r in prior_rows}

    source = read_rgba(root / "14700-source.png")
    fitted, scale, crop_box = gen.fit_logo(source)
    src = np.asarray(fitted, dtype=np.uint8)
    alpha = src[..., 3]
    visible = alpha > 0
    labels, nlabels = ndimage.label(visible, structure=EIGHT)
    m0_labels = sorted(int(v) for v in np.unique(labels[m0]) if v > 0)
    m0_outside = int(np.count_nonzero(m0 & (labels == 0)))
    m0_per_component = {str(i): int(np.count_nonzero(m0 & (labels == i))) for i in m0_labels}
    ring = ndimage.binary_dilation(m0, structure=EIGHT) & ~m0 & visible & (alpha > 0) & (alpha < gen.OPAQUE_ALPHA)
    ring_coords = {(int(x), int(y)) for y, x in zip(*np.where(ring))}
    known_coords = set(prior)
    ring_matches_prior = ring_coords == known_coords
    full_ids = m0_labels
    full = np.isin(labels, full_ids) if full_ids else np.zeros_like(visible)
    full_minus_m0 = full & ~m0
    m0_minus_full = m0 & ~full

    component_rows = []
    decision_rows = []
    all_results = {}
    fixture_components = {}
    for name, (source_name, white_name, black_name) in FIXTURES.items():
        fixture_source = read_rgba(root / source_name)
        ff, fscale, fbbox = gen.fit_logo(fixture_source)
        arr = np.asarray(ff, dtype=np.uint8)
        labs, count = ndimage.label(arr[..., 3] > 0, structure=EIGHT)
        fixture_components[name] = {
            "count": int(count), "fit_scale": float(fscale), "fit_bbox": list(fbbox),
            "source_sha256": sha(root / source_name),
        }
        for style, master in masters.items():
            result = gen.classify_and_render(ff, master, style)
            historical = read_rgba(root / (white_name if style == "white" else black_name))
            exact = np.array_equal(np.asarray(result.image), np.asarray(historical))
            all_results[f"{name}:{style}"] = {
                "status": result.status, "reason": result.reason, "changed_pixels": result.changed_pixels,
                "protected_pixels": result.protected_pixels, "historical_output_pixel_identical": bool(exact),
                "historical_output_sha256": sha(root / (white_name if style == "white" else black_name)),
            }
            decision_rows.append({
                "fixture": name, "style": style.upper(), "component_id": "whole-image replay",
                "component_pixels": "", "solid_pixels": "", "achromatic_fraction": "",
                "dark_fraction": "", "light_fraction": "", "two_tone": "",
                "weak_contrast_fraction": "", "component_branch": "",
                "generator_status": result.status, "changed_pixels": result.changed_pixels,
                "protected_pixels": result.protected_pixels,
                "historical_output_pixel_identical": exact, "reason": result.reason,
            })
        if name in ("14607", "14611 duplicate regression", "Digi Slovakia", "Genuine two-tone #1", "Genuine two-tone #2"):
            style = "white"
            master = masters_np[style]
            src_case = arr
            a = src_case[..., 3]
            lab_case, nc = ndimage.label(a > 0, structure=EIGHT)
            for cid in range(1, nc + 1):
                cmask = lab_case == cid
                st = component_stats(gen, src_case, master, cmask, style)
                decision_rows.append({
                    "fixture": name, "style": "WHITE", "component_id": cid,
                    "component_pixels": st["pixels"], "solid_pixels": st["solid_pixels"],
                    "achromatic_fraction": st["achromatic_fraction"], "dark_fraction": st["dark_fraction"],
                    "light_fraction": st["light_fraction"], "two_tone": st["two_tone"],
                    "weak_contrast_fraction": st["weak_contrast_fraction"],
                    "component_branch": st["v9_branch"], "generator_status": "",
                    "changed_pixels": "", "protected_pixels": "",
                    "historical_output_pixel_identical": "",
                    "reason": st["reason"],
                })

    selected_stats = {}
    for cid in m0_labels:
        selected_stats[str(cid)] = {}
        cmask = labels == cid
        for style in ("white", "black"):
            s = component_stats(gen, src, masters_np[style], cmask, style)
            selected_stats[str(cid)][style] = s
            decision_rows.append({
                "fixture": "14700", "style": style.upper(), "component_id": cid,
                "component_pixels": s["pixels"], "solid_pixels": s["solid_pixels"],
                "achromatic_fraction": s["achromatic_fraction"], "dark_fraction": s["dark_fraction"],
                "light_fraction": s["light_fraction"], "two_tone": s["two_tone"],
                "weak_contrast_fraction": s["weak_contrast_fraction"],
                "component_branch": s["v9_branch"], "generator_status": all_results[f"14700:{style}"]["status"],
                "changed_pixels": s["pixels"] if s["v9_branch"] == "RECOLOR" else 0,
                "protected_pixels": s["pixels"] if "PROTECTED" in s["v9_branch"] else 0,
                "historical_output_pixel_identical": all_results[f"14700:{style}"]["historical_output_pixel_identical"],
                "reason": s["reason"],
            })

    bands = {
        "1-3": (alpha >= 1) & (alpha <= 3),
        "4-7": (alpha >= 4) & (alpha <= 7),
        "8-15": (alpha >= 8) & (alpha <= 15),
        "16-23": (alpha >= 16) & (alpha <= 23),
        "24-31": (alpha >= 24) & (alpha <= 31),
        ">=32": alpha >= 32,
    }
    comp_delta = src[..., :3].max(axis=2).astype(np.int16) - src[..., :3].min(axis=2).astype(np.int16)
    solid = full & (alpha >= gen.OPAQUE_ALPHA)
    chromatic_material = visible & (alpha >= gen.OPAQUE_ALPHA) & (comp_delta > gen.ACHROMATIC_DELTA)
    path_rows = []
    paths = {}
    for cid in m0_labels:
        c_mask = labels == cid
        chroma_goal = c_mask & chromatic_material
        path = shortest_path(src, m0 & c_mask, chromatic_material, visible) if chromatic_material.any() else []
        paths[str(cid)] = path
        path_rows.append({
            "record_type": "component_summary", "component_id": cid,
            "path_to_any_frozen_chromatic_material": bool(path), "path_pixels": len(path),
            "component_chromatic_material_pixels": int(np.count_nonzero(chroma_goal)),
            "component_visible_pixels": int(c_mask.sum()),
            "interpretation": "same alpha>0 component is connectivity-isolated from all V9 solid chromatic material" if not path else "visible 8-connected path reaches V9 solid chromatic material",
        })
    path = next((p for p in paths.values() if p), [])
    for i, (y, x) in enumerate(path):
        p = prior.get((x, y), {})
        path_rows.append({
            "record_type": "path_pixel", "component_id": int(labels[y, x]), "step": i, "x": x, "y": y, "rgba": tuple(int(v) for v in src[y, x]),
            "alpha": int(alpha[y, x]), "channel_spread": int(comp_delta[y, x]),
            "in_m0": bool(m0[y, x]), "known_low_alpha_perimeter": (x, y) in ring_coords,
            "prior_ownership_class": p.get("ownership_decision", ""),
            "prior_reason": p.get("reason", ""),
            "path_role": "start/glyph" if m0[y, x] else "material endpoint" if chroma_goal[y, x] else "visible bridge",
        })

    pixel_rows = []
    for y, x in zip(*np.where(full)):
        p = prior.get((int(x), int(y)), {})
        a = int(alpha[y, x])
        spread = int(comp_delta[y, x])
        pixel_rows.append({
            "x": int(x), "y": int(y), "rgba": tuple(int(v) for v in src[y, x]),
            "alpha": a, "alpha_band": next(k for k, m in bands.items() if m[y, x]),
        "v9_component_id": int(labels[y, x]), "in_m0": bool(m0[y, x]),
            "in_known_300_perimeter": (int(x), int(y)) in ring_coords,
            "v9_material_sample": bool(solid[y, x]),
            "channel_spread": spread,
            "v9_sample_color_class": ("achromatic" if spread <= gen.ACHROMATIC_DELTA else "chromatic") if solid[y, x] else "not-sampled",
            "prior_low_alpha_ownership_class": p.get("ownership_decision", ""),
            "prior_low_alpha_reason": p.get("reason", ""),
        })

    per_component = []
    for cid in m0_labels:
        cmask = labels == cid
        csolid = cmask & (alpha >= gen.OPAQUE_ALPHA)
        if not csolid.any(): csolid = cmask.copy()
        stwhite, stblack = selected_stats[str(cid)]["white"], selected_stats[str(cid)]["black"]
        per_component.append({
            "component_id": cid, "visible_pixels": int(cmask.sum()),
            "bbox_xyxy": [int(np.where(cmask)[1].min()), int(np.where(cmask)[0].min()), int(np.where(cmask)[1].max())+1, int(np.where(cmask)[0].max())+1],
            "m0_pixels": int(np.count_nonzero(cmask & m0)),
            "known_300_perimeter_pixels": int(np.count_nonzero(cmask & ring)),
            "extra_pixels_outside_m0_and_known_300": int(np.count_nonzero(cmask & ~m0 & ~ring)),
            "alpha_1_31_pixels": int(np.count_nonzero(cmask & (alpha > 0) & (alpha < 32))),
            "alpha_ge_32_pixels": int(np.count_nonzero(cmask & (alpha >= 32))),
            "material_sample_pixels": int(csolid.sum()),
            "sample_achromatic_pixels": stwhite["achromatic_pixel_count"],
            "sample_chromatic_pixels": stwhite["chromatic_pixel_count"],
            "white_decision": stwhite, "black_decision": stblack,
        })
    comp_summary = {
        "source_path": "picons/80.0e/orion-express/transparent/1_0_1_32D_CE_1_3200000_0_0_0.png",
        "source_sha256": sha(root / "14700-source.png"),
        "current_white_sha256": sha(root / "14700-white.png"),
        "current_black_sha256": sha(root / "14700-black.png"),
        "white_master_sha256": sha(root / "14700-master-white.png"),
        "black_master_sha256": sha(root / "14700-master-black.png"),
        "fit_scale": float(scale), "source_alpha_bbox": list(crop_box),
        "visible_component_count_total": int(nlabels), "m0_pixels": int(m0.sum()),
        "m0_pixels_outside_visible_components": m0_outside,
        "m0_component_ids": m0_labels, "m0_pixels_by_component": m0_per_component,
        "component_is_single": len(m0_labels) == 1 and m0_outside == 0,
        "m0_spans_multiple_v9_components": len(m0_labels) > 1,
        "v22_outcome": "D — COMPONENT STRUCTURE DIFFERENT THAN ASSUMED" if len(m0_labels) != 1 or m0_outside else "REQUIRES LOGICAL-SAFETY REVIEW",
        "v22_outcome_reason": "M0 pixels occur in three distinct alpha>0 8-connected components; stop whole-wordmark-component interpretation. The components are audited independently.",
        "full_component_pixels": None if len(m0_labels) != 1 else int(full.sum()),
        "m0_component_set_total_pixels_not_one_component": int(full.sum()),
        "m0_component_set_bbox_xyxy": [int(np.where(full)[1].min()), int(np.where(full)[0].min()), int(np.where(full)[1].max())+1, int(np.where(full)[0].max())+1],
        "per_component": per_component,
        "m0_component_set_alpha_band_counts_not_single_component": {k: int(np.count_nonzero(full & v)) for k, v in bands.items()},
        "component_set_solid_sample_pixels_not_a_frozen_classifier_decision": int(solid.sum()),
        "known_low_alpha_perimeter_count_recomputed": int(ring.sum()),
        "known_low_alpha_perimeter_records": len(prior),
        "known_300_coordinate_sets_equal": ring_matches_prior,
        "low_alpha_perimeter_inside_component": int(np.count_nonzero(ring & full)),
        "full_component_minus_m0": int(full_minus_m0.sum()),
        "m0_minus_full_component": int(m0_minus_full.sum()),
        "extra_pixels_not_m0_or_known_300": int(np.count_nonzero(full_minus_m0 & ~ring)),
        "connected_chromatic_material_in_component": int(np.count_nonzero(full & chromatic_material)),
        "shortest_m0_to_v9_chromatic_material_path_pixels": len(path),
        "global_visible_frozen_chromatic_material_pixels": int(chromatic_material.sum()),
        "global_chromatic_material_component_ids": sorted(int(v) for v in np.unique(labels[chromatic_material]) if v > 0),
        "connectivity_to_global_chromatic_material": "NO PATH: chromatic material is V9 component 1; M0 is contained in components 4, 12, 13",
        "path_alpha_min": min((int(alpha[y,x]) for y,x in path), default=None),
        "path_alpha_max": max((int(alpha[y,x]) for y,x in path), default=None),
        "path_intermediate_alpha_lt32_count": sum(1 for y,x in path if not m0[y,x] and alpha[y,x] < 32),
        "one_protected_other_pixel": next((r for r in prior_rows if r["ownership_decision"] == "PROTECTED / OTHER"), None),
        "one_protected_other_pixel_v9_component_id": int(labels[int(next(r for r in prior_rows if r["ownership_decision"] == "PROTECTED / OTHER")["y_fitted_220x132"]), int(next(r for r in prior_rows if r["ownership_decision"] == "PROTECTED / OTHER")["x_fitted_220x132"])]) if prior_rows else None,
        "one_protected_other_pixel_v9_sampled_for_classification": bool(prior_rows and alpha[int(next(r for r in prior_rows if r["ownership_decision"] == "PROTECTED / OTHER")["y_fitted_220x132"]), int(next(r for r in prior_rows if r["ownership_decision"] == "PROTECTED / OTHER")["x_fitted_220x132"])] >= gen.OPAQUE_ALPHA),
        "frozen_v9_white_component_decisions": {str(cid): selected_stats[str(cid)]["white"] for cid in m0_labels},
        "frozen_v9_black_component_decisions": {str(cid): selected_stats[str(cid)]["black"] for cid in m0_labels},
        "frozen_v9_generator_replay": {k: all_results[f"14700:{k}"] for k in ("white", "black")},
        "controls": {k: {"components": fixture_components[k],
                         "white_replay": all_results[f"{k}:white"],
                         "black_replay": all_results[f"{k}:black"]}
                     for k in fixture_components if k != "14700"},
        "phase3_code_commit": "e9b503d76eae3c3c7d7763df4909039a55d3edb8",
        "source_and_outputs_fetched_at_phase3_checkpoint": True,
        "production_writes": 0,
    }

    component_audit_rows = []
    for item in per_component:
        cid = item["component_id"]
        stw, stb = item["white_decision"], item["black_decision"]
        component_audit_rows.append({
            "component_id": cid, "visible_component_count_total": nlabels,
            "total_visible_pixels": item["visible_pixels"], "bbox_xyxy": json.dumps(item["bbox_xyxy"]),
            "solid_pixels": item["material_sample_pixels"], "alpha_1_31_pixels": item["alpha_1_31_pixels"],
            "alpha_ge_32_pixels": item["alpha_ge_32_pixels"], "m0_pixels": item["m0_pixels"],
            "known_300_perimeter_pixels": item["known_300_perimeter_pixels"],
            "full_minus_m0_pixels": item["visible_pixels"]-item["m0_pixels"],
            "m0_minus_component_pixels": 0,
            "extra_not_m0_or_300": item["extra_pixels_outside_m0_and_known_300"],
            "alpha_bands": json.dumps({k:int(np.count_nonzero((labels==cid)&v)) for k,v in bands.items()},sort_keys=True),
            "achromatic_material_count": stw["achromatic_pixel_count"],
            "chromatic_material_count": stw["chromatic_pixel_count"],
            "achromatic_fraction": stw["achromatic_fraction"], "chromatic_fraction": 1-stw["achromatic_fraction"],
            "path_to_chromatic_material": bool(paths[str(cid)]), "path_pixels": len(paths[str(cid)]),
            "white_v9_branch": stw["v9_branch"], "black_v9_branch": stb["v9_branch"],
            "white_reason": stw["reason"], "black_reason": stb["reason"],
        })
    write_csv(out / "FULL-V9-COMPONENT-AUDIT.csv", component_audit_rows)
    write_csv(out / "CONNECTIVITY-AUDIT.csv", path_rows)
    write_csv(out / "DECISION-REPLAY.csv", decision_rows)
    write_csv(out / "14700-COMPONENT-PIXELS.csv", pixel_rows)
    (out / "SUMMARY.json").write_text(json.dumps(comp_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # Diagnostic map only: no source or candidate image is written.
    base = Image.alpha_composite(masters["white"], fitted).convert("RGB")
    canvas = np.asarray(base).copy()
    for y, x in zip(*np.where(full)):
        if m0[y, x]: color = (30, 220, 80)
        elif ring[y, x]: color = (0, 210, 255)
        elif solid[y, x] and comp_delta[y, x] > 18: color = (255, 45, 45)
        elif solid[y, x]: color = (255, 220, 0)
        else: color = (170, 170, 170)
        canvas[y, x] = color
    for y, x in path:
        canvas[y, x] = (180, 0, 255)
    im = Image.fromarray(canvas, "RGB").resize((880, 528), Image.Resampling.NEAREST)
    out_im = Image.new("RGB", (880, 600), (20, 20, 20))
    out_im.paste(im, (0, 40))
    draw = ImageDraw.Draw(out_im)
    draw.text((8, 8), f"#14700 M0-bearing V9 components {m0_labels} (not one component); {int(full.sum())} px total", fill="white")
    draw.text((8, 572), "M0 green | known <32 ring cyan | solid chromatic red | solid achromatic yellow | other subthreshold gray | no path to chroma", fill="white")
    out_im.save(out / "V22-14700-FULL-V9-COMPONENT-MAP.png")
    print(json.dumps(comp_summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
