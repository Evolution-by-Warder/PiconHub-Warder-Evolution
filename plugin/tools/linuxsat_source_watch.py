#!/usr/bin/env python3
"""Read-only public LinuxSat Enigma2 Picons forum RSS watcher.

The feed is a discovery hint, not a source of verified artwork or Enigma2 DVB
identities. Never log in, scrape protected posts, or download attachments.
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

RSS_URL = "https://www.linuxsat-support.com/thread-list-rss-feed/19/"
BOARD_URL = "https://www.linuxsat-support.com/board/19-enigma2-picons/"
HOSTS = {"www.linuxsat-support.com", "linuxsat-support.com"}
MAX_RSS_BYTES = 512 * 1024
MAX_ITEMS = 150
USER_AGENT = "Warder-SAT-Picon-Source-Watch/1.1 (public RSS only)"
THREAD_RE = re.compile(r"^/thread/(\d+)(?:[-/].*)?$", re.I)
NON_SAT_RE = re.compile(r"\b(?:iptv|rakuten|samsung\s+tv|dtt|dvb-t|terrestrial|tdt)\b", re.I)
DUPLICATE_GIOPPY = re.compile(r"gioppygio", re.I)


class RestrictRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, target):
        parsed = urllib.parse.urlsplit(target)
        if parsed.scheme != "https" or parsed.hostname not in HOSTS:
            raise ValueError("LinuxSat RSS redirect left the allowlisted domain")
        return super().redirect_request(request, fp, code, msg, headers, target)


def fetch_rss() -> bytes:
    request = urllib.request.Request(RSS_URL, headers={
        "User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml;q=0.9",
    })
    opener = urllib.request.build_opener(RestrictRedirect)
    with opener.open(request, timeout=25) as response:
        target = urllib.parse.urlsplit(response.geturl())
        if target.scheme != "https" or target.hostname not in HOSTS:
            raise ValueError("Unexpected LinuxSat RSS host")
        payload = response.read(MAX_RSS_BYTES + 1)
    if len(payload) > MAX_RSS_BYTES:
        raise ValueError("LinuxSat RSS larger than safety limit")
    return payload


def parse_rss(payload: bytes) -> list[dict[str, str]]:
    if not payload or len(payload) > MAX_RSS_BYTES:
        raise ValueError("Missing or oversized LinuxSat RSS feed")
    if b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper():
        raise ValueError("Untrusted XML document type declaration")
    root = ET.fromstring(payload)
    entries = root.findall("./channel/item")
    if root.tag != "rss" or not entries or len(entries) > MAX_ITEMS:
        raise ValueError("LinuxSat must return a complete bounded public RSS feed")
    result: dict[str, dict[str, str]] = {}
    for item in entries:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        updated = (item.findtext("pubDate") or "").strip()
        if not title or not link or not updated:
            raise ValueError("LinuxSat RSS item missing title, link or date")
        parsed = urllib.parse.urlsplit(link)
        if parsed.scheme != "https" or parsed.hostname not in HOSTS:
            raise ValueError("Unexpected LinuxSat RSS item URL")
        match = THREAD_RE.match(parsed.path)
        if not match:
            raise ValueError("Cannot map LinuxSat item to thread identity")
        thread_id = match.group(1)
        row = {
            "thread_id": thread_id, "title": title[:180],
            "url": f"https://www.linuxsat-support.com/thread/{thread_id}/",
            "updated": updated[:100],
            "category": "NOT_SAT_IGNORE" if NON_SAT_RE.search(title) else "UNVERIFIED_FORUM_TOPIC",
            "duplicate_of": "gioppygio-sat-snp" if DUPLICATE_GIOPPY.search(title) else "",
        }
        previous = result.get(thread_id)
        if previous is None or row["updated"] > previous["updated"]:
            result[thread_id] = row
    return sorted(result.values(), key=lambda x: x["thread_id"])


def scan_source(source: dict, baseline: dict, read_feed=fetch_rss) -> dict:
    if source.get("url") != RSS_URL or baseline.get("url") != RSS_URL:
        raise ValueError("Untrusted LinuxSat RSS URL")
    items = parse_rss(read_feed())
    snapshot = {"threads": items}
    current = hashlib.sha256(json.dumps(
        snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()
    old = baseline.get("index_sha256")
    if old == current and baseline.get("snapshot") == snapshot:
        status, changes = "UNCHANGED_SKIP", []
    elif old is None:
        status = "INITIAL_BASELINE_REVIEW_REQUIRED"
        changes = [
            {"thread_id": x["thread_id"], "title": x["title"], "url": x["url"],
             "reason": "initial forum RSS entry",
             "duplicate_of": x["duplicate_of"]}
            for x in items if x["category"] == "UNVERIFIED_FORUM_TOPIC"
        ]
    else:
        status = "CHANGED_REVIEW_REQUIRED"
        older = {x["thread_id"]: x for x in
                 (baseline.get("snapshot") or {}).get("threads", [])}
        changes = [
            {"thread_id": x["thread_id"], "title": x["title"], "url": x["url"],
             "reason": "new or updated forum RSS entry",
             "duplicate_of": x["duplicate_of"]}
            for x in items if x["category"] == "UNVERIFIED_FORUM_TOPIC"
            and older.get(x["thread_id"]) != x
        ]
        if not changes:
            changes = [{"reason": "RSS window changed but no new eligible SAT topic"}]
    return {
        "id": source["id"], "url": source["url"],
        "role": source["role"], "source_group": source["source_group"],
        "previous_sha": old, "current_sha": current, "status": status,
        "changed_path_count": len(changes), "rss_items_seen": len(items),
        "candidates": changes[:100], "candidate_list_truncated": len(changes) > 100,
        "snapshot": snapshot, "public_metadata_only": True, "no_attachment_download": True,
        "identity_note": "Forum update is not proof of a new SAT logo or service reference.",
    }
