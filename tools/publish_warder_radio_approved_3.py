#!/usr/bin/env python3
"""Publish exactly three owner-approved Warder radio logos, one per country.

The 27 original preview PNGs are reused byte-for-byte. Every prior package PNG
remains byte-identical; no image editing, recolouring or source substitution.
Staging and release metadata are separate commits to pin immutable payload URLs.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import io
import json
import re
from pathlib import Path
import stat
import struct
import subprocess
from urllib.request import Request, urlopen
import zipfile

ROOT = Path("picons")
REPO = "Evolution-by-Warder/PiconHub-Warder-Evolution"
RAW = "https://raw.githubusercontent.com/" + REPO + "/"
OLD = "2026.11.04-1"
NEW = "2026.11.04-2"
SIZE = ("50x30", "220x132", "400x240")
STYLE = ("transparent", "white", "black")
CONFIG = {
    "AT": dict(ref="4097:0:2:45CD:FE8F:EC:0:0:0:0",
        station="Antenne Kärnten", base=11, refs=16, total=219,
        source_commit="430a4ba51621959454e9a0155103a1c1fe8a525f",
        review_base="picons/IPTV-SK-CZ/review/foreign-radio-20261104/antenne-kaernten",
        source_name="source.svg"),
    "DE": dict(ref="4097:0:2:C634:62DF:ED:0:0:0:0",
        station="radio 3 | rbb | HQ", base=61, refs=87, total=3422,
        source_commit="430a4ba51621959454e9a0155103a1c1fe8a525f",
        review_base="picons/IPTV-SK-CZ/review/foreign-radio-20261104/radio3-official-rbb",
        source_name="official-rbb.jpg"),
    "PL": dict(ref="4097:0:2:A68C:EC79:ED:0:0:0:0",
        station="ESKA ROCK", base=24, refs=35, total=500,
        source_commit="04db0d182d9e951ca13ab8beb582e4f3f4fd505b",
        review_base="picons/IPTV-SK-CZ/review/eskarock-20261104/alternatives/official-og",
        source_name="original.png"),
}
SHA = lambda raw: hashlib.sha256(raw).hexdigest()

def checked_git_blob(commit, path):
    assert re.fullmatch(r"[a-f0-9]{40}", commit)
    assert path.startswith("picons/IPTV-SK-CZ/review/") and ".." not in Path(path).parts
    return subprocess.check_output(["git", "show", commit + ":" + path])

def readjson(path):
    return json.loads(path.read_text(encoding="utf-8"))

def writejson(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def filename(code):
    return CONFIG[code]["ref"].replace(":", "_") + ".png"

def packname(code, size, style):
    return "iptv-%s-%s-%s.zip" % (code.lower(), style, size)

def archive(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = z.namelist()
        assert len(names) == len(set(names))
        assert all(re.fullmatch(r"(4097|5001|5002|8193)_0_[A-Z0-9_]+\.png", n) for n in names)
        return {n: z.read(n) for n in names}

def pack(files):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for name, blob in sorted(files.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            z.writestr(info, blob)
    return out.getvalue()

def pngcheck(blob, size):
    assert len(blob) >= 33 and blob[:8] == b"\x89PNG\r\n\x1a\n"
    assert blob[12:16] == b"IHDR"
    assert struct.unpack(">II", blob[16:24]) == tuple(map(int, size.split("x")))

def root(code):
    return ROOT / ("IPTV-" + code)

def approved(code):
    folder = root(code)
    plan = readjson(folder / "plan.json")
    release = readjson(folder / "catalog/release.json")
    expected = CONFIG[code]
    assert plan["collection"] == release["collection"] == "IPTV-" + code
    assert plan["version"] == NEW
    new = [a for a in plan["artwork"] if "frozen_review_assets" in a]
    assert len(new) == 1
    a = new[0]
    assert a["owner_approved_exact_pngs"] is True
    assert a["stations"] == [dict(name=expected["station"], country=code,
                                reference=expected["ref"], target=filename(code),
                                stream_url=a["stations"][0]["stream_url"], source_view=False)]
    assert a["source_review_commit"] == expected["source_commit"]
    assert all(set(a["render_sha256"][sz]) == set(STYLE) for sz in SIZE)
    return folder, plan, release, a

def baseline(code, release):
    cfg = CONFIG[code]
    assert release["status"] == "verified"
    assert release["version"] == OLD
    assert release["stations"] == cfg["base"]
    assert release["catalogue_stations"] == cfg["total"]
    assert release["reference_files_per_variant"] == cfg["refs"]
    for size in SIZE:
        for style in STYLE:
            entry = release["packages"][size][style]
            name = packname(code, size, style)
            blob = (root(code) / "packages" / name).read_bytes()
            assert len(blob) == entry["bytes"] and SHA(blob) == entry["sha256"], name
            files = archive(blob)
            assert len(files) == cfg["refs"]
            assert set(files) == set(entry["files"])
            assert filename(code) not in files
            for key, value in files.items():
                assert SHA(value) == entry["files"][key]
                pngcheck(value, size)

def stage():
    for code in CONFIG:
        folder, plan, release, a = approved(code)
        baseline(code, release)
        source_target = folder / a["path"]
        source_target.parent.mkdir(parents=True, exist_ok=True)
        source_blob = checked_git_blob(a["source_review_commit"],
                                       CONFIG[code]["review_base"] + "/" +
                                       CONFIG[code]["source_name"])
        assert SHA(source_blob) == a["sha256"], "Approved source changed"
        source_target.write_bytes(source_blob)
        for size in SIZE:
            for style in STYLE:
                rel = a["frozen_review_assets"][size][style]
                destination = folder / rel
                destination.parent.mkdir(parents=True, exist_ok=True)
                blob = checked_git_blob(a["source_review_commit"],
                                        CONFIG[code]["review_base"] +
                                        ("/" if code == "PL" else "/artwork/") +
                                        size + "/" + style + "/" + filename(code))
                assert SHA(blob) == a["render_sha256"][size][style], (code,size,style)
                pngcheck(blob,size)
                destination.write_bytes(blob)
                archive_path = folder / "packages" / packname(code,size,style)
                old = archive(archive_path.read_bytes())
                assert filename(code) not in old
                old[filename(code)] = blob
                new = pack(old)
                rebuilt = archive(new)
                assert all(rebuilt[key] == value for key,value in old.items())
                assert len(rebuilt) == release["reference_files_per_variant"] + 1
                archive_path.write_bytes(new)
        print("STAGED",code,"exact 9 owner-approved Warder PNGs; all originals preserved")

def remaining_entries(raw):
    obj = json.loads(gzip.decompress(raw))
    if isinstance(obj, list):
        return obj, obj, None
    if isinstance(obj, dict):
        for field in ("remaining","rows","stations","items"):
            if isinstance(obj.get(field), list):
                return obj, obj[field], field
    raise ValueError("Unsupported remaining country file")

def remove_remaining(code):
    path=root(code)/"remaining.json.gz"
    obj, rows, key = remaining_entries(path.read_bytes())
    ref=CONFIG[code]["ref"]
    before=len(rows)
    rest=[s for s in rows if (s.get("reference") or s.get("service_reference")) != ref]
    assert before-len(rest) == 1, "Missing/duplicate target in remaining " + code
    if key: obj[key]=rest
    else: obj=rest
    payload=json.dumps(obj,ensure_ascii=False,separators=(",",":")).encode("utf-8")
    path.write_bytes(gzip.compress(payload,compresslevel=9,mtime=0))
    assert len(remaining_entries(path.read_bytes())[1])==before-1

def finalize(sha):
    assert re.fullmatch(r"[a-f0-9]{40}",sha),sha
    for code in CONFIG:
        folder,plan,release,a=approved(code)
        baseline_references=release["reference_files_per_variant"]
        assert release["version"]==OLD
        published={}
        common=None
        for size in SIZE:
            published[size]={}
            for style in STYLE:
                entry=release["packages"][size][style]
                old=dict(entry["files"])
                blob=(folder/"packages"/packname(code,size,style)).read_bytes()
                new=archive(blob)
                assert set(new)==set(old)|{filename(code)}
                assert all(SHA(new[n])==digest for n,digest in old.items())
                assert SHA(new[filename(code)])==a["render_sha256"][size][style]
                for n,v in new.items():pngcheck(v,size)
                hashes={name:SHA(data) for name,data in sorted(new.items())}
                assert common is None or common==set(hashes)
                common=set(hashes)
                entry.update(url=RAW+sha+"/"+str(folder/"packages"/packname(code,size,style)),
                             bytes=len(blob),sha256=SHA(blob),files=hashes)
                published[size][style]=dict(new_sha256=SHA(blob),bytes=len(blob),
                    old_refs_preserved=len(old),
                    approved_reference_sha256=hashes[filename(code)])
        release.update(version=NEW,stations=CONFIG[code]["base"]+1,
                       reference_files_per_variant=baseline_references+1,
                       payload_commit=sha)
        writejson(folder/"catalog/release.json",release)
        coverage=readjson(folder/"coverage.json")
        assert coverage["with_picons"]==CONFIG[code]["base"]
        assert coverage["missing"]==CONFIG[code]["total"]-CONFIG[code]["base"]
        coverage.update(with_picons=CONFIG[code]["base"]+1,
                        missing=CONFIG[code]["total"]-CONFIG[code]["base"]-1)
        writejson(folder/"coverage.json",coverage)
        remove_remaining(code)
        readme=folder/"README.md"
        text=readme.read_text(encoding="utf-8")
        oldmsg=("Current reviewed batch: %s of %s catalogue stations, %s references in every variant."
                %(CONFIG[code]["base"],CONFIG[code]["total"],CONFIG[code]["refs"]))
        newmsg=("Current reviewed batch: %s of %s catalogue stations, %s references in every variant."
                %(CONFIG[code]["base"]+1,CONFIG[code]["total"],CONFIG[code]["refs"]+1))
        assert oldmsg in text,code
        text=text.replace(oldmsg,newmsg)
        text+="\nWarder approved 4 Nov 2026: added original station %s under exact service ref %s in all nine Warder variants. Every original package PNG remained byte-for-byte unchanged. Source asset provenance and frozen render SHA-256 are recorded in plan.json and catalog/owner-approved-radio-20261104-r2.json. Physical receiver check remains separate.\n"%(CONFIG[code]["station"],CONFIG[code]["ref"])
        readme.write_text(text,encoding="utf-8")
        proof=dict(schema=1,status="verified",version=NEW,payload_commit=sha,
                   previous_version=OLD,country=code,
                   station=CONFIG[code]["station"],reference=CONFIG[code]["ref"],
                   source_url=a["source_url"],source_sha256=a["sha256"],
                   source_license=a["source_license"],user_approved_exact_pngs=True,
                   new_references=1,all_original_png_bytes_preserved=True,
                   base_refs_per_variant=baseline_references,
                   new_refs_per_variant=baseline_references+1,
                   variants=published,production_files_verified=True,
                   physical_receiver_test=False)
        writejson(folder/"catalog/owner-approved-radio-20261104-r2.json",proof)
        print("FINAL",code,release["stations"],"/",release["catalogue_stations"],
              "station coverage; 9 variants",release["reference_files_per_variant"],"references each")

def validate(include_native=False):
    release_by_country={}
    for code in CONFIG:
        folder,plan,release,a=approved(code)
        assert (release["version"],release["stations"],release["reference_files_per_variant"])==(
            NEW,CONFIG[code]["base"]+1,CONFIG[code]["refs"]+1)
        assert release["catalogue_stations"]==CONFIG[code]["total"]
        coverage=readjson(folder/"coverage.json")
        assert (coverage["with_picons"],coverage["missing"])==(
            release["stations"],release["catalogue_stations"]-release["stations"])
        assert len(remaining_entries((folder/"remaining.json.gz").read_bytes())[1])==coverage["missing"]
        proof=readjson(folder/"catalog/owner-approved-radio-20261104-r2.json")
        assert proof["payload_commit"]==release["payload_commit"]
        allpack={}
        for size in SIZE:
            for style in STYLE:
                entry=release["packages"][size][style]
                assert entry["url"]==RAW+release["payload_commit"]+"/"+str(folder/"packages"/packname(code,size,style))
                body=(folder/"packages"/packname(code,size,style)).read_bytes()
                assert len(body)==entry["bytes"] and SHA(body)==entry["sha256"]
                content=archive(body)
                assert len(content)==CONFIG[code]["refs"]+1
                assert set(content)==set(entry["files"])
                assert all(SHA(raw)==entry["files"][name] for name,raw in content.items())
                assert content[filename(code)]==(folder/a["frozen_review_assets"][size][style]).read_bytes()
                assert SHA(content[filename(code)])==a["render_sha256"][size][style]
                allpack[packname(code,size,style)]=body
        release_by_country[code]=(release,allpack)
        print("PASS",code,"approved source, nine intact ZIPs and country manifest")
    if include_native:
        # Reuse the exact native PiconHub manifest/install emulator already
        # applied to the original production country packages.
        import importlib.util,sys
        spec=importlib.util.spec_from_file_location("warder_country_build",Path("tools/publish_country_radio_picons.py"))
        module=importlib.util.module_from_spec(spec)
        sys.modules[spec.name]=module
        spec.loader.exec_module(module)
        for release,packages in release_by_country.values():
            module.verify_receiver(release,packages)
        print("PASS: native PiconHub package planner and non-destructive installer, 27 variants")

def public():
    for code in CONFIG:
        manifest=readjson(root(code)/"catalog/release.json")
        def check(item):
            size,style,e=item
            with urlopen(Request(e["url"],headers={"User-Agent":"Warder-Radio-Approved-20261104"}),timeout=40) as response:
                data=response.read(e["bytes"]+1)
            assert len(data)==e["bytes"] and SHA(data)==e["sha256"],(code,size,style)
            return size,style
        tasks=[(size,style,manifest["packages"][size][style]) for size in SIZE for style in STYLE]
        with ThreadPoolExecutor(max_workers=3) as pool:
            for size,style in pool.map(check,tasks):
                print("PUBLIC VERIFIED",code,size,style)

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    mx=p.add_mutually_exclusive_group(required=True)
    mx.add_argument("--prepare",action="store_true")
    mx.add_argument("--finalize",metavar="PAYLOAD_SHA")
    mx.add_argument("--verify",action="store_true")
    mx.add_argument("--public",action="store_true")
    a=p.parse_args()
    if a.prepare:stage()
    elif a.finalize:finalize(a.finalize)
    elif a.verify:validate(include_native=True)
    else:public()
