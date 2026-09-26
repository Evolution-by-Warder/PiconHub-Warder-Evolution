#!/usr/bin/env python3
"""Run only the original V10 mixed-logo failures with the frozen V9 gates.

The script reads the repository's transparent sources, current WHITE outputs,
and immutable white MASTER. It writes candidates and comparisons only under an
external --output-dir, and refuses a destination within the production picons.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

SIZE = (220, 132)
OPAQUE_ALPHA = 32
ACHROMATIC_DELTA = 18
ACHROMATIC_REQUIRED = 0.985
ACHROMATIC_CONTRAST_RATIO = 2.50
MATERIAL_FRACTION = 0.08
TWO_TONE_FRACTION = 0.03
SAFE_MARGIN_X, SAFE_MARGIN_Y = 8, 8
RECOLOUR_DARK = np.array([16, 16, 16], dtype=np.uint8)
WHITE_MASTER_SHA256 = "c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589"
FOUR = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=np.uint8)
EIGHT = np.ones((3, 3), dtype=np.uint8)

CASES = [
    {"case": "#14607", "key": "14607", "review_index": 14607,
     "source": "picons/80.0e/orion-express/transparent/1_0_1_2C8_CD_1_3200000_0_0_0.png",
     "current": "picons/80.0e/orion-express/white/1_0_1_2C8_CD_1_3200000_0_0_0.png",
     "duplicate_of": "", "probe_only": False},
    {"case": "#14611", "key": "14611", "review_index": 14611,
     "source": "picons/80.0e/orion-express/transparent/1_0_1_2CA_CD_1_3200000_0_0_0.png",
     "current": "picons/80.0e/orion-express/white/1_0_1_2CA_CD_1_3200000_0_0_0.png",
     "duplicate_of": "#14607", "probe_only": False},
    {"case": "#14700", "key": "14700", "review_index": 14700,
     "source": "picons/80.0e/orion-express/transparent/1_0_1_32D_CE_1_3200000_0_0_0.png",
     "current": "picons/80.0e/orion-express/white/1_0_1_32D_CE_1_3200000_0_0_0.png",
     "duplicate_of": "", "probe_only": False},
    {"case": "#14593", "key": "14593", "review_index": 14593,
     "source": "picons/80.0e/orion-express/transparent/1_0_1_2C1_CD_1_3200000_0_0_0.png",
     "current": "picons/80.0e/orion-express/white/1_0_1_2C1_CD_1_3200000_0_0_0.png",
     "duplicate_of": "", "probe_only": False},
    {"case": "#14597", "key": "14597", "review_index": 14597,
     "source": "picons/80.0e/orion-express/transparent/1_0_1_2C3_CD_1_3200000_0_0_0.png",
     "current": "picons/80.0e/orion-express/white/1_0_1_2C3_CD_1_3200000_0_0_0.png",
     "duplicate_of": "", "probe_only": True},
    {"case": "PASS-control", "key": "pass", "review_index": "",
     "source": "picons/0.8w/digislovakia/transparent/1_0_16_3F6_AF1_BB_E080000_0_0_0.png",
     "current": "picons/0.8w/digislovakia/white/1_0_16_3F6_AF1_BB_E080000_0_0_0.png",
     "duplicate_of": "", "probe_only": False},
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def open_rgba(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        im.load()
        if im.format != "PNG" or im.size != SIZE:
            raise ValueError(f"invalid fixture {path}: {im.format} {im.size}")
        return np.array(im.convert("RGBA"), dtype=np.uint8)


def fit_logo(source: np.ndarray) -> tuple[np.ndarray, float, tuple[int, int, int, int]]:
    im = Image.fromarray(source, "RGBA")
    bbox = im.getchannel("A").getbbox()
    if bbox is None:
        return source.copy(), 1.0, (0, 0, 0, 0)
    crop = im.crop(bbox)
    scale = min(1.0, (SIZE[0] - 2 * SAFE_MARGIN_X) / crop.width,
                (SIZE[1] - 2 * SAFE_MARGIN_Y) / crop.height)
    size = (max(1, round(crop.width * scale)), max(1, round(crop.height * scale)))
    if size != crop.size:
        crop = crop.resize(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    canvas.alpha_composite(crop, ((SIZE[0] - crop.width) // 2,
                                  (SIZE[1] - crop.height) // 2))
    return np.array(canvas, dtype=np.uint8), scale, bbox


def rel_luma(rgb: np.ndarray) -> np.ndarray:
    x = rgb.astype(np.float32) / 255.0
    x = np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
    return x[..., 0] * 0.2126 + x[..., 1] * 0.7152 + x[..., 2] * 0.0722


def render_case(root: Path, out: Path, case: dict, master: np.ndarray) -> tuple[dict, Image.Image, np.ndarray]:
    src_bytes = (root / case["source"]).read_bytes()
    current_bytes = (root / case["current"]).read_bytes()
    source = open_rgba(root / case["source"])
    current = open_rgba(root / case["current"])
    fitted, scale, bbox = fit_logo(source)
    alpha = fitted[..., 3]
    visible = alpha > 0
    solid = alpha >= OPAQUE_ALPHA
    rgb = fitted[..., :3]
    delta = rgb.max(axis=2).astype(np.int16) - rgb.min(axis=2).astype(np.int16)

    achro_core = solid & (delta <= ACHROMATIC_DELTA)
    chroma_core = solid & (delta > ACHROMATIC_DELTA)
    achro_labels, achro_n = ndimage.label(achro_core, structure=FOUR)
    chroma_labels, chroma_n = ndimage.label(chroma_core, structure=EIGHT)
    protected_chroma = chroma_core
    all_chroma_neighborhood = ndimage.binary_dilation(chroma_core, structure=EIGHT) & visible
    protected_boundary = all_chroma_neighborhood & ~protected_chroma
    protected = protected_chroma | protected_boundary

    # Low-alpha/transparent pixels are ambiguous and never become editable.
    # Their 8-connected exterior-reachable class is used only as positive
    # evidence that an achromatic core is on the MASTER, outside a filled badge.
    ambiguous = alpha < OPAQUE_ALPHA
    amb_labels, amb_n = ndimage.label(ambiguous, structure=EIGHT)
    border_labels = set(np.unique(np.concatenate((amb_labels[0, :], amb_labels[-1, :],
                                                  amb_labels[:, 0], amb_labels[:, -1]))))
    exterior_ambiguous = np.isin(amb_labels, list(border_labels)) & ambiguous

    # Frozen MASTER compositing convention used by V9.
    master_rgb = master[..., :3].astype(np.float32)
    master_alpha = master[..., 3:4].astype(np.float32) / 255.0
    bg = np.rint(master_rgb * master_alpha).astype(np.uint8)
    candidate_layer = fitted.copy()
    proposed_mask = np.zeros(visible.shape, dtype=bool)
    accepted_labels: list[int] = []
    decisions: list[str] = []
    rejected = 0
    contrast_relevant = 0
    for idx in range(1, achro_n + 1):
        comp = achro_labels == idx
        vals = rgb[comp]
        if not vals.size:
            continue
        achro_fraction = float(np.mean(delta[comp] <= ACHROMATIC_DELTA))
        lums = rel_luma(vals.reshape((-1, 1, 3))).reshape(-1) * 255.0
        two_tone = (float(np.mean(lums <= 64.0)) >= TWO_TONE_FRACTION and
                    float(np.mean(lums >= 192.0)) >= TWO_TONE_FRACTION)
        bgs = bg[comp].astype(np.float32) / 255.0
        fgs = vals.astype(np.float32) / 255.0
        lf = rel_luma(fgs.reshape((-1, 1, 3))).reshape(-1)
        lb = rel_luma(bgs.reshape((-1, 1, 3))).reshape(-1)
        ratio = (np.maximum(lf, lb) + 0.05) / (np.minimum(lf, lb) + 0.05)
        low_fraction = float(np.mean(ratio < ACHROMATIC_CONTRAST_RATIO))
        needs_fix = low_fraction >= MATERIAL_FRACTION
        if not needs_fix:
            decisions.append(f"{idx}:readable({low_fraction:.3f})")
            continue
        contrast_relevant += 1
        touches_protected = bool(np.any(comp & protected))
        # Require a topological path through only ambiguous pixels to the
        # exterior. This prevents editing light lettering enclosed by a badge.
        comp_ring = ndimage.binary_dilation(comp, structure=EIGHT) & ~comp
        exterior_contact = bool(np.any(comp_ring & exterior_ambiguous))
        if achro_fraction < ACHROMATIC_REQUIRED:
            rejected += 1; decisions.append(f"{idx}:REVIEW-class-fraction({achro_fraction:.3f})"); continue
        if two_tone:
            rejected += 1; decisions.append(f"{idx}:REVIEW-two-tone"); continue
        if touches_protected:
            rejected += 1; decisions.append(f"{idx}:REVIEW-protected-boundary"); continue
        if not exterior_contact:
            rejected += 1; decisions.append(f"{idx}:REVIEW-no-exterior-alpha-topology"); continue
        proposed_mask |= comp
        accepted_labels.append(idx)
        decisions.append(f"{idx}:ACCEPT-separated-exterior-achromatic({low_fraction:.3f})")

    locally_separated_count = len(accepted_labels)
    locally_proposed_core_pixel_count = int(proposed_mask.sum())
    locally_proposed_rgb_changed_pixels = int(np.count_nonzero(
        proposed_mask & np.any(candidate_layer[..., :3] != RECOLOUR_DARK, axis=2)))
    incomplete_case = bool(rejected and locally_separated_count)
    if incomplete_case:
        # Do not recolour only a fragment of a logical wordmark when another
        # contrast-relevant achromatic core remains ambiguous or protected.
        proposed_mask[:] = False
        accepted_labels = []
        decisions.append("CASE:REVIEW-incomplete-wordmark-separation")
    changed_mask = proposed_mask & np.any(candidate_layer[..., :3] != RECOLOUR_DARK, axis=2)
    candidate_layer[..., :3][proposed_mask] = RECOLOUR_DARK
    alpha_equal = bool(np.array_equal(candidate_layer[..., 3], fitted[..., 3]))
    protected_chroma_equal = bool(np.array_equal(candidate_layer[protected_chroma], fitted[protected_chroma]))
    protected_boundary_equal = bool(np.array_equal(candidate_layer[protected_boundary], fitted[protected_boundary]))
    intersects_protected = bool(np.any(proposed_mask & protected))
    if not (alpha_equal and protected_chroma_equal and protected_boundary_equal) or intersects_protected:
        raise RuntimeError(f"hard preservation invariant failed: {case['case']}")
    if case["case"] == "PASS-control" and changed_mask.any():
        raise RuntimeError("PASS control changed")

    candidate_composite = Image.alpha_composite(Image.fromarray(master, "RGBA"),
                                                Image.fromarray(candidate_layer, "RGBA"))
    # Keep current output exactly for cases with no accepted edit; candidates
    # are never emitted into the production tree.
    if not accepted_labels:
        candidate_composite = Image.fromarray(current, "RGBA")
    candidate_path = out / "candidates" / f"{case['key']}-white.png"
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_composite.save(candidate_path, format="PNG")
    candidate_img = candidate_composite.convert("RGBA")
    current_px = np.array(Image.fromarray(current, "RGBA"), dtype=np.uint8)
    candidate_px = np.array(candidate_img, dtype=np.uint8)
    candidate_current_diff = np.any(current_px != candidate_px, axis=2)
    actual_changes = int(changed_mask.sum())
    if case["case"] == "PASS-control":
        status = "PASS"
        reason = "PASS control preserved exactly with 0 candidate-vs-current changed pixels"
    elif case["probe_only"]:
        status = "REVIEW"
        reason = "cautious probe only: any gold/brand or badge-integrated content is protected; no automatic decision promoted"
    elif actual_changes:
        status = "ACCEPT"
        reason = "exterior-reachable achromatic core(s) passed frozen V9 contrast gates; proposed mask is disjoint from protected chroma/boundary"
    elif rejected:
        status = "REVIEW"
        reason = "contrast-relevant achromatic component(s) could not be separated from protected boundary/badge topology"
    else:
        status = "REVIEW"
        reason = "no contrast-relevant, safely separated achromatic core produced a repair"

    row = {
        "case_number": case["case"], "review_index": case["review_index"],
        "source_path": case["source"], "current_white_path": case["current"],
        "source_sha256": digest(src_bytes), "current_white_sha256": digest(current_bytes),
        "candidate_path": candidate_path.relative_to(out).as_posix(),
        "candidate_sha256": digest(candidate_path.read_bytes()),
        "duplicate_relationship": case["duplicate_of"],
        "source_duplicate_group": "#14607/#14611" if case["case"] in ("#14607", "#14611") else "",
        "changed_achromatic_core_pixels": actual_changes,
        "locally_proposed_core_pixels_before_case_gate": locally_proposed_core_pixel_count,
        "locally_proposed_rgb_changed_pixels_before_case_gate": locally_proposed_rgb_changed_pixels,
        "candidate_vs_current_changed_pixels": int(candidate_current_diff.sum()),
        "alpha_equality": alpha_equal,
        "source_alpha_unchanged_after_frozen_fit": alpha_equal,
        "protected_chromatic_equality": protected_chroma_equal,
        "protected_AA_boundary_equality": protected_boundary_equal,
        "protected_chromatic_pixel_count": int(protected_chroma.sum()),
        "protected_AA_boundary_pixel_count": int(protected_boundary.sum()),
        "achromatic_component_count": int(achro_n),
        "chromatic_component_count": int(chroma_n),
        "accepted_separated_component_count": len(accepted_labels),
        "locally_separated_component_count_before_case_gate": locally_separated_count,
        "case_level_partial_mask_rejected": incomplete_case,
        "rejected_ambiguous_component_count": rejected,
        "contrast_relevant_component_count": contrast_relevant,
        "ambiguous_low_alpha_pixel_count": int((visible & (alpha < OPAQUE_ALPHA)).sum()),
        "edit_mask_subset_of_accepted_components": bool(np.all(~proposed_mask | np.isin(achro_labels, accepted_labels))),
        "edit_mask_protected_intersection_pixels": int(np.count_nonzero(proposed_mask & protected)),
        "fit_scale": f"{scale:.8f}", "fit_bbox": ",".join(map(str, bbox)),
        "status": status, "reason": reason, "component_decisions": ";".join(decisions),
    }
    return row, candidate_img, source


def panel(source: np.ndarray, current_path: Path, candidate: Image.Image, label: str) -> Image.Image:
    sheet = Image.new("RGB", (660, 176), (28, 28, 28))
    checker = Image.new("RGBA", SIZE, (94, 94, 94, 255))
    d = ImageDraw.Draw(checker)
    for y in range(0, SIZE[1], 12):
        for x in range(0, SIZE[0], 12):
            if (x // 12 + y // 12) % 2:
                d.rectangle((x, y, x + 11, y + 11), fill=(132, 132, 132, 255))
    checker.alpha_composite(Image.fromarray(source, "RGBA"))
    with Image.open(current_path) as im:
        current = im.convert("RGBA")
    sheet.paste(checker.convert("RGB"), (0, 0))
    sheet.paste(current.convert("RGB"), (220, 0))
    sheet.paste(candidate.convert("RGB"), (440, 0))
    draw = ImageDraw.Draw(sheet)
    draw.text((4, 139), f"{label}  SOURCE | CURRENT WHITE | CANDIDATE", fill="white")
    return sheet


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=Path.cwd())
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()
    root, out = args.root.resolve(), args.output_dir.resolve()
    try:
        out.relative_to((root / "picons").resolve())
    except ValueError:
        pass
    else:
        raise SystemExit("refusing to write experiment candidates inside production picons")
    out.mkdir(parents=True, exist_ok=True)
    with Image.open(root / "templates/picons/white-sablona.png") as m:
        m.load()
        if m.format != "PNG" or m.size != SIZE or m.mode != "RGBA":
            raise SystemExit("invalid immutable WHITE MASTER fixture")
        master = np.array(m, dtype=np.uint8)
    master_sha = digest((root / "templates/picons/white-sablona.png").read_bytes())
    if master_sha != WHITE_MASTER_SHA256:
        raise SystemExit("immutable WHITE MASTER SHA256 mismatch")

    results: dict[str, tuple[dict, Image.Image, np.ndarray]] = {}
    rows = []
    for case in CASES:
        if case["duplicate_of"] and case["duplicate_of"] in results:
            primary = results[case["duplicate_of"].replace("#", "")]
            source_hash = digest((root / case["source"]).read_bytes())
            current_hash = digest((root / case["current"]).read_bytes())
            if source_hash != primary[0]["source_sha256"]:
                raise RuntimeError("declared duplicate is not byte-identical source")
            # Reuse the primary candidate, but preserve the duplicate service
            # reference as its own artifact and independently audit its current.
            img = primary[1].copy()
            candidate_path = out / "candidates" / f"{case['key']}-white.png"
            img.save(candidate_path, format="PNG")
            cpix = np.array(img.convert("RGBA"), dtype=np.uint8)
            cur = np.array(open_rgba(root / case["current"]), dtype=np.uint8)
            diff = int(np.any(cpix != cur, axis=2).sum())
            row = dict(primary[0])
            row.update({
                "case_number": case["case"], "review_index": case["review_index"],
                "source_path": case["source"], "current_white_path": case["current"],
                "source_sha256": source_hash, "current_white_sha256": current_hash,
                "candidate_path": candidate_path.relative_to(out).as_posix(),
                "candidate_sha256": digest(candidate_path.read_bytes()),
                "duplicate_relationship": "byte-identical source; candidate reused from #14607 and not recomputed",
                "candidate_vs_current_changed_pixels": diff,
                "status": "ACCEPT" if primary[0]["status"] == "ACCEPT" else "REVIEW",
                "reason": "duplicate regression check: identical source and exact reused candidate; status follows primary case",
            })
            results[case["key"]] = (row, img, primary[2])
            rows.append(row)
            continue
        row, img, src = render_case(root, out, case, master)
        results[case["key"]] = (row, img, src)
        rows.append(row)

    # Byte-level duplicate and candidate checks are explicit preconditions.
    r0, r1 = results["14607"][0], results["14611"][0]
    if r0["source_sha256"] != r1["source_sha256"] or r0["candidate_sha256"] != r1["candidate_sha256"]:
        raise RuntimeError("#14607/#14611 duplicate regression mismatch")
    if r0["current_white_sha256"] != r1["current_white_sha256"]:
        raise RuntimeError("byte-identical sources have different current WHITE outputs")
    if any(r["candidate_vs_current_changed_pixels"] != 0 for r in rows if r["case_number"] == "PASS-control"):
        raise RuntimeError("PASS control differs from current")

    fields = list(rows[0].keys())
    with (out / "AUDIT.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader(); w.writerows(rows)
    summary = {
        "experiment": "original V10 mixed-logo failures; color-class topology; no production writes",
        "branch_expected": "phase4-v10-component-mask-test",
        "frozen_v9_thresholds": {"opaque_alpha": OPAQUE_ALPHA, "achromatic_delta": ACHROMATIC_DELTA,
             "achromatic_required": ACHROMATIC_REQUIRED, "contrast_ratio": ACHROMATIC_CONTRAST_RATIO,
             "material_fraction": MATERIAL_FRACTION, "two_tone_fraction": TWO_TONE_FRACTION,
             "recolor_rgb": RECOLOUR_DARK.tolist()},
        "white_master_sha256": master_sha,
        "duplicate_check": {"cases": ["#14607", "#14611"], "source_byte_identical": True,
                            "current_white_byte_identical": True, "candidate_computed_once": True},
        "rows": rows,
    }
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    panels = []
    grouped = [("#14607 / #14611 duplicate pair", "14607"), ("#14700", "14700"),
               ("#14593", "14593"), ("#14597 cautious probe", "14597"), ("PASS control", "pass")]
    for label, key in grouped:
        case = next(c for c in CASES if c["key"] == key)
        src = results[key][2]
        img = results[key][1]
        p = panel(src, root / case["current"], img, label)
        p.save(out / f"CASE-{key}-COMPARISON.jpg", quality=96)
        panels.append(p)
    contact = Image.new("RGB", (660, len(panels) * 176), (25, 25, 25))
    for i, p in enumerate(panels):
        contact.paste(p, (0, i * 176))
    contact.save(out / "COMPARISON-SHEET.jpg", quality=96)
    print(json.dumps(rows, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
