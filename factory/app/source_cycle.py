"""Single-source processing policy and one-time legacy queue cancellation."""
from __future__ import annotations

import hashlib
import gzip
import json
import re
import base64
import urllib.error
import urllib.request
from pathlib import Path

from source_registry import atomic_json

SOURCE_ORDER = ("openatv8", "vhannibal", "chocholousek")
SOURCE_STATUSES = frozenset({
    "NOT_CHECKED", "UNCHANGED", "DOWNLOADED", "PROCESSING",
    "AWAITING_APPROVAL", "COMPLETED", "FAILED",
})
LEGACY_QUEUE_COUNTS = {
    "IDENTITY_VERIFICATION": 4054,
    "ARTWORK_REVIEW": 5877,
    "TECHNICAL_QA": 1,
}
LEGACY_QUEUE_TOTAL = sum(LEGACY_QUEUE_COUNTS.values())
# Earlier Factory builds exposed the unsuppressed queue as 18,011 rows.  The
# owner later cancelled its 9,932-row successor. Both fingerprints are retired
# from active UI/recovery; reports and decision history remain untouched.
RETIRED_QUEUE_FINGERPRINTS = (
    (18011, {"IDENTITY_VERIFICATION": 12133, "ARTWORK_REVIEW": 5877, "TECHNICAL_QA": 1}),
    (LEGACY_QUEUE_TOTAL, LEGACY_QUEUE_COUNTS),
)
_PACKAGE_ID = re.compile(r"^[0-9a-f]{64}$")
_SERVICE_REF = re.compile(r"^[0-9a-fA-F]+(?:_[0-9a-fA-F]+){9}$")
_REPOSITORY = "Evolution-by-Warder/PiconHub-Warder-Evolution"
_BRANCH = "factory-warder-development"
_API = "https://api.github.com/repos/" + _REPOSITORY
_SOURCE_LEDGER = "factory/registry/source-processing-ledger.json"


def _api_json(token, method, url, payload=None, opener=urllib.request.urlopen):
    body = None if payload is None else json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
               "User-Agent": "Warder-Picon-Factory-Source-Cycle"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with opener(request, timeout=20) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read(1024).decode("utf-8", "replace")
        raise RuntimeError(f"SOURCE_GIT_{method}_{exc.code}: {detail}") from exc


def fetch_source_ledger(*, opener=urllib.request.urlopen) -> tuple[str, dict]:
    """Load the public source ledger pinned to the development branch HEAD."""
    branch = _api_json("", "GET", _API + "/branches/" + _BRANCH, opener=opener)
    head = branch.get("commit", {}).get("sha") if isinstance(branch, dict) else None
    if not isinstance(head, str) or not re.fullmatch(r"[0-9a-f]{40}", head):
        raise ValueError("SOURCE_GIT_HEAD_INVALID")
    item = _api_json("", "GET", _API + "/contents/" + _SOURCE_LEDGER + "?ref=" + head, opener=opener)
    if item.get("encoding") != "base64" or not isinstance(item.get("content"), str):
        raise ValueError("SOURCE_GIT_LEDGER_NOT_BASE64")
    try:
        raw = base64.b64decode(item["content"], validate=True)
        ledger = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("SOURCE_GIT_LEDGER_DECODE_FAILED: " + type(exc).__name__) from exc
    errors = validate_source_ledger(ledger)
    if errors:
        raise ValueError("SOURCE_GIT_LEDGER_INVALID: " + ",".join(errors))
    return head, ledger


def commit_source_checkpoint(token: str, expected_head: str, files: dict[str, bytes], *, opener=None) -> dict:
    """Atomically commit source ledger/evidence on the fixed development branch.

    A branch-head race fails closed. Only source metadata, manifests and the
    allowlisted source checkpoint report may be written; PNGs are never accepted.
    """
    if not isinstance(token, str) or not token.strip():
        raise PermissionError("SOURCE_GIT_WRITE_CREDENTIAL_REQUIRED")
    if not isinstance(expected_head, str) or not re.fullmatch(r"[0-9a-f]{40}", expected_head):
        raise ValueError("SOURCE_GIT_EXPECTED_HEAD_INVALID")
    if not isinstance(files, dict) or _SOURCE_LEDGER not in files or not files:
        raise ValueError("SOURCE_GIT_LEDGER_REQUIRED")
    normalized = {}
    for path, content in files.items():
        if (not isinstance(path, str) or path.startswith("/") or ".." in Path(path).parts or
                "\\" in path or not (path.endswith(".json") or path.endswith(".jsonl.gz")) or
                not isinstance(content, bytes)):
            raise ValueError("SOURCE_GIT_PATH_OR_CONTENT_REJECTED")
        allowed = (path == _SOURCE_LEDGER or
                   any(path.startswith("factory/registry/source-manifests/" + source_id + "/")
                       for source_id in SOURCE_ORDER) or
                   any(path.startswith("factory/app/diagnostic-checkpoints/source-" + source_id + "-")
                       for source_id in SOURCE_ORDER))
        if not allowed:
            raise ValueError("SOURCE_GIT_PATH_NOT_ALLOWLISTED: " + path)
        normalized[path] = content
    if sum(len(content) for content in normalized.values()) > 25_000_000:
        raise ValueError("SOURCE_GIT_PAYLOAD_TOO_LARGE")
    try:
        ledger = json.loads(normalized[_SOURCE_LEDGER].decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("SOURCE_GIT_LEDGER_INVALID_JSON") from exc
    errors = validate_source_ledger(ledger)
    if errors:
        raise ValueError("SOURCE_GIT_LEDGER_INVALID: " + ",".join(errors))
    open = opener or urllib.request.urlopen
    branch = _api_json(token, "GET", _API + "/branches/" + _BRANCH, opener=open)
    head = branch.get("commit", {}).get("sha") if isinstance(branch, dict) else None
    if head != expected_head:
        raise RuntimeError("SOURCE_GIT_HEAD_CHANGED: expected " + expected_head + ", found " + str(head))
    base = _api_json(token, "GET", _API + "/git/commits/" + head, opener=open)
    base_tree = base.get("tree", {}).get("sha")
    if not isinstance(base_tree, str) or not re.fullmatch(r"[0-9a-f]{40}", base_tree):
        raise RuntimeError("SOURCE_GIT_BASE_TREE_UNAVAILABLE")
    blob_shas = {}
    for path, content in sorted(normalized.items()):
        blob = _api_json(token, "POST", _API + "/git/blobs", {
            "content": base64.b64encode(content).decode("ascii"), "encoding": "base64"}, opener=open)
        sha = blob.get("sha")
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise RuntimeError("SOURCE_GIT_BLOB_CREATE_FAILED: " + path)
        blob_shas[path] = sha
    tree = _api_json(token, "POST", _API + "/git/trees", {
        "base_tree": base_tree,
        "tree": [{"path": path, "mode": "100644", "type": "blob", "sha": sha}
                 for path, sha in sorted(blob_shas.items())]}, opener=open)
    tree_sha = tree.get("sha")
    if not isinstance(tree_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", tree_sha):
        raise RuntimeError("SOURCE_GIT_TREE_CREATE_FAILED")
    commit = _api_json(token, "POST", _API + "/git/commits", {
        "message": "factory: checkpoint OpenATV source processing",
        "tree": tree_sha, "parents": [head]}, opener=open)
    commit_sha = commit.get("sha")
    if not isinstance(commit_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
        raise RuntimeError("SOURCE_GIT_COMMIT_CREATE_FAILED")
    _api_json(token, "PATCH", _API + "/git/refs/heads/" + _BRANCH,
              {"sha": commit_sha, "force": False}, opener=open)
    readback = _api_json(token, "GET", _API + "/branches/" + _BRANCH, opener=open)
    if readback.get("commit", {}).get("sha") != commit_sha:
        raise RuntimeError("SOURCE_GIT_READBACK_HEAD_MISMATCH")
    commit_info = _api_json(token, "GET", _API + "/git/commits/" + commit_sha, opener=open)
    read_tree = _api_json(token, "GET", _API + "/git/trees/" + commit_info["tree"]["sha"] + "?recursive=1", opener=open)
    entries = {item.get("path"): item.get("sha") for item in read_tree.get("tree", [])}
    for path, sha in blob_shas.items():
        if entries.get(path) != sha:
            raise RuntimeError("SOURCE_GIT_READBACK_FILE_MISMATCH: " + path)
    return {"status": "SAVED_TO_GIT", "branch": _BRANCH, "commit": commit_sha,
            "parent": head, "files": len(blob_shas), "file_blob_shas": blob_shas}


def active_source(ledger: dict) -> str:
    """Keep the Factory on OpenATV until a later owner-approved change."""
    return SOURCE_ORDER[0]


def validate_source_ledger(ledger: dict) -> list[str]:
    errors = []
    if not isinstance(ledger, dict) or ledger.get("schema") != 1:
        return ["INVALID_SOURCE_LEDGER_SCHEMA"]
    if ledger.get("source_order") != list(SOURCE_ORDER):
        errors.append("SOURCE_ORDER_MISMATCH")
    sources = ledger.get("sources")
    if not isinstance(sources, dict):
        return errors + ["SOURCE_MAP_REQUIRED"]
    for source_id in SOURCE_ORDER:
        row = sources.get(source_id)
        if not isinstance(row, dict):
            errors.append("SOURCE_RECORD_MISSING:" + source_id)
            continue
        if row.get("status") not in SOURCE_STATUSES:
            errors.append("SOURCE_STATUS_INVALID:" + source_id)
        if source_id != "openatv8" and row.get("status") != "NOT_CHECKED":
            errors.append("SOURCE_OWNER_DECISION_REQUIRED:" + source_id)
    active = [key for key, row in sources.items()
              if isinstance(row, dict) and row.get("status") in {"PROCESSING", "AWAITING_APPROVAL"}]
    if len(active) > 1:
        errors.append("MULTIPLE_ACTIVE_SOURCES")
    expected_active = active_source(ledger)
    if active and active[0] != expected_active:
        errors.append("ACTIVE_SOURCE_ORDER_VIOLATION")
    return errors


def classify_master_reference(service_reference: str | None, candidate_sha256: str,
                               master_services: dict) -> str:
    """Exact SHA is an artwork match only for the same reference."""
    if not service_reference:
        return "AMBIGUOUS_OR_CONFLICT"
    rows = master_services.get(service_reference)
    if not rows:
        return "NEW_IDENTITY_CANDIDATE"
    if any(row.get("sha256") == candidate_sha256 for row in rows):
        return "EXACT_MATCH"
    return "EXISTING_REFERENCE_DIFFERENT_ARTWORK"


def find_verified_openatv_packages(originals_root: str | Path, schema: int = 3) -> list[dict]:
    """Find only content-addressed OpenATV packages with the expected marker."""
    root = Path(originals_root) / "openatv8" / ("schema-" + str(int(schema)))
    if not root.is_dir() or root.is_symlink():
        return []
    result = []
    for package in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
        if not package.is_dir() or package.is_symlink() or not _PACKAGE_ID.fullmatch(package.name):
            continue
        marker = package / ".warder-import-schema"
        try:
            if marker.is_symlink() or marker.read_text(encoding="ascii").strip() != str(schema):
                continue
            png_count = sum(1 for path in package.rglob("*.png") if path.is_file() and not path.is_symlink())
        except OSError:
            continue
        result.append({"package_id": package.name, "png_count": png_count})
    return result


def build_source_manifest(records: list[dict], source_id: str, source_roots: list[str | Path],
                          output_dir: str | Path) -> tuple[dict[str, bytes], dict]:
    """Create compressed per-PNG metadata manifests; never include PNG bytes or local roots."""
    if source_id not in SOURCE_ORDER:
        raise ValueError("SOURCE_MANIFEST_SOURCE_INVALID")
    roots = [Path(item).resolve() for item in source_roots]
    groups: dict[str, list[dict]] = {}
    seen_paths = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        source = Path(record.get("source", ""))
        digest = str(record.get("sha256", "")).lower()
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            continue
        resolved = source.resolve()
        root = next((candidate for candidate in roots if resolved == candidate or candidate in resolved.parents), None)
        if root is None or source.suffix.casefold() != ".png":
            continue
        try:
            # Resolve both sides before deriving the relative path.  On Windows,
            # Path.resolve() may add a long-path prefix (\\?\) that is absent
            # from the original source path; mixing the two forms silently drops
            # the record from the manifest even though it passed the containment
            # check above.
            rel = resolved.relative_to(root).as_posix()
        except ValueError:
            continue
        if rel.startswith("/") or ".." in Path(rel).parts:
            continue
        key_path = (str(root), rel)
        if key_path in seen_paths:
            continue
        seen_paths.add(key_path)
        parts = Path(rel).parts
        package_id = "unclassified"
        for index, part in enumerate(parts[:-1]):
            if part.casefold() == "schema-3" and index + 1 < len(parts) and _PACKAGE_ID.fullmatch(parts[index + 1]):
                package_id = parts[index + 1]
                break
        stem = source.stem
        ref = stem.split(" (")[0]
        service_ref = ref.upper() if _SERVICE_REF.fullmatch(ref) else None
        row = {"path": rel, "source_package_id": package_id,
               "service_reference": service_ref, "sha256": digest}
        groups.setdefault(package_id, []).append(row)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    blobs = {}
    packages = {}
    for package_id, rows in sorted(groups.items()):
        rows.sort(key=lambda row: row["path"].casefold())
        raw = "".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows).encode("utf-8")
        compressed = gzip.compress(raw, compresslevel=9, mtime=0)
        filename = source_id + "-" + package_id + ".jsonl.gz"
        path = output / filename
        path.write_bytes(compressed)
        blobs[filename] = compressed
        packages[package_id] = {"png_count": len(rows), "manifest_sha256": hashlib.sha256(compressed).hexdigest(),
                                "manifest_bytes": len(compressed), "filename": filename}
    canonical = "".join(key + ":" + str(value["manifest_sha256"]) + "\n" for key, value in sorted(packages.items())).encode("ascii")
    summary = {"png_observations": len(seen_paths), "package_count": len(packages),
               "packages": packages, "manifest_set_sha256": hashlib.sha256(canonical).hexdigest(),
               "metadata_only": True, "contains_png_bytes": False}
    return blobs, summary


def build_openatv_manifest(records: list[dict], source_roots: list[str | Path],
                            output_dir: str | Path) -> tuple[dict[str, bytes], dict]:
    """Backward-compatible OpenATV manifest helper."""
    return build_source_manifest(records, "openatv8", source_roots, output_dir)


def _queue_fingerprint(payload: dict) -> bool:
    if not isinstance(payload, dict):
        return False
    items = payload.get("items")
    if not isinstance(items, list):
        return False
    for total, expected_counts in RETIRED_QUEUE_FINGERPRINTS:
        if payload.get("count") != total or len(items) != total:
            continue
        counts = {key: 0 for key in expected_counts}
        for item in items:
            if not isinstance(item, dict):
                break
            lane = item.get("workstream")
            if lane not in counts:
                lane = {"IDENTITY_COLLISION": "IDENTITY_VERIFICATION"}.get(item.get("category"))
            if lane not in counts:
                break
            counts[lane] += 1
        else:
            recorded = payload.get("workstream_counts")
            if (counts == expected_counts and
                    (not isinstance(recorded, dict) or
                     all(recorded.get(key) == count for key, count in expected_counts.items()))):
                return True
    return False


def is_cancelled_legacy_review_queue(payload: dict) -> bool:
    """Recognize the owner-cancelled queue so no UI can reload it on restart."""
    return _queue_fingerprint(payload)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def migrate_legacy_review_queue(exceptions_dir: str | Path, reports_dir: str | Path,
                                state_dir: str | Path) -> dict:
    """Cancel only exact owner-retired queue fingerprints; preserve all else.

    The migration plan pins filenames and SHA-256 before deletion. A crash can
    resume that plan, but a replaced/new queue is never deleted on retry.
    Reports, ledgers, registries, PNGs, and nonmatching queues are untouched.
    """
    marker = Path(state_dir) / "migrations" / "cancel-retired-review-queues-v2.json"
    marker.parent.mkdir(parents=True, exist_ok=True)
    if marker.is_file():
        try:
            prior = json.loads(marker.read_text(encoding="utf-8"))
            if prior.get("status") == "COMPLETED":
                return prior
            plan = prior.get("targets", [])
            if not plan:
                marker.unlink()
                return migrate_legacy_review_queue(exceptions_dir, reports_dir, state_dir)
        except (OSError, ValueError, TypeError):
            return {"status": "BLOCKED", "reason": "MIGRATION_MARKER_INVALID", "deleted": 0}
    else:
        roots = [Path(exceptions_dir), Path(reports_dir)]
        plan = []
        for root_id, root in zip(("exceptions", "reports"), roots):
            if not root.is_dir() or root.is_symlink():
                continue
            for path in sorted(root.glob("review-queue-*.json"), key=lambda item: item.name.casefold()):
                if path.is_symlink() or not path.is_file():
                    continue
                try:
                    payload = json.loads(path.read_text(encoding="utf-8"))
                    if _queue_fingerprint(payload):
                        plan.append({"root_id": root_id, "filename": path.name, "sha256": _sha256(path),
                                     "item_count": len(payload.get("items", []))})
                except (OSError, ValueError, TypeError):
                    continue
        prior = {"schema": 2, "migration": "cancel-retired-review-queues-v2",
                 "status": "PLANNED", "targets": plan, "deleted": 0, "conflicts": []}
        atomic_json(marker, prior)

    # Empty discovery is not completed cancellation; allow future rescans.
    if not plan:
        marker.unlink(missing_ok=True)
        return {"schema": 2, "migration": "cancel-retired-review-queues-v2",
                "status": "NOT_FOUND", "targets": [], "deleted": 0,
                "discarded_legacy_items": 0, "conflicts": []}

    roots = {"exceptions": Path(exceptions_dir), "reports": Path(reports_dir)}
    deleted = int(prior.get("deleted", 0) or 0)
    conflicts = list(prior.get("conflicts", []))
    for target in plan:
        root = roots.get(target.get("root_id"))
        name = target.get("filename")
        if root is None or not isinstance(name, str) or Path(name).name != name or not name.startswith("review-queue-"):
            conflicts.append("INVALID_TARGET")
            continue
        path = root / name
        if not path.exists():
            continue
        try:
            if path.is_symlink() or not path.is_file() or _sha256(path) != target.get("sha256"):
                conflicts.append(name + ":CONTENT_CHANGED")
                continue
            path.unlink()
            deleted += 1
        except OSError as exc:
            conflicts.append(name + ":" + type(exc).__name__)
    result = {"schema": 2, "migration": "cancel-retired-review-queues-v2",
              "status": "BLOCKED" if conflicts else "COMPLETED", "targets": plan,
              "deleted": deleted, "discarded_legacy_items": sum(
                  int(target.get("item_count", 0)) for target in plan),
              "conflicts": sorted(set(conflicts))}
    atomic_json(marker, result)
    return result
