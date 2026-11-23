#!/usr/bin/env python3
"""Change-only, read-only upstream picon source watcher for one Warder SAT cycle.

Never downloads package binaries, alters artwork, or publishes production archives.
An --advance requires separately reviewed candidates and explicit execution.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "reports/sat-manager/sources.json"
STATE = ROOT / "reports/sat-manager/source-watch-state.json"
SHA = re.compile(r"^[0-9a-f]{40}$")
REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
CANDIDATE_EXT = {".png", ".svg", ".tv", ".radio", ".xml", ".csv", ".json", ".txt"}


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Expected object: " + str(path))
    return value


def validate(config: dict, state: dict) -> None:
    if config.get("schema") != 1 or state.get("schema") != 1:
        raise ValueError("Unexpected schema")
    sources = config.get("sources")
    if not isinstance(sources, list) or len(sources) != 9:
        raise ValueError("Expected nine curated sources")
    ids = set()
    for item in sources:
        sid = item["id"]
        if sid in ids:
            raise ValueError("Duplicate source: " + sid)
        ids.add(sid)
        baseline = state.get("sources", {}).get(sid)
        if not isinstance(baseline, dict):
            raise ValueError("Missing source baseline: " + sid)
        if item["kind"] == "site-index":
            from gioppygio_source_watch import CATALOG_URL as GIOPPY_URL
            if (sid != "gioppygio-sat-snp" or item.get("url") != GIOPPY_URL
                    or baseline.get("url") != GIOPPY_URL):
                raise ValueError("Untrusted GioppyGio source URL: " + sid)
            index_sha = baseline.get("index_sha256")
            if index_sha is not None and not re.fullmatch(r"[0-9a-f]{64}", index_sha):
                raise ValueError("Invalid GioppyGio catalogue hash")
            continue
        if item["kind"] == "http-index":
            from satdigitalne_source_watch import CATALOG_URL
            if (sid != "satdigitalne-sat-picons" or item.get("url") != CATALOG_URL
                    or baseline.get("url") != CATALOG_URL):
                raise ValueError("Untrusted external source URL: " + sid)
            index_sha = baseline.get("index_sha256")
            if index_sha is not None and not re.fullmatch(r"[0-9a-f]{64}", index_sha):
                raise ValueError("Invalid HTML catalogue fingerprint")
            continue
        repo, branch = item["repo"], item["branch"]
        if not REPO.fullmatch(repo) or not branch:
            raise ValueError("Unsafe source: " + sid)
        if not SHA.fullmatch(baseline.get("head_sha", "")):
            raise ValueError("Missing verified source baseline: " + sid)
        if baseline["repo"] != repo or baseline["branch"] != branch:
            raise ValueError("Source identity does not match baseline: " + sid)
        if item["kind"] not in ("git", "package-index"):
            raise ValueError("Unsupported source kind: " + sid)
        if not item["include_paths"] or any(p.startswith("/") or ".." in p for p in item["include_paths"]):
            raise ValueError("Unsafe source path filters: " + sid)


def api(path: str) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Warder-SAT-Picon-Source-Watch/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request("https://api.github.com" + path, headers=headers)
    with urllib.request.urlopen(req, timeout=35) as response:
        raw = response.read(4_000_001)
    if len(raw) > 4_000_000:
        raise RuntimeError("Too large GitHub API response; review manually")
    return json.loads(raw)


def branch_head(repo: str, branch: str) -> str:
    b = urllib.parse.quote(branch, safe="")
    response = api("/repos/" + repo + "/branches/" + b)
    head = response["commit"]["sha"]
    if not SHA.fullmatch(head):
        raise ValueError("Invalid source head SHA")
    return head


def compare(repo: str, old: str, new: str) -> dict:
    return api("/repos/" + repo + "/compare/" + old + "..." + new + "?per_page=100")


def candidate(path: str, source: dict) -> bool:
    if not any(path == p or path.startswith(p) for p in source["include_paths"]):
        return False
    if source["kind"] == "package-index":
        return path == "Packages"
    return Path(path).suffix.lower() in CANDIDATE_EXT


def scan(config: dict, state: dict, fetch_head=branch_head, fetch_compare=compare) -> dict:
    report = {
        "schema": 1,
        "manager": "Warder SAT Picon Manager",
        "status": "READ_ONLY_SOURCE_COMPARISON",
        "no_picon_publication": True,
        "sources": [],
    }
    for source in config["sources"]:
        sid = source["id"]
        if source["kind"] in ("http-index", "site-index"):
            if source["kind"] == "http-index":
                from satdigitalne_source_watch import scan_source
            else:
                from gioppygio_source_watch import scan_source
            try:
                row = scan_source(source, state["sources"][sid])
            except (ValueError, KeyError, urllib.error.HTTPError, urllib.error.URLError,
                    TimeoutError, OSError, RuntimeError) as exc:
                row = {
                    "id": sid, "url": source["url"], "previous_sha": state["sources"][sid].get("index_sha256"),
                    "current_sha": None, "status": "SOURCE_ERROR_NO_ADVANCE",
                    "error": str(exc)[:250], "candidates": [], "changed_path_count": 0,
                }
            report["sources"].append(row)
            continue
        previous = state["sources"][sid]["head_sha"]
        row = {
            "id": sid, "repo": source["repo"], "branch": source["branch"],
            "role": source["role"], "source_group": source["source_group"],
            "previous_sha": previous, "current_sha": None,
            "status": "UNVERIFIED", "changed_path_count": 0, "candidates": [],
        }
        try:
            current = fetch_head(source["repo"], source["branch"])
            row["current_sha"] = current
            if current == previous:
                row["status"] = "UNCHANGED_SKIP"
            else:
                result = fetch_compare(source["repo"], previous, current)
                files = result.get("files", [])
                ahead = result.get("ahead_by", 0)
                if result.get("status") != "ahead" or ahead < 1:
                    row["status"] = "DIVERGED_REVIEW_NO_ADVANCE"
                elif len(files) >= 300 or result.get("total_commits", 0) >= 250:
                    row["status"] = "COMPARISON_TRUNCATED_REVIEW_NO_ADVANCE"
                else:
                    changed = [
                        {"path": f["filename"], "status": f.get("status")}
                        for f in files if candidate(f["filename"], source)
                    ]
                    row["status"] = "CHANGED_REVIEW_REQUIRED" if changed else "UNRELATED_CHANGES_ONLY"
                    row["changed_path_count"] = len(changed)
                    row["candidates"] = changed[:100]
                    row["candidate_list_truncated"] = len(changed) > 100
        except (ValueError, KeyError, urllib.error.HTTPError, urllib.error.URLError, OSError, RuntimeError) as exc:
            row["status"] = "SOURCE_ERROR_NO_ADVANCE"
            row["error"] = str(exc)[:250]
        report["sources"].append(row)
    report["changed_sources"] = sum(r["status"] in ("CHANGED_REVIEW_REQUIRED", "INITIAL_BASELINE_REVIEW_REQUIRED") for r in report["sources"])
    report["unchanged_sources"] = sum(r["status"] == "UNCHANGED_SKIP" for r in report["sources"])
    report["needs_manual_review"] = any(
        r["status"] not in ("UNCHANGED_SKIP", "UNRELATED_CHANGES_ONLY")
        for r in report["sources"]
    )
    report["safe_to_advance_after_explicit_review"] = all(
        r["status"] in ("UNCHANGED_SKIP", "UNRELATED_CHANGES_ONLY", "CHANGED_REVIEW_REQUIRED", "INITIAL_BASELINE_REVIEW_REQUIRED")
        for r in report["sources"]
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--state", type=Path, default=STATE)
    parser.add_argument("--output", type=Path, help="Write one JSON report (otherwise stdout)")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--advance", action="store_true",
                        help="Explicitly acknowledge reviewed source changes; not an automatic publication")
    args = parser.parse_args()
    config, state = read_json(args.config), read_json(args.state)
    validate(config, state)
    if args.validate_only:
        print("PASS: 7 GitHub sources and 2 allowlisted SAT picon catalogues")
        return 0
    result = scan(config, state)
    payload = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    if args.advance:
        if not result["safe_to_advance_after_explicit_review"]:
            print("BLOCKED: some sources diverged, errored, or could not be fully compared", file=sys.stderr)
            return 2
        changed = [r for r in result["sources"] if r["current_sha"] != r["previous_sha"]]
        if changed:
            by_id = {s["id"]: s for s in config["sources"]}
            for row in changed:
                if by_id[row["id"]]["kind"] in ("http-index", "site-index"):
                    state["sources"][row["id"]]["index_sha256"] = row["current_sha"]
                    state["sources"][row["id"]]["snapshot"] = row["snapshot"]
                else:
                    state["sources"][row["id"]]["head_sha"] = row["current_sha"]
            args.state.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print("ACKNOWLEDGED: " + str(len(changed)) + " source checkpoint(s); no picons published", file=sys.stderr)
    return 0 if result["safe_to_advance_after_explicit_review"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
