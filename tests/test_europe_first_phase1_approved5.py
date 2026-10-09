#!/usr/bin/env python3
"""Regression gate for the Europe First approved-five staging catalog."""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import auxiliary_catalog as catalog  # noqa: E402

EVIDENCE = ROOT / "reports/warder-master-production/europe-first-phase1-approved5-2026-10-09/approved5-assets.json"
CATALOG = ROOT / "catalog/auxiliary-catalog.json"
ORIGINAL_CATALOG = ROOT / "reports/auxiliary-production-integration-2026-10-08/auxiliary-catalog.json"
ORIGINAL_CATALOG_SHA256 = "6631f646ed3d51a1e84317c9e3a45456b48c002781dc7338442e5c4d26b3a754"
BASE_MANIFEST = ROOT / "reports/warder-master-production/auxiliary-centering-2026-10-08/sha256-manifest.jsonl"
EXPECTED = {
    "Skylink": "SKYLINK.png",
    "freeSAT": "FREESAT.png",
    "Focus Sat": "FOCUS_SAT.png",
    "DigitAlb": "DIGITALB.png",
    "Tring": "TRING.png",
}


def normalized(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def main() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["source_archive"]["sha256"] == "44730735b69b46b58596ba1c509a4c0e3a21ffd52c82b91f77c32e66bfa637fb"
    assert evidence["user_visual_approval"]["status"] == "APPROVED 5/5"
    assert {item["identity"]: item["filename"] for item in evidence["assets"]} == EXPECTED

    old_names = set()
    old_provider_count = 0
    for line in BASE_MANIFEST.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("type") == "transparent-master" and row["identity"].startswith("provider-logo::"):
            old_names.add(row["identity"].split("::", 1)[1])
            old_provider_count += 1
    assert old_provider_count == 172
    assert not old_names.intersection(f"provider-logo::{filename}" for filename in EXPECTED.values())
    old_normalized = {normalized(Path(name).stem) for name in old_names}
    candidate_normalized = [normalized(Path(filename).stem) for filename in EXPECTED.values()]
    assert len(candidate_normalized) == len(set(candidate_normalized))
    assert not old_normalized.intersection(candidate_normalized)

    loaded = catalog.load_catalog(CATALOG, ROOT)
    assert len(loaded.entries) == 178
    provider_ids = {identity for (kind, identity) in loaded.entries if kind == "provider-logo"}
    satellite_ids = {identity for (kind, identity) in loaded.entries if kind == "satellite-logo"}
    assert len(provider_ids) == 177
    assert satellite_ids == {"150W.png"}

    # Extending the catalog must retain the original identity and approval
    # provenance fields for every pre-existing approved identity.
    original_bytes = ORIGINAL_CATALOG.read_bytes()
    assert hashlib.sha256(original_bytes).hexdigest() == ORIGINAL_CATALOG_SHA256
    original = json.loads(original_bytes)
    original_entries = {(row["kind"], row["filename"]): row for row in original["entries"]}
    staged_entries = loaded.entries
    assert len(original_entries) == 173
    assert set(original_entries).issubset(staged_entries)
    preserved_fields = (
        "identity", "kind", "filename", "black", "white",
        "transparent_source_sha256", "qc_status", "visual_approval_provenance",
    )
    for key, source_entry in original_entries.items():
        staged_entry = staged_entries[key]
        for field in preserved_fields:
            assert staged_entry[field] == source_entry[field], (key, field)

    expected_new_keys = {("provider-logo", filename) for filename in EXPECTED.values()}
    assert set(staged_entries) - set(original_entries) == expected_new_keys

    for item in evidence["assets"]:
        key = ("provider-logo", item["filename"])
        assert key in loaded.entries
        entry = loaded.entries[key]
        assert entry["transparent_source_sha256"] == item["source_master_sha256"]
        for variant in ("black", "white"):
            path = ROOT / "auxiliary/provider-logo" / variant / item["filename"]
            data = path.read_bytes()
            assert hashlib.sha256(data).hexdigest() == item[variant]["sha256"]
            assert entry[variant]["sha256"] == item[variant]["sha256"]
            with Image.open(path) as image:
                image.load()
                assert image.format == "PNG" and image.mode == "RGBA" and image.size == (220, 132)

    print("PASS: ZIP approval pin, identity uniqueness, 177 Provider / 1 Satellite catalog, all PNG pairs and SHA256 pins")


if __name__ == "__main__":
    main()
