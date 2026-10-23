#!/usr/bin/env python3
import csv
import os
import re
import shutil
import struct
import sys
import unicodedata
from pathlib import Path

ROOT = Path(os.environ.get("GITHUB_WORKSPACE", Path(__file__).resolve().parents[2]))
PICON_ROOT = ROOT / "picons"
SOURCE_ROOT = Path(os.environ["VHANNIBAL_PICON_DIR"])
LAMEDB = Path(os.environ["VHANNIBAL_LAMEDB"])
REPORT = ROOT / "migration" / "vhannibal" / "import-report.tsv"


def hexint(value):
    return int(value, 16)


def slugify(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return value


def orbital_position(namespace):
    raw = (namespace >> 16) & 0xFFFF
    if raw <= 1800:
        return f"{raw / 10:.1f}e"
    if raw <= 3600:
        return f"{(3600 - raw) / 10:.1f}w"
    return None


def png_size(path):
    with path.open("rb") as fh:
        head = fh.read(24)
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", head[16:24])


def parse_lamedb(path):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    try:
        start = lines.index("services") + 1
    except ValueError:
        raise SystemExit("lamedb: missing services section")
    providers = {}
    i = start
    key_re = re.compile(r"^([0-9a-fA-F]+):([0-9a-fA-F]+):([0-9a-fA-F]+):([0-9a-fA-F]+):([0-9a-fA-F]+):")
    while i < len(lines):
        line = lines[i].strip()
        if line == "end":
            break
        m = key_re.match(line)
        if not m:
            i += 1
            continue
        sid, namespace, tsid, onid, stype = [hexint(x) for x in m.groups()]
        provider = ""
        if i + 2 < len(lines):
            attrs = lines[i + 2].strip()
            if attrs.startswith("p:"):
                provider = attrs[2:].split(",", 1)[0].strip()
        if provider:
            providers[(sid, namespace, tsid, onid, stype)] = provider
        i += 3
    return providers


def parse_picon_filename(name):
    stem = Path(name).stem
    parts = stem.split("_")
    if len(parts) < 7:
        return None
    try:
        stype = hexint(parts[2])
        sid = hexint(parts[3])
        tsid = hexint(parts[4])
        onid = hexint(parts[5])
        namespace = hexint(parts[6])
    except ValueError:
        return None
    return sid, namespace, tsid, onid, stype


def existing_basenames():
    return {p.name.lower() for p in PICON_ROOT.rglob("*.png")}


def run():
    providers = parse_lamedb(LAMEDB)
    existing = existing_basenames()
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    added = 0
    skipped_existing = 0
    skipped_unknown_position = 0
    skipped_size = 0
    skipped_provider = 0
    skipped_badname = 0

    source_files = sorted(SOURCE_ROOT.rglob("*.png"), key=lambda p: p.name.lower())
    for src in source_files:
        filename = src.name
        low = filename.lower()
        if low in existing:
            skipped_existing += 1
            rows.append(("existing", filename, "", "", "", "already present in PiconHub"))
            continue
        parsed = parse_picon_filename(filename)
        if not parsed:
            skipped_badname += 1
            rows.append(("skipped", filename, "", "", "", "invalid service-reference filename"))
            continue
        sid, namespace, tsid, onid, stype = parsed
        position = orbital_position(namespace)
        if not position:
            skipped_unknown_position += 1
            rows.append(("skipped", filename, "", "", "", "unknown/non-satellite namespace"))
            continue
        size = png_size(src)
        if size != (220, 132):
            skipped_size += 1
            rows.append(("skipped", filename, position, "", "", f"non-standard size {size}"))
            continue
        provider = providers.get((sid, namespace, tsid, onid, stype), "").strip()
        provider_slug = slugify(provider)
        if not provider_slug:
            skipped_provider += 1
            rows.append(("skipped", filename, position, provider, "", "provider missing in Vhannibal lamedb"))
            continue
        dest = PICON_ROOT / position / provider_slug / "transparent" / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            skipped_existing += 1
            rows.append(("existing", filename, position, provider, str(dest.relative_to(ROOT)), "destination already exists"))
            existing.add(low)
            continue
        shutil.copy2(src, dest)
        existing.add(low)
        added += 1
        rows.append(("added", filename, position, provider, str(dest.relative_to(ROOT)), ""))

    with REPORT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(["status", "filename", "position", "provider", "destination", "reason"])
        writer.writerows(rows)

    summary = REPORT.parent / "import-summary.txt"
    summary.write_text(
        "Vhannibal Motor guarded import\n"
        f"source_png={len(source_files)}\n"
        f"added={added}\n"
        f"existing={skipped_existing}\n"
        f"skipped_unknown_position={skipped_unknown_position}\n"
        f"skipped_non_220x132={skipped_size}\n"
        f"skipped_missing_provider={skipped_provider}\n"
        f"skipped_invalid_filename={skipped_badname}\n",
        encoding="utf-8",
    )
    print(summary.read_text(encoding="utf-8"))
    if added == 0:
        raise SystemExit("No picons were added; refusing to create an empty import commit")


if __name__ == "__main__":
    run()
