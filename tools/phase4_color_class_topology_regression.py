#!/usr/bin/env python3
"""Isolated V9-threshold color-class topology experiment for five fixtures.

This script is intentionally scoped to the regression sample copied from the
GitHub test branch. It does not read or write the repository production tree.
"""
from __future__ import annotations

import csv
import argparse
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
RECOLOUR = np.array([16, 16, 16], dtype=np.uint8)
FOUR = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=np.uint8)
EIGHT = np.ones((3, 3), dtype=np.uint8)

CASES = [
    ("#11359", "turksat"),
    ("#5136", "ard"),
    ("#14406", "harmonic"),
    ("#10954", "demiroren"),
    ("PASS-control", "digislovakia"),
]
FIXTURE_PATHS = {
    "turksat": ("picons/42.0e/turksat/transparent/1_0_1_C740_EC55_42E_1A40000_0_0_0.png", "picons/42.0e/turksat/white/1_0_1_C740_EC55_42E_1A40000_0_0_0.png"),
    "ard": ("picons/19.2e/ard-ndr/transparent/1_0_A_28D6_40F_1_C00000_0_0_0.png", "picons/19.2e/ard-ndr/white/1_0_A_28D6_40F_1_C00000_0_0_0.png"),
    "harmonic": ("picons/80.0e/harmonic/transparent/1_0_1_21_14_1113_3200000_0_0_0.png", "picons/80.0e/harmonic/white/1_0_1_21_14_1113_3200000_0_0_0.png"),
    "demiroren": ("picons/42.0e/demiroren-medya/transparent/1_0_2_2C57_3_42_1A40000_0_0_0.png", "picons/42.0e/demiroren-medya/white/1_0_2_2C57_3_42_1A40000_0_0_0.png"),
    "digislovakia": ("picons/0.8w/digislovakia/transparent/1_0_16_3F6_AF1_BB_E080000_0_0_0.png", "picons/0.8w/digislovakia/white/1_0_16_3F6_AF1_BB_E080000_0_0_0.png"),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def arr(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        im.load()
        if im.size != SIZE:
            raise ValueError(f"{path} is {im.size}, expected {SIZE}")
        return np.array(im.convert("RGBA"), dtype=np.uint8)


def fit_logo(source: np.ndarray) -> tuple[np.ndarray, float, tuple[int, int, int, int]]:
    im = Image.fromarray(source, "RGBA")
    bbox = im.getchannel("A").getbbox()
    if bbox is None:
        return source.copy(), 1.0, (0, 0, 0, 0)
    crop = im.crop(bbox)
    scale = min(1.0, 204 / crop.width, 116 / crop.height)
    new_size = (max(1, round(crop.width * scale)), max(1, round(crop.height * scale)))
    if new_size != crop.size:
        crop = crop.resize(new_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    canvas.alpha_composite(crop, ((220 - crop.width) // 2, (132 - crop.height) // 2))
    return np.array(canvas, dtype=np.uint8), scale, bbox


def rel_luma(rgb: np.ndarray) -> np.ndarray:
    x = rgb.astype(np.float32) / 255.0
    x = np.where(x <= .04045, x / 12.92, ((x + .055) / 1.055) ** 2.4)
    return x[..., 0] * .2126 + x[..., 1] * .7152 + x[..., 2] * .0722


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root")
    parser.add_argument("--output-dir", type=Path, required=True, help="isolated output directory outside production picons")
    args = parser.parse_args()
    root = args.root.resolve()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    master = arr(root / "templates/picons/white-sablona.png")
    rows = []
    sheet = Image.new("RGB", (660, len(CASES) * 176), (30, 30, 30))
    draw = ImageDraw.Draw(sheet)

    for row_i, (case_id, key) in enumerate(CASES):
        source_rel, current_rel = FIXTURE_PATHS[key]
        src_raw = arr(root / source_rel)
        current = arr(root / current_rel)
        fitted, scale, bbox = fit_logo(src_raw)
        a = fitted[..., 3]
        visible = a > 0
        solid = a >= OPAQUE_ALPHA
        rgb = fitted[..., :3]
        delta = rgb.max(axis=2).astype(np.int16) - rgb.min(axis=2).astype(np.int16)

        # Color classes follow the frozen V9 per-pixel color boundary. Pixels
        # below the V9 opaque-alpha floor are ambiguous and never join a class.
        achro_core = solid & (delta <= ACHROMATIC_DELTA)
        chroma_core = solid & (delta > ACHROMATIC_DELTA)
        achro_labels, achro_count = ndimage.label(achro_core, structure=FOUR)
        chroma_labels, chroma_count = ndimage.label(chroma_core, structure=EIGHT)

        # Protect chromatic core and its immediate visible AA/boundary ring.
        # The ring is a topological neighborhood only; it is never recolored.
        chroma_neighborhood = ndimage.binary_dilation(chroma_core, structure=EIGHT) & visible
        protected = chroma_neighborhood
        ambiguous = visible & ~solid
        ambiguous_near_chroma = ambiguous & ndimage.binary_dilation(chroma_core, structure=EIGHT)

        candidate = fitted.copy()
        changed_mask = np.zeros(visible.shape, dtype=bool)
        accepted = 0
        rejected = 0
        component_types = []
        lumas = rel_luma(rgb)
        master_rgb = master[..., :3].astype(np.float32)
        master_alpha = master[..., 3].astype(np.float32) / 255.0
        bg = np.rint(master_rgb * master_alpha[..., None]).astype(np.uint8)

        for idx in range(1, achro_count + 1):
            comp = achro_labels == idx
            pixels = rgb[comp]
            if not pixels.size:
                continue
            achro_fraction = float(np.mean(delta[comp] <= ACHROMATIC_DELTA))
            if achro_fraction < ACHROMATIC_REQUIRED:
                rejected += 1
                component_types.append("rejected-noncoherent-achromatic")
                continue
            lum = lumas[comp] * 255.0
            two_tone = (float(np.mean(lum <= 64.0)) >= TWO_TONE_FRACTION and
                        float(np.mean(lum >= 192.0)) >= TWO_TONE_FRACTION)
            # Frozen V9 contrast and materiality tests; WHITE uses the same
            # compositing convention as the production generator.
            p_bg = bg[comp].astype(np.float32) / 255.0
            p_rgb = pixels.astype(np.float32) / 255.0
            l1 = rel_luma(p_rgb.reshape((-1, 1, 3))).reshape(-1)
            l2 = rel_luma(p_bg.reshape((-1, 1, 3))).reshape(-1)
            ratio = (np.maximum(l1, l2) + .05) / (np.minimum(l1, l2) + .05)
            needs_fix = float(np.mean(ratio < ACHROMATIC_CONTRAST_RATIO)) >= MATERIAL_FRACTION
            if two_tone or not needs_fix:
                component_types.append("ambiguous-two-tone" if two_tone else "achromatic-readable")
                if two_tone:
                    rejected += 1
                continue

            # A candidate is rejected if it would touch any protected chroma
            # core/AA pixel. The only editable class is the separate achromatic
            # core; low-alpha bridges are excluded from topology and editing.
            touches_protected = bool(np.any(comp & protected))
            if touches_protected:
                rejected += 1
                component_types.append("rejected-protected-boundary")
                continue
            candidate[..., :3][comp] = RECOLOUR
            changed_mask |= comp
            accepted += 1
            component_types.append("separated-achromatic-core")

        # Fail closed on all hard invariants.
        alpha_equal = bool(np.array_equal(candidate[..., 3], fitted[..., 3]))
        protected_equal = bool(np.array_equal(candidate[protected], fitted[protected]))
        if not alpha_equal or not protected_equal:
            raise RuntimeError(f"hard invariant failed for {case_id}")
        if case_id == "PASS-control" and int(changed_mask.sum()) != 0:
            raise RuntimeError("PASS control changed")

        composed = (Image.alpha_composite(Image.fromarray(master, "RGBA"), Image.fromarray(candidate, "RGBA"))
                    if accepted else Image.fromarray(current, "RGBA"))
        candidate_path = out / f"{key}-candidate.png"
        composed.save(candidate_path, format="PNG")
        candidate_bytes = candidate_path.read_bytes()
        current_rgba = Image.fromarray(current, "RGBA")
        candidate_rgba = composed.convert("RGBA")
        current_px = np.array(current_rgba, dtype=np.uint8)
        candidate_px = np.array(candidate_rgba, dtype=np.uint8)
        diff_current = np.any(current_px != candidate_px, axis=2)
        cur_path = root / current_rel
        src_path = root / source_rel
        rows.append({
            "case": case_id,
            "source_path": source_rel,
            "source_sha256": sha(src_path.read_bytes()),
            "current_output_sha256": sha(cur_path.read_bytes()),
            "candidate_sha256": sha(candidate_bytes),
            "changed_pixels": int(changed_mask.sum()),
            "candidate_vs_current_changed_pixels": int(diff_current.sum()),
            "candidate_vs_current_max_channel_delta": int(np.abs(current_px.astype(np.int16) - candidate_px.astype(np.int16)).max()),
            "alpha_equal": alpha_equal,
            "protected_chromatic_and_AA_pixels_equal": protected_equal,
            "protected_pixel_count": int(protected.sum()),
            "chromatic_core_components": int(chroma_count),
            "achromatic_core_components": int(achro_count),
            "separated_achromatic_components": accepted,
            "ambiguous_or_rejected_components": rejected,
            "ambiguous_low_alpha_pixels": int(ambiguous.sum()),
            "ambiguous_low_alpha_pixels_near_chroma": int(ambiguous_near_chroma.sum()),
            "component_decisions": ";".join(component_types),
            "fit_scale": f"{scale:.8f}",
            "fit_bbox": ",".join(map(str, bbox)),
            "topology_candidate_status": "CANDIDATE-GENERATED" if accepted else "NO-CANDIDATE",
            "status": "REVIEW" if accepted or rejected else "PASS",
            "reason": ("topology-safe candidate generated, but no visually new repair versus current WHITE was established; keep REVIEW" if accepted
                       else "no safely separated, material low-contrast achromatic core; remain REVIEW" if rejected
                       else "no contrast edit required"),
        })

        # Comparison canvas: source over checker, current WHITE, candidate.
        y = row_i * 176
        checker = Image.new("RGBA", SIZE, (92, 92, 92, 255))
        cd = ImageDraw.Draw(checker)
        for yy in range(0, SIZE[1], 12):
            for xx in range(0, SIZE[0], 12):
                if (xx // 12 + yy // 12) % 2:
                    cd.rectangle((xx, yy, xx + 11, yy + 11), fill=(132, 132, 132, 255))
        checker.alpha_composite(Image.fromarray(src_raw, "RGBA"))
        sheet.paste(checker.convert("RGB"), (0, y))
        sheet.paste(Image.fromarray(current, "RGBA").convert("RGB"), (220, y))
        sheet.paste(composed.convert("RGB"), (440, y))
        draw.text((4, y + 138), f"{case_id} {key}: SOURCE | CURRENT WHITE | COLOR-TOPOLOGY CANDIDATE", fill="white")

    with (out / "audit.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    (out / "summary.json").write_text(json.dumps({
        "algorithm": "V9 threshold color-class topology; 4-connected achromatic core; 8-connected chromatic core; low-alpha excluded; protected chromatic core plus visible 8-neighbor boundary ring",
        "frozen_v9_thresholds": {"opaque_alpha": OPAQUE_ALPHA, "achromatic_delta": ACHROMATIC_DELTA,
            "achromatic_required": ACHROMATIC_REQUIRED, "contrast_ratio": ACHROMATIC_CONTRAST_RATIO,
            "material_fraction": MATERIAL_FRACTION, "two_tone_fraction": TWO_TONE_FRACTION},
        "rows": rows,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sheet.save(out / "comparison.jpg", quality=96)
    print(json.dumps(rows, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
