"""Read-only index of the current Warder PiconHub production tree.

The runtime filename/service reference is the stable key.  This module never
creates Warder IDs, selects a winner for conflicting artwork, or writes into
the PiconHub checkout.
"""
from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from pathlib import Path, PurePosixPath

SERVICE_REF = re.compile(r"^[0-9a-fA-F]+(?:_[0-9a-fA-F]+){9}$")
DUPLICATE_SUFFIX = re.compile(r"^(?P<ref>[0-9a-fA-F]+(?:_[0-9a-fA-F]+){9}) \((?P<copy>[1-9][0-9]*)\)$")
STYLES = frozenset(("transparent", "black", "white"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def index_master_tree(root: str | Path, previous_cache: dict | None = None, allowed_paths=None) -> dict:
    """Index canonical paths; reuse SHA-256 when path, size and mtime are unchanged."""
    root = Path(root).resolve(strict=True)
    previous_cache = previous_cache if isinstance(previous_cache, dict) else {}
    old_files = previous_cache.get("files", {})
    allow = set(allowed_paths) if allowed_paths is not None else None
    cache_files = {}
    rows = defaultdict(list)
    rejected = 0
    for path in root.rglob("*.png"):
        try:
            rel = path.relative_to(root)
        except ValueError:
            rejected += 1
            continue
        parts = rel.parts
        # PiconHub architecture: picons/<position>/<provider>/<style>/<service>.png
        if len(parts) != 5 or parts[0] != "picons" or parts[3] not in STYLES:
            continue
        if not path.is_file() or not SERVICE_REF.fullmatch(path.stem):
            rejected += 1
            continue
        ref = path.stem.upper()
        stat = path.stat()
        key = rel.as_posix()
        if allow is not None and key not in allow:
            continue
        old = old_files.get(key, {})
        if old.get("size") == stat.st_size and old.get("mtime_ns") == stat.st_mtime_ns and old.get("sha256"):
            digest = old["sha256"]
        else:
            digest = _sha256(path)
        cache_files[key] = {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256": digest}
        rows[ref].append({
            "position": parts[1], "provider": parts[2], "style": parts[3],
            "path": key, "sha256": digest,
        })
    services = {}
    conflicts = []
    for ref, entries in sorted(rows.items()):
        entries.sort(key=lambda row: (row["style"], row["position"], row["provider"], row["path"]))
        services[ref] = entries
        by_style = defaultdict(set)
        for entry in entries:
            by_style[entry["style"]].add(entry["sha256"])
        for style, hashes in sorted(by_style.items()):
            if len(hashes) > 1:
                conflicts.append({"service_reference": ref, "style": style,
                                  "sha256": sorted(hashes), "reason": "MASTER_STYLE_CONFLICT"})
    return {"schema": 1, "authority": "PiconHub-Warder-Evolution/warder-master-production",
            "service_count": len(services), "asset_count": sum(map(len, services.values())),
            "rejected_paths": rejected, "services": services, "conflicts": conflicts,
            "cache": {"schema": 1, "files": cache_files}}


def classify_candidate(path: str | Path, candidate_sha256: str, registry: dict) -> dict:
    """Compare an external image with the master without changing identity or art."""
    path = Path(path)
    stem = path.stem
    duplicate = DUPLICATE_SUFFIX.fullmatch(stem)
    ref = (duplicate.group("ref") if duplicate else stem).upper()
    if not SERVICE_REF.fullmatch(ref):
        return {"classification": "UNMAPPED", "reason": "UNRECOGNIZED_SERVICE_REFERENCE",
                "service_reference": None, "candidate_source": str(path),
                "candidate_sha256": candidate_sha256}
    matches = registry.get("services", {}).get(ref, [])
    master_hashes = sorted({item["sha256"] for item in matches if item["style"] == "transparent"})
    if not matches:
        status, reason = "NEW", "SERVICE_NOT_IN_WARDER_MASTER"
    elif candidate_sha256 in master_hashes:
        status, reason = "IDENTICAL", "EXACT_TRANSPARENT_MATCH"
    else:
        status, reason = "REVIEW", "EXISTING_SERVICE_DIFFERENT_ART"
    return {"classification": status, "reason": reason, "service_reference": ref,
            "duplicate_filename_suffix": int(duplicate.group("copy")) if duplicate else None,
            "candidate_sha256": candidate_sha256, "master_transparent_sha256": master_hashes,
            "master_locations": matches, "candidate_source": str(path)}


def is_master_path(path: str | Path) -> bool:
    """True for files fetched into the protected production-baseline snapshot."""
    normalized = PurePosixPath(str(path).replace("\\", "/"))
    return "github-piconhub" in normalized.parts
