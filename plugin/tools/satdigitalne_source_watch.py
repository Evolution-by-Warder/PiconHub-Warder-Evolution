#!/usr/bin/env python3
"""Read-only catalogue comparison for 005jon / SatDigitalne SAT picons.

Fetches one small HTML index and HEAD metadata of at most two transparent
reference archives per SAT collection. Never downloads binary archives, IPKs,
plugins, or blindly promotes someone else's artwork to Warder production.
"""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
import re
import urllib.error
import urllib.parse
import urllib.request

CATALOG_URL = "https://feed.satdigitalne.cz/picon/"
MAX_HTML = 1024 * 1024
MAX_HEAD = 32
ALLOWED_HOST = "feed.satdigitalne.cz"
FILENAME_RE = re.compile(r"^srp\.[A-Za-z0-9._-]{10,190}\.tar\.xz$")
REQUIRED_GEOMETRIES = (
    "220x132-220x132.light.on.transparent",
    "400x240-400x240.light.on.transparent",
)
USER_AGENT = "Warder-SAT-Source-Watch/1.0 (read-only metadata)"


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.files = set()

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        target = dict(attrs).get("href", "")
        address = urllib.parse.urljoin(CATALOG_URL, target)
        parsed = urllib.parse.urlsplit(address)
        if (parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST
                or parsed.path.count("/") != 2 or not parsed.path.startswith("/picon/")
                or parsed.query or parsed.fragment):
            return
        name = urllib.parse.unquote(parsed.path.rsplit("/", 1)[-1])
        if FILENAME_RE.fullmatch(name):
            self.files.add(name)


def catalog_names(document: bytes) -> list[str]:
    if not document or len(document) > MAX_HTML:
        raise ValueError("Catalogue HTML size outside safety limit")
    parser = Links()
    parser.feed(document.decode("utf-8", errors="replace"))
    names = sorted(parser.files)
    if len(names) < 12:
        raise ValueError("Suspiciously small SAT SRP listing; do not advance")
    return names


def requested_archives(names: list[str]) -> dict[str, str]:
    """Only transparent original-family packages, once per group/geometry."""
    selected: dict[str, str] = {}
    for name in names:
        for geometry in REQUIRED_GEOMETRIES:
            prefix = "srp." + geometry + "_"
            if not name.startswith(prefix):
                continue
            bundle = name[len(prefix):].rsplit(".005jon.tar.xz", 1)[0]
            if not bundle or ".005jon.tar.xz" not in name:
                continue
            selected[bundle + "/" + geometry] = name
    if len(selected) < 8 or len(selected) > MAX_HEAD:
        raise ValueError("Unexpected SAT original archive count; manual review required")
    return dict(sorted(selected.items()))


class SameHostRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlsplit(newurl)
        if parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST:
            raise ValueError("Unexpected redirect outside allowlisted SAT feed")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_safe(request):
    opener = urllib.request.build_opener(SameHostRedirect)
    return opener.open(request, timeout=25)


def fetch_catalogue() -> bytes:
    request = urllib.request.Request(CATALOG_URL, headers={"User-Agent": USER_AGENT})
    with open_safe(request) as response:
        if urllib.parse.urlsplit(response.geturl()).hostname != ALLOWED_HOST:
            raise ValueError("Catalogue escaped host allowlist")
        document = response.read(MAX_HTML + 1)
    if len(document) > MAX_HTML:
        raise ValueError("Oversized catalogue HTML")
    return document


def fetch_archive_head(name: str) -> dict[str, str]:
    if not FILENAME_RE.fullmatch(name):
        raise ValueError("Unsafe external archive filename")
    url = CATALOG_URL + urllib.parse.quote(name)
    request = urllib.request.Request(
        url, method="HEAD", headers={"User-Agent": USER_AGENT}
    )
    with open_safe(request) as response:
        if urllib.parse.urlsplit(response.geturl()).hostname != ALLOWED_HOST:
            raise ValueError("Archive escaped host allowlist")
        meta = {
            "etag": response.headers.get("ETag", "").strip(),
            "last_modified": response.headers.get("Last-Modified", "").strip(),
            "content_length": response.headers.get("Content-Length", "").strip(),
        }
    if not (meta["etag"] or meta["last_modified"]):
        raise ValueError("Archive has no usable ETag or Last-Modified; cannot detect same-name overwrite")
    if meta["content_length"] and not meta["content_length"].isdigit():
        raise ValueError("Invalid content length")
    return meta


def scan_source(source: dict, baseline: dict,
                read_catalogue=fetch_catalogue,
                read_head=fetch_archive_head) -> dict:
    if source["url"] != CATALOG_URL or baseline["url"] != CATALOG_URL:
        raise ValueError("Unexpected SAT feed URL")
    names = catalog_names(read_catalogue())
    selected = requested_archives(names)
    metadata = {}
    for key, filename in selected.items():
        metadata[key] = {"filename": filename, **read_head(filename)}
    snapshot = {
        "archive_names": names,
        "representative_archive_metadata": metadata,
    }
    current = hashlib.sha256(
        json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    previous = baseline.get("index_sha256")
    old_snapshot = baseline.get("snapshot")
    if previous == current and old_snapshot == snapshot:
        status = "UNCHANGED_SKIP"
        candidates = []
    elif previous is None:
        status = "INITIAL_BASELINE_REVIEW_REQUIRED"
        candidates = [{"bundle": key, "filename": val["filename"], "reason": "initial source registration"}
                      for key, val in metadata.items()]
    else:
        status = "CHANGED_REVIEW_REQUIRED"
        older = (old_snapshot or {}).get("representative_archive_metadata", {})
        candidates = [
            {"bundle": key, "filename": val["filename"], "reason": "metadata changed"}
            for key, val in metadata.items() if older.get(key) != val
        ]
        old_names = set((old_snapshot or {}).get("archive_names", []))
        for name in sorted(set(names) - old_names):
            candidates.append({"filename": name, "reason": "new catalogue archive name"})
        for name in sorted(old_names - set(names)):
            candidates.append({"filename": name, "reason": "catalogue archive removed"})
        if not candidates:
            candidates = [{"reason": "source catalogue metadata changed; review"}]
    return {
        "id": source["id"], "repo": None, "branch": None,
        "url": source["url"], "source_group": source["source_group"], "role": source["role"],
        "previous_sha": previous, "current_sha": current, "status": status,
        "changed_path_count": len(candidates),
        "archive_names_seen": len(names), "representative_head_requests": len(metadata),
        "candidates": candidates[:100], "candidate_list_truncated": len(candidates) > 100,
        "snapshot": snapshot,
        "no_binary_download": True,
    }
