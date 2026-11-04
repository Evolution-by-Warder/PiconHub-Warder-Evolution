#!/usr/bin/env python3
"""Read-only Warder radio alias discovery for existing AT/DE/HU/PL country packs.

Only exact canonical stream URLs and matching programme names are proposed.
Similarity is not proof of identity; NO PNG or package is changed here.
"""
import argparse
from collections import defaultdict
import gzip
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit

ROOT = Path("picons")
COUNTRIES = ("AT", "DE", "HU", "PL")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def remaining(path):
    value = json.loads(gzip.decompress(path.read_bytes()))
    if isinstance(value, dict):
        value = next((value[name] for name in ("remaining", "rows", "stations", "items") if isinstance(value.get(name), list)), value)
    if not isinstance(value, list):
        raise ValueError("Unexpected country remaining format: " + str(path))
    return value


def uri_key(address):
    try:
        p = urlsplit(str(address or "").strip())
        if p.scheme.lower() not in ("http", "https") or not p.netloc:
            return ""
        # Preserve ports, pathname, query and their case. Ignore only URL fragment,
        # capitalization of hostname and trailing empty pathname equivalence.
        host = p.hostname.lower()
        port = ":" + str(p.port) if p.port else ""
        path = p.path or "/"
        return (host + port + path + (("?" + p.query) if p.query else ""))
    except ValueError:
        return ""


def name_key(name):
    value = unicodedata.normalize("NFKD", str(name or "").casefold())
    return " ".join(re.findall(r"[a-z0-9]+", value))


def ref(item):
    return item.get("reference") or item.get("service_reference") or ""


def stream(item):
    return item.get("stream_url") or item.get("url") or ""


def build():
    report = {
        "shortlist_for_official_logo_research": {},
        "schema": 1,
        "version": "2026-11-04",
        "status": "research_candidates_not_approved",
        "scope": "IPTV-AT, IPTV-DE, IPTV-HU, IPTV-PL",
        "rule": "Exact URL match or exact normalized broadcaster name; the second class must not auto-assign graphics.",
        "production_unchanged": True,
        "country_counts": {},
        "candidates": [],
    }
    counts = {}
    for code in COUNTRIES:
        folder = ROOT / ("IPTV-" + code)
        plan = load(folder / "plan.json")
        cov = load(folder / "coverage.json")
        release = load(folder / "catalog/release.json")
        uncovered = remaining(folder / "remaining.json.gz")
        assert len(uncovered) == cov["missing"], (code, len(uncovered), cov["missing"])
        assert cov["with_picons"] == plan["covered_stations"] == release["stations"]
        assert cov["total_stations"] == plan["catalogue_stations"] == release["catalogue_stations"]
        approved = [dict(s, logo_slug=entry["slug"], source_page=entry.get("source_page", ""))
                    for entry in plan["artwork"] for s in entry["stations"]]
        metadata = release["packages"]
        approved_files = set(metadata["220x132"]["transparent"]["files"])
        assert all(s["target"] in approved_files for s in approved)
        exact = defaultdict(list)
        names = defaultdict(list)
        for s in approved:
            key = uri_key(stream(s))
            if key:
                exact[key].append(s)
            if name_key(s.get("name")):
                names[name_key(s["name"])].append(s)
        # Review leads only: useful when no byte-identical alias exists yet.
        # Never infer official identities from broadcaster-name similarity.
        family_words = re.compile(
            r"\b(?:orf|bayern|br\b|hr\b|mdr|ndr|swr|wdr|rbb|"
            r"deutschland|antenne|radio\s?1|oe3|oe1|fm4|"
            r"rmf|zet|eska|polskie|radiowa|retro|petofi|kossuth)\b", re.I
        )
        seen = set()
        selected = []
        for station in uncovered:
            station_name = station.get("name", "")
            key = name_key(station_name)
            if key in seen or not family_words.search(str(station_name)):
                continue
            seen.add(key)
            selected.append({"name": station_name, "reference": ref(station),
                             "stream_url": stream(station)})
            if len(selected) == 35:
                break
        report["shortlist_for_official_logo_research"][code] = selected
        safe, review, unmatched = 0, 0, 0
        for item in uncovered:
            target_ref = ref(item)
            if not target_ref:
                raise ValueError("Missing radio reference in %s: %r" % (code, item))
            filename = target_ref.replace(":", "_").rstrip("_") + ".png"
            if filename in approved_files:
                raise ValueError("Already covered station in remaining: %s" % filename)
            matches = exact.get(uri_key(stream(item)), []) if uri_key(stream(item)) else []
            category = "same_exact_stream_url" if matches else "same_normalized_station_name" if names.get(name_key(item.get("name")), []) else ""
            matches = matches or names.get(name_key(item.get("name")), [])
            if not category:
                unmatched += 1
                continue
            usable = {s["logo_slug"] for s in matches}
            if category == "same_exact_stream_url" and len(usable) == 1:
                safe += 1
            else:
                review += 1
            report["candidates"].append({
                "country": code,
                "name": item.get("name"),
                "reference": target_ref,
                "stream_url": stream(item),
                "category": category,
                "candidate_only": True,
                "approved_logo_slug_count": len(usable),
                "ambiguous": len(usable) != 1,
                "approved_aliases": [
                    {
                        "station": s["name"], "reference": s["reference"],
                        "logo_slug": s["logo_slug"],
                        "source_page": s["source_page"],
                        "stream_url": s["stream_url"],
                    } for s in matches[:8]
                ],
            })
        counts[code] = {"catalogue": cov["total_stations"],
                        "approved_stations": cov["with_picons"],
                        "remaining_stations": cov["missing"],
                        "exact_stream_single_logo": safe,
                        "needs_identity_review": review,
                        "no_existing_alias_evidence": unmatched}
    report["country_counts"] = counts
    report["candidates"].sort(key=lambda x: (
        0 if x["category"] == "same_exact_stream_url" and not x["ambiguous"] else 1,
        x["country"], name_key(x["name"]), x["reference"]))
    report["summary"] = {
        "catalogue_stations": sum(x["catalogue"] for x in counts.values()),
        "existing_approved_station_coverage": sum(x["approved_stations"] for x in counts.values()),
        "not_yet_covered": sum(x["remaining_stations"] for x in counts.values()),
        "strict_same_stream_single_approved_logo_candidates": sum(x["exact_stream_single_logo"] for x in counts.values()),
        "other_candidates_for_identity_review": sum(x["needs_identity_review"] for x in counts.values()),
        "no_alias_evidence": sum(x["no_existing_alias_evidence"] for x in counts.values()),
    }
    assert sum([report["summary"]["strict_same_stream_single_approved_logo_candidates"],
                report["summary"]["other_candidates_for_identity_review"],
                report["summary"]["no_alias_evidence"]]) == report["summary"]["not_yet_covered"]
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="picons/IPTV-SK-CZ/catalog/world-radio-alias-scan-20261104.json")
    a = p.parse_args()
    result = build()
    Path(a.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("WARDER RADIO PROVENANCE RESEARCH (not published graphics)")
    print(json.dumps(result["summary"], ensure_ascii=False))
    for row in result["candidates"][:25]:
        print("CANDIDATE", row["country"], row["name"], row["category"],
              row["approved_aliases"][0]["station"])
