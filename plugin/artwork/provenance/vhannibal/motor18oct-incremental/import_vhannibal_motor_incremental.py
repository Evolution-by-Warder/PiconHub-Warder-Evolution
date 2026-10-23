#!/usr/bin/env python3
"""Guarded incremental Vhannibal Motor import for PiconHub Warder Evolution.

Only globally absent service-reference filenames are considered. Provider
classification must be uniquely supported by matching Vhannibal service
metadata or an existing PiconHub record for the same service identity. Source
QC and BLACK/WHITE rendering use the frozen Warder V9 rules; REVIEW items are
reported but never written into the runtime picon tree.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import re
import shutil
import struct
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image


SIZE = (220, 132)
SERVICE_REF = re.compile(r"^[0-9A-F]+(?:_[0-9A-F]+){9}\.png$", re.IGNORECASE)
EXPECTED_MASTER_SHA256 = {
    "black": "61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe",
    "white": "c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589",
}

# Provider labels that are placeholders rather than maintainable categories.
# Never create new runtime paths from these values, even when they occur in a
# source lamedb or in historical repository data.
GENERIC_PROVIDER_SLUGS = {
    "default",
    "myserviceprovider",
    "n-a",
    "na",
    "none",
    "other",
    "provider",
    "serviceprovider",
    "unknown",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rgba_sha256(path: Path) -> str:
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
        if rgba.size != SIZE:
            raise ValueError(f"invalid reference dimensions: {path}: {rgba.size}")
        return hashlib.sha256(rgba.tobytes()).hexdigest()


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")


def parse_service_ref(name: str) -> tuple[int, int, int, int, int] | None:
    if not SERVICE_REF.fullmatch(name):
        return None
    parts = Path(name).stem.split("_")
    try:
        service_type = int(parts[2], 16)
        sid = int(parts[3], 16)
        tsid = int(parts[4], 16)
        onid = int(parts[5], 16)
        namespace = int(parts[6], 16)
    except (IndexError, ValueError):
        return None
    return sid, namespace, tsid, onid, service_type


def orbital_position(namespace: int) -> str | None:
    raw = (namespace >> 16) & 0xFFFF
    if 0 < raw <= 1800:
        return f"{raw / 10:.1f}e"
    if 1800 < raw <= 3600:
        return f"{(3600 - raw) / 10:.1f}w"
    return None


def png_dimensions(path: Path) -> tuple[int, int] | None:
    with path.open("rb") as handle:
        head = handle.read(24)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", head[16:24])


def parse_lamedb(path: Path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    try:
        index = lines.index("services") + 1
    except ValueError:
        return
    key_re = re.compile(
        r"^([0-9a-fA-F]+):([0-9a-fA-F]+):([0-9a-fA-F]+):"
        r"([0-9a-fA-F]+):([0-9a-fA-F]+):"
    )
    while index < len(lines) and lines[index].strip() != "end":
        match = key_re.match(lines[index].strip())
        if not match:
            index += 1
            continue
        sid, namespace, tsid, onid, service_type = [int(value, 16) for value in match.groups()]
        provider = ""
        if index + 2 < len(lines):
            attrs = lines[index + 2].strip()
            if attrs.startswith("p:"):
                provider = attrs[2:].split(",", 1)[0].strip()
        provider_slug = slugify(provider)
        if provider_slug:
            yield (sid, namespace, tsid, onid, service_type), provider_slug
        index += 3


def provider_indexes(settings_root: Path):
    exact: dict[tuple[int, int, int, int, int], set[str]] = defaultdict(set)
    service: dict[tuple[int, int, int, int], set[str]] = defaultdict(set)
    lamedbs = sorted(settings_root.glob("*/lamedb"))
    if not lamedbs:
        raise SystemExit(f"No */lamedb files found under {settings_root}")
    for lamedb in lamedbs:
        for key, provider in parse_lamedb(lamedb):
            exact[key].add(provider)
            service[key[:4]].add(provider)
    return exact, service, lamedbs


def repository_indexes(picon_root: Path):
    basenames: set[str] = set()
    services: dict[tuple[int, int, int, int], set[str]] = defaultdict(set)
    for path in picon_root.glob("*/*/*/*.png"):
        basenames.add(path.name.casefold())
    for path in picon_root.glob("*/*/transparent/*.png"):
        key = parse_service_ref(path.name)
        if key:
            services[key[:4]].add(path.parts[-3])
    return basenames, services


def approved_reference_index(reference_root: Path | None):
    index: dict[str, list[dict[str, object]]] = defaultdict(list)
    by_filename: dict[str, list[dict[str, object]]] = defaultdict(list)
    if reference_root is None:
        return index, by_filename, 0
    picon_root = reference_root / "picons"
    if not picon_root.is_dir():
        raise SystemExit(f"Approved reference picon root not found: {picon_root}")
    triplets = 0
    for transparent in sorted(picon_root.glob("*/*/transparent/*.png")):
        black = transparent.parent.parent / "black" / transparent.name
        white = transparent.parent.parent / "white" / transparent.name
        if not black.exists() or not white.exists():
            continue
        with Image.open(black) as black_image, Image.open(white) as white_image:
            if (
                black_image.size != SIZE
                or white_image.size != SIZE
                or black_image.mode != "RGBA"
                or white_image.mode != "RGBA"
            ):
                continue
        source_pixels = rgba_sha256(transparent)
        record = {
            "transparent": transparent,
            "black": black,
            "white": white,
            "black_pixels": rgba_sha256(black),
            "white_pixels": rgba_sha256(white),
        }
        index[source_pixels].append(record)
        by_filename[transparent.name.casefold()].append(record)
        triplets += 1
    return index, by_filename, triplets


def unique_approved_match(image: Image.Image, reference_index):
    source_pixels = hashlib.sha256(image.convert("RGBA").tobytes()).hexdigest()
    matches = reference_index.get(source_pixels, [])
    if not matches:
        return None, "no approved pixel-identical source"
    black_pixels = {str(match["black_pixels"]) for match in matches}
    white_pixels = {str(match["white_pixels"]) for match in matches}
    if len(black_pixels) != 1 or len(white_pixels) != 1:
        return None, (
            f"approved source match is visually ambiguous: "
            f"black_variants={len(black_pixels)}, white_variants={len(white_pixels)}"
        )
    match = sorted(matches, key=lambda item: str(item["transparent"]))[0]
    return match, f"reused one unique approved result from {len(matches)} pixel-identical source(s)"


def choose_provider(
    key: tuple[int, int, int, int, int],
    exact: dict[tuple[int, int, int, int, int], set[str]],
    service: dict[tuple[int, int, int, int], set[str]],
    repository_service: dict[tuple[int, int, int, int], set[str]],
) -> tuple[str, str, str]:
    exact_values = exact.get(key, set()) - GENERIC_PROVIDER_SLUGS
    if len(exact_values) == 1:
        return (
            next(iter(exact_values)),
            "lamedb-exact",
            "provider identity exact in Vhannibal lamedb",
        )
    service_values = service.get(key[:4], set()) - GENERIC_PROVIDER_SLUGS
    if len(service_values) == 1:
        return next(iter(service_values)), "lamedb-service", "service type differs; provider identity is unique"
    repository_values = repository_service.get(key[:4], set()) - GENERIC_PROVIDER_SLUGS
    if len(repository_values) == 1:
        return next(iter(repository_values)), "repository-service", "same service identity already has one provider"
    conflicts = []
    if len(exact_values) > 1:
        conflicts.append("exact=" + ",".join(sorted(exact_values)))
    if len(service_values) > 1:
        conflicts.append("service=" + ",".join(sorted(service_values)))
    if len(repository_values) > 1:
        conflicts.append("repository=" + ",".join(sorted(repository_values)))
    reason = "provider conflict: " + "; ".join(conflicts) if conflicts else "provider metadata unavailable"
    return "", "", reason


def source_qc(image: Image.Image) -> tuple[str, str, dict[str, object]]:
    alpha = np.asarray(image.getchannel("A"), dtype=np.uint8)
    visible = alpha > 5
    ys, xs = np.where(visible)
    if not len(xs):
        return "SOURCE-ERROR", "empty alpha/fully transparent source", {}
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    box = alpha[y0:y1, x0:x1]
    opaque = box >= 250
    box_visible = box > 5
    area_fraction = box.size / alpha.size
    opaque_edge = np.concatenate((opaque[0], opaque[-1], opaque[:, 0], opaque[:, -1]))
    visible_edge = np.concatenate((box_visible[0], box_visible[-1], box_visible[:, 0], box_visible[:, -1]))
    opaque_corners = np.mean([opaque[0, 0], opaque[0, -1], opaque[-1, 0], opaque[-1, -1]])
    visible_corners = np.mean(
        [box_visible[0, 0], box_visible[0, -1], box_visible[-1, 0], box_visible[-1, -1]]
    )
    metrics = {
        "bbox": f"{x0},{y0},{x1},{y1}",
        "bbox_area_fraction": round(area_fraction, 6),
        "bbox_opaque_fill": round(float(np.mean(opaque)), 6),
        "bbox_visible_fill": round(float(np.mean(box_visible)), 6),
        "canvas_opaque_fraction": round(float(np.mean(alpha >= 250)), 6),
    }
    reasons = []
    if (
        area_fraction >= 0.08
        and np.mean(opaque) >= 0.94
        and np.mean(opaque_edge) >= 0.94
        and opaque_corners >= 0.75
    ):
        reasons.append("suspected opaque rectangular background in transparent source")
    if (
        area_fraction >= 0.08
        and np.mean(box_visible) >= 0.98
        and np.mean(visible_edge) >= 0.95
        and visible_corners >= 0.75
    ):
        reasons.append("suspected rectangular raster background in transparent source")
    if np.mean(alpha >= 250) >= 0.90:
        reasons.append("source is almost fully opaque across the 220x132 canvas")
    if reasons:
        return "SOURCE-REVIEW", "; ".join(dict.fromkeys(reasons)), metrics
    return "PASS", "", metrics


def load_renderer(renderer_path: Path):
    sys.path.insert(0, str(renderer_path.parent))
    spec = importlib.util.spec_from_file_location("warder_frozen_renderer", renderer_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load renderer: {renderer_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def overall_status(results: dict[str, object]) -> str:
    rank = {"PASS": 0, "AUTO-FIXED": 1, "REVIEW": 2, "ERROR-SKIP": 3}
    return max((results["black"].status, results["white"].status), key=rank.__getitem__)


def audit_row(filename: str) -> dict[str, object]:
    return {
        "status": "",
        "filename": filename,
        "position": "",
        "provider": "",
        "provider_method": "",
        "source_sha256": "",
        "source_qc": "",
        "black_qc": "",
        "white_qc": "",
        "variant_method": "",
        "transparent_destination": "",
        "black_destination": "",
        "white_destination": "",
        "reason": "",
    }


def run(args: argparse.Namespace) -> dict[str, object]:
    root = args.repo.resolve()
    picon_root = root / "picons"
    source_root = args.source.resolve()
    settings_root = args.settings.resolve()
    renderer_path = args.renderer.resolve()
    report_dir = args.report_dir
    if not report_dir.is_absolute():
        report_dir = root / report_dir
    report_dir = report_dir.resolve()
    try:
        report_dir.relative_to(root)
    except ValueError as error:
        raise SystemExit("Report directory must be inside the repository") from error
    if not picon_root.is_dir() or not source_root.is_dir() or not renderer_path.is_file():
        raise SystemExit("Missing repo picons, source directory, or frozen renderer")

    render = load_renderer(renderer_path)
    masters = {}
    for style in ("black", "white"):
        path = root / "templates" / "picons" / f"{style}-sablona.png"
        actual = sha256(path)
        if actual != EXPECTED_MASTER_SHA256[style]:
            raise SystemExit(f"Immutable {style} MASTER SHA256 mismatch: {actual}")
        with Image.open(path) as image:
            if image.size != SIZE or image.mode != "RGBA":
                raise SystemExit(f"Invalid {style} MASTER format")
            masters[style] = image.copy()

    exact, service, lamedbs = provider_indexes(settings_root)
    existing, repository_service = repository_indexes(picon_root)
    reference_root = args.approved_reference.resolve() if args.approved_reference else None
    reference_index, reference_by_filename, reference_triplets = approved_reference_index(reference_root)
    source_files = sorted(source_root.rglob("*.png"), key=lambda path: path.name.casefold())
    rows = []
    counts = Counter()
    variant_counts = Counter()
    planned = []
    seen_source: set[str] = set()

    for source_path in source_files:
        row = audit_row(source_path.name)
        folded = source_path.name.casefold()
        if folded in seen_source:
            row.update(status="skipped-duplicate-source", reason="duplicate source basename")
            counts[row["status"]] += 1
            rows.append(row)
            continue
        seen_source.add(folded)
        if folded in existing:
            row.update(status="existing", reason="service-reference filename already present in PiconHub")
            counts[row["status"]] += 1
            rows.append(row)
            continue
        key = parse_service_ref(source_path.name)
        if not key:
            row.update(status="skipped-invalid-filename", reason="invalid service-reference filename")
            counts[row["status"]] += 1
            rows.append(row)
            continue
        position = orbital_position(key[1])
        row["position"] = position or ""
        if not position:
            row.update(status="skipped-unknown-position", reason="unknown/non-satellite namespace")
            counts[row["status"]] += 1
            rows.append(row)
            continue
        dimensions = png_dimensions(source_path)
        if dimensions != SIZE:
            row.update(status="skipped-nonstandard-source", reason=f"PNG dimensions/format {dimensions}")
            counts[row["status"]] += 1
            rows.append(row)
            continue
        exact_reference_matches = []
        try:
            with Image.open(source_path) as raw:
                source_pixels = hashlib.sha256(raw.convert("RGBA").tobytes()).hexdigest()
        except Exception:
            source_pixels = ""
        for match in reference_by_filename.get(folded, []):
            if rgba_sha256(match["transparent"]) == source_pixels:
                exact_reference_matches.append(match)
        if len(exact_reference_matches) == 1:
            approved_match = exact_reference_matches[0]
            approved_transparent = approved_match["transparent"]
            approved_parts = approved_transparent.relative_to(reference_root).parts
            if len(approved_parts) != 5 or approved_parts[0] != "picons" or approved_parts[3] != "transparent":
                raise SystemExit(f"Invalid approved reference path: {approved_transparent}")
            position, provider = approved_parts[1], approved_parts[2]
            filename = approved_transparent.name
            transparent = picon_root / position / provider / "transparent" / filename
            black = picon_root / position / provider / "black" / filename
            white = picon_root / position / provider / "white" / filename
            for destination in (transparent, black, white):
                if destination.exists():
                    raise SystemExit(f"Refusing to overwrite existing file: {destination}")
            row.update(
                filename=filename,
                position=position,
                provider=provider,
                provider_method="approved-service-reference",
                source_sha256=sha256(source_path),
                source_qc="APPROVED-REUSE",
                black_qc="APPROVED-REUSE",
                white_qc="APPROVED-REUSE",
                variant_method="approved-service-reference",
                status="planned" if args.dry_run else "added",
                transparent_destination=transparent.relative_to(root).as_posix(),
                black_destination=black.relative_to(root).as_posix(),
                white_destination=white.relative_to(root).as_posix(),
                reason="exact service-reference and RGBA match on approved QC branch",
            )
            counts[row["status"]] += 1
            variant_counts["APPROVED-REUSE"] += 2
            rows.append(row)
            planned.append((source_path, transparent, black, white, None, approved_match))
            continue
        provider, provider_method, provider_reason = choose_provider(
            key, exact, service, repository_service
        )
        row.update(provider=provider, provider_method=provider_method)
        if not provider:
            row.update(status="skipped-unresolved-provider", reason=provider_reason)
            counts[row["status"]] += 1
            rows.append(row)
            continue
        row["source_sha256"] = sha256(source_path)
        try:
            with Image.open(source_path) as raw:
                if raw.format != "PNG":
                    raise ValueError("not PNG")
                image = raw.convert("RGBA")
                image.load()
        except Exception as error:
            row.update(status="skipped-source-error", source_qc="SOURCE-ERROR", reason=str(error))
            counts[row["status"]] += 1
            rows.append(row)
            continue
        source_status, source_reason, _metrics = source_qc(image)
        row["source_qc"] = source_status
        if source_status != "PASS":
            row.update(status="review-source", reason=source_reason)
            counts[row["status"]] += 1
            rows.append(row)
            continue

        approved_match, approved_reason = unique_approved_match(image, reference_index)
        if approved_match is not None:
            results = None
            row["black_qc"] = "APPROVED-REUSE"
            row["white_qc"] = "APPROVED-REUSE"
            row["variant_method"] = "approved-rgba-reuse"
            variant_counts["APPROVED-REUSE"] += 2
        else:
            try:
                fitted, scale, source_bbox = render.fit_logo(image)
                if hasattr(render, "fit_geometry_mask"):
                    centering_mask = render.fit_geometry_mask(image, source_bbox, scale)
                    results = {
                        style: render.classify_and_render(
                            fitted, masters[style], style, centering_mask=centering_mask
                        )
                        for style in ("black", "white")
                    }
                else:
                    results = {
                        style: render.classify_and_render(fitted, masters[style], style)
                        for style in ("black", "white")
                    }
            except Exception as error:
                row.update(
                    status="review-variant",
                    black_qc="ERROR-SKIP",
                    white_qc="ERROR-SKIP",
                    reason=f"renderer fail-closed: {type(error).__name__}: {error}",
                )
                counts[row["status"]] += 1
                variant_counts["ERROR-SKIP"] += 2
                rows.append(row)
                continue
            row["black_qc"] = results["black"].status
            row["white_qc"] = results["white"].status
            row["variant_method"] = "frozen-v9-renderer"
            variant_counts.update(result.status for result in results.values())
            family_status = overall_status(results)
            if family_status == "REVIEW":
                row.update(
                    status="review-variant",
                    reason=(
                        f"{approved_reason} | BLACK: {results['black'].reason} | "
                        f"WHITE: {results['white'].reason}"
                    ),
                )
                counts[row["status"]] += 1
                rows.append(row)
                continue
            if family_status == "ERROR-SKIP":
                row.update(status="skipped-variant-error", reason="renderer returned ERROR-SKIP")
                counts[row["status"]] += 1
                rows.append(row)
                continue

        transparent = picon_root / position / provider / "transparent" / source_path.name
        black = picon_root / position / provider / "black" / source_path.name
        white = picon_root / position / provider / "white" / source_path.name
        for destination in (transparent, black, white):
            if destination.exists():
                raise SystemExit(f"Refusing to overwrite existing file: {destination}")
        row.update(
            status="planned" if args.dry_run else "added",
            transparent_destination=transparent.relative_to(root).as_posix(),
            black_destination=black.relative_to(root).as_posix(),
            white_destination=white.relative_to(root).as_posix(),
            reason="; ".join(value for value in (provider_reason, approved_reason if approved_match else "") if value),
        )
        counts[row["status"]] += 1
        rows.append(row)
        planned.append((source_path, transparent, black, white, results, approved_match))

    if not args.dry_run:
        for source_path, transparent, black, white, results, approved_match in planned:
            for destination in (transparent, black, white):
                destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, transparent)
            if approved_match is not None:
                shutil.copy2(approved_match["black"], black)
                shutil.copy2(approved_match["white"], white)
            else:
                results["black"].image.save(black, format="PNG")
                results["white"].image.save(white, format="PNG")

        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "import-report.tsv.gz"
        with gzip.open(report_path, "wt", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(audit_row("").keys()), delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "dry-run" if args.dry_run else "apply",
        "baseline_commit": args.baseline_commit,
        "source_archive": args.source_archive,
        "source_archive_sha256": args.source_archive_sha256,
        "settings_archive_sha256": args.settings_archive_sha256,
        "source_png": len(source_files),
        "existing_preserved": counts["existing"],
        "complete_triplets_added": counts["planned"] if args.dry_run else counts["added"],
        "files_added": (counts["planned"] if args.dry_run else counts["added"]) * 3,
        "source_review": counts["review-source"],
        "variant_review": counts["review-variant"],
        "skipped_unknown_position": counts["skipped-unknown-position"],
        "skipped_nonstandard_source": counts["skipped-nonstandard-source"],
        "skipped_unresolved_provider": counts["skipped-unresolved-provider"],
        "skipped_invalid_filename": counts["skipped-invalid-filename"],
        "provider_lamedb_exact": sum(1 for row in rows if row["provider_method"] == "lamedb-exact"),
        "provider_lamedb_service": sum(1 for row in rows if row["provider_method"] == "lamedb-service"),
        "provider_repository_service": sum(1 for row in rows if row["provider_method"] == "repository-service"),
        "provider_approved_service_reference": sum(
            1 for row in rows if row["provider_method"] == "approved-service-reference"
        ),
        "variant_status_counts": dict(sorted(variant_counts.items())),
        "approved_reference_triplets": reference_triplets,
        "approved_reference_commit": args.approved_reference_commit,
        "triplets_reused_from_approved_rgba": sum(
            1 for row in rows if row["variant_method"] == "approved-rgba-reuse" and row["status"] in {"planned", "added"}
        ),
        "triplets_reused_from_approved_service_reference": sum(
            1 for row in rows if row["variant_method"] == "approved-service-reference" and row["status"] in {"planned", "added"}
        ),
        "triplets_created_by_renderer": sum(
            1 for row in rows if row["variant_method"] == "frozen-v9-renderer" and row["status"] in {"planned", "added"}
        ),
        "settings_lamedb_files": len(lamedbs),
        "settings_commit": args.settings_commit,
        "renderer_commit": args.renderer_commit,
        "renderer_sha256": sha256(renderer_path),
        "master_sha256": EXPECTED_MASTER_SHA256,
        "existing_overwritten": 0,
        "plugin_or_gui_files_changed": 0,
    }
    if not args.dry_run:
        summary["report_sha256"] = sha256(report_path)
    if not args.dry_run:
        summary_path = report_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--settings", type=Path, required=True)
    parser.add_argument("--renderer", type=Path, required=True)
    parser.add_argument("--settings-commit", required=True)
    parser.add_argument("--renderer-commit", required=True)
    parser.add_argument("--approved-reference", type=Path)
    parser.add_argument("--approved-reference-commit", default="")
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--baseline-commit", required=True)
    parser.add_argument("--source-archive", required=True)
    parser.add_argument("--source-archive-sha256", required=True)
    parser.add_argument("--settings-archive-sha256", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
