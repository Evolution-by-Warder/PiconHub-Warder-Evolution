#!/usr/bin/env python3
"""Fail-closed catalog contract for Provider/Satellite auxiliary logos.

This module is deliberately separate from rebuild_master_catalog and the
channel service-reference namespace. It validates a staged auxiliary asset
root and exposes an explicit, no-fallback lookup boundary.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import stat
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from PIL import Image

SCHEMA_VERSION = 1
ASSET_ROOT = "auxiliary"
KINDS = ("provider-logo", "satellite-logo")
VARIANTS = ("black", "white")
PNG_SIZE = (220, 132)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
CHECKPOINT_RE = re.compile(r"^[0-9a-f]{40}$")


class AuxiliaryCatalogError(ValueError):
    """The manifest, files, or pinned archive are not safe to publish."""


@dataclass(frozen=True)
class AuxiliaryCatalog:
    """Validated lookup index; contains no channel or orbital-position data."""

    root: Path
    entries: Mapping[tuple[str, str], Mapping[str, Any]]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_filename(filename: Any) -> bool:
    if not isinstance(filename, str) or not filename or filename in {".", ".."}:
        return False
    if filename != PurePosixPath(filename).name:
        return False
    if "/" in filename or "\\" in filename or "::" in filename:
        return False
    if filename.startswith(".") or filename.endswith((".", " ")):
        return False
    if unicodedata.normalize("NFC", filename) != filename:
        return False
    if not filename.endswith(".png"):
        return False
    return not any(ord(ch) < 32 or ord(ch) == 127 for ch in filename)


def _expected_identity(kind: str, filename: str) -> str:
    return f"{kind}::{filename}"


def _expected_asset_path(kind: str, variant: str, filename: str) -> str:
    if kind not in KINDS or variant not in VARIANTS or not _safe_filename(filename):
        raise AuxiliaryCatalogError("invalid auxiliary kind, variant, or filename")
    return f"{ASSET_ROOT}/{kind}/{variant}/{filename}"


def build_manifest(
    records: Sequence[Mapping[str, Any]], *, approved_candidate_checkpoint: str
) -> dict[str, Any]:
    """Build the canonical minimal manifest from already-approved records.

    Each record supplies identity, kind, filename, source SHA, BLACK/WHITE
    SHA, QC status and a visual-approval/provenance reference. Asset paths are
    derived here; callers cannot redirect an identity into the channel tree.
    """
    if not CHECKPOINT_RE.fullmatch(approved_candidate_checkpoint or ""):
        raise AuxiliaryCatalogError("invalid approved candidate checkpoint")
    entries: list[dict[str, Any]] = []
    for record in records:
        kind = record.get("kind")
        filename = record.get("filename")
        if kind not in KINDS or not _safe_filename(filename):
            raise AuxiliaryCatalogError("invalid kind or unsafe filename")
        identity = _expected_identity(kind, filename)
        if record.get("identity") != identity:
            raise AuxiliaryCatalogError(f"identity/key mismatch: {identity}")
        black_sha = record.get("black_sha256")
        white_sha = record.get("white_sha256")
        source_sha = record.get("transparent_source_sha256")
        if any(not isinstance(value, str) or not SHA256_RE.fullmatch(value)
               for value in (black_sha, white_sha, source_sha)):
            raise AuxiliaryCatalogError(f"invalid SHA256: {identity}")
        qc_status = record.get("qc_status")
        provenance = record.get("visual_approval_provenance")
        if qc_status != "PASS" or not isinstance(provenance, str) or not provenance.strip():
            raise AuxiliaryCatalogError(f"missing approval/QC provenance: {identity}")
        entries.append({
            "identity": identity,
            "kind": kind,
            "filename": filename,
            "black": {"path": _expected_asset_path(kind, "black", filename), "sha256": black_sha},
            "white": {"path": _expected_asset_path(kind, "white", filename), "sha256": white_sha},
            "transparent_source_sha256": source_sha,
            "qc_status": "PASS",
            "visual_approval_provenance": provenance.strip(),
        })
    entries.sort(key=lambda entry: entry["identity"].casefold())
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "approved_candidate_checkpoint": approved_candidate_checkpoint,
        "entries": entries,
    }
    _validate_manifest_shape(manifest)
    return manifest


def canonical_manifest_bytes(manifest: Mapping[str, Any]) -> bytes:
    """Stable UTF-8 serialization used for review and content-addressing."""
    _validate_manifest_shape(manifest)
    return (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _validate_manifest_shape(manifest: Mapping[str, Any]) -> None:
    if set(manifest) != {"schema_version", "approved_candidate_checkpoint", "entries"}:
        raise AuxiliaryCatalogError("manifest has missing or unsupported top-level fields")
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise AuxiliaryCatalogError("unsupported schema_version")
    if not CHECKPOINT_RE.fullmatch(str(manifest.get("approved_candidate_checkpoint", ""))):
        raise AuxiliaryCatalogError("invalid approved candidate checkpoint")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise AuxiliaryCatalogError("entries must be a non-empty array")
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    sort_keys: list[str] = []
    for entry in entries:
        required = {"identity", "kind", "filename", "black", "white",
                    "transparent_source_sha256", "qc_status", "visual_approval_provenance"}
        if not isinstance(entry, dict) or set(entry) != required:
            raise AuxiliaryCatalogError("entry has missing or unsupported fields")
        kind, filename = entry.get("kind"), entry.get("filename")
        if kind not in KINDS or not _safe_filename(filename):
            raise AuxiliaryCatalogError("invalid auxiliary kind or unsafe filename")
        identity = _expected_identity(kind, filename)
        if entry.get("identity") != identity:
            raise AuxiliaryCatalogError(f"identity/key mismatch: {identity}")
        key = identity.casefold()
        if key in seen_ids:
            raise AuxiliaryCatalogError(f"duplicate auxiliary identity: {identity}")
        seen_ids.add(key)
        sort_keys.append(key)
        if entry.get("qc_status") != "PASS":
            raise AuxiliaryCatalogError(f"QC status is not PASS: {identity}")
        provenance = entry.get("visual_approval_provenance")
        if not isinstance(provenance, str) or not provenance.strip():
            raise AuxiliaryCatalogError(f"missing visual approval/provenance: {identity}")
        source_sha = entry.get("transparent_source_sha256")
        if not isinstance(source_sha, str) or not SHA256_RE.fullmatch(source_sha):
            raise AuxiliaryCatalogError(f"invalid transparent source SHA256: {identity}")
        for variant in VARIANTS:
            asset = entry.get(variant)
            if not isinstance(asset, dict) or set(asset) != {"path", "sha256"}:
                raise AuxiliaryCatalogError(f"missing {variant} asset record: {identity}")
            expected_path = _expected_asset_path(kind, variant, filename)
            path = asset.get("path")
            folded_path = path.casefold()
            if folded_path in seen_paths:
                raise AuxiliaryCatalogError(f"duplicate asset path: {path}")
            seen_paths.add(folded_path)
            if path != expected_path:
                raise AuxiliaryCatalogError(f"unsafe or misbound asset path: {identity} {variant}")
            if path.startswith("picons/") or not path.startswith("auxiliary/"):
                raise AuxiliaryCatalogError(f"channel namespace collision: {path}")
            digest = asset.get("sha256")
            if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
                raise AuxiliaryCatalogError(f"invalid {variant} SHA256: {identity}")
    if sort_keys != sorted(sort_keys):
        raise AuxiliaryCatalogError("entries are not in deterministic identity order")


def _validate_png(data: bytes, *, expected_sha256: str, label: str) -> None:
    if _sha256(data) != expected_sha256:
        raise AuxiliaryCatalogError(f"SHA256 mismatch: {label}")
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            if image.format != "PNG" or image.size != PNG_SIZE or image.mode != "RGBA":
                raise AuxiliaryCatalogError(f"PNG must be RGBA {PNG_SIZE}: {label}")
    except AuxiliaryCatalogError:
        raise
    except Exception as exc:
        raise AuxiliaryCatalogError(f"invalid PNG: {label}: {exc}") from exc


def verify_pinned_archive(
    archive_bytes: bytes,
    *,
    expected_archive_sha256: str,
    expected_members: Mapping[str, str],
) -> None:
    """Verify archive pin, safe members, exact member set, and per-member hashes."""
    if not SHA256_RE.fullmatch(expected_archive_sha256 or "") or _sha256(archive_bytes) != expected_archive_sha256:
        raise AuxiliaryCatalogError("archive SHA256 mismatch")
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            bad = archive.testzip()
            if bad:
                raise AuxiliaryCatalogError(f"archive CRC failure: {bad}")
            actual: dict[str, bytes] = {}
            for info in archive.infolist():
                path = PurePosixPath(info.filename)
                mode = (info.external_attr >> 16) & 0xFFFF
                if (path.is_absolute() or ".." in path.parts or "." in path.parts
                        or "\\" in info.filename or path.as_posix() != info.filename):
                    raise AuxiliaryCatalogError(f"unsafe archive path: {info.filename}")
                if stat.S_ISLNK(mode):
                    raise AuxiliaryCatalogError(f"archive symlink forbidden: {info.filename}")
                if info.is_dir():
                    continue
                if path.suffix.lower() != ".png" or info.filename in actual:
                    raise AuxiliaryCatalogError(f"unexpected or duplicate archive member: {info.filename}")
                if any(existing.casefold() == info.filename.casefold() for existing in actual):
                    raise AuxiliaryCatalogError(f"case-insensitive duplicate archive member: {info.filename}")
                actual[info.filename] = archive.read(info)
    except AuxiliaryCatalogError:
        raise
    except Exception as exc:
        raise AuxiliaryCatalogError(f"invalid ZIP archive: {exc}") from exc
    if set(actual) != set(expected_members):
        raise AuxiliaryCatalogError("archive member set does not match manifest")
    for member, expected_sha in expected_members.items():
        if not SHA256_RE.fullmatch(expected_sha or "") or _sha256(actual[member]) != expected_sha:
            raise AuxiliaryCatalogError(f"archive member SHA256 mismatch: {member}")


def verify_candidate_archives(
    manifest: Mapping[str, Any],
    archives: Mapping[str, bytes],
    archive_sha256_pins: Mapping[str, str],
) -> None:
    """Bind the approved candidate ZIP set to the catalog's exact identities.

    Candidate archive layout is treated as input provenance only. The
    production target paths are still derived by _expected_asset_path().
    """
    _validate_manifest_shape(manifest)
    names = {
        "transparent-sources.zip",
        "provider-black-centered.zip",
        "provider-white-centered.zip",
        "satellite-black-white-centered.zip",
    }
    if set(archives) != names or set(archive_sha256_pins) != names:
        raise AuxiliaryCatalogError("candidate archive set is incomplete or contains extras")
    expected: dict[str, dict[str, str]] = {name: {} for name in names}
    for entry in manifest["entries"]:
        kind, filename = entry["kind"], entry["filename"]
        if kind == "provider-logo":
            source_member = f"source-transparent/provider/{filename}"
            black_archive, black_member = "provider-black-centered.zip", f"black/provider/{filename}"
            white_archive, white_member = "provider-white-centered.zip", f"white/provider/{filename}"
        else:
            source_member = f"source-transparent/satellite/{filename}"
            black_archive = white_archive = "satellite-black-white-centered.zip"
            black_member, white_member = f"black/satellite/{filename}", f"white/satellite/{filename}"
        expected["transparent-sources.zip"][source_member] = entry["transparent_source_sha256"]
        expected[black_archive][black_member] = entry["black"]["sha256"]
        expected[white_archive][white_member] = entry["white"]["sha256"]
    for name in sorted(names):
        verify_pinned_archive(
            archives[name],
            expected_archive_sha256=archive_sha256_pins[name],
            expected_members=expected[name],
        )


def validate_manifest(
    manifest: Mapping[str, Any],
    repository_root: Path,
    *,
    channel_paths: Sequence[str] = (),
) -> AuxiliaryCatalog:
    """Fail closed on manifest, path, PNG, hash, namespace, or orphan errors."""
    _validate_manifest_shape(manifest)
    root = repository_root.resolve()
    auxiliary_root = root / ASSET_ROOT
    channel_paths_folded = {str(path).casefold() for path in channel_paths}
    indexed: dict[tuple[str, str], Mapping[str, Any]] = {}
    expected_files: set[str] = set()
    for entry in manifest["entries"]:
        kind, filename = entry["kind"], entry["filename"]
        identity = entry["identity"]
        for variant in VARIANTS:
            asset = entry[variant]
            rel = asset["path"]
            if rel.casefold() in channel_paths_folded:
                raise AuxiliaryCatalogError(f"target collides with channel path: {rel}")
            candidate = (root / PurePosixPath(rel)).resolve()
            if not candidate.is_relative_to(auxiliary_root.resolve()):
                raise AuxiliaryCatalogError(f"asset escaped auxiliary root: {rel}")
            current = root
            for part in PurePosixPath(rel).parts:
                current = current / part
                if current.is_symlink():
                    raise AuxiliaryCatalogError(f"symlink forbidden: {rel}")
            if not candidate.is_file():
                raise AuxiliaryCatalogError(f"missing asset: {rel}")
            _validate_png(candidate.read_bytes(), expected_sha256=asset["sha256"], label=rel)
            expected_files.add(PurePosixPath(rel).as_posix())
        indexed[(kind, filename)] = entry

    actual_files: set[str] = set()
    if auxiliary_root.exists():
        for path in auxiliary_root.rglob("*"):
            if path.is_symlink():
                raise AuxiliaryCatalogError(f"symlink forbidden in auxiliary tree: {path}")
            if path.is_file():
                actual_files.add(path.relative_to(root).as_posix())
    if actual_files != expected_files:
        extras = sorted(actual_files - expected_files)
        missing = sorted(expected_files - actual_files)
        raise AuxiliaryCatalogError(f"orphan/missing auxiliary files: extras={extras[:5]} missing={missing[:5]}")
    return AuxiliaryCatalog(root=root, entries=indexed)


def validate_publication(
    manifest: Mapping[str, Any],
    repository_root: Path,
    *,
    archives: Mapping[str, bytes],
    archive_sha256_pins: Mapping[str, str],
    channel_paths: Sequence[str] = (),
) -> AuxiliaryCatalog:
    """Single fail-closed gate: pinned candidate bundle plus staged asset tree."""
    verify_candidate_archives(manifest, archives, archive_sha256_pins)
    return validate_manifest(manifest, repository_root, channel_paths=channel_paths)


def load_catalog(
    manifest_path: Path,
    repository_root: Path,
    *,
    channel_paths: Sequence[str] = (),
) -> AuxiliaryCatalog:
    """Read and validate a JSON catalog before exposing its lookup boundary."""
    manifest_path = Path(manifest_path)
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise AuxiliaryCatalogError("catalog manifest is missing or is a symlink")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise AuxiliaryCatalogError(f"invalid catalog JSON: {exc}") from exc
    if not isinstance(manifest, dict):
        raise AuxiliaryCatalogError("catalog JSON root must be an object")
    return validate_manifest(manifest, repository_root, channel_paths=channel_paths)


def lookup_auxiliary(
    catalog: AuxiliaryCatalog, kind: str, filename: str, variant: str
) -> str | None:
    """Return an exact auxiliary path or clean miss; never falls back/infer IDs."""
    if kind not in KINDS or variant not in VARIANTS or not _safe_filename(filename):
        raise AuxiliaryCatalogError("invalid auxiliary lookup key")
    entry = catalog.entries.get((kind, filename))
    if entry is None:
        return None
    return entry[variant]["path"]
