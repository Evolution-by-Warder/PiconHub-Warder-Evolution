#!/usr/bin/env python3
"""Add exact service-reference aliases to the nine approved Warder radio PNG archives.

The images are copied byte-for-byte from already published, approved Warder
picons. This script never redraws, recolours, resizes or generates any logo.
It refuses a changed baseline or any unrelated file modification.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import stat
import struct
import zipfile

ROOT = Path("picons/IPTV-SK-CZ")
CATALOG = ROOT / "catalog"
BASE = "https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/"
BASE_VERSION = "2026.11.04-r5"
NEW_VERSION = "2026.11.04-r6"
STYLES = ("transparent", "white", "black")
SIZES = ("50x30", "220x132", "400x240")
ALIASES = (
    dict(
        name="Radio FRM", source_name="Fajn rock music",
        target="4097_0_2_9423_81E4_EC_0_0_0_0.png",
        source="4097_0_2_2FFE_2E69_EC_0_0_0_0.png",
        target_reference="4097:0:2:9423:81E4:EC:0:0:0:0",
        source_reference="4097:0:2:2FFE:2E69:EC:0:0:0:0",
        evidence="https://www.fajnrockmusic.cz/radio",
        identity="The broadcaster's own navigation calls Fajn Rock Music RÁDIO FRM.",
    ),
    dict(
        name="Radio Student", source_name="Radio R",
        target="4097_0_2_57EC_2C91_EC_0_0_0_0.png",
        source="4097_0_2_A90_A8A5_EC_0_0_0_0.png",
        target_reference="4097:0:2:57EC:2C91:EC:0:0:0:0",
        source_reference="4097:0:2:A90:A8A5:EC:0:0:0:0",
        evidence="https://radior.video.muni.cz/",
        identity="The official Icecast mount points FSS_mp3-64.mp3 and FSS_mp3-128.mp3 both report RadioR student radio.",
    ),
)
SHA = lambda raw: hashlib.sha256(raw).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def zip_name(size, style):
    return "iptv-sk-cz-%s-%s.zip" % (style, size)


def package_file(size, style):
    return ROOT / "packages" / zip_name(size, style)


def assert_identity():
    catalogue = read_json(CATALOG / "stations.json")
    stations = {row["service_reference"]: row for row in catalogue["stations"]}
    assert len(stations) == 320
    assert {a["name"] for a in ALIASES} == {"Radio FRM", "Radio Student"}
    for alias in ALIASES:
        old = stations[alias["source_reference"]]
        new = stations[alias["target_reference"]]
        assert (old["name"], new["name"]) == (alias["source_name"], alias["name"])
        assert (old["picon_filename"], new["picon_filename"]) == (alias["source"], alias["target"])
        assert old["country"] == new["country"] == "CZ"
    assert (CATALOG / "missing-artwork.csv").read_text(encoding="utf-8-sig").count("Chýba") == 2


def assert_png(raw, size):
    assert raw.startswith(b"\x89PNG\r\n\x1a\n")
    assert raw[12:16] == b"IHDR"
    assert struct.unpack(">II", raw[16:24]) == tuple(map(int, size.split("x")))


def contents(archive):
    with zipfile.ZipFile(io.BytesIO(archive), "r") as z:
        names = z.namelist()
        assert len(names) == len(set(names))
        assert all("/" not in name and name.endswith(".png") for name in names)
        return {name: z.read(name) for name in names}


def packed(files):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            z.writestr(info, raw)
    return out.getvalue()


def inventory_sha256(mapping):
    return SHA(json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode())


def verify_archive(size, style, meta, already_added=False):
    body = package_file(size, style).read_bytes()
    assert len(body) == meta["bytes"] and SHA(body) == meta["sha256"], (size, style)
    old = contents(body)
    assert set(old) == set(meta["files"])
    assert len(old) == (358 if already_added else 356)
    for name, raw in old.items():
        assert SHA(raw) == meta["files"][name], (name, size, style)
        assert_png(raw, size)
    for alias in ALIASES:
        assert alias["source"] in old, (size, style, alias["source"])
        if already_added:
            assert alias["target"] in old and old[alias["target"]] == old[alias["source"]]
        else:
            assert alias["target"] not in old, (size, style, alias["target"])
    return old


def prepare():
    assert_identity()
    release = read_json(CATALOG / "release.json")
    assert release["status"] == "verified"
    assert release["version"] == BASE_VERSION and release["reference_files_per_variant"] == 356
    assert (release["picon_stations"], release["missing_artwork"], release["stations"]) == (318, 2, 320)
    for size in SIZES:
        for style in STYLES:
            meta = release["packages"][size][style]
            old = verify_archive(size, style, meta)
            new = dict(old)
            for alias in ALIASES:
                new[alias["target"]] = old[alias["source"]]
            assert len(new) == 358
            for name, body in old.items():
                assert new[name] is body or new[name] == body
            new_archive = packed(new)
            check = contents(new_archive)
            assert set(check) == set(new) and all(check[k] == v for k, v in new.items())
            package_file(size, style).write_bytes(new_archive)
            print("STAGED %s/%s: 356 -> 358 PNGs, originals byte-identical" % (size, style))


def finalize(commit_sha):
    assert re.fullmatch("[a-f0-9]{40}", commit_sha)
    release = read_json(CATALOG / "release.json")
    assert release["version"] == BASE_VERSION
    summaries = {}
    common = None
    for size in SIZES:
        summaries[size] = {}
        for style in STYLES:
            meta = release["packages"][size][style]
            raw = package_file(size, style).read_bytes()
            old_expected = meta["files"]
            new = contents(raw)
            assert len(old_expected) == 356 and len(new) == 358
            assert set(old_expected) < set(new)
            assert set(new) - set(old_expected) == {a["target"] for a in ALIASES}
            assert all(SHA(new[n]) == digest for n, digest in old_expected.items())
            for name, data in new.items():
                assert_png(data, size)
            for a in ALIASES:
                assert new[a["target"]] == new[a["source"]]
            digests = {name: SHA(data) for name, data in sorted(new.items())}
            assert common is None or common == set(digests)
            common = set(digests)
            meta.update(
                url=BASE + commit_sha + "/" + str(package_file(size, style)),
                bytes=len(raw), sha256=SHA(raw), files=digests,
            )
            summaries[size][style] = dict(
                bytes=len(raw),
                sha256=SHA(raw),
                previous_images_unchanged=356,
                old_inventory_sha256=inventory_sha256(old_expected),
                new_references={a["target"]: digests[a["target"]] for a in ALIASES},
            )
    release.update(
        version=NEW_VERSION, picon_stations=320, missing_artwork=0,
        reference_files_per_variant=358, payload_commit=commit_sha,
    )
    write_json(CATALOG / "release.json", release)
    proof = dict(
        schema=1, status="verified", version=NEW_VERSION, payload_commit=commit_sha,
        previous_version=BASE_VERSION, source_graphics=0, new_references=2,
        album_artwork_generated=False, inherited_approved_warder_png_byte_exact=True,
        aliases=[dict(x) for x in ALIASES],
        original_station_counts=dict(stations=320, with_picons=320, missing=0),
        styles=list(STYLES), resolutions=list(SIZES), files_per_variant=358,
        variants=summaries, physical_receiver_test=False,
    )
    write_json(CATALOG / "warder-radio-picons-20261104-r6.json", proof)
    with (CATALOG / "missing-artwork.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        csv.writer(handle).writerow(("Krajina", "Stanica", "Dôvod"))
    readme = ROOT / "README.md"
    old = readme.read_text(encoding="utf-8")
    original = (
        "Picony pokrývajú 318 položiek pôvodného bouquetu, 356 súborov vrátane starších referencií "
        "v každom variante. Zvyšné 2 položky zatiaľ nemá vhodný overený podklad. "
        "Nevymýšľame náhradné logá."
    )
    updated = (
        "Picony pokrývajú všetkých 320 položiek pôvodného bouquetu, 358 súborov vrátane "
        "starších referencií v každom variante. Posledné dve historické referencie "
        "Radio FRM a Radio Student používajú presné byte-identické schválené Warder "
        "picony svojich oficiálne overených programových aliasov."
    )
    assert original in old
    old = old.replace(original, updated, 1)
    old += (
        "\nŠieste doplnenie 4. novembra 2026: aliasy Radio FRM → Fajn Rock Music "
        "a Radio Student → Radio R sú doložené oficiálnou stránkou vysielateľa "
        "a verejným Icecast serverom Masarykovej univerzity. Oba nové picony sú "
        "v každom z deviatich variantov byte-identickou kópiou už schváleného "
        "Warder PNG príslušnej stanice. Starších 356 PNG zostalo presne zachovaných; "
        "teraz 358 PNG/balík a pokrytie 320/320 SK/CZ. \n"
    )
    readme.write_text(old, encoding="utf-8")
    print("FINALIZED r6: 9 archives x 358 PNG, all 320 SK/CZ services covered")


def verify():
    release = read_json(CATALOG / "release.json")
    proof = read_json(CATALOG / "warder-radio-picons-20261104-r6.json")
    assert release["version"] == proof["version"] == NEW_VERSION
    assert release["payload_commit"] == proof["payload_commit"]
    assert (release["stations"], release["picon_stations"], release["missing_artwork"]) == (320, 320, 0)
    assert release["reference_files_per_variant"] == 358
    assert (CATALOG / "missing-artwork.csv").read_text(encoding="utf-8-sig").strip() == "Krajina,Stanica,Dôvod"
    for size in SIZES:
        for style in STYLES:
            meta = release["packages"][size][style]
            assert meta["url"] == BASE + release["payload_commit"] + "/" + str(package_file(size, style))
            current = verify_archive(size, style, meta, already_added=True)
            assert len(current) == 358
            old_only = {k: v for k, v in meta["files"].items() if k not in {a["target"] for a in ALIASES}}
            assert inventory_sha256(old_only) == proof["variants"][size][style]["old_inventory_sha256"]
            assert proof["variants"][size][style]["previous_images_unchanged"] == 356
    print("PASS: original 356 PNG bytes unchanged in 9 archives, new alias references verified, 320/320 services")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--finalize", metavar="PAYLOAD_SHA")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    assert sum(bool(x) for x in (args.prepare, args.finalize, args.verify)) == 1
    if args.prepare:
        prepare()
    elif args.finalize:
        finalize(args.finalize)
    else:
        verify()
