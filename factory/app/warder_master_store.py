"""Git-native, atomic Warder Master transactions on the development branch.

Identity, approval events, and immutable artwork blobs are one commit. A local
decision is never called committed until Git's branch ref is advanced and the
result is read back. Production refs are not accepted by this module.
"""
from __future__ import annotations

import base64
import hashlib
import json
import urllib.error
import urllib.request
from pathlib import PurePosixPath

from warder_identity_registry import (
    append_identity_event, make_approval_event, register_confirmed_identity, sha256_json,
    validate_approval_ledger,
    validate_approval_ledger_transition, validate_master_store,
    validate_registry, validate_registry_transition,
)

REPOSITORY = "Evolution-by-Warder/PiconHub-Warder-Evolution"
BRANCH = "factory-warder-development"
REGISTRY_PATH = "factory/registry/warder-identity-registry.json"
LEDGER_PATH = "factory/registry/master-approval-ledger.json"
API = "https://api.github.com/repos/" + REPOSITORY


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def validate_artwork_blob(content, expected_sha256, style=None):
    """Check bytes and PNG semantics before any Git object is created."""
    if hashlib.sha256(content).hexdigest() != str(expected_sha256).lower():
        raise ValueError("ARTWORK_SHA256_MISMATCH")
    try:
        from PIL import Image
        import io
        with Image.open(io.BytesIO(content)) as image:
            if image.format != "PNG" or image.size != (220, 132) or image.mode != "RGBA":
                raise ValueError("ARTWORK_NOT_220x132_RGBA_PNG")
            image.verify()
        with Image.open(io.BytesIO(content)) as image:
            if style == "transparent" and image.getchannel("A").getbbox() is None:
                raise ValueError("ARTWORK_TRANSPARENT_VARIANT_EMPTY")
            if style in {"black", "white"} and image.getchannel("A").getextrema() != (255, 255):
                raise ValueError("ARTWORK_OPAQUE_VARIANT_HAS_ALPHA")
    except ImportError as exc:
        raise RuntimeError("Pillow is required to validate approved Master PNG assets") from exc
    return True


def _request(token, method, url, payload=None, opener=urllib.request.urlopen):
    body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(url, data=body, method=method, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Warder-Picon-Factory-Master",
        **({"Content-Type": "application/json"} if body is not None else {}),
    })
    try:
        with opener(request, timeout=20) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read(2048).decode("utf-8", "replace")
        raise RuntimeError(f"GitHub API {method} {url.rsplit('/', 1)[-1]} failed ({exc.code}): {detail}") from exc


def _content_at(token, path, commit, opener):
    url = API + "/contents/" + path + "?ref=" + commit
    result = _request(token, "GET", url, opener=opener)
    if result.get("encoding") != "base64" or not isinstance(result.get("content"), str):
        raise ValueError("GIT_MASTER_FILE_NOT_BASE64: " + path)
    return base64.b64decode(result["content"], validate=True)


def _safe_asset_path(path):
    parsed = PurePosixPath(path)
    return (parsed.as_posix() == path and not parsed.is_absolute() and
            ".." not in parsed.parts and path.startswith("factory/approved-picons/"))


def validate_store_transition(old_registry, old_ledger, new_registry, new_ledger):
    issues = []
    identity = validate_registry_transition(old_registry, new_registry)
    approvals = validate_approval_ledger_transition(old_ledger, new_ledger)
    issues.extend({"scope": "identity", **issue} for issue in identity["issues"])
    issues.extend({"scope": "approval", **issue} for issue in approvals["issues"])
    checked = validate_approval_ledger(new_ledger, new_registry)
    issues.extend({"scope": "approval", **issue} for issue in checked["issues"])
    return {"status": "VALID" if not issues else "INVALID", "issues": issues,
            "new_ids": identity.get("new_ids", []),
            "identity_events_appended": identity.get("history_appended", 0),
            "approval_events_appended": approvals.get("appended", 0)}


def build_artwork_approval(registry, approval_ledger, *, warder_id,
                           approval_id, approved_at, evidence_ref,
                           evidence_sha256, review_evidence_sha256,
                           variants, asset_paths, qa_evidence_ref,
                           qa_evidence_sha256, human_approved=False,
                           official_rebrand_confirmed=False, qa_approved=False):
    """Build a coupled registry + ledger candidate; persist only via transaction."""
    approval = make_approval_event(warder_id=warder_id, decision="ARTWORK_APPROVED",
        approval_id=approval_id, approved_at=approved_at, evidence_ref=evidence_ref,
        evidence_sha256=evidence_sha256, review_evidence_sha256=review_evidence_sha256,
        variants=variants, asset_paths=asset_paths, human_approved=human_approved,
        qa_evidence_ref=qa_evidence_ref, qa_evidence_sha256=qa_evidence_sha256)
    is_rebrand = bool(registry.get("records", {}).get(warder_id, {}).get("artwork_current"))
    ledger = json.loads(json.dumps(approval_ledger))
    ledger.setdefault("events", []).append(approval)
    event = {"event_type": "ARTWORK_REBRANDED" if is_rebrand else "ARTWORK_APPROVED",
             "warder_id": warder_id, "evidence_ref": evidence_ref,
             "evidence_sha256": evidence_sha256, "occurred_at": approved_at,
             "identity_continuity_confirmed": True, "qa_approved": qa_approved,
             "human_approved": human_approved, "approval_ledger_event_id": approval["event_id"],
             "asset_paths": asset_paths}
    if is_rebrand:
        event.update({"official_rebrand_confirmed": official_rebrand_confirmed,
                      "previous_variants": registry["records"][warder_id]["artwork_current"],
                      "new_variants": variants})
    else:
        event["variants"] = variants
    updated_registry = append_identity_event(registry, event, human_confirmed=human_approved)
    return updated_registry, ledger, approval


def build_identity_approval(registry, approval_ledger, *, warder_id,
                            approval_id, approved_at, evidence_ref,
                            evidence_sha256, review_evidence_sha256,
                            human_approved=False):
    """Append an identity approval to Git ledger and the same-ID history."""
    approval = make_approval_event(warder_id=warder_id, decision="IDENTITY_APPROVED",
        approval_id=approval_id, approved_at=approved_at, evidence_ref=evidence_ref,
        evidence_sha256=evidence_sha256, review_evidence_sha256=review_evidence_sha256,
        human_approved=human_approved)
    ledger = json.loads(json.dumps(approval_ledger))
    ledger.setdefault("events", []).append(approval)
    event = {"event_type": "IDENTITY_APPROVED", "warder_id": warder_id,
             "evidence_ref": evidence_ref, "evidence_sha256": evidence_sha256,
             "occurred_at": approved_at, "identity_continuity_confirmed": True,
             "approval_ledger_event_id": approval["event_id"]}
    updated_registry = append_identity_event(registry, event, human_confirmed=human_approved)
    return updated_registry, ledger, approval


def build_approval_revocation(registry, approval_ledger, *, warder_id,
                              revokes_event_id, approval_id, approved_at,
                              evidence_ref, evidence_sha256,
                              review_evidence_sha256, human_approved=False):
    """Append an auditable revocation without deleting or rewriting approval."""
    event_target = next((event for event in approval_ledger.get("events", [])
                         if event.get("event_id") == revokes_event_id), None)
    if not event_target or event_target.get("warder_id") != warder_id or event_target.get("decision") == "APPROVAL_REVOKED":
        raise ValueError("Revocation must target a prior approval event for this Warder ID")
    approval = make_approval_event(warder_id=warder_id, decision="APPROVAL_REVOKED",
        approval_id=approval_id, approved_at=approved_at, evidence_ref=evidence_ref,
        evidence_sha256=evidence_sha256, review_evidence_sha256=review_evidence_sha256,
        human_approved=human_approved)
    approval["revokes_event_id"] = revokes_event_id
    approval["event_id"] = "AP-" + sha256_json(
        {key: value for key, value in approval.items() if key != "event_id"})[:24]
    ledger = json.loads(json.dumps(approval_ledger))
    ledger.setdefault("events", []).append(approval)
    registry_event = {"event_type": "APPROVAL_REVOKED", "warder_id": warder_id,
             "evidence_ref": evidence_ref, "evidence_sha256": evidence_sha256,
             "occurred_at": approved_at, "identity_continuity_confirmed": True,
             "approval_ledger_event_id": approval["event_id"]}
    updated_registry = append_identity_event(registry, registry_event, human_confirmed=human_approved)
    return updated_registry, ledger, approval


def build_confirmed_identity_with_artwork(registry, approval_ledger, identity, *,
                                          identity_evidence, approval_id,
                                          approved_at, artwork_evidence_ref,
                                          artwork_evidence_sha256,
                                          review_evidence_sha256, variants,
                                          asset_paths, qa_evidence_ref,
                                          qa_evidence_sha256, human_approved=False,
                                          qa_approved=False):
    """Build a new ID plus its identity/art approvals for one Git transaction."""
    created, warder_id = register_confirmed_identity(registry, identity,
        evidence=identity_evidence, identity_confirmed=human_approved)
    created, ledger, identity_event = build_identity_approval(created, approval_ledger,
        warder_id=warder_id, approval_id=approval_id + "-identity",
        approved_at=approved_at, evidence_ref=identity_evidence["evidence_ref"],
        evidence_sha256=identity_evidence["evidence_sha256"],
        review_evidence_sha256=review_evidence_sha256,
        human_approved=human_approved)
    created, ledger, artwork_event = build_artwork_approval(created, ledger,
        warder_id=warder_id, approval_id=approval_id + "-artwork",
        approved_at=approved_at, evidence_ref=artwork_evidence_ref,
        evidence_sha256=artwork_evidence_sha256,
        review_evidence_sha256=review_evidence_sha256, variants=variants,
        asset_paths=asset_paths, qa_evidence_ref=qa_evidence_ref,
        qa_evidence_sha256=qa_evidence_sha256, human_approved=human_approved,
        qa_approved=qa_approved)
    return created, ledger, warder_id, {"identity": identity_event, "artwork": artwork_event}


def commit_master_transaction(*, token, expected_head, registry, approval_ledger,
                              artwork_blobs=None, message="Update Warder Master",
                              opener=urllib.request.urlopen):
    """Commit registry + ledger + new 220x132 assets as one CAS-guarded Git commit.

    `artwork_blobs` maps immutable repository paths to exact PNG bytes. This
    only targets factory-warder-development and never changes production.
    Failures before ref update leave the branch untouched and return an error.
    """
    if not token or any(char.isspace() for char in token):
        raise PermissionError("A GitHub write credential is required; decision remains PENDING")
    if not isinstance(expected_head, str) or len(expected_head) != 40:
        raise ValueError("A full expected development HEAD is required")
    assets = dict(artwork_blobs or {})
    for path, content in assets.items():
        if not _safe_asset_path(path) or not isinstance(content, bytes):
            raise ValueError("UNSAFE_OR_INVALID_ARTWORK_BLOB")
    branch_info = _request(token, "GET", API + "/branches/" + BRANCH, opener=opener)
    head = branch_info.get("commit", {}).get("sha")
    if head != expected_head:
        raise RuntimeError("STALE_EXPECTED_HEAD: decision remains PENDING; refresh and revalidate")
    old_registry = json.loads(_content_at(token, REGISTRY_PATH, head, opener))
    old_ledger = json.loads(_content_at(token, LEDGER_PATH, head, opener))
    transition = validate_store_transition(old_registry, old_ledger, registry, approval_ledger)
    if transition["status"] != "VALID":
        raise ValueError("MASTER_TRANSACTION_INVALID: " + json.dumps(transition["issues"], ensure_ascii=False))
    for path, content in assets.items():
        digest = hashlib.sha256(content).hexdigest()
        expected = None
        for wid, row in registry.get("records", {}).items():
            for style, asset_path in row.get("artwork_asset_paths", {}).items():
                if asset_path == path:
                    expected = row.get("artwork_current", {}).get(style)
        if expected is None or expected != digest:
            raise ValueError("ARTWORK_NOT_REFERENCED_BY_CANDIDATE_REGISTRY: " + path)
        style = path.rsplit("/", 1)[-1].removesuffix(".png")
        validate_artwork_blob(content, digest, style)
    pending_asset_data = {path: data for path, data in assets.items()}
    old_asset_cache = {}
    def read_asset(path):
        if path in pending_asset_data:
            return pending_asset_data[path]
        if path not in old_asset_cache:
            old_asset_cache[path] = _content_at(token, path, head, opener)
        return old_asset_cache[path]
    store_check = validate_master_store(registry, approval_ledger, read_asset=read_asset)
    if store_check["status"] != "VALID":
        raise ValueError("MASTER_STORE_INVALID: " + json.dumps(store_check["issues"][:20], ensure_ascii=False))
    # Immutable artwork paths cannot be replaced, even with the same bytes.
    for path in assets:
        try:
            _content_at(token, path, head, opener)
        except RuntimeError as exc:
            if "(404)" not in str(exc):
                raise
        else:
            raise ValueError("ARTWORK_PATH_ALREADY_EXISTS_IMMUTABLE: " + path)
    blobs = {}
    payloads = {REGISTRY_PATH: _json_bytes(registry), LEDGER_PATH: _json_bytes(approval_ledger), **assets}
    for path, content in payloads.items():
        response = _request(token, "POST", API + "/git/blobs", {
            "content": base64.b64encode(content).decode("ascii"), "encoding": "base64"}, opener=opener)
        blob_sha = response.get("sha")
        if not isinstance(blob_sha, str) or len(blob_sha) != 40:
            raise RuntimeError("GITHUB_BLOB_CREATE_FAILED: " + path)
        blobs[path] = blob_sha
    commit_obj = _request(token, "GET", API + "/git/commits/" + head, opener=opener)
    tree_sha = commit_obj.get("tree", {}).get("sha")
    if not isinstance(tree_sha, str) or len(tree_sha) != 40:
        raise RuntimeError("GITHUB_BASE_TREE_UNAVAILABLE")
    tree = _request(token, "POST", API + "/git/trees", {
        "base_tree": tree_sha,
        "tree": [{"path": path, "mode": "100644", "type": "blob", "sha": sha}
                 for path, sha in sorted(blobs.items())]}, opener=opener)
    new_tree = tree.get("sha")
    if not isinstance(new_tree, str) or len(new_tree) != 40:
        raise RuntimeError("GITHUB_TREE_CREATE_FAILED")
    commit = _request(token, "POST", API + "/git/commits", {
        "message": message, "tree": new_tree, "parents": [head]}, opener=opener)
    new_commit = commit.get("sha")
    if not isinstance(new_commit, str) or len(new_commit) != 40:
        raise RuntimeError("GITHUB_COMMIT_CREATE_FAILED")
    # Recheck immediately before a non-forced ref update; competing writes fail closed.
    current = _request(token, "GET", API + "/branches/" + BRANCH, opener=opener)
    if current.get("commit", {}).get("sha") != head:
        raise RuntimeError("CONCURRENT_GIT_WRITE: branch unchanged by this transaction; decision remains PENDING")
    _request(token, "PATCH", API + "/git/refs/heads/" + BRANCH,
             {"sha": new_commit, "force": False}, opener=opener)
    # Read-after-write verification. Never claim success from a successful PATCH alone.
    verified_branch = _request(token, "GET", API + "/branches/" + BRANCH, opener=opener)
    if verified_branch.get("commit", {}).get("sha") != new_commit:
        return {"status": "COMMITTED_UNVERIFIED", "commit": new_commit,
                "error": "Branch readback did not match the transaction commit"}
    readback_registry = json.loads(_content_at(token, REGISTRY_PATH, new_commit, opener))
    readback_ledger = json.loads(_content_at(token, LEDGER_PATH, new_commit, opener))
    if readback_registry != registry or readback_ledger != approval_ledger:
        return {"status": "COMMITTED_UNVERIFIED", "commit": new_commit,
                "error": "Registry or approval ledger readback mismatch"}
    for path, data in assets.items():
        if _content_at(token, path, new_commit, opener) != data:
            return {"status": "COMMITTED_UNVERIFIED", "commit": new_commit,
                    "error": "Artwork readback mismatch: " + path}
    return {"status": "COMMITTED_VERIFIED", "branch": BRANCH, "parent": head,
            "commit": new_commit, "paths": sorted(payloads),
            "identity_events_appended": transition["identity_events_appended"],
            "approval_events_appended": transition["approval_events_appended"],
            "production_branch_written": False}
