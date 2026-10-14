"""Chunked, retryable item-level diagnostic upload with GitHub readback verification.

Only anonymized JSON reports are uploaded. This module has no PNG or binary
image input path.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

_REPO = "Evolution-by-Warder/PiconHub-Warder-Evolution"
_BRANCH = "factory-warder-development"
_CHUNK_BYTES = 512 * 1024
_RUN = re.compile(r"^\d{8}-\d{6}-\d+$")
_FORBIDDEN_KEY_PARTS = ("token", "secret", "password", "credential",
                        "png_bytes", "image_bytes", "image_data",
                        "absolute_path", "windows_username", "user_profile")


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _validate_no_private_payload(value, key=""):
    normalized_key = key.casefold().replace("-", "_")
    if any(part in normalized_key for part in _FORBIDDEN_KEY_PARTS):
        raise ValueError("private field in review evidence payload")
    if isinstance(value, dict):
        for child_key, child in value.items():
            if not isinstance(child_key, str):
                raise ValueError("non-string evidence key")
            _validate_no_private_payload(child, child_key)
    elif isinstance(value, list):
        for child in value:
            _validate_no_private_payload(child, key)
    elif isinstance(value, str):
        if re.search(r"(?i)(?:[A-Z]:[\\/]|\\\\|(?:^|[\\s=])/(?:users|home|private)/)", value):
            raise ValueError("absolute path in review evidence payload")
        if len(value) > 4096:
            raise ValueError("oversized review evidence field")


def _request_json(url, method="GET", payload=None, token="", opener=None):
    headers = {
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "User-Agent": "Warder-Picon-Factory-Review-Evidence",
    }
    data = None if payload is None else _canonical(payload)
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, method=method, headers=headers)
    return (opener or urllib.request.urlopen)(request, timeout=30)


def _remote_bytes(url, token, opener=None):
    try:
        with _request_json(url + "?ref=" + _BRANCH, token=token, opener=opener) as response:
            remote = json.load(response)
        if remote.get("encoding") != "base64":
            return None
        return base64.b64decode(remote.get("content", "").replace("\n", ""), validate=True)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def _put_and_readback(path, payload_bytes, *, token, opener=None):
    blob_sha = hashlib.sha256(payload_bytes).hexdigest()
    url = ("https://api.github.com/repos/" + _REPO + "/contents/" + path)
    existing = _remote_bytes(url, token, opener)
    if existing is not None:
        if hashlib.sha256(existing).hexdigest() == blob_sha:
            return {"path": path, "sha256": blob_sha, "already_present": True}
        raise ValueError("remote evidence path already exists with different bytes")
    body = {
        "message": "review evidence: " + path.rsplit("/", 1)[-1],
        "branch": _BRANCH,
        "content": base64.b64encode(payload_bytes).decode("ascii"),
    }
    with _request_json(url, "PUT", body, token=token, opener=opener) as response:
        if response.status not in (200, 201):
            raise OSError("GitHub rejected review evidence upload")
    readback = _remote_bytes(url, token, opener)
    if readback is None or hashlib.sha256(readback).hexdigest() != blob_sha:
        raise OSError("GitHub review evidence readback SHA mismatch")
    return {"path": path, "sha256": blob_sha, "already_present": False}


def upload_review_evidence(report_path, *, token=None, opener=None, chunk_bytes=_CHUNK_BYTES):
    """Upload a deterministic gzip stream split into hash-verified chunks."""
    token = (token or os.environ.get("WARDER_DIAGNOSTICS_TOKEN", "")).strip()
    if not token:
        return {"status": "not_configured"}
    if not isinstance(chunk_bytes, int) or not 1024 <= chunk_bytes <= _CHUNK_BYTES:
        raise ValueError("invalid chunk size")
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    _validate_no_private_payload(report)
    run = str(report.get("run", ""))
    if not _RUN.fullmatch(run):
        return {"status": "invalid_run"}
    raw = _canonical(report)
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    # Chunks are contiguous pieces of one gzip stream; concatenate after
    # download, then decompress. Each stored chunk has its own SHA-256.
    chunks = [compressed[i:i + chunk_bytes] for i in range(0, len(compressed), chunk_bytes)] or [b""]
    root = "factory/temp/review-evidence/" + run
    uploaded = []
    for index, chunk in enumerate(chunks, 1):
        name = f"{root}/chunk-{index:04d}.json.gz.part"
        uploaded.append(_put_and_readback(name, chunk, token=token, opener=opener))
    manifest = {
        "schema": 1,
        "run": run,
        "format": "concatenated-gzip-json-chunks",
        "record_count": int(report.get("active_review_tasks", -1)),
        "decision_group_count": int(report.get("decision_group_count", -1)),
        "covered_observation_count": int(report.get("covered_observation_count", 0)),
        "uncompressed_sha256": hashlib.sha256(raw).hexdigest(),
        "compressed_sha256": hashlib.sha256(compressed).hexdigest(),
        "uncompressed_bytes": len(raw),
        "compressed_bytes": len(compressed),
        "chunks": [{"path": row["path"], "sha256": row["sha256"],
                    "bytes": len(chunks[index])}
                   for index, row in enumerate(uploaded)],
        "privacy": report.get("privacy", {}),
    }
    manifest_path = root + "/manifest.json"
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, sort_keys=True,
                                indent=2).encode("utf-8") + b"\n"
    manifest_upload = _put_and_readback(manifest_path, manifest_bytes,
                                        token=token, opener=opener)
    return {
        "status": "sent",
        "run": run,
        "records": manifest["record_count"],
        "groups": manifest["decision_group_count"],
        "covered": manifest["covered_observation_count"],
        "chunks": len(chunks),
        "manifest_path": manifest_path,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "verified": True,
        "already_present": all(row["already_present"] for row in uploaded + [manifest_upload]),
    }


def _read_delivery_state(path):
    if not path.exists():
        return {"delivered": {}, "attempts": {}}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(state, dict):
        return None
    delivered, attempts = state.setdefault("delivered", {}), state.setdefault("attempts", {})
    if not isinstance(delivered, dict) or not isinstance(attempts, dict):
        return None
    if any(not isinstance(k, str) or not isinstance(v, int) or v < 0
           for k, v in attempts.items()):
        return None
    return state


def _write_delivery_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix=path.name + ".", suffix=".tmp",
                                         delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(state, stream, ensure_ascii=False, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError:
        if temporary is not None:
            try:
                temporary.unlink()
            except OSError:
                pass
        raise


def retry_review_evidence_exports(report_dir, state_path, *, limit=5, token=None,
                                  opener=None, max_attempts=3, force_retry=False,
                                  sleeper=time.sleep):
    """Retry local exports without rescanning; stop at a bounded retry budget."""
    folder, state_file = Path(report_dir), Path(state_path)
    if limit < 1 or max_attempts < 1:
        raise ValueError("limit and max_attempts must be positive")
    paths = [p for p in sorted(folder.glob("review-evidence-*.json"))
             if not p.is_symlink() and p.is_file()] if folder.is_dir() else []
    if not paths:
        return []
    configured_token = (token or os.environ.get("WARDER_DIAGNOSTICS_TOKEN", "")).strip()
    if not configured_token:
        return [{"report": p.name, "status": "not_configured"} for p in paths[:limit]]
    state = _read_delivery_state(state_file)
    if state is None:
        return [{"report": p.name, "status": "retry_state_invalid"} for p in paths[:limit]]
    delivered, attempts = state["delivered"], state["attempts"]
    results = []
    for path in paths:
        if len(results) >= limit:
            break
        run = path.stem.removeprefix("review-evidence-")
        if run in delivered:
            continue
        try:
            before = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            results.append({"report": path.name, "status": "local_read_error"})
            continue
        key = run + ":" + before
        if force_retry:
            attempts.pop(key, None)
        count = attempts.get(key, 0)
        if count >= max_attempts:
            results.append({"report": path.name, "status": "retry_limit_reached",
                            "attempts": count})
            continue
        result = {"status": "offline_or_failed"}
        for attempt in range(count, max_attempts):
            attempts[key] = attempt + 1
            try:
                _write_delivery_state(state_file, state)
            except OSError:
                result = {"status": "retry_state_write_failed"}
                break
            try:
                result = upload_review_evidence(path, token=configured_token, opener=opener)
            except (OSError, ValueError, urllib.error.URLError, urllib.error.HTTPError) as exc:
                result = {"status": "offline_or_failed", "detail": type(exc).__name__}
            if result.get("status") == "sent" and result.get("verified"):
                try:
                    after = hashlib.sha256(path.read_bytes()).hexdigest()
                except OSError:
                    result = {"status": "local_read_error"}
                    break
                if after != before:
                    result = {"status": "changed_during_delivery"}
                    attempts.pop(key, None)
                    _write_delivery_state(state_file, state)
                    break
                delivered[run] = {"manifest_sha256": result["manifest_sha256"],
                                  "verified": True}
                attempts.pop(key, None)
                _write_delivery_state(state_file, state)
                break
            if result.get("status") in ("not_configured", "invalid_run",
                                        "invalid_configuration"):
                break
            if attempt + 1 >= max_attempts:
                break
            sleeper(min(2 ** attempt, 5))
        results.append({"report": path.name, **result,
                        "attempts": attempts.get(key, 0)})
        if result.get("status") not in ("sent", "not_configured"):
            break
    return results
