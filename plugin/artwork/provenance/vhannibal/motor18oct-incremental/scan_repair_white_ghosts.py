#!/usr/bin/env python3
"""Scan and repair WHITE ghost/underlay defects in the 18-Oct delta.

The first WHITE-QC pass incorrectly wrote some candidates even though the
Warder V9 engine classified them REVIEW.  This second gate always runs the
engine, records its raw decision, detects split light/dark logical artwork,
and applies only digest-bound component repairs that have been visually
verified.  Transparent, BLACK and MASTER assets are immutable.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


SIZE = (220, 132)
WHITE_MASTER_SHA256 = "c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589"
BLACK_MASTER_SHA256 = "61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe"
RECOLOUR_BLACK = np.array([16, 16, 16], dtype=np.uint8)

# RGBA source digest: policy and exact expected multiplicity in the complete
# catalog.  Every rule was selected from the scanner output and visually
# verified at native size and 4x nearest-neighbour enlargement.
TARGET_RULES = {
    # Asharq Bloomberg: the whole source is one light monochrome wordmark;
    # chromatic-looking pixels are raster/AA fringe, not a brand component.
    "1d3f45acad953662ca8274ef07b35d1aafb417d5a744b1e983ed26a19e2f530e": {
        "policy": "whole-monochrome-wordmark",
        "expected_catalog": 4,
        "expected_delta": 1,
    },
    # OSN families: select complete neutral logical components that already
    # contain engine-darkened seed pixels.  The coloured tv mark is excluded
    # by content, never by a coordinate rectangle.
    "626b44c3978a7da2e60e7137738d576ea84561a3188f2e2c69adc1ce7941e19a": {
        "policy": "neutral-components-from-engine-seeds",
        "expected_catalog": 2,
        "expected_delta": 1,
    },
    "3e8ac3c0e4aa9af4f555b2ab1a742afb4892c84be5d1b7da33e96e61bb514a1b": {
        "policy": "neutral-components-from-engine-seeds",
        "expected_catalog": 2,
        "expected_delta": 1,
    },
    "ded1047dba3fcfc121de16291f68798f45c0cb11a99e87da3f6f201b9a0d5dbd": {
        "policy": "neutral-components-from-engine-seeds",
        "expected_catalog": 2,
        "expected_delta": 1,
    },
    "580fec515b60da3ceea67ecdce9196a61abcb3a553bb598db33b4c747eb5b877": {
        "policy": "neutral-components-from-engine-seeds",
        "expected_catalog": 2,
        "expected_delta": 1,
    },
}

# Exact-source visual approvals for scanner signals that are intentional brand
# content, not a white underlay.  These 21 unique artworks were reviewed
# source/WHITE/BLACK side by side after the repair pass.  The binding is to the
# RGBA source digest so a changed source cannot inherit an old approval.
PROTECTED_VISUAL_APPROVALS = {
    "69a088a9ca7ee1e18ce65e9014a5d3d05fc3b3011db3ecf8da47986e1816585a":
        "National Geographic: white HD glyph inside its black badge and yellow frame are protected",
    "f60b3116513c3ff88f06ee8ff9a88397bd0e9b15b53f66ef50177559af59a621":
        "Match Premier: white lettering is embedded in the gold provider panel",
    "0334a603ad3a278ba6bb0f95236056877ea95e2498a7f8dc32375af46252c43e":
        "Cartoon Network: white C and checker detail belong inside the black/white brand panel",
    "aa660a2c5f18c1b91f5b20f3a5304433d522238b0adc52a0e80e4102cc6dc378":
        "metallic 3D logo: highlights and gradients are protected brand artwork",
    "8a69bbad215eb1795d0f50724712034b1c1d4a5ea34f312d99f23d4b1d8d4a22":
        "metallic 3D logo with numeral panel: highlights and gradients are protected",
    "d00e4af55d54268212984b8f7d261bb1c1aa803770b0793f0cd712c2141d6c63":
        "Demiroren: white cutout is enclosed by the black/orange brand symbol",
    "9d9d8b1ce6b60e87cb9d4bcfe10ee993491bd804a48e2b25596a2a5f18fbe7f5":
        "Demiroren: white cutout is enclosed by the black/orange brand symbol",
    "913954cecb43f67b9615f1f31c3bc0d7fda649cb6e1d7cfec24cf051046c1d39":
        "SES Astra: small light pixels belong to the coloured arch/tagline artwork",
    "05f80aa05aaad09c079c3ad48e0bba0e4b2498fc792b7d1799f1ce7130eb6e91":
        "Eurosport 2: white numeral is protected inside the red badge",
    "c9cf69aef5ca1a8f72d71ff853972918bbed972c22fc1d02709cafea38f47256":
        "Cinemax 2 HD: light glyphs are enclosed by the yellow/black badge artwork",
    "60e699c8920286bb918f381670d930d868057be885233b33c1f7eef1f66cbb46":
        "BetaDigital: scanner residue is the antialias boundary of the blue brand symbol",
    "87eaaca7c45a7df164421b1c87fd39877e95e229c5c3846372d871212b136512":
        "TRT Cocuk: light face details are embedded in the yellow wordmark",
    "36bd504a2fcbefa4c334aa6f848a5f7299fb93b4198ab80f245dc4e07fb5ae08":
        "Rudaw: scanner residue belongs to the orange sun and letter accents",
    "91e754e77b718e88d5814f11195bc9f7123791cbbcd43a3295f2b3628af34e1a":
        "Animal Planet: small light pixels belong to the blue symbol antialias",
    "b21cc85c8b9a6a835f23f8adfd794f36b298ede40f2d4a9175e42d5aaf45f3d4":
        "FON MUSIC: white MUSIC text is protected inside the red badge",
    "63f36b06e4a4c7d7a601c302a980feba18cff5eacfdfad6c9a04810a1a52e199":
        "ID X HD: light pixels belong to the tilted white/grey brand panel",
    "860b12f43996986bf77e26098cff35423a1812da6fdfff7ed7ba5831cf9ca689":
        "Crime+Investigation: scanner residue is adjacent to the protected red plus",
    "2064da54ba2c5da0304a8f8e95dd9e2e09e86c868cb09e6476091b1419cbd491":
        "HBO 3: light pixels belong to the yellow numeral and registered-mark detail",
    "3844c72a8532dd873efb5c1b05120b244475a16524946af0d610193fa28c0d95":
        "Private HD: white P remains protected inside the red tile",
    "45df455e486a9c56ad82971de0047dbf514935c96211cc4ebd1527d2741ef45c":
        "Hustler TV: scanner residue is the protected red TV antialias boundary",
    "8ae96470dd53a5052c3d50a7146d12ab1483e49ccfd2bc0c814b5f1716b5c2ac":
        "National Geographic: yellow frame and its antialias are protected",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rgba_sha256(image: Image.Image) -> str:
    return hashlib.sha256(image.convert("RGBA").tobytes()).hexdigest()


def load_renderer(path: Path):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location("warder_white_ghost_engine", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load renderer: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_delta_rows(report: Path) -> list[dict[str, str]]:
    with gzip.open(report, "rt", encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle, delimiter="\t") if row["status"] == "added"]
    rows.sort(key=lambda row: (row["position"], row["provider"], row["filename"]))
    if len(rows) != 174:
        raise SystemExit(f"Expected 174 added triplets, found {len(rows)}")
    return rows


def align_source(source: Image.Image, renderer) -> tuple[Image.Image, object]:
    fitted, scale, source_bbox = renderer.fit_logo(source)
    geometry = renderer.fit_geometry_mask(source, source_bbox, scale)
    centered = renderer.center_rgba_layer(fitted, geometry_mask=geometry)
    if centered.clipped or not centered.centered or not centered.safe_area:
        raise SystemExit(f"Engine alignment failed: {centered.reason}")
    return centered.image, (fitted, geometry)


def rgb_luma(rgb: np.ndarray) -> np.ndarray:
    values = rgb.astype(np.float32)
    return values[..., 0] * 0.2126 + values[..., 1] * 0.7152 + values[..., 2] * 0.0722


def split_ghost_metrics(source: Image.Image, master: Image.Image, current: Image.Image) -> dict[str, int]:
    src = np.asarray(source, dtype=np.uint8)
    before = np.asarray(Image.alpha_composite(master, source), dtype=np.uint8)
    after = np.asarray(current, dtype=np.uint8)
    alpha = src[..., 3]
    rgb = src[..., :3].astype(np.int16)
    saturation = rgb.max(axis=2) - rgb.min(axis=2)
    light_neutral = (alpha >= 16) & (rgb_luma(rgb) >= 150) & (saturation <= 80)
    darkening = rgb_luma(before[..., :3]) - rgb_luma(after[..., :3])
    darkened = (alpha >= 16) & (darkening >= 28)
    unchanged = np.max(np.abs(after.astype(np.int16) - before.astype(np.int16)), axis=2) <= 4
    residual = light_neutral & unchanged
    near_darkened = ndimage.binary_dilation(darkened, structure=np.ones((7, 7), dtype=bool))
    ghost = residual & near_darkened
    labels, count = ndimage.label(alpha >= 16, structure=np.ones((3, 3), dtype=np.uint8))
    split_components = 0
    split_residual = 0
    for component_id in range(1, count + 1):
        component = labels == component_id
        if np.any(component & darkened) and np.any(component & residual):
            split_components += 1
            split_residual += int(np.count_nonzero(component & residual))
    return {
        "ghost_pixels": int(ghost.sum()),
        "residual_light_pixels": int(residual.sum()),
        "darkened_pixels": int(darkened.sum()),
        "split_components": split_components,
        "split_residual_pixels": split_residual,
    }


def whole_monochrome_mask(layer: np.ndarray) -> tuple[np.ndarray, int]:
    visible = layer[..., 3] > 0
    rgb = layer[..., :3].astype(np.int16)
    saturation = rgb.max(axis=2) - rgb.min(axis=2)
    light = rgb_luma(rgb) >= 128
    if int(visible.sum()) < 1000:
        raise SystemExit("Whole-wordmark rule rejected an unexpectedly small source")
    # LANCZOS fitting spreads a small number of source fringe pixels; the
    # exact digest binding plus this 96% gate prevents use on a coloured logo.
    if float(np.mean((saturation <= 80)[visible])) < 0.96:
        raise SystemExit("Whole-wordmark rule rejected source chroma evidence")
    if float(np.mean(light[visible])) < 0.99:
        raise SystemExit("Whole-wordmark rule rejected source luminance evidence")
    return visible, 1


def neutral_component_mask(
    layer: np.ndarray, master: Image.Image, engine_candidate: Image.Image
) -> tuple[np.ndarray, int]:
    source = Image.fromarray(layer, "RGBA")
    original = np.asarray(Image.alpha_composite(master, source), dtype=np.uint8)
    after = np.asarray(engine_candidate, dtype=np.uint8)
    rgb = layer[..., :3].astype(np.int16)
    alpha = layer[..., 3]
    saturation = rgb.max(axis=2) - rgb.min(axis=2)
    darkened_seed = (
        (alpha >= 16)
        & ((rgb_luma(original[..., :3]) - rgb_luma(after[..., :3])) >= 28)
    )
    neutral = (alpha > 0) & (saturation <= 80)
    labels, count = ndimage.label(neutral, structure=np.ones((3, 3), dtype=np.uint8))
    target = np.zeros(alpha.shape, dtype=bool)
    selected = 0
    for component_id in range(1, count + 1):
        component = labels == component_id
        area = int(component.sum())
        seeds = int(np.count_nonzero(component & darkened_seed))
        if area >= 12 and seeds >= 12 and seeds / area >= 0.10:
            target |= component
            selected += 1
    if selected != 2 or int(target.sum()) < 2500:
        raise SystemExit(
            f"Neutral-component binding changed: selected={selected}, pixels={int(target.sum())}"
        )
    return target, selected


def render_repair(
    source: Image.Image,
    master: Image.Image,
    current: Image.Image,
    renderer,
    policy: str,
) -> tuple[Image.Image, dict[str, object]]:
    aligned, engine_inputs = align_source(source, renderer)
    fitted, geometry = engine_inputs
    engine_result = renderer.classify_and_render(
        fitted, master, "white", centering_mask=geometry
    )
    if engine_result.status != "REVIEW":
        raise SystemExit(
            f"Expected raw engine REVIEW for digest-bound repair, got {engine_result.status}"
        )
    work = np.asarray(aligned, dtype=np.uint8).copy()
    if policy == "whole-monochrome-wordmark":
        target, components = whole_monochrome_mask(work)
    elif policy == "neutral-components-from-engine-seeds":
        target, components = neutral_component_mask(work, master, engine_result.image)
    else:
        raise SystemExit(f"Unknown repair policy: {policy}")
    work[..., :3][target] = RECOLOUR_BLACK
    result = Image.alpha_composite(master, Image.fromarray(work, "RGBA"))
    return result, {
        "engine_status": engine_result.status,
        "engine_reason": engine_result.reason,
        "repair_components": components,
        "repair_mask_pixels": int(target.sum()),
    }


def write_tsv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise SystemExit(f"Refusing to write empty report: {path}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run(args: argparse.Namespace) -> dict[str, object]:
    root = args.repo.resolve()
    renderer_path = args.renderer.resolve()
    renderer = load_renderer(renderer_path)
    report_dir = root / "migration/vhannibal/motor18oct-incremental"
    delta_rows = load_delta_rows(report_dir / "import-report.tsv.gz")
    white_master_path = root / "templates/picons/white-sablona.png"
    black_master_path = root / "templates/picons/black-sablona.png"
    if sha256_file(white_master_path) != WHITE_MASTER_SHA256:
        raise SystemExit("Immutable WHITE master hash mismatch")
    if sha256_file(black_master_path) != BLACK_MASTER_SHA256:
        raise SystemExit("Immutable BLACK master hash mismatch")
    white_master = Image.open(white_master_path).convert("RGBA")

    target_paths: list[tuple[Path, str, dict[str, object]]] = []
    catalog_counts: Counter[str] = Counter()
    for source_path in sorted((root / "picons").glob("*/*/transparent/*.png")):
        source = Image.open(source_path).convert("RGBA")
        digest = rgba_sha256(source)
        if digest in TARGET_RULES:
            black_path = source_path.parent.parent / "black" / source_path.name
            white_path = source_path.parent.parent / "white" / source_path.name
            # This gate repairs existing WHITE outputs only.  A legacy
            # transparent-only identity is outside this delta and is not
            # silently promoted into a new triplet.
            if not black_path.is_file() or not white_path.is_file():
                continue
            catalog_counts[digest] += 1
            target_paths.append((source_path, digest, TARGET_RULES[digest]))
    expected_catalog = Counter(
        {digest: int(rule["expected_catalog"]) for digest, rule in TARGET_RULES.items()}
    )
    if catalog_counts != expected_catalog:
        raise SystemExit(f"Catalog digest/count binding mismatch: {catalog_counts} != {expected_catalog}")

    delta_counts: Counter[str] = Counter()
    for row in delta_rows:
        digest = rgba_sha256(Image.open(root / row["transparent_destination"]).convert("RGBA"))
        if digest in TARGET_RULES:
            delta_counts[digest] += 1
    expected_delta = Counter(
        {digest: int(rule["expected_delta"]) for digest, rule in TARGET_RULES.items()}
    )
    if delta_counts != expected_delta:
        raise SystemExit(f"Delta digest/count binding mismatch: {delta_counts} != {expected_delta}")

    immutable_before: dict[Path, str] = {
        white_master_path: sha256_file(white_master_path),
        black_master_path: sha256_file(black_master_path),
    }
    previous_repairs: dict[str, dict[str, str]] = {}
    previous_report_path = report_dir / "white-ghost-qc-repair.tsv"
    if previous_report_path.is_file():
        with previous_report_path.open(encoding="utf-8", newline="") as handle:
            previous_repairs = {
                row["white_output"]: row
                for row in csv.DictReader(handle, delimiter="\t")
            }
    repair_rows: list[dict[str, object]] = []
    for source_path, digest, rule in target_paths:
        black_path = source_path.parent.parent / "black" / source_path.name
        white_path = source_path.parent.parent / "white" / source_path.name
        immutable_before[source_path] = sha256_file(source_path)
        immutable_before[black_path] = sha256_file(black_path)
        source = Image.open(source_path).convert("RGBA")
        current = Image.open(white_path).convert("RGBA")
        before_metrics = split_ghost_metrics(*(
            align_source(source, renderer)[0], white_master, current
        ))
        repaired, evidence = render_repair(
            source, white_master, current, renderer, str(rule["policy"])
        )
        changed_pixels = int(
            np.count_nonzero(
                np.any(
                    np.asarray(repaired, dtype=np.uint8)
                    != np.asarray(current, dtype=np.uint8),
                    axis=2,
                )
            )
        )
        relative_white = white_path.relative_to(root).as_posix()
        previous = previous_repairs.get(relative_white)
        current_sha256 = sha256_file(white_path)
        already_fixed = changed_pixels == 0
        if already_fixed and (
            previous is None or previous.get("new_sha256") != current_sha256
        ):
            raise SystemExit(f"Unbound no-op repair state: {white_path}")
        old_sha256 = previous["old_sha256"] if already_fixed else current_sha256
        if args.apply and not already_fixed:
            repaired.save(white_path, "PNG")
            new_sha256 = sha256_file(white_path)
            verified = Image.open(white_path).convert("RGBA")
        else:
            new_sha256 = current_sha256 if already_fixed else hashlib.sha256(repaired.tobytes()).hexdigest()
            verified = current if already_fixed else repaired
        aligned, _ = align_source(source, renderer)
        after_metrics = split_ghost_metrics(aligned, white_master, verified)
        if after_metrics["ghost_pixels"] != 0 or after_metrics["split_residual_pixels"] != 0:
            raise SystemExit(f"Residual ghost signal after repair: {white_path}: {after_metrics}")
        repair_rows.append({
            "source_rgba_sha256": digest,
            "policy": rule["policy"],
            "position": source_path.relative_to(root / "picons").parts[0],
            "provider": source_path.relative_to(root / "picons").parts[1],
            "filename": source_path.name,
            "white_output": relative_white,
            "raw_engine_status": evidence["engine_status"],
            "raw_engine_reason": evidence["engine_reason"],
            "repair_components": evidence["repair_components"],
            "repair_mask_pixels": evidence["repair_mask_pixels"],
            "output_changed_pixels": (
                previous["output_changed_pixels"] if already_fixed else changed_pixels
            ),
            "ghost_pixels_before": (
                previous["ghost_pixels_before"]
                if already_fixed
                else before_metrics["ghost_pixels"]
            ),
            "ghost_pixels_after": after_metrics["ghost_pixels"],
            "old_sha256": old_sha256,
            "new_sha256": new_sha256,
            "result": (
                "ALREADY_FIXED_ENGINE_RESCAN_PASS"
                if already_fixed
                else ("FIXED_ENGINE_RESCAN_PASS" if args.apply else "DRY_RUN")
            ),
        })

    for path, expected in immutable_before.items():
        if sha256_file(path) != expected:
            raise SystemExit(f"Immutable source/BLACK/MASTER changed: {path}")

    scan_rows: list[dict[str, object]] = []
    for index, row in enumerate(delta_rows, 1):
        source_path = root / row["transparent_destination"]
        white_path = root / row["white_destination"]
        source = Image.open(source_path).convert("RGBA")
        aligned, engine_inputs = align_source(source, renderer)
        fitted, geometry = engine_inputs
        engine_result = renderer.classify_and_render(
            fitted, white_master, "white", centering_mask=geometry
        )
        current = Image.open(white_path).convert("RGBA")
        metrics = split_ghost_metrics(aligned, white_master, current)
        digest = rgba_sha256(source)
        if digest in TARGET_RULES:
            scan_status = "PASS_REPAIRED"
            visual_reason = "digest-bound ghost repair; engine rescan found no residual underlay"
        elif digest in PROTECTED_VISUAL_APPROVALS:
            scan_status = "PASS_PROTECTED"
            visual_reason = PROTECTED_VISUAL_APPROVALS[digest]
        elif metrics["ghost_pixels"] or metrics["split_residual_pixels"]:
            scan_status = "VISUAL_REVIEW"
            visual_reason = "unapproved light/dark split requires visual review"
        else:
            scan_status = "PASS"
            visual_reason = "no light-underlay signal"
        scan_rows.append({
            "index": index,
            "position": row["position"],
            "provider": row["provider"],
            "filename": row["filename"],
            "source_rgba_sha256": digest,
            "raw_engine_status": engine_result.status,
            "scan_status": scan_status,
            "visual_reason": visual_reason,
            **metrics,
        })

    if args.apply:
        repair_report = report_dir / "white-ghost-qc-repair.tsv"
        scan_report = report_dir / "white-ghost-qc-scan.tsv"
        write_tsv(repair_report, repair_rows)
        write_tsv(scan_report, scan_rows)
        scan_counts = Counter(str(row["scan_status"]) for row in scan_rows)
        if scan_counts.get("VISUAL_REVIEW", 0):
            raise SystemExit(
                f"Unresolved WHITE ghost visual reviews remain: {scan_counts['VISUAL_REVIEW']}"
            )
        summary = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "scope_white_variants_scanned": len(scan_rows),
            "catalog_white_files_repaired": len(repair_rows),
            "delta_white_files_repaired": sum(
                int(row["source_rgba_sha256"] in TARGET_RULES) for row in scan_rows
            ),
            "unique_source_artworks_repaired": len(TARGET_RULES),
            "scan_status_counts": dict(scan_counts),
            "transparent_sources_changed": 0,
            "black_variants_changed": 0,
            "master_files_changed": 0,
            "plugin_gui_skin_files_changed": 0,
            "renderer_sha256": sha256_file(renderer_path),
            "white_master_sha256": WHITE_MASTER_SHA256,
            "repair_report_sha256": sha256_file(repair_report),
            "scan_report_sha256": sha256_file(scan_report),
            "note": "All scanner signals are either repaired and rescanned or bound to exact-source protected-brand visual approval; unresolved VISUAL_REVIEW is a hard failure.",
        }
        summary_path = report_dir / "white-ghost-qc-summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return summary
    return {
        "mode": "dry-run",
        "catalog_white_files_selected": len(repair_rows),
        "unique_source_artworks_selected": len(TARGET_RULES),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--renderer", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
