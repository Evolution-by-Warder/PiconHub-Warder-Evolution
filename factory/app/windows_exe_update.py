"""Fail-closed Windows EXE update discovery and integrity verification.

Only an explicitly published Factory Windows manifest is trusted; Actions
artifacts and diagnostics never authorize code installation.
"""
import hashlib
import json
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

REPO = "Evolution-by-Warder/PiconHub-Warder-Evolution"
BRANCH = "factory-warder-development"
MANIFEST_URL = "https://raw.githubusercontent.com/" + REPO + "/" + BRANCH + "/factory/update/windows-exe-manifest.json"
MAX_MANIFEST = 16384
MAX_EXE = 300 * 1024 * 1024
VERSION = re.compile(r"^factory-v(\\d+)\\.(\\d+)\\.(\\d+)$")
SHA = re.compile(r"^[0-9a-f]{64}$")


def version(value):
    match = VERSION.fullmatch(value) if isinstance(value, str) else None
    if not match:
        raise ValueError("Invalid Factory version")
    return tuple(int(v) for v in match.groups())


def validate_manifest(data, installed_version, installed_commit=""):
    if not isinstance(data, dict) or type(data.get("schema")) is not int or data["schema"] != 1:
        raise ValueError("Invalid Windows manifest")
    tag = data.get("version")
    latest = version(tag)
    current = version(installed_version)
    commit = data.get("commit")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Invalid build commit")
    if latest < current or (latest == current and commit == installed_commit):
        return None
    if latest == current:
        # A new commit without a version bump is not an authorized upgrade.
        return None
    asset = "WARDER-PICON-FACTORY.exe"
    expected = "https://github.com/" + REPO + "/releases/download/" + tag + "/" + asset
    if data.get("url") != expected:
        raise ValueError("Untrusted release URL")
    size = data.get("size")
    if type(size) is not int or not 1024 < size <= MAX_EXE:
        raise ValueError("Invalid release size")
    digest = data.get("sha256")
    if not isinstance(digest, str) or not SHA.fullmatch(digest):
        raise ValueError("Invalid release digest")
    return {"version": tag, "commit": commit, "url": expected,
            "size": size, "sha256": digest}


def read_manifest(*, opener=None):
    opener = opener or urllib.request.urlopen
    req = urllib.request.Request(MANIFEST_URL, headers={"User-Agent": "Warder-Picon-Factory", "Accept": "application/json"})
    with opener(req, timeout=8) as response:
        if response.geturl() != MANIFEST_URL:
            raise ValueError("Manifest redirect rejected")
        data = response.read(MAX_MANIFEST + 1)
    if len(data) > MAX_MANIFEST:
        raise ValueError("Oversized manifest")
    return json.loads(data)


def download_verified(info, target, *, opener=None):
    opener = opener or urllib.request.urlopen
    target = Path(target)
    req = urllib.request.Request(info["url"], headers={"User-Agent": "Warder-Picon-Factory"})
    digest = hashlib.sha256()
    total = 0
    try:
        with opener(req, timeout=30) as response, target.open("xb") as output:
            final = urlsplit(response.geturl())
            if (final.scheme != "https" or final.hostname not in
                    ("github.com", "release-assets.githubusercontent.com") or
                    final.username or final.password or final.port not in (None, 443)):
                raise ValueError("Untrusted asset host")
            if final.hostname == "github.com" and response.geturl() != info["url"]:
                raise ValueError("Unexpected GitHub redirect")
            if "text/html" in response.headers.get("Content-Type", "").lower():
                raise ValueError("HTML instead of executable")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > info["size"]:
                    raise ValueError("Oversized EXE")
                digest.update(chunk)
                output.write(chunk)
        if total != info["size"] or digest.hexdigest() != info["sha256"]:
            raise ValueError("Executable integrity mismatch")
        with target.open("rb") as stream:
            if stream.read(2) != b"MZ":
                raise ValueError("Not a Windows executable")
        return target
    except BaseException:
        target.unlink(missing_ok=True)
        raise
