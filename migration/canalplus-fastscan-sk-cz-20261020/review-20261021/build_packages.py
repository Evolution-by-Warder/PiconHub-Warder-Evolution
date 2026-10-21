#!/usr/bin/env python3
"""Bundle existing PNG bytes only; never generate or replace runtime artwork."""
import hashlib
import json
from pathlib import Path
import zipfile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
STYLES = ("transparent", "white", "black")
report = json.loads((OUT / "audit.json").read_text())
for market, expected in report["packages"].items():
    provider = "canal-plus-" + market
    base = ROOT / "picons/23.5e" / provider
    contents = []
    for style in STYLES:
        files = sorted((base / style).glob("*.png"))
        assert len(files) == expected["service_references"]
        contents.extend((path, provider + "/" + style + "/" + path.name) for path in files)
        operator = ROOT / "migration/canalplus-provider-rebrand-20261022/prepared/provider-logo" / style / "CANAL+.png"
        contents.append((operator, provider + "/provider-logo/" + style + "/CANAL+.png"))
    archive = OUT / expected["archive"]
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as output:
        for path, name in contents:
            info = zipfile.ZipInfo(name, (2026, 10, 21, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            output.writestr(info, path.read_bytes())
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == expected["sha256"]
    with zipfile.ZipFile(archive) as check:
        assert check.testzip() is None
        for path, name in contents:
            assert check.read(name) == path.read_bytes()
    print(market, len(contents), "original PNGs; ZIP SHA-256 verified")
