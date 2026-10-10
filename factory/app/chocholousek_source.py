"""Clean-room monitor/importer for Chocholousek's official picon.cz archive index.

The server's updater protocol publishes a small permalink index. Checks are
limited to once per seven days per the source's published download guidance.
No archived source is deleted or treated as a production approval.
"""
from __future__ import annotations

import hashlib
import html
from html.parser import HTMLParser
import json
import os
import re
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath

from source_registry import atomic_json
from source_inventory import SourceError

INDEX_URL = "https://picon.cz/download/7337/"
HOSTS = frozenset(("picon.cz", "www.picon.cz"))
MIN_CHECK_SECONDS = 7 * 24 * 60 * 60
MAX_INDEX_BYTES = 8_000_000
MAX_ARCHIVE_BYTES = 450_000_000
SAFE_NAME = re.compile(r"^[A-Za-z0-9_.() -]+\.7z$", re.IGNORECASE)
MAGIC = b"7z\xbc\xaf'\x1c"


class _ArchiveLinks(HTMLParser):
    """Collect only explicit 7z links from the official archive page."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.href = None
        self.label = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.href = dict(attrs).get("href")
            self.label = []

    def handle_data(self, data):
        if self.href is not None:
            self.label.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append((self.href, "".join(self.label).strip()))
            self.href = None
            self.label = []


def _parse_html_archives(text):
    parser = _ArchiveLinks()
    parser.feed(text)
    found = {}
    for href, label in parser.links:
        parsed = urllib.parse.urlsplit(html.unescape(href))
        if parsed.scheme and (parsed.scheme != "https" or parsed.hostname not in HOSTS):
            continue
        if parsed.netloc and parsed.hostname not in HOSTS:
            continue
        match = re.fullmatch(r"/download/(\d+)/?", parsed.path)
        if not match:
            continue
        filename = label.strip()
        if not SAFE_NAME.fullmatch(filename) or ".." in filename:
            continue
        found[filename] = {"permalink": match.group(1), "filename": filename}
    return sorted(found.values(), key=lambda item: item["filename"].casefold())


def _raise_no_archives():
    raise SourceError("No Chocholousek archive entries were found")


def parse_archive_index(text):
    """Parse updater index rows as (permalink, archive filename), keeping exact names."""
    if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_INDEX_BYTES:
        raise SourceError("Invalid Chocholousek archive index")
    found = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) < 2:
            continue
        permalink, filename = fields[0], fields[1]
        if not permalink.isdigit() or not SAFE_NAME.fullmatch(filename):
            continue
        if PurePosixPath(filename).name != filename or ".." in filename:
            continue
        found[filename] = {"permalink": permalink, "filename": filename}
    if not found and "<a" in text.lower():
        return _parse_html_archives(text) or _raise_no_archives()
    if not found:
        raise SourceError("No Chocholousek archive entries were found")
    return sorted(found.values(), key=lambda item: item["filename"].casefold())


def _request(url, limit, opener=None):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in HOSTS:
        raise SourceError("Unapproved Chocholousek endpoint")
    opener = opener or urllib.request.urlopen
    req = urllib.request.Request(url, headers={"User-Agent": "WarderPiconFactory/1.0"})
    with opener(req, timeout=45) as response:
        final = urllib.parse.urlsplit(response.geturl())
        if final.scheme != "https" or final.hostname not in HOSTS:
            raise SourceError("Chocholousek redirected outside picon.cz")
        payload = response.read(limit + 1)
        if len(payload) > limit:
            raise SourceError("Chocholousek response exceeds safety limit")
        return payload


def _download_7z(permalink, target, opener=None):
    url = f"https://picon.cz/download/{urllib.parse.quote(permalink, safe='')}/"
    payload = _request(url, MAX_ARCHIVE_BYTES, opener)
    if not payload.startswith(MAGIC):
        raise SourceError("Chocholousek response is not a 7-Zip archive")
    digest = hashlib.sha256(payload).hexdigest()
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".chocho-", suffix=".partial", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
    return digest


def _import_7z(archive, originals_root):
    try:
        import py7zr
    except ImportError as exc:
        raise SourceError("Missing bundled py7zr runtime for Chocholousek 7z archives") from exc
    archive = Path(archive)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    root = Path(originals_root)
    target = root / digest
    if target.is_dir():
        return {"imported": 0, "skipped": sum(1 for p in target.rglob("*.png") if p.is_file()), "sha256": digest}
    root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".chocho-import-", dir=root))
    try:
        with py7zr.SevenZipFile(archive, mode="r") as seven:
            infos = seven.list()
            if len(infos) > 100_000:
                raise SourceError("Too many Chocholousek archive entries")
            selected = []
            total = 0
            for info in infos:
                name = info.filename.replace("\\", "/")
                rel = PurePosixPath(name)
                if rel.is_absolute() or any(part in ("", ".", "..") or ":" in part for part in rel.parts):
                    raise SourceError("Unsafe Chocholousek archive path")
                if getattr(info, "is_symlink", False):
                    raise SourceError("Symlink in Chocholousek archive")
                if name.lower().endswith(".png") and not getattr(info, "is_directory", False):
                    size = int(getattr(info, "uncompressed", 0) or 0)
                    if not 0 < size <= 30_000_000:
                        raise SourceError("Chocholousek PNG outside size limits")
                    total += size
                    if total > 2_000_000_000:
                        raise SourceError("Chocholousek archive expands beyond limit")
                    selected.append(name)
            if not selected:
                raise SourceError("No PNG assets in Chocholousek archive")
            seven.extract(path=stage, targets=selected)
        for path in stage.rglob("*.png"):
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 30_000_000:
                raise SourceError("Unsafe extracted Chocholousek PNG")
        os.replace(stage, target)
        return {"imported": len(selected), "skipped": 0, "sha256": digest}
    finally:
        if stage.exists():
            import shutil
            shutil.rmtree(stage)


def sync_chocholousek(workspace, opener=None, now=None):
    """Weekly conditional update check, then download only newly indexed archives."""
    workspace = Path(workspace)
    state_path = workspace / "chocholousek-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
    now = int(now if now is not None else time.time())
    last = int(state.get("checked_unix", 0) or 0)
    if last and now - last < MIN_CHECK_SECONDS and state.get("archives"):
        return {"status": "cooldown", "source": "chocholousek", "next_check_unix": last + MIN_CHECK_SECONDS,
                "archive_count": len(state["archives"]), "downloaded": 0}
    index_bytes = _request(INDEX_URL, MAX_INDEX_BYTES, opener)
    index_hash = hashlib.sha256(index_bytes).hexdigest()
    if state.get("index_sha256") == index_hash:
        state["checked_unix"] = now
        atomic_json(state_path, state)
        return {"status": "unchanged", "source": "chocholousek", "index_sha256": index_hash,
                "archive_count": len(state.get("archives", {})), "downloaded": 0}
    entries = parse_archive_index(index_bytes.decode("utf-8", "replace"))
    previous = state.get("archives", {})
    archives = dict(previous)
    downloaded = imported = 0
    for item in entries:
        filename = item["filename"]
        previous_item = previous.get(filename)
        if previous_item and previous_item.get("permalink") == item["permalink"]:
            continue
        archive_path = workspace / "archives" / "chocholousek" / (item["permalink"] + "-" + filename)
        archive_hash = _download_7z(item["permalink"], archive_path, opener)
        outcome = _import_7z(archive_path, workspace / "originals" / "chocholousek")
        archives[filename] = {**item, "sha256": archive_hash,
                              "imported_png": outcome["imported"], "skipped_png": outcome["skipped"]}
        downloaded += 1
        imported += outcome["imported"]
    result = {"schema": 1, "index_sha256": index_hash, "checked_unix": now,
              "archives": archives, "source": "chocholousek"}
    atomic_json(state_path, result)
    return {"status": "updated" if downloaded else "index-changed-no-new-archives",
            "source": "chocholousek", "index_sha256": index_hash,
            "downloaded": downloaded, "imported_png": imported,
            "archive_count": len(archives)}
