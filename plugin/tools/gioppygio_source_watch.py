#!/usr/bin/env python3
"""Read-only GioppyGio 220x132 SNP SAT bundle metadata watcher.

A single canonical style (Ful-Trs) is selected to avoid six-fold downloading
or repeatedly checking the same station artwork in decorative variants.
No ZIP contents, plugin files or executables are ever fetched.
"""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
import re
import urllib.parse
import urllib.request

CATALOG_URL = "https://gioppygio.it/ful-trs-1.html"
ALLOWED_HOST = "gioppygio.it"
MAX_HTML_BYTES = 750_000
MAX_ARCHIVE_HEADS = 32
ZIP_NAME = re.compile(r"^gioppygio-ful-trs-220x132-[A-Za-z0-9._-]+\.zip$", re.I)
USER_AGENT = "Warder-SAT-Picon-Source-Watch/1.1 (read-only metadata)"


class LinkIndex(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.filenames: dict[str, str] = {}

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        href = dict(attrs).get("href", "")
        url = urllib.parse.urljoin(CATALOG_URL, href)
        parsed = urllib.parse.urlsplit(url)
        if (parsed.scheme != "https" or parsed.hostname != ALLOWED_HOST
                or parsed.query or parsed.fragment):
            return
        if parsed.path.count("/") != 3 or not parsed.path.startswith("/picons/220x132/"):
            return
        name = urllib.parse.unquote(parsed.path.rsplit("/", 1)[-1])
        if not ZIP_NAME.fullmatch(name):
            return
        self.filenames[name] = CATALOG_URL.split("/ful-trs-1.html")[0] + "/picons/220x132/" + urllib.parse.quote(name)


def find_archives(html: bytes) -> dict[str, str]:
    if not 0 < len(html) <= MAX_HTML_BYTES:
        raise ValueError("GioppyGio source listing empty or too large; refusing advance")
    parser = LinkIndex()
    parser.feed(html.decode("utf-8", errors="replace"))
    found = dict(sorted(parser.filenames.items()))
    if not 8 <= len(found) <= MAX_ARCHIVE_HEADS:
        raise ValueError("Unexpected GioppyGio SAT archive count; no checkpoint advance")
    return found


class RestrictRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        dest = urllib.parse.urlsplit(newurl)
        if dest.scheme != "https" or dest.hostname != ALLOWED_HOST:
            raise ValueError("GioppyGio link redirect left allowlisted host")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def opener():
    return urllib.request.build_opener(RestrictRedirect)


def fetch_page() -> bytes:
    request = urllib.request.Request(CATALOG_URL, headers={"User-Agent": USER_AGENT})
    with opener().open(request, timeout=25) as response:
        if urllib.parse.urlsplit(response.geturl()).hostname != ALLOWED_HOST:
            raise ValueError("GioppyGio page redirected away from allowlisted host")
        result = response.read(MAX_HTML_BYTES + 1)
    if len(result) > MAX_HTML_BYTES:
        raise ValueError("GioppyGio catalogue size exceeds limit")
    return result


def fetch_metadata(name: str) -> dict[str, str]:
    if not ZIP_NAME.fullmatch(name):
        raise ValueError("Unexpected SAT zip filename")
    url = "https://gioppygio.it/picons/220x132/" + urllib.parse.quote(name)
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    with opener().open(request, timeout=25) as response:
        if urllib.parse.urlsplit(response.geturl()).hostname != ALLOWED_HOST:
            raise ValueError("GioppyGio archive redirected away from allowlisted host")
        meta = {
            "etag": response.headers.get("ETag", "").strip(),
            "last_modified": response.headers.get("Last-Modified", "").strip(),
            "content_length": response.headers.get("Content-Length", "").strip(),
        }
    if not meta["etag"] and not meta["last_modified"]:
        raise ValueError("GioppyGio archive has no ETag or Last-Modified: cannot monitor overwrite")
    if meta["content_length"] and not meta["content_length"].isdigit():
        raise ValueError("Bad GioppyGio archive Content-Length")
    return meta


def scan_source(source: dict, baseline: dict, read_html=fetch_page,
                read_metadata=fetch_metadata) -> dict:
    if (source.get("url") != CATALOG_URL
            or baseline.get("url") != CATALOG_URL):
        raise ValueError("GioppyGio URL not allowlisted")
    archives = find_archives(read_html())
    meta = {name: read_metadata(name) for name in archives}
    snapshot = {"archive_names": list(archives), "archive_head_metadata": meta}
    current = hashlib.sha256(json.dumps(
        snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")).hexdigest()
    old = baseline.get("index_sha256")
    if old == current and baseline.get("snapshot") == snapshot:
        status, changes = "UNCHANGED_SKIP", []
    elif old is None:
        status = "INITIAL_BASELINE_REVIEW_REQUIRED"
        changes = [{"filename": n, "reason": "initial source registration"} for n in archives]
    else:
        status = "CHANGED_REVIEW_REQUIRED"
        before = (baseline.get("snapshot") or {}).get("archive_head_metadata", {})
        changes = [{"filename": n, "reason": "archive metadata changed"}
                   for n in meta if before.get(n) != meta[n]]
        changes += [{"filename": n, "reason": "removed archive"}
                    for n in before if n not in meta]
        if not changes:
            changes = [{"reason": "source fingerprint changed; review"}]
    return {
        "id": source["id"], "url": source["url"],
        "source_group": source["source_group"], "role": source["role"],
        "previous_sha": old, "current_sha": current, "status": status,
        "changed_path_count": len(changes), "archive_count": len(archives),
        "metadata_head_requests": len(meta), "candidates": changes[:100],
        "candidate_list_truncated": len(changes) > 100,
        "snapshot": snapshot, "no_binary_download": True,
        "source_format": "SNP (names, not Enigma2 reference)",
    }
