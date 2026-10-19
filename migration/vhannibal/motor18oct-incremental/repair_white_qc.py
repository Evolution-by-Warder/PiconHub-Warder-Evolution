#!/usr/bin/env python3
"""Repair visually rejected WHITE variants in the Vhannibal 18-Oct delta.

The full 174-triplet delta was inspected side-by-side.  This repair is bound
to exact RGBA source digests, writes WHITE outputs only, and uses the pinned
Warder V9 renderer.  Five logo families require a small protected region so
white lettering inside a coloured/local brand panel is not recoloured.
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


SIZE = (220, 132)
WHITE_MASTER_SHA256 = "c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589"

# source RGBA digest: (repair policy, expected service-reference count)
SOURCE_RULES = {
    "860b12f43996986bf77e26098cff35423a1812da6fdfff7ed7ba5831cf9ca689": ("v9-direct", 1),
    "c9cf69aef5ca1a8f72d71ff853972918bbed972c22fc1d02709cafea38f47256": ("v9-direct", 1),
    "3844c72a8532dd873efb5c1b05120b244475a16524946af0d610193fa28c0d95": ("private-panel", 3),
    "a83815e1c66e8960d6bfa0b06c1bee696728ae643d3fc5f66dce41d3491087d6": ("v9-direct", 2),
    "36bd504a2fcbefa4c334aa6f848a5f7299fb93b4198ab80f245dc4e07fb5ae08": ("v9-direct", 1),
    "b38758f0bc0b4f382002974d719e46283f0a5c4459b8ed012dc9dab55f69f24d": ("eurosport-number", 1),
    "c2cee750b2867e099c931ca03715a49f8c6335ff658a1b9a9ac5318a678f1a14": ("eurosport-number", 2),
    "60e699c8920286bb918f381670d930d868057be885233b33c1f7eef1f66cbb46": ("v9-direct", 1),
    "05f80aa05aaad09c079c3ad48e0bba0e4b2498fc792b7d1799f1ce7130eb6e91": ("eurosport-number", 2),
    "913954cecb43f67b9615f1f31c3bc0d7fda649cb6e1d7cfec24cf051046c1d39": ("v9-direct", 4),
    "1d3f45acad953662ca8274ef07b35d1aafb417d5a744b1e983ed26a19e2f530e": ("v9-direct", 1),
    "0066dc106ed3b8c830c7e40cc781538180c4918b29cfb9b6938880ca75f83af1": ("mtv-panel", 2),
    "9a6fa3651310b25efc08e93af1e3c358057722486d3eecdc633d7b4ed5fd9d84": ("v9-direct", 1),
    "61f99087c4ea6530f56d1c47035ccd37ed7386266d1856013450f8f31058ccb8": ("v9-direct", 1),
    "0bd4aa47ebb9cdcef304c715ec0d619f89c94075a1c177b15badd59c2662774d": ("v9-direct", 1),
    "9d9d8b1ce6b60e87cb9d4bcfe10ee993491bd804a48e2b25596a2a5f18fbe7f5": ("v9-direct", 36),
    "d00e4af55d54268212984b8f7d261bb1c1aa803770b0793f0cd712c2141d6c63": ("v9-direct", 1),
    "7bcf07cdf4b1c473b71356659f767804feb75303df6b1f3240b5c38dc7f6253c": ("v9-direct", 1),
    "c801816f805138a39779fb9538d11b7cbaccea23729e79ed32c57f9ae0a140ec": ("v9-direct", 1),
    "87eaaca7c45a7df164421b1c87fd39877e95e229c5c3846372d871212b136512": ("v9-direct", 1),
    "b21cc85c8b9a6a835f23f8adfd794f36b298ede40f2d4a9175e42d5aaf45f3d4": ("fon-panel", 1),
    "626b44c3978a7da2e60e7137738d576ea84561a3188f2e2c69adc1ce7941e19a": ("v9-direct", 1),
    "0334a603ad3a278ba6bb0f95236056877ea95e2498a7f8dc32375af46252c43e": ("cn-panel", 1),
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
    spec = importlib.util.spec_from_file_location("warder_white_qc_renderer", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load renderer: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def protect_local_panel(candidate: np.ndarray, current: np.ndarray, policy: str) -> int:
    yy, xx = np.indices(candidate.shape[:2])
    if policy == "private-panel":
        mask = (xx >= 28) & (xx < 135) & (yy >= 18) & (yy < 105)
    elif policy == "eurosport-number":
        mask = (xx >= 180) & (xx < 204) & (yy >= 52) & (yy < 80)
    elif policy == "mtv-panel":
        mask = (xx >= 30) & (xx < 190) & (yy >= 4) & (yy < 109)
    elif policy == "fon-panel":
        mask = (xx >= 10) & (xx < 210) & (yy >= 85) & (yy < 132)
    elif policy == "cn-panel":
        mask = (xx >= 8) & (xx < 148) & (yy >= 20) & (yy < 95)
    else:
        return 0
    changed = np.any(candidate != current, axis=2)
    restore = mask & changed
    candidate[restore] = current[restore]
    return int(restore.sum())


def load_added_rows(report: Path) -> list[dict[str, str]]:
    with gzip.open(report, "rt", encoding="utf-8", newline="") as handle:
        rows = [row for row in csv.DictReader(handle, delimiter="\t") if row["status"] == "added"]
    rows.sort(key=lambda row: (row["position"], row["provider"], row["filename"]))
    if len(rows) != 174:
        raise SystemExit(f"Expected 174 added triplets, found {len(rows)}")
    return rows


def run(args: argparse.Namespace) -> dict[str, object]:
    root = args.repo.resolve()
    renderer_path = args.renderer.resolve()
    report_dir = root / "migration/vhannibal/motor18oct-incremental"
    rows = load_added_rows(report_dir / "import-report.tsv.gz")
    renderer = load_renderer(renderer_path)

    master_path = root / "templates/picons/white-sablona.png"
    if sha256_file(master_path) != WHITE_MASTER_SHA256:
        raise SystemExit("Immutable WHITE master hash mismatch")
    with Image.open(master_path) as image:
        master = image.convert("RGBA")

    immutable_before = {
        root / row[key]: sha256_file(root / row[key])
        for row in rows
        for key in ("transparent_destination", "black_destination")
    }
    records = []
    selected_counts: Counter[str] = Counter()

    for row in rows:
        transparent = root / row["transparent_destination"]
        white = root / row["white_destination"]
        with Image.open(transparent) as image:
            source = image.convert("RGBA")
        source_digest = rgba_sha256(source)
        rule = SOURCE_RULES.get(source_digest)
        if rule is None:
            continue
        policy, _expected = rule
        selected_counts[source_digest] += 1

        fitted, scale, source_bbox = renderer.fit_logo(source)
        geometry = renderer.fit_geometry_mask(source, source_bbox, scale)
        result = renderer.classify_and_render(fitted, master, "white", centering_mask=geometry)
        candidate = np.array(result.image.convert("RGBA"), dtype=np.uint8)
        with Image.open(white) as image:
            current = np.array(image.convert("RGBA"), dtype=np.uint8)
        old_sha256 = sha256_file(white)
        restored = protect_local_panel(candidate, current, policy)
        final = Image.fromarray(candidate, "RGBA")
        if args.apply:
            final.save(white, "PNG")
        new_sha256 = sha256_file(white) if args.apply else hashlib.sha256(final.tobytes()).hexdigest()
        records.append({
            "position": row["position"],
            "provider": row["provider"],
            "filename": row["filename"],
            "white_output": row["white_destination"],
            "source_rgba_sha256": source_digest,
            "policy": policy,
            "renderer_status": result.status,
            "renderer_changed_pixels": result.changed_pixels,
            "protected_pixels_restored": restored,
            "old_sha256": old_sha256,
            "new_sha256": new_sha256,
            "result": "FIXED_QA_PASS" if args.apply else "DRY_RUN",
        })

    expected_counts = Counter({digest: count for digest, (_policy, count) in SOURCE_RULES.items()})
    if selected_counts != expected_counts:
        raise SystemExit(f"Source binding/count mismatch: {selected_counts} != {expected_counts}")
    if len(records) != 67:
        raise SystemExit(f"Expected 67 WHITE repairs, selected {len(records)}")

    for path, expected in immutable_before.items():
        if sha256_file(path) != expected:
            raise SystemExit(f"Immutable transparent/BLACK file changed: {path}")
    if sha256_file(master_path) != WHITE_MASTER_SHA256:
        raise SystemExit("WHITE master changed during repair")

    if args.apply:
        for record in records:
            path = root / str(record["white_output"])
            with Image.open(path) as image:
                if image.size != SIZE or image.mode != "RGBA":
                    raise SystemExit(f"Invalid repaired output: {path}: {image.size} {image.mode}")
        report_path = report_dir / "white-qc-repair.tsv"
        with report_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=records[0].keys(), delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(records)
        summary = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "scope_triplets_inspected": 174,
            "white_variants_inspected": 174,
            "black_variants_inspected": 174,
            "white_variants_repaired": 67,
            "unique_artworks_repaired": 23,
            "white_variants_unchanged": 107,
            "black_variants_changed": 0,
            "transparent_sources_changed": 0,
            "master_files_changed": 0,
            "plugin_gui_skin_files_changed": 0,
            "renderer_sha256": sha256_file(renderer_path),
            "white_master_sha256": WHITE_MASTER_SHA256,
            "repair_report_sha256": sha256_file(report_path),
        }
        (report_dir / "white-qc-summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return summary
    return {"mode": "dry-run", "selected": len(records)}


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
