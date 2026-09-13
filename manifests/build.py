#!/usr/bin/env python3
"""Build PiconHub v2 manifests from the canonical picon tree.

Input:
    picons/<satellite>/<provider>/<variant>/*.png
Output:
    manifests/<satellite>/<provider>/<variant>.json
    manifests/index.json

No intermediate `satellite` directory is supported.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PICONS = ROOT / "picons"
MANIFESTS = ROOT / "manifests"
VARIANTS = ("transparent", "white", "black")
RAW_BASE = "https://raw.githubusercontent.com/PiconHub-Warder/piconhub-server/main"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def service_reference(filename: str) -> str:
    name = filename[:-4] if filename.lower().endswith(".png") else filename
    return name.replace("_", ":")


def clean_generated_manifests() -> None:
    for child in MANIFESTS.iterdir():
        if child.name in {"README.md", "build.py"}:
            continue
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            import shutil
            shutil.rmtree(str(child))


def main() -> None:
    MANIFESTS.mkdir(parents=True, exist_ok=True)
    clean_generated_manifests()

    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    index = {
        "schema": 2,
        "generated": generated,
        "layout": "manifests/{satellite}/{provider}/{variant}.json",
        "picon_layout": "picons/{satellite}/{provider}/{variant}/{file}",
        "variants": list(VARIANTS),
        "satellites": [],
        "manifest_count": 0,
        "picon_count": 0,
    }

    for sat_dir in sorted(p for p in PICONS.iterdir() if p.is_dir()):
        sat_item = {"position": sat_dir.name, "providers": []}
        for provider_dir in sorted(p for p in sat_dir.iterdir() if p.is_dir()):
            provider_item = {"id": provider_dir.name, "variants": {}}
            any_variant = False
            for variant in VARIANTS:
                variant_dir = provider_dir / variant
                if not variant_dir.is_dir():
                    continue
                files = sorted(p for p in variant_dir.iterdir() if p.is_file() and p.suffix.lower() == ".png")
                if not files:
                    continue
                entries = []
                for path in files:
                    rel = path.relative_to(ROOT).as_posix()
                    entries.append({
                        "service_reference": service_reference(path.name),
                        "file": path.name,
                        "size": path.stat().st_size,
                        "sha256": sha256_file(path),
                        "url": "%s/%s" % (RAW_BASE, rel),
                    })
                payload = {
                    "schema": 2,
                    "generated": generated,
                    "satellite": sat_dir.name,
                    "provider": provider_dir.name,
                    "variant": variant,
                    "count": len(entries),
                    "picons": entries,
                }
                out = MANIFESTS / sat_dir.name / provider_dir.name / (variant + ".json")
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                provider_item["variants"][variant] = {
                    "count": len(entries),
                    "manifest": out.relative_to(ROOT).as_posix(),
                }
                index["manifest_count"] += 1
                index["picon_count"] += len(entries)
                any_variant = True
            if any_variant:
                sat_item["providers"].append(provider_item)
        if sat_item["providers"]:
            index["satellites"].append(sat_item)

    (MANIFESTS / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Generated %d manifests for %d picons" % (index["manifest_count"], index["picon_count"]))


if __name__ == "__main__":
    main()
