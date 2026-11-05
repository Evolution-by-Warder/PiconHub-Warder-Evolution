#!/usr/bin/env python3
"""Fail-closed inventory and completeness QA for the five Warder radio collections.

Runs without network, graphical recomposition, or alterations to approved picons.
It crosschecks immutable public package metadata, style/resolution completeness,
filenames and country coverage. It is not a physical receiver validation.
"""
import gzip
import hashlib
import json
from pathlib import Path
import re

BASE=Path("picons")
COUNTRIES=("SK-CZ","AT","DE","HU","PL")
SIZES=("50x30","220x132","400x240")
STYLES=("transparent","white","black")
HASH=re.compile(r"^[a-f0-9]{64}$")
SHA=re.compile(r"^[a-f0-9]{40}$")
FILENAME=re.compile(r"^(?:4097|5001|5002|8193)_0_(?:2|A)_(?:[0-9A-F]+_){6}[0-9A-F]+\.png$")
ROOT_REPO="https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/"

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def gzip_rows(path):
    rows=json.loads(gzip.decompress(path.read_bytes()))
    if isinstance(rows,list):return rows
    if isinstance(rows,dict):
        for key in ("remaining","rows","stations","items"):
            if isinstance(rows.get(key),list):return rows[key]
    raise AssertionError("Unsupported remaining list schema in "+str(path))

def main():
    countries={}
    approved=0
    total=0
    all_variants=0
    packages={}
    for code in COUNTRIES:
        folder=BASE/("IPTV-"+code)
        release=load(folder/"catalog/release.json")
        assert release["schema"]==1 and release["status"]=="verified"
        assert release["collection"]=="IPTV-"+code
        assert SHA.fullmatch(release["payload_commit"])
        assert set(release["packages"])==set(SIZES)
        expected=release["reference_files_per_variant"]
        assert isinstance(expected,int) and expected>0
        common=None
        variants={}
        for size in SIZES:
            styles=release["packages"][size]
            assert set(styles)==set(STYLES)
            variants[size]={}
            for style in STYLES:
                meta=styles[style]
                assert meta["resolution"]==size
                assert HASH.fullmatch(meta["sha256"])
                assert 0<meta["bytes"]<=64*1024*1024
                filename="iptv-"+code.lower()+"-"+style+"-"+size+".zip"
                path=str(folder/"packages"/filename)
                assert meta["url"]==ROOT_REPO+release["payload_commit"]+"/"+path
                files=meta["files"]
                assert isinstance(files,dict) and len(files)==expected
                assert all(FILENAME.fullmatch(name) and HASH.fullmatch(sha)
                           for name,sha in files.items())
                names=set(files)
                assert common is None or names==common
                if common is None:common=names
                archive_path=folder/"packages"/filename
                assert archive_path.is_file(),path
                # Test actual archive bytes in the CI checkout, not metadata alone.
                import zipfile
                body=archive_path.read_bytes()
                assert len(body)==meta["bytes"]
                assert hashlib.sha256(body).hexdigest()==meta["sha256"],filename
                with zipfile.ZipFile(archive_path) as archive:
                    observed=archive.namelist()
                    assert len(observed)==expected and set(observed)==names
                    for name in observed:
                        assert hashlib.sha256(archive.read(name)).hexdigest()==files[name]
                variants[size][style]=dict(bytes=meta["bytes"],
                                          sha256=meta["sha256"],
                                          references=len(files))
                all_variants+=1
                packages[path]=meta["sha256"]
        if code=="SK-CZ":
            station_count=release["stations"]
            with_picons=release["picon_stations"]
            missing=release["missing_artwork"]
            assert station_count==320 and with_picons==320 and missing==0
            rows=load(folder/"catalog/stations.json")["stations"]
            assert len(rows)==station_count
            assert all(r["picon_filename"] in common for r in rows)
        else:
            cov=load(folder/"coverage.json")
            station_count=cov["total_stations"]
            with_picons=cov["with_picons"]
            missing=cov["missing"]
            assert release["catalogue_stations"]==station_count
            assert release["stations"]==with_picons
            assert station_count==with_picons+missing
            assert len(gzip_rows(folder/cov["remaining_file"]))==missing
        assert with_picons<=expected
        countries[code]=dict(version=release["version"],
                             total_stations=station_count,
                             covered_stations=with_picons,
                             missing_stations=missing,
                             references_per_variant=expected,
                             variants=variants,
                             package_commit=release["payload_commit"],
                             original_graphics_not_modified=True)
        approved+=with_picons
        total+=station_count
        print("PASS",code,with_picons,"/",station_count,
              "stations and",expected,"references in nine verified packages")
    report=dict(schema=1,status="verified",date="2026-11-05",
                countries=countries,
                summary=dict(country_collections=5,
                             variants=all_variants,
                             covered_stations=approved,
                             total_stations=total,
                             missing_stations=total-approved,
                             package_count=len(packages)),
                caveats=[
                    "This audits published PNGs and source manifests; no physical receiver was tested.",
                    "Coverage is bounded by catalogued stations in these five country collections; the global World Radio catalogue is larger.",
                    "Open drafts with new images must be independently approved before release."
                ])
    assert all_variants==45 and len(packages)==45
    assert (approved,total)==(432,4698), (approved,total)
    out=Path("reports/radio-country-quality-20261105.json")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("PASS 45 complete Warder archives / 432 of 4698 catalogued stations")

if __name__=="__main__":
    main()
