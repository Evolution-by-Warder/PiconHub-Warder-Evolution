#!/usr/bin/env python3
"""Conservative SOURCE-QC preflight for Warder MASTER production.

This scanner runs BEFORE BLACK/WHITE generation. It never modifies transparent
sources. Suspected fake-transparent / opaque-background sources are quarantined
as SOURCE-REVIEW and written to a recovery list for later identity-safe web
recovery. Ambiguous cases are never auto-approved.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

SIZE = (220, 132)
SERVICE_REF = re.compile(r"^[0-9A-F]+(?:_[0-9A-F]+){9}\.png$")

# Conservative source-only thresholds. These are detection gates, not visual
# recolour rules. A hit becomes SOURCE-REVIEW, never an automatic deletion.
OPAQUE = 250
NEAR_TRANSPARENT = 5
RECT_FILL_REVIEW = 0.94
RECT_EDGE_REVIEW = 0.94
RECT_CORNER_REVIEW = 0.75
MIN_RECT_AREA = 0.08
FULL_CANVAS_OPAQUE_REVIEW = 0.90


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rectangular_background_signals(rgba: Image.Image) -> tuple[list[str], dict]:
    a = np.asarray(rgba.getchannel("A"), dtype=np.uint8)
    visible = a > NEAR_TRANSPARENT
    ys, xs = np.where(visible)
    if len(xs) == 0:
        return ["empty alpha/fully transparent source"], {}

    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    box = a[y0:y1, x0:x1]
    opaque = box >= OPAQUE
    box_area = box.size
    canvas_area = a.size
    fill = float(np.mean(opaque))
    area_fraction = box_area / canvas_area

    edge = np.concatenate((opaque[0, :], opaque[-1, :], opaque[:, 0], opaque[:, -1]))
    edge_fraction = float(np.mean(edge)) if edge.size else 0.0
    corners = np.array([opaque[0,0], opaque[0,-1], opaque[-1,0], opaque[-1,-1]], dtype=float)
    corner_fraction = float(np.mean(corners))
    canvas_opaque_fraction = float(np.mean(a >= OPAQUE))

    metrics = {
        "bbox": f"{x0},{y0},{x1},{y1}",
        "bbox_area_fraction": round(area_fraction, 6),
        "bbox_opaque_fill": round(fill, 6),
        "bbox_opaque_edge_fraction": round(edge_fraction, 6),
        "bbox_opaque_corner_fraction": round(corner_fraction, 6),
        "canvas_opaque_fraction": round(canvas_opaque_fraction, 6),
    }

    reasons: list[str] = []
    # Strong rectangle signature: almost all pixels inside the visible bbox are
    # opaque and the complete bbox perimeter/corners are opaque. Legitimate
    # rectangular badges can match, so this is REVIEW, not automatic ERROR.
    if (area_fraction >= MIN_RECT_AREA and fill >= RECT_FILL_REVIEW
            and edge_fraction >= RECT_EDGE_REVIEW
            and corner_fraction >= RECT_CORNER_REVIEW):
        reasons.append("suspected opaque rectangular background in transparent source")
    if canvas_opaque_fraction >= FULL_CANVAS_OPAQUE_REVIEW:
        reasons.append("source is almost fully opaque across the 220x132 canvas")
    return reasons, metrics


def inspect(path: Path, picon_root: Path) -> dict:
    rel = path.relative_to(picon_root.parent).as_posix()
    parts = path.relative_to(picon_root).parts
    position = parts[0] if len(parts) > 0 else ""
    provider = parts[1] if len(parts) > 1 else ""
    sha = sha256_file(path)
    reasons: list[str] = []
    metrics: dict = {}

    if len(parts) != 4 or parts[2] != "transparent":
        reasons.append("invalid source path architecture")
    if not SERVICE_REF.fullmatch(path.name):
        reasons.append("invalid service-reference filename")

    try:
        with Image.open(path) as raw:
            if raw.format != "PNG": reasons.append("not PNG")
            if raw.size != SIZE: reasons.append(f"invalid dimensions {raw.size[0]}x{raw.size[1]}")
            rgba = raw.convert("RGBA")
            rgba.load()
    except Exception as exc:
        reasons.append(f"decode error: {exc}")
        rgba = None

    if rgba is not None:
        alpha = np.asarray(rgba.getchannel("A"), dtype=np.uint8)
        if not np.any(alpha > 0):
            reasons.append("empty alpha/fully transparent source")
        else:
            fake_reasons, metrics = rectangular_background_signals(rgba)
            reasons.extend(fake_reasons)

    hard = any(r.startswith(("decode error", "invalid dimensions", "not PNG", "empty alpha", "invalid source path", "invalid service")) for r in reasons)
    status = "SOURCE-ERROR" if hard else ("SOURCE-REVIEW" if reasons else "PASS")
    return {
        "source": rel,
        "satellite_position": position,
        "provider": provider,
        "service_reference": path.name,
        "source_sha256": sha,
        "source_status": status,
        "source_reason": "; ".join(dict.fromkeys(reasons)),
        "recovery_status": "RECOVERY-SEARCH" if status != "PASS" else "",
        "recovery_source_url": "",
        "recovery_note": "",
        **metrics,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path.cwd())
    args = ap.parse_args()
    root = args.root.resolve()
    picon_root = root / "picons"
    report_dir = root / "reports" / "warder-master-production" / "source-qc"
    report_dir.mkdir(parents=True, exist_ok=True)

    sources = sorted(picon_root.glob("*/*/transparent/*.png"))
    rows = [inspect(p, picon_root) for p in sources]
    counts = Counter(r["source_status"] for r in rows)

    # Duplicate SHA groups are explicitly retained per service-reference.
    sha_groups = defaultdict(list)
    for r in rows:
        sha_groups[r["source_sha256"]].append(r["source"])
    duplicate_sha_groups = {k:v for k,v in sha_groups.items() if len(v) > 1}

    fields = sorted({k for r in rows for k in r.keys()})
    with (report_dir / "source-audit.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader(); w.writerows(rows)

    recovery = [r for r in rows if r["source_status"] != "PASS"]
    with (report_dir / "recovery-list.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader(); w.writerows(recovery)

    summary = {
        "transparent_sources": len(rows),
        "source_status_counts": dict(counts),
        "recovery_items": len(recovery),
        "duplicate_sha_groups": len(duplicate_sha_groups),
        "policy": "SOURCE-REVIEW/ERROR items are quarantined before BLACK/WHITE generation; no source is modified or deleted",
    }
    (report_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    (report_dir / "duplicate-sha.json").write_text(json.dumps(duplicate_sha_groups, indent=2, sort_keys=True)+"\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))
    # Nonzero when quarantine exists: callers must not proceed to generation.
    return 2 if recovery else 0


if __name__ == "__main__":
    raise SystemExit(main())
