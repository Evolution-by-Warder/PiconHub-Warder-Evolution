"""Discover the current Motor picon ZIP from Vhannibal's official homepage."""
from __future__ import annotations

import hashlib
import html.parser
import json
import os
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from hardening import import_png_zip
from source_registry import atomic_json
from source_inventory import SourceError

HOME = "https://www.vhannibal.net/"
HOSTS = frozenset(("www.vhannibal.net",))
MAX_PAGE = 4_000_000
MAX_ARCHIVE = 450_000_000


class _TableParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self.row_text = None
        self.anchor = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == "tr":
            self.row_text = []
        elif tag.lower() == "a":
            self.anchor = {"href": attrs.get("href", ""), "text": []}

    def handle_data(self, data):
        if self.row_text is not None:
            self.row_text.append(data)
        if self.anchor is not None:
            self.anchor["text"].append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self.anchor is not None:
            self.anchor["text"] = " ".join(self.anchor["text"]).strip()
            if self.row_text is None:
                self.rows.append({"text": self.anchor["text"], "links": [self.anchor]})
            else:
                self.rows.append({"text": " ".join(self.row_text).strip(), "links": [self.anchor]})
            self.anchor = None
        elif tag.lower() == "tr":
            self.row_text = None


def discover_motor_zip(page: str) -> dict:
    parser = _TableParser()
    parser.feed(page)
    matches = []
    for row in parser.rows:
        for link in row["links"]:
            label = " ".join(link["text"].casefold().split())
            if "picon vhannibal motor" not in label:
                continue
            url = urllib.parse.urljoin(HOME, link["href"])
            parsed = urllib.parse.urlsplit(url)
            query = urllib.parse.parse_qs(parsed.query)
            if (parsed.scheme != "https" or parsed.hostname not in HOSTS or
                parsed.path != "/download_setting.php" or query.get("action") != ["download"] or
                not query.get("id", [""])[0].isdigit()):
                continue
            fingerprint = hashlib.sha256((row["text"] + "\0" + url).encode("utf-8")).hexdigest()
            matches.append({"url": url, "label": link["text"], "row": row["text"],
                            "fingerprint": fingerprint})
    if not matches:
        raise SourceError("Current Vhannibal Motor picon archive link was not found")
    return matches[-1]


def _get(url, limit, opener=None, headers=None):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in HOSTS:
        raise SourceError("Unapproved Vhannibal endpoint")
    opener = opener or urllib.request.urlopen
    request = urllib.request.Request(url, headers={"User-Agent": "WarderPiconFactory/1.0",
                                                    **(headers or {})})
    with opener(request, timeout=45) as response:
        final = urllib.parse.urlsplit(response.geturl())
        if final.scheme != "https" or final.hostname not in HOSTS:
            raise SourceError("Vhannibal redirected outside the official host")
        payload = response.read(limit + 1)
        if len(payload) > limit:
            raise SourceError("Vhannibal response exceeds safety limit")
        return payload


def sync_vhannibal(workspace, opener=None, now=None):
    """Check official page, fetch only when its current Motor row changes, import safely."""
    workspace = Path(workspace)
    state_path = workspace / "vhannibal-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
    now = int(now if now is not None else time.time())
    page = _get(HOME, MAX_PAGE, opener).decode("utf-8", "replace")
    current = discover_motor_zip(page)
    if state.get("fingerprint") == current["fingerprint"] and state.get("archive_sha256"):
        return {"status": "unchanged", "archive_sha256": state["archive_sha256"],
                "source": "vhannibal", "fingerprint": current["fingerprint"]}
    archive = workspace / "archives" / "vhannibal" / (current["fingerprint"] + ".zip")
    archive.parent.mkdir(parents=True, exist_ok=True)
    payload = _get(current["url"], MAX_ARCHIVE, opener)
    if not payload.startswith(b"PK\x03\x04"):
        raise SourceError("Vhannibal response is not a ZIP archive")
    digest = hashlib.sha256(payload).hexdigest()
    if not archive.exists():
        fd, temporary = tempfile.mkstemp(prefix=".vhannibal-", suffix=".partial", dir=archive.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, archive)
        finally:
            if os.path.exists(temporary): os.unlink(temporary)
    elif hashlib.sha256(archive.read_bytes()).hexdigest() != digest:
        raise SourceError("Content-addressed Vhannibal archive mismatch")
    with zipfile.ZipFile(archive) as package:
        corrupt = package.testzip()
    if corrupt:
        raise SourceError("Corrupt Vhannibal ZIP member: " + corrupt[:160])
    imported = import_png_zip(archive, workspace / "originals" / "vhannibal")
    new_state = {"schema": 1, "fingerprint": current["fingerprint"],
                 "archive_sha256": digest, "label": current["label"],
                 "source_url": current["url"], "checked_unix": now,
                 "imported_png": imported["imported"], "skipped_png": imported["skipped"]}
    atomic_json(state_path, new_state)
    return {"status": "updated", "source": "vhannibal", "archive_sha256": digest,
            "imported": imported["imported"], "skipped": imported["skipped"],
            "fingerprint": current["fingerprint"]}
