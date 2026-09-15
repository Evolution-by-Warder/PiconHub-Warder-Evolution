#!/usr/bin/env python3
"""Rebuild BLACK/WHITE picons from immutable transparent sources and masters.

The classifier is deliberately conservative.  It only recolours a complete
8-connected achromatic component.  A chromatic component is never modified;
if it contains a material light/dark region that can disappear on a master,
the source is classified REVIEW and the untouched-colour candidate is emitted.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


SIZE = (220, 132)
SERVICE_REF = re.compile(r"^[0-9A-F]+(?:_[0-9A-F]+){9}\.png$")
STYLES = ("black", "white")
MASTER_PATHS = {
    "black": Path("templates/picons/black-sablona.png"),
    "white": Path("templates/picons/white-sablona.png"),
}
MASTER_SHA256 = {
    "black": "61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe",
    "white": "c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589",
}

# Frozen V9 production constants.  Borderline chroma/contrast is REVIEW.
OPAQUE_ALPHA = 32
ACHROMATIC_DELTA = 18
ACHROMATIC_REQUIRED = 0.985
ACHROMATIC_CONTRAST_RATIO = 2.50
MATERIAL_FRACTION = 0.08
TWO_TONE_FRACTION = 0.03
SAFE_MARGIN_X = 8
SAFE_MARGIN_Y = 8
RECOLOUR_BLACK = np.array([16, 16, 16], dtype=np.uint8)
RECOLOUR_WHITE = np.array([240, 240, 240], dtype=np.uint8)


@dataclass
class VariantResult:
    status: str
    reason: str
    image: Image.Image
    changed_pixels: int
    protected_pixels: int


def fit_logo(source: Image.Image) -> tuple[Image.Image, float, tuple[int, int, int, int]]:
    """Proportionally fit the visible logo inside the MASTER safe area and centre it."""
    bbox = source.getchannel("A").getbbox()
    if bbox is None:
        return source.copy(), 1.0, (0, 0, 0, 0)
    crop = source.crop(bbox)
    max_w = SIZE[0] - 2 * SAFE_MARGIN_X
    max_h = SIZE[1] - 2 * SAFE_MARGIN_Y
    scale = min(1.0, max_w / crop.width, max_h / crop.height)
    new_size = (max(1, round(crop.width * scale)), max(1, round(crop.height * scale)))
    if new_size != crop.size:
        crop = crop.resize(new_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    xy = ((SIZE[0] - crop.width) // 2, (SIZE[1] - crop.height) // 2)
    canvas.alpha_composite(crop, xy)
    return canvas, scale, bbox


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel_luma(rgb: np.ndarray) -> np.ndarray:
    x = rgb.astype(np.float32) / 255.0
    x = np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
    return x[..., 0] * 0.2126 + x[..., 1] * 0.7152 + x[..., 2] * 0.0722


def contrast_ratio(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    la, lb = rel_luma(a), rel_luma(b)
    hi, lo = np.maximum(la, lb), np.minimum(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def master_rgb_under(master: np.ndarray, mask: np.ndarray) -> np.ndarray:
    # Masters are used exactly as stored.  For contrast QC their semi-transparent
    # pixels are evaluated against black, matching normal transparent rendering.
    rgb = master[..., :3].astype(np.float32)
    alpha = master[..., 3:4].astype(np.float32) / 255.0
    rendered = np.rint(rgb * alpha).astype(np.uint8)
    return rendered[mask]


def classify_and_render(source: Image.Image, master: Image.Image, style: str) -> VariantResult:
    src = np.array(source, dtype=np.uint8)
    mst = np.array(master, dtype=np.uint8)
    alpha = src[..., 3]
    visible = alpha > 0
    labels, count = ndimage.label(visible, structure=np.ones((3, 3), dtype=np.uint8))
    work = src.copy()
    changed = 0
    protected = np.zeros(visible.shape, dtype=bool)
    review_reasons: list[str] = []
    fixed_components = 0

    for idx in range(1, count + 1):
        component = labels == idx
        solid = component & (alpha >= OPAQUE_ALPHA)
        if not solid.any():
            solid = component
        rgb = src[..., :3][solid]
        delta = rgb.max(axis=1).astype(np.int16) - rgb.min(axis=1).astype(np.int16)
        achromatic_fraction = float(np.mean(delta <= ACHROMATIC_DELTA))
        is_achromatic = achromatic_fraction >= ACHROMATIC_REQUIRED
        luma = rel_luma(rgb.reshape((-1, 1, 3))).reshape(-1) * 255.0
        has_dark_and_light = (
            float(np.mean(luma <= 64.0)) >= TWO_TONE_FRACTION
            and float(np.mean(luma >= 192.0)) >= TWO_TONE_FRACTION
        )

        if is_achromatic and not has_dark_and_light:
            bg = master_rgb_under(mst, solid)
            cr = contrast_ratio(rgb.reshape((-1, 1, 3)), bg.reshape((-1, 1, 3))).reshape(-1)
            needs_fix = float(np.mean(cr < ACHROMATIC_CONTRAST_RATIO)) >= MATERIAL_FRACTION
            if needs_fix:
                target = RECOLOUR_BLACK if style == "white" else RECOLOUR_WHITE
                work[..., :3][component] = target
                changed += int(component.sum())
                fixed_components += 1
            continue

        protected |= component
        bg = master_rgb_under(mst, solid)
        cr = contrast_ratio(rgb.reshape((-1, 1, 3)), bg.reshape((-1, 1, 3))).reshape(-1)
        weak_fraction = float(np.mean(cr < ACHROMATIC_CONTRAST_RATIO))
        if weak_fraction >= MATERIAL_FRACTION:
            component_kind = "two-tone achromatic" if has_dark_and_light else "chromatic"
            review_reasons.append(
                f"{component_kind} component {idx} has {weak_fraction:.1%} materially low-contrast pixels on {style.upper()}"
            )

    # Hard invariant: all protected brand-component RGBA pixels are untouched.
    if protected.any() and not np.array_equal(work[protected], src[protected]):
        raise RuntimeError("protected brand component changed")

    logo = Image.fromarray(work, "RGBA")
    result = Image.alpha_composite(master, logo)
    if review_reasons:
        status = "REVIEW"
        reason = "; ".join(review_reasons)
    elif changed:
        status = "AUTO-FIXED"
        reason = f"recoloured {fixed_components} safely isolated achromatic component(s)"
    else:
        status = "PASS"
        reason = "source components preserved; no approved contrast correction required"
    return VariantResult(status, reason, result, changed, int(protected.sum()))


def overall_status(black: str, white: str) -> str:
    rank = {"PASS": 0, "AUTO-FIXED": 1, "REVIEW": 2, "ERROR-SKIP": 3}
    return max((black, white), key=rank.__getitem__)


def validate_source(path: Path, root: Path) -> tuple[Image.Image | None, list[str]]:
    reasons: list[str] = []
    parts = path.relative_to(root).parts
    if len(parts) != 4 or parts[2] != "transparent":
        reasons.append("invalid source path architecture")
    if not SERVICE_REF.fullmatch(path.name):
        reasons.append("invalid service-reference filename")
    try:
        with Image.open(path) as raw:
            if raw.format != "PNG":
                reasons.append("not PNG")
            if raw.size != SIZE:
                reasons.append(f"invalid dimensions {raw.size[0]}x{raw.size[1]}")
            rgba = raw.convert("RGBA")
            rgba.load()
    except Exception as exc:
        return None, reasons + [f"decode error: {exc}"]
    if rgba.getchannel("A").getbbox() is None:
        reasons.append("empty alpha/fully transparent source")
    return rgba, reasons


def write_reports(report_dir: Path, rows: list[dict], summary: dict) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else []
    with (report_dir / "catalog-audit.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (report_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    counts = summary["source_class_counts"]
    variants = summary["variant_class_counts"]
    lines = [
        "# Warder MASTER production report",
        "",
        f"Generated: {summary['generated_at_utc']}",
        f"Branch baseline: `{summary['baseline_commit']}`",
        "",
        "## Source classification",
        "",
        f"- PASS: {counts.get('PASS', 0)}",
        f"- AUTO-FIXED: {counts.get('AUTO-FIXED', 0)}",
        f"- REVIEW: {counts.get('REVIEW', 0)}",
        f"- ERROR/SKIP: {counts.get('ERROR-SKIP', 0)}",
        "",
        "## Variant classification",
        "",
        f"- PASS: {variants.get('PASS', 0)}",
        f"- AUTO-FIXED: {variants.get('AUTO-FIXED', 0)}",
        f"- REVIEW: {variants.get('REVIEW', 0)}",
        f"- ERROR/SKIP: {variants.get('ERROR-SKIP', 0)}",
        "",
        "## Validation",
        "",
        f"- Transparent sources: {summary['transparent_sources']}",
        f"- BLACK outputs: {summary['black_outputs']}",
        f"- WHITE outputs: {summary['white_outputs']}",
        f"- Output validation errors: {summary['output_validation_errors']}",
        f"- Source bytes changed: {summary['source_bytes_changed']}",
        f"- MASTER bytes changed: {summary['master_bytes_changed']}",
        "",
        "REVIEW candidates are generated with their original brand colours intact. They are",
        "not automatically approved and this branch must not be merged before visual review.",
        "",
    ]
    (report_dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def write_qc_samples(root: Path, report_dir: Path, rows: list[dict]) -> None:
    chosen = []
    for status in ("PASS", "AUTO-FIXED", "REVIEW"):
        group = [row for row in rows if row["overall_status"] == status]
        if not group:
            continue
        indices = sorted({round(i * (len(group) - 1) / 4) for i in range(5)})
        chosen.extend(group[i] for i in indices)
    cell_w, cell_h = 660, 176
    sheet = Image.new("RGB", (cell_w, len(chosen) * cell_h), (30, 30, 30))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(sheet)
    for row_index, row in enumerate(chosen):
        y = row_index * cell_h
        source = Image.open(root / row["source"]).convert("RGBA")
        black = Image.open(root / row["black_output"]).convert("RGBA")
        white = Image.open(root / row["white_output"]).convert("RGBA")
        checker = Image.new("RGBA", SIZE, (80, 80, 80, 255))
        checker_draw = ImageDraw.Draw(checker)
        for yy in range(0, SIZE[1], 12):
            for xx in range(0, SIZE[0], 12):
                if (xx // 12 + yy // 12) % 2:
                    checker_draw.rectangle((xx, yy, xx + 11, yy + 11), fill=(120, 120, 120, 255))
        checker.alpha_composite(source)
        for column, image in enumerate((checker, black, white)):
            sheet.paste(image.convert("RGB"), (column * SIZE[0], y))
        draw.rectangle((0, y + SIZE[1], cell_w, y + cell_h), fill=(18, 18, 18))
        draw.text((5, y + 136), f"{row['overall_status']}  {row['source'][-82:]}", fill="white")
    sheet.save(report_dir / "qc-samples.png", format="PNG")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--baseline", default="1428a108c5a2d5cdd9725a35ca4cb2c43e703d6e")
    args = parser.parse_args()
    root = args.root.resolve()
    picon_root = root / "picons"
    report_dir = root / "reports" / "warder-master-production"
    masters = {}
    initial_master_hashes = {}
    for style, rel in MASTER_PATHS.items():
        path = root / rel
        initial_master_hashes[style] = sha256_file(path)
        if initial_master_hashes[style] != MASTER_SHA256[style]:
            raise SystemExit(f"immutable {style} MASTER SHA256 mismatch")
        with Image.open(path) as im:
            if im.size != SIZE or im.mode != "RGBA":
                raise SystemExit(f"invalid {style} MASTER format")
            masters[style] = im.copy()

    sources = sorted(picon_root.glob("*/*/transparent/*.png"))
    initial_source_hashes = {p: sha256_file(p) for p in sources}
    stale_outputs = [
        p
        for style in STYLES
        for p in picon_root.glob(f"*/*/{style}/*.png")
    ]
    for path in stale_outputs:
        path.unlink()
    rows: list[dict] = []
    source_counts = Counter()
    variant_counts = Counter()

    for n, source_path in enumerate(sources, 1):
        rel = source_path.relative_to(root)
        rgba, errors = validate_source(source_path, picon_root)
        base = {
            "source": rel.as_posix(),
            "source_sha256": initial_source_hashes[source_path],
        }
        if errors or rgba is None:
            reason = "; ".join(errors)
            rows.append({
                **base, "overall_status": "ERROR-SKIP",
                "source_bbox": "", "geometry_scale": "",
                "black_status": "ERROR-SKIP", "white_status": "ERROR-SKIP",
                "black_reason": reason, "white_reason": reason,
                "black_changed_pixels": 0, "white_changed_pixels": 0,
                "black_output": "", "white_output": "",
            })
            source_counts["ERROR-SKIP"] += 1
            variant_counts["ERROR-SKIP"] += 2
            continue

        fitted, geometry_scale, source_bbox = fit_logo(rgba)
        results = {}
        output_paths = {}
        for style in STYLES:
            result = classify_and_render(fitted, masters[style], style)
            output = source_path.parent.parent / style / source_path.name
            output.parent.mkdir(parents=True, exist_ok=True)
            result.image.save(output, format="PNG")
            results[style] = result
            output_paths[style] = output.relative_to(root).as_posix()
            variant_counts[result.status] += 1
        overall = overall_status(results["black"].status, results["white"].status)
        source_counts[overall] += 1
        rows.append({
            **base, "overall_status": overall,
            "source_bbox": ",".join(map(str, source_bbox)),
            "geometry_scale": f"{geometry_scale:.8f}",
            "black_status": results["black"].status,
            "white_status": results["white"].status,
            "black_reason": results["black"].reason,
            "white_reason": results["white"].reason,
            "black_changed_pixels": results["black"].changed_pixels,
            "white_changed_pixels": results["white"].changed_pixels,
            "black_output": output_paths["black"],
            "white_output": output_paths["white"],
        })
        if n % 500 == 0:
            print(f"processed {n}/{len(sources)}", flush=True)

    validation_errors = []
    for row in rows:
        if row["overall_status"] == "ERROR-SKIP":
            continue
        src_parts = (root / row["source"]).relative_to(picon_root).parts
        for style in STYLES:
            out = root / row[f"{style}_output"]
            parts = out.relative_to(picon_root).parts
            if len(parts) != 4 or parts[:2] != src_parts[:2] or parts[2] != style or parts[3] != src_parts[3]:
                validation_errors.append(f"architecture mismatch: {out}")
                continue
            try:
                with Image.open(out) as im:
                    im.load()
                    if im.format != "PNG" or im.size != SIZE or im.mode != "RGBA":
                        validation_errors.append(f"format mismatch: {out}")
            except Exception as exc:
                validation_errors.append(f"decode failure: {out}: {exc}")

    changed_sources = sum(sha256_file(p) != h for p, h in initial_source_hashes.items())
    changed_masters = sum(
        sha256_file(root / MASTER_PATHS[s]) != h for s, h in initial_master_hashes.items()
    )
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline_commit": args.baseline,
        "transparent_sources": len(sources),
        "stale_outputs_removed_before_rebuild": len(stale_outputs),
        "black_outputs": sum(1 for p in picon_root.glob("*/*/black/*.png")),
        "white_outputs": sum(1 for p in picon_root.glob("*/*/white/*.png")),
        "source_class_counts": dict(sorted(source_counts.items())),
        "variant_class_counts": dict(sorted(variant_counts.items())),
        "output_validation_errors": len(validation_errors),
        "validation_error_examples": validation_errors[:100],
        "source_bytes_changed": changed_sources,
        "master_bytes_changed": changed_masters,
        "master_sha256": initial_master_hashes,
        "constants": {
            "opaque_alpha": OPAQUE_ALPHA,
            "achromatic_delta": ACHROMATIC_DELTA,
            "achromatic_required": ACHROMATIC_REQUIRED,
            "achromatic_contrast_ratio": ACHROMATIC_CONTRAST_RATIO,
            "material_fraction": MATERIAL_FRACTION,
            "two_tone_fraction": TWO_TONE_FRACTION,
            "safe_margin_x": SAFE_MARGIN_X,
            "safe_margin_y": SAFE_MARGIN_Y,
        },
    }
    write_reports(report_dir, rows, summary)
    write_qc_samples(root, report_dir, rows)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 1 if validation_errors or changed_sources or changed_masters else 0


if __name__ == "__main__":
    raise SystemExit(main())
