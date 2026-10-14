"""Fetch and cache the complete, commit-pinned Git Warder Master metadata."""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import tempfile
import urllib.request
from pathlib import Path

from warder_identity_registry import validate_master_store

REPOSITORY = "Evolution-by-Warder/PiconHub-Warder-Evolution"
BRANCH = "factory-warder-development"
REGISTRY_PATH = "factory/registry/warder-identity-registry.json"
APPROVAL_LEDGER_PATH = "factory/registry/master-approval-ledger.json"
API = "https://api.github.com/repos/" + REPOSITORY


def _request_json(url, opener=urllib.request.urlopen, token=""):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Warder-Picon-Factory",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, headers={
        **headers,
    })
    with opener(request, timeout=8) as response:
        return json.loads(response.read().decode("utf-8"))


def _read_json_at_commit(path, commit, opener, token):
    contents = _request_json(API + "/contents/" + path + "?ref=" + commit, opener, token)
    if not isinstance(contents, dict) or not isinstance(contents.get("content"), str):
        raise ValueError("GitHub Contents API response is missing encoded content: " + path)
    encoding = contents.get("encoding")
    if encoding != "base64":
        raise ValueError("GitHub Contents API encoding metadata mismatch (expected base64, got "
                         + repr(encoding) + "): " + path)

    # GitHub's Contents API line-wraps base64 content. Remove only ASCII
    # whitespace before strict validation; do not use validate=False, which
    # would silently ignore arbitrary non-base64 characters.
    encoded = "".join(char for char in contents["content"] if char not in " \t\r\n\v\f")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("GitHub Contents API base64 decode failed for " + path + ": " + str(exc)) from exc
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("GitHub Contents API returned invalid UTF-8 JSON for " + path + ": "
                         + type(exc).__name__ + ": " + str(exc)) from exc
    return value, raw


def fetch_master_snapshot(opener=urllib.request.urlopen, token=""):
    """Read registry and approval ledger from the same dev commit."""
    branch = _request_json(API + "/branches/" + BRANCH, opener, token)
    commit = branch.get("commit", {}).get("sha") if isinstance(branch, dict) else None
    if not isinstance(commit, str) or len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit.lower()):
        raise ValueError("GitHub returned an invalid development branch commit")
    registry, registry_raw = _read_json_at_commit(REGISTRY_PATH, commit, opener, token)
    ledger, ledger_raw = _read_json_at_commit(APPROVAL_LEDGER_PATH, commit, opener, token)
    checked = validate_master_store(registry, ledger)
    if checked["status"] != "VALID":
        raise ValueError("GitHub Warder Master failed validation: " + json.dumps(checked["issues"][:10]))
    return {"schema": 2, "repository": REPOSITORY, "branch": BRANCH,
            "commit": commit,
            "registry_sha256": hashlib.sha256(registry_raw).hexdigest(),
            "approval_ledger_sha256": hashlib.sha256(ledger_raw).hexdigest(),
            "registry": registry, "approval_ledger": ledger}


def fetch_registry_snapshot(opener=urllib.request.urlopen, token=""):
    """Backward-compatible name; snapshots now contain the complete Master metadata."""
    return fetch_master_snapshot(opener, token)


def validate_snapshot(snapshot):
    if not isinstance(snapshot, dict) or snapshot.get("schema") != 2:
        return False
    if snapshot.get("repository") != REPOSITORY or snapshot.get("branch") != BRANCH:
        return False
    commit = snapshot.get("commit")
    if not isinstance(commit, str) or len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit.lower()):
        return False
    def digest(value):
        return hashlib.sha256((json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8")).hexdigest()
    if snapshot.get("registry_sha256") != digest(snapshot.get("registry")):
        return False
    if snapshot.get("approval_ledger_sha256") != digest(snapshot.get("approval_ledger")):
        return False
    return validate_master_store(snapshot.get("registry"), snapshot.get("approval_ledger"))["status"] == "VALID"


def _atomic_cache(path, snapshot):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".warder-master-cache-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(snapshot, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def load_cached_snapshot(path):
    try:
        snapshot = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    return snapshot if validate_snapshot(snapshot) else None


def sync_registry(cache_path, fetcher=None, token=""):
    """Return Git Master state, or its checksum-verified full metadata cache offline."""
    try:
        snapshot = fetcher() if fetcher is not None else fetch_master_snapshot(token=token)
        if not validate_snapshot(snapshot):
            raise ValueError("Fetched Git Warder Master snapshot failed validation")
        _atomic_cache(cache_path, snapshot)
        return {"status": "GIT_CURRENT", "snapshot": snapshot, "error": None}
    except Exception as exc:
        cached = load_cached_snapshot(cache_path)
        if cached is not None:
            return {"status": "OFFLINE_VERIFIED_CACHE", "snapshot": cached,
                    "error": type(exc).__name__ + ": " + str(exc)[:200]}
        return {"status": "UNAVAILABLE", "snapshot": None,
                "error": type(exc).__name__ + ": " + str(exc)[:200]}
