"""Verified import of previously rendered OpenATV candidate triplets.

The bundle is a render cache seed, never an approval source.  Every imported
file is bound to its source artwork SHA-256 and checked against the candidate
ledger before it enters the normal Factory QA and review flow.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path


_PART_RE = re.compile(r"^WARDER-OPENATV-TECHNICAL-CANDIDATES-(\d{8})-PART-(0[1-4])-OF-04\.zip$")
_HASH = re.compile(r"^[0-9a-f]{64}$")
_OUTPUTS = ("transparent", "white", "black")
_MAX_BUNDLE_BYTES = 3_000_000_000


class CandidateBundleError(ValueError):
    """The cached render bundle is incomplete, unsafe, or inconsistent."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _file_signature(path: Path) -> dict:
    stat = path.stat()
    return {"size": stat.st_size, "mtime_ns": stat.st_mtime_ns,
            "ctime_ns": getattr(stat, "st_ctime_ns", 0), "sha256": _sha256(path)}


def _read_json_bytes(raw: bytes, code: str) -> dict:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise CandidateBundleError(code) from exc
    if not isinstance(value, dict):
        raise CandidateBundleError(code)
    return value


def _checksums(raw: bytes) -> dict[str, str]:
    result = {}
    try:
        lines = raw.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise CandidateBundleError("CHECKSUM_FILE_ENCODING") from exc
    for line in lines:
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", line.strip())
        if not match or match.group(2) in result:
            raise CandidateBundleError("CHECKSUM_FILE_INVALID")
        result[match.group(2)] = match.group(1)
    if not result:
        raise CandidateBundleError("CHECKSUM_FILE_EMPTY")
    return result


def _safe_candidate_path(value: object) -> str:
    if not isinstance(value, str):
        raise CandidateBundleError("CANDIDATE_PATH_INVALID")
    match = re.fullmatch(r"candidates/([0-9a-f]{2})/([0-9a-f]{64})/(transparent|white|black)\.png", value)
    if not match or match.group(1) != match.group(2)[:2]:
        raise CandidateBundleError("CANDIDATE_PATH_INVALID")
    return value


class RenderedCandidateBundle:
    def __init__(self, run_id: str, rows: dict[str, dict], archives: dict[int, Path],
                 members: dict[str, int], checksums: dict[str, str], signatures: dict[str, dict]):
        self.run_id = run_id
        self.rows = rows
        self.archives = archives
        self.members = members
        self.checksums = checksums
        self.signatures = signatures
        self._open_zips = {}

    @classmethod
    def load(cls, directory: str | Path, *, checkpoint_path: str | Path | None = None,
             progress=None) -> "RenderedCandidateBundle | None":
        """Load one complete dated bundle; return None when none was supplied.

        Archive SHA-256 values are checked against the included SHA256SUMS file.
        A small local checkpoint avoids rehashing immutable archives on resume;
        imported PNG hashes are always checked again when an item is installed.
        """
        root = Path(directory)
        if not root.is_dir() or root.is_symlink():
            return None
        first_parts = [p for p in root.rglob("WARDER-OPENATV-TECHNICAL-CANDIDATES-*-PART-01-OF-04.zip")
                       if p.is_file() and not p.is_symlink()]
        if not first_parts:
            return None
        if len(first_parts) != 1:
            raise CandidateBundleError("MULTIPLE_CANDIDATE_BUNDLES")
        first = first_parts[0]
        root = first.parent
        match = _PART_RE.fullmatch(first.name)
        if not match:
            raise CandidateBundleError("CANDIDATE_BUNDLE_NAME_INVALID")
        date_key = match.group(1)
        part_paths = {index: root / f"WARDER-OPENATV-TECHNICAL-CANDIDATES-{date_key}-PART-{index:02d}-OF-04.zip"
                      for index in range(1, 5)}
        manifest_path = root / f"WARDER-OPENATV-PRODUCTION-MANIFESTS-{date_key}.zip"
        if not manifest_path.is_file() or any(not path.is_file() for path in part_paths.values()):
            raise CandidateBundleError("CANDIDATE_BUNDLE_INCOMPLETE")
        paths = {**{path.name: path for path in part_paths.values()}, manifest_path.name: manifest_path}
        total_bytes = sum(path.stat().st_size for path in paths.values())
        if total_bytes > _MAX_BUNDLE_BYTES:
            raise CandidateBundleError("CANDIDATE_BUNDLE_TOO_LARGE")

        old_state = {}
        if checkpoint_path:
            try:
                old_state = json.loads(Path(checkpoint_path).read_text(encoding="utf-8"))
                if not isinstance(old_state, dict):
                    old_state = {}
            except (OSError, ValueError, TypeError):
                old_state = {}
        old_signatures = old_state.get("archives", {}) if isinstance(old_state, dict) else {}
        signatures = {}
        for index, name in enumerate(sorted(paths), 1):
            path = paths[name]
            stat = path.stat()
            old = old_signatures.get(name, {}) if isinstance(old_signatures, dict) else {}
            unchanged = (old.get("size") == stat.st_size and old.get("mtime_ns") == stat.st_mtime_ns
                         and old.get("ctime_ns") == getattr(stat, "st_ctime_ns", 0)
                         and _HASH.fullmatch(str(old.get("sha256", ""))))
            signatures[name] = dict(old) if unchanged else _file_signature(path)
            if progress:
                progress(index, len(paths), name)

        try:
            with zipfile.ZipFile(manifest_path) as manifest_zip:
                names = manifest_zip.namelist()
                summary_names = [name for name in names if re.fullmatch(
                    r"WARDER-OPENATV-PRODUCTION-SUMMARY-\d{8}\.json", name)]
                candidate_ledgers = [name for name in names if re.fullmatch(
                    r"WARDER-OPENATV-CANDIDATE-LEDGER-\d{8}\.jsonl\.gz", name)]
                source_ledgers = [name for name in names if re.fullmatch(
                    r"WARDER-OPENATV-SOURCE-OBSERVATIONS-\d{8}\.jsonl\.gz", name)]
                if len(summary_names) != 1 or len(candidate_ledgers) != 1 or len(source_ledgers) != 1:
                    raise CandidateBundleError("PRODUCTION_MANIFEST_SET_INVALID")
                summary = _read_json_bytes(manifest_zip.read(summary_names[0]), "PRODUCTION_SUMMARY_INVALID")
                if summary.get("source_id") != "openatv8":
                    raise CandidateBundleError("PRODUCTION_SUMMARY_SOURCE_MISMATCH")
                if summary.get("status") != "COMPLETED":
                    raise CandidateBundleError("PRODUCTION_SUMMARY_NOT_COMPLETED")
                sums = _checksums(manifest_zip.read("SHA256SUMS.txt"))
                for name, expected in sums.items():
                    if name not in manifest_zip.namelist() and name not in paths:
                        raise CandidateBundleError("CHECKSUM_TARGET_MISSING:" + name)
                    if name in paths:
                        if signatures[name]["sha256"] != expected:
                            raise CandidateBundleError("ARCHIVE_SHA256_MISMATCH:" + name)
                    elif _sha256_bytes(manifest_zip.read(name)) != expected:
                        raise CandidateBundleError("MANIFEST_SHA256_MISMATCH:" + name)
                # The manifest ZIP cannot contain its own outer SHA-256. Its
                # signed-by-content inventory covers every part archive and
                # each extracted manifest object; its computed outer digest
                # is retained in the local checkpoint for resume integrity.
                for name in (path.name for path in part_paths.values()):
                    if name not in sums:
                        raise CandidateBundleError("ARCHIVE_SHA256_NOT_DECLARED:" + name)
                candidate_ledger_name = candidate_ledgers[0]
                source_ledger_name = source_ledgers[0]
                if candidate_ledger_name.rsplit("-", 1)[-1].split(".", 1)[0] != date_key or source_ledger_name.rsplit("-", 1)[-1].split(".", 1)[0] != date_key:
                    raise CandidateBundleError("PRODUCTION_MANIFEST_DATE_MISMATCH")
                candidate_ledger = gzip.decompress(manifest_zip.read(candidate_ledger_name))
                source_ledger = gzip.decompress(manifest_zip.read(source_ledger_name))
                if _sha256_bytes(manifest_zip.read(candidate_ledger_name)) != sums.get(candidate_ledger_name):
                    raise CandidateBundleError("CANDIDATE_LEDGER_SHA256_MISMATCH")
                if _sha256_bytes(manifest_zip.read(source_ledger_name)) != sums.get(source_ledger_name):
                    raise CandidateBundleError("SOURCE_LEDGER_SHA256_MISMATCH")
        except (OSError, KeyError, zipfile.BadZipFile, EOFError) as exc:
            raise CandidateBundleError("CANDIDATE_MANIFEST_ARCHIVE_INVALID") from exc

        rows = {}
        try:
            source_observations = [json.loads(line.decode("utf-8")) for line in source_ledger.splitlines() if line]
            expected_source_observations = summary.get("source_png_count_sha_verified", summary.get("source_png_observations", -1))
            if len(source_observations) != int(expected_source_observations):
                raise CandidateBundleError("SOURCE_LEDGER_COUNT_MISMATCH")
            for line in candidate_ledger.splitlines():
                row = json.loads(line.decode("utf-8"))
                if not isinstance(row, dict):
                    raise CandidateBundleError("CANDIDATE_LEDGER_ROW_INVALID")
                source_sha = row.get("source_artwork_sha256")
                if not isinstance(source_sha, str) or not _HASH.fullmatch(source_sha) or source_sha in rows:
                    raise CandidateBundleError("CANDIDATE_LEDGER_KEY_INVALID")
                outputs = row.get("outputs", {})
                if row.get("status") == "TECHNICAL_CANDIDATE_QA_PASS":
                    if not isinstance(outputs, dict) or set(outputs) != set(_OUTPUTS):
                        raise CandidateBundleError("CANDIDATE_TRIPLET_INCOMPLETE")
                    checked = {}
                    for style, item in outputs.items():
                        if not isinstance(item, dict) or not _HASH.fullmatch(str(item.get("sha256", ""))):
                            raise CandidateBundleError("CANDIDATE_OUTPUT_METADATA_INVALID")
                        member = _safe_candidate_path(item.get("path"))
                        if member.split("/")[-1] != style + ".png":
                            raise CandidateBundleError("CANDIDATE_OUTPUT_STYLE_MISMATCH")
                        checked[style] = {"path": member, "sha256": item["sha256"], "bytes": int(item.get("bytes", -1))}
                    row["outputs"] = checked
                rows[source_sha] = row
        except (UnicodeDecodeError, ValueError, TypeError) as exc:
            if isinstance(exc, CandidateBundleError):
                raise
            raise CandidateBundleError("CANDIDATE_LEDGER_INVALID") from exc
        expected_candidates = summary.get("unique_candidate_artwork", summary.get("candidate_artwork_total", -1))
        if len(rows) != int(expected_candidates):
            raise CandidateBundleError("CANDIDATE_LEDGER_COUNT_MISMATCH")
        passing = [row for row in rows.values() if row.get("status") == "TECHNICAL_CANDIDATE_QA_PASS"]
        expected_triplets = int(summary.get("qa_pass_triplets", -1))
        if len(passing) != expected_triplets or int(summary.get("output_png_count", -1)) != expected_triplets * 3:
            raise CandidateBundleError("CANDIDATE_SUMMARY_COUNT_MISMATCH")

        archives, members = {}, {}
        observed_paths = set()
        for index, path in part_paths.items():
            try:
                with zipfile.ZipFile(path) as archive:
                    names = [name for name in archive.namelist() if not name.endswith("/")]
                    if names.count("part-metadata.json") != 1:
                        raise CandidateBundleError("PART_METADATA_MISSING")
                    metadata = _read_json_bytes(archive.read("part-metadata.json"), "PART_METADATA_INVALID")
                    if (metadata.get("run_id") != summary.get("run_id") or metadata.get("part") != index
                            or metadata.get("parts") != 4 or metadata.get("status") != "TECHNICAL_CANDIDATE_NOT_APPROVED"):
                        raise CandidateBundleError("PART_METADATA_MISMATCH")
                    candidate_names = [name for name in names if name != "part-metadata.json"]
                    if len(candidate_names) != metadata.get("png_count"):
                        raise CandidateBundleError("PART_PNG_COUNT_MISMATCH")
                    metadata["_candidate_names"] = candidate_names
                    archives[index] = path
            except (OSError, zipfile.BadZipFile, KeyError) as exc:
                raise CandidateBundleError("CANDIDATE_PART_INVALID:" + str(index)) from exc
        declared_paths = {item["path"] for row in passing for item in row["outputs"].values()}
        for index, path in archives.items():
            with zipfile.ZipFile(path) as archive:
                meta = _read_json_bytes(archive.read("part-metadata.json"), "PART_METADATA_INVALID")
                candidate_names = [name for name in archive.namelist() if not name.endswith("/") and name != "part-metadata.json"]
                for name in candidate_names:
                    if name not in declared_paths or name in observed_paths:
                        raise CandidateBundleError("UNDECLARED_OR_DUPLICATE_CANDIDATE_OUTPUT")
                    observed_paths.add(name)
                    members[name] = index
                if len(candidate_names) != int(meta.get("triplet_count", -1)) * 3:
                    raise CandidateBundleError("PART_TRIPLET_COUNT_MISMATCH")
        if observed_paths != declared_paths:
            raise CandidateBundleError("CANDIDATE_OUTPUT_SET_MISMATCH")

        result = cls(str(summary.get("run_id")), rows, archives, members, sums, signatures)
        if checkpoint_path:
            from source_registry import atomic_json
            atomic_json(Path(checkpoint_path), {"schema": 1, "status": "VERIFIED",
                "run_id": result.run_id, "archives": signatures,
                "candidate_rows": len(rows), "qa_pass_triplets": len(passing),
                "output_png_count": len(observed_paths)})
        return result

    def close(self):
        for archive in self._open_zips.values():
            try:
                archive.close()
            except Exception:
                pass
        self._open_zips.clear()

    def install_triplet(self, source_sha: str, output_root: str | Path, *,
                        render_revision: str, template_sha256: dict[str, str]) -> str:
        """Install one manifest-bound triplet without replacing existing PNGs."""
        row = self.rows.get(source_sha)
        if not row or row.get("status") != "TECHNICAL_CANDIDATE_QA_PASS":
            return "NOT_FOUND"
        if not _HASH.fullmatch(str(source_sha)) or not render_revision:
            return "INVALID_SOURCE_KEY"
        output_root = Path(output_root)
        folder = output_root / source_sha[:2] / source_sha
        folder.mkdir(parents=True, exist_ok=True)
        targets = {style: folder / (style + ".png") for style in _OUTPUTS}
        staged_dir = Path(tempfile.mkdtemp(prefix=".openatv-candidate-", dir=str(output_root)))
        staged = {}
        try:
            for style in _OUTPUTS:
                item = row["outputs"][style]
                destination = targets[style]
                if destination.is_file():
                    if destination.stat().st_size != item["bytes"] or _sha256(destination) != item["sha256"]:
                        return "CONFLICT"
                    continue
                archive_index = self.members.get(item["path"])
                if archive_index not in self.archives:
                    return "BUNDLE_MEMBER_MISSING"
                archive = self._open_zips.get(archive_index)
                if archive is None:
                    archive = zipfile.ZipFile(self.archives[archive_index])
                    self._open_zips[archive_index] = archive
                staged_path = staged_dir / (style + ".png")
                digest = hashlib.sha256()
                written = 0
                with archive.open(item["path"], "r") as source, staged_path.open("xb") as target:
                    for block in iter(lambda: source.read(1024 * 1024), b""):
                        written += len(block)
                        if written > item["bytes"]:
                            raise CandidateBundleError("CANDIDATE_OUTPUT_SIZE_MISMATCH")
                        digest.update(block)
                        target.write(block)
                    target.flush()
                    os.fsync(target.fileno())
                if written != item["bytes"] or digest.hexdigest() != item["sha256"]:
                    raise CandidateBundleError("CANDIDATE_OUTPUT_SHA256_MISMATCH")
                _verify_png(staged_path, style)
                staged[style] = staged_path

            installed = False
            for style in _OUTPUTS:
                if style not in staged:
                    continue
                # Hard-link installation is atomic and exclusive on the same
                # Windows volume. It cannot replace an existing candidate.
                try:
                    os.link(staged[style], targets[style])
                    installed = True
                except FileExistsError:
                    item = row["outputs"][style]
                    if targets[style].stat().st_size != item["bytes"] or _sha256(targets[style]) != item["sha256"]:
                        return "CONFLICT"
            for style in ("black", "white"):
                expected = template_sha256.get(style)
                if not isinstance(expected, str) or not _HASH.fullmatch(expected):
                    raise CandidateBundleError("TEMPLATE_SHA256_REQUIRED")
                (folder / (style + ".template-sha256")).write_text(expected, encoding="ascii")
            for style in _OUTPUTS:
                (folder / (style + ".render-revision")).write_text(render_revision, encoding="ascii")
            return "IMPORTED" if installed else "ALREADY_PRESENT"
        finally:
            shutil.rmtree(staged_dir, ignore_errors=True)


def _verify_png(path: Path, style: str) -> None:
    try:
        from PIL import Image
        with Image.open(path) as image:
            if image.format != "PNG" or image.size != (220, 132) or image.mode != "RGBA":
                raise CandidateBundleError("CANDIDATE_OUTPUT_FORMAT_INVALID")
            image.verify()
        with Image.open(path) as image:
            alpha = image.getchannel("A")
            if style == "transparent" and alpha.getbbox() is None:
                raise CandidateBundleError("CANDIDATE_OUTPUT_EMPTY")
            if style != "transparent" and alpha.getextrema() != (255, 255):
                raise CandidateBundleError("CANDIDATE_OUTPUT_NOT_OPAQUE")
    except CandidateBundleError:
        raise
    except Exception as exc:
        raise CandidateBundleError("CANDIDATE_OUTPUT_DECODE_FAILED") from exc


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()
