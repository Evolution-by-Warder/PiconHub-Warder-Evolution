#!/usr/bin/env python3
"""Focused tests for the non-production hybrid auxiliary archive candidate."""
from __future__ import annotations

import hashlib
import json
import zipfile
from io import BytesIO
from pathlib import Path, PurePosixPath

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/warder-master-production/auxiliary-hybrid-runtime-candidate-2026-10-07"
GATE = ROOT / "reports/warder-master-production/auxiliary-publishability-gate-2026-10-07"
ARCHIVES = OUT / "archives"
LEGACY_INPUTS = {
    ("provider", "transparent"): Path("/tmp/piconhub-provider-transparent.zip"),
    ("provider", "black"): Path("/tmp/aux-source-recovery-provider-black.zip"),
    ("provider", "white"): Path("/tmp/aux-source-recovery-provider-white.zip"),
    ("satellite", "transparent"): Path("/tmp/piconhub-satellite-transparent.zip"),
    ("satellite", "black"): Path("/tmp/aux-source-recovery-satellite-black.zip"),
    ("satellite", "white"): Path("/tmp/aux-source-recovery-satellite-white.zip"),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_archives_and_manifest():
    manifest = json.loads((OUT / "archive-manifest.json").read_text(encoding="utf-8"))
    safe_rows = read_jsonl(GATE / "publishability-manifest.jsonl")
    gate_qc = json.loads((GATE / "qc-summary.json").read_text(encoding="utf-8"))
    safe = {}
    for row in safe_rows:
        domain = "provider" if row["domain"] == "provider-logo" else "satellite"
        safe[(domain, row["identity_filename"])] = row
    assert gate_qc["status"] == "PASS"
    assert gate_qc["review_or_unresolved_files_present"] == 0
    assert gate_qc["review_or_unresolved_identities_in_tree"] == 0
    assert len(safe) == 173
    assert len(manifest["archives"]) == 8

    expected_counts = {
        "provider-transparent-legacy-fallback.zip": (1145, "piconProv", "LEGACY_FALLBACK"),
        "satellite-transparent-legacy-fallback.zip": (69, "piconSat", "LEGACY_FALLBACK"),
    }
    expected_safe = {
        "provider": (172, "piconProv_220x132"),
        "satellite": (1, "piconSat_220x132"),
    }
    # Pinned legacy archives remain byte-identical inputs. Transparent fallback
    # repacks may change ZIP bytes and member paths, but not any PNG payload.
    for (domain, variant), src in LEGACY_INPUTS.items():
        with zipfile.ZipFile(src) as archive:
            source_pngs = {
                PurePosixPath(name).name: sha(archive.read(name))
                for name in archive.namelist()
                if name.lower().endswith(".png")
            }
        if variant == "transparent":
            candidate = ARCHIVES / f"{domain}-transparent-legacy-fallback.zip"
            with zipfile.ZipFile(candidate) as archive:
                candidate_pngs = {
                    PurePosixPath(name).name: sha(archive.read(name))
                    for name in archive.namelist()
                    if name.lower().endswith(".png")
                }
            assert candidate_pngs == source_pngs
        else:
            pin = json.loads((ROOT / "reports/warder-master-production/auxiliary-coverage-impact-2026-10-07/summary.json").read_text())
            record = pin["archives"][f"{domain}-{variant}"]
            assert len(src.read_bytes()) == record["size_bytes"]
            assert sha(src.read_bytes()) == record["sha256"]
            assert len(source_pngs) == record["png_count"]
    for filename, item in manifest["archives"].items():
        path = ARCHIVES / filename
        raw = path.read_bytes()
        assert len(raw) == item["size_bytes"]
        assert sha(raw) == item["sha256"]
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None
            members = [m for m in archive.namelist() if m.lower().endswith(".png")]
            assert len(members) == item["png_count"]
            names = [PurePosixPath(m).name for m in members]
            assert len(names) == len(set(names))
            if item["layer"] == "WARDER_SAFE_PRIORITY":
                count, root = expected_safe[item["domain"]]
                assert len(members) == count
                assert all(m.startswith(root + "/") for m in members)
                for member in members:
                    data = archive.read(member)
                    with Image.open(BytesIO(data)) as image:
                        image.load()
                        assert image.format == "PNG" and image.size == (220, 132) and image.mode == "RGBA"
                    row = safe[(item["domain"], PurePosixPath(member).name)]
                    assert row["qc_status"][item["variant"]] in ("PASS", "AUTO-FIXED")
                    assert sha(data) == row[item["variant"] + "_sha256"]
            elif filename in expected_counts:
                count, root, layer = expected_counts[filename]
                assert item["png_count"] == count and item["destination"] == root and item["layer"] == layer
                assert all(m.startswith(root + "/") for m in members)


def test_candidate_contract():
    mapping = json.loads((OUT / "candidate-downloads.json").read_text(encoding="utf-8"))
    assert mapping["size_selector"] is False
    assert mapping["no_destructive_cleanup"] is True
    for domain, base, priority in (
        ("provider", "piconProv", "piconProv_220x132"),
        ("satellite", "piconSat", "piconSat_220x132"),
    ):
        item = mapping["domains"][domain]
        assert item["lookup_priority"] == [priority, base]
        for variant in ("transparent", "black", "white"):
            plan = item["variants"][variant]
            assert plan["install_order"] == ["legacy_fallback", "warder_safe_priority"]
            assert plan["fallback"]["destination"] == base
            assert plan["safe_priority"]["destination"] == priority
            assert plan["safe_priority"]["png_count"] == (172 if domain == "provider" else 1)
    coverage = json.loads((OUT / "lookup-coverage.json").read_text(encoding="utf-8"))
    for domain in coverage.values():
        for variant in domain.values():
            assert variant["legacy_current_identities_preserved"] is True
    design = (OUT / "hybrid-runtime-design.md").read_text(encoding="utf-8")
    assert "Never remove, rename, or recursively replace" in design
    assert "piconProv_220x132/" in design and "piconSat_220x132/" in design


if __name__ == "__main__":
    test_archives_and_manifest()
    test_candidate_contract()
    print("PASS: hybrid archive counts, SHA/CRC, safe identity isolation, destinations, priority, and additive fallback")
