"""Small read-only gallery of genuine additions to the Warder source repository."""
import hashlib
import json
import os
import pathlib
import re
import ssl
import struct
import tempfile
import time
from urllib.request import Request, urlopen

REPOSITORY = "Evolution-by-Warder/PiconHub-Warder-Evolution"
API = "https://api.github.com/repos/" + REPOSITORY
RAW = "https://raw.githubusercontent.com/" + REPOSITORY + "/"
CACHE = pathlib.Path("/var/cache/piconhub-warder-evolution/recent-black")
COUNT, MAX_PNG, TTL = 6, 512 * 1024, 1800
SHA = re.compile(r"[0-9a-f]{40}\Z")
SOURCE = re.compile(r"picons/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+/black/[a-zA-Z0-9_]+\.png\Z")


def network_open(url):
    return urlopen(Request(url, headers={"User-Agent": "PiconHub-Warder-Evolution",
                                       "Cache-Control": "no-cache"}),
                   timeout=8, context=ssl.create_default_context())


def read_json(url, opener):
    with opener(url) as response:
        data = response.read(2 * 1024 * 1024 + 1)
    if len(data) > 2 * 1024 * 1024:
        raise ValueError("Recent picon metadata is too large")
    return json.loads(data)


def verify_png(data, sha):
    if len(data) < 33 or len(data) > MAX_PNG or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError("Invalid recent picon")
    width, height = struct.unpack(">II", data[16:24])
    if not 0 < width <= 1600 or not 0 < height <= 960:
        raise ValueError("Invalid recent picon dimensions")
    if not SHA.fullmatch(sha) or hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() != sha:
        raise ValueError("Recent picon does not match its Git blob")
    return data


def discover(opener):
    commits = read_json(API + "/commits?sha=main&path=picons&per_page=8", opener)
    if not isinstance(commits, list):
        raise ValueError("Invalid recent history")
    seen, result = set(), []
    for commit in commits[:8]:
        sha = commit.get("sha", "")
        if not SHA.fullmatch(sha):
            raise ValueError("Invalid recent commit")
        # One bounded page per commit; do not walk the entire picon database.
        detail = read_json(API + "/commits/" + sha + "?per_page=100", opener)
        for entry in detail.get("files", [])[:100]:
            path, blob = entry.get("filename", ""), entry.get("sha", "")
            if entry.get("status") != "added" or not SOURCE.fullmatch(path) or ".." in path.split("/"):
                continue
            if not SHA.fullmatch(blob) or blob in seen:
                continue
            with opener(RAW + sha + "/" + path) as response:
                data = response.read(MAX_PNG + 1)
            result.append((blob, verify_png(data, blob)))
            seen.add(blob)
            if len(result) == COUNT:
                return result
    if not result:
        raise ValueError("No recent additions in bounded history")
    return result


def bundled(root):
    manifest = json.loads((root / "images/recent/sources.json").read_text())
    paths = []
    for entry in manifest["items"][:COUNT]:
        sha = entry["sha"]
        if not SHA.fullmatch(sha):
            continue
        path = root / "images/recent" / (sha + ".png")
        verify_png(path.read_bytes(), sha)
        paths.append(path)
    return paths


def cached(folder):
    try:
        document = json.loads((folder / "manifest.json").read_text())
        if document.get("style") != "black":
            return [], 0
        paths = []
        for sha in document["items"][:COUNT]:
            if not isinstance(sha, str) or not SHA.fullmatch(sha):
                return [], 0
            path = folder / (sha + ".png")
            with path.open("rb") as stream:
                verify_png(stream.read(MAX_PNG + 1), sha)
            paths.append(path)
        return paths, float(document["checked_at"])
    except (OSError, ValueError, KeyError, TypeError):
        return [], 0


def atomic_write(path, data):
    handle, temporary = tempfile.mkstemp(prefix=".recent-", dir=str(path.parent))
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_recent(root, folder=CACHE, opener=network_open, now=None):
    """Run in a worker. Offline/limited API access retains actual known additions."""
    folder = pathlib.Path(folder)
    now = time.time() if now is None else now
    old, checked = cached(folder)
    if old and 0 <= now - checked < TTL:
        return old
    try:
        images = discover(opener)
        # Retain older genuine additions if the bounded scan found fewer than six.
        if len(images) < COUNT:
            seen = {sha for sha, data in images}
            for path in old + bundled(root):
                if path.stem not in seen:
                    data = verify_png(path.read_bytes(), path.stem)
                    images.append((path.stem, data));seen.add(path.stem)
                if len(images) == COUNT:
                    break
        folder.mkdir(parents=True, exist_ok=True)
        for sha, data in images:
            atomic_write(folder / (sha + ".png"), data)
        identities = [sha for sha, data in images]
        atomic_write(folder / "manifest.json", json.dumps({"style": "black", "checked_at": now, "items": identities}).encode())
        for path in folder.glob("*.png"):
            if SHA.fullmatch(path.stem) and path.stem not in identities:
                try:
                    path.unlink()
                except OSError:
                    pass
        return [folder / (sha + ".png") for sha in identities]
    except Exception:
        return old or bundled(root)
