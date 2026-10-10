"""Safe extraction of PNG candidates from OE/OpenATV .ipk (ar + tar) files."""
from __future__ import annotations

import hashlib
import io
import os
import shutil
import stat
import tempfile
import tarfile
from pathlib import Path, PurePosixPath

MAX_IPK = 450_000_000
MAX_MEMBER = 30_000_000
MAX_TOTAL = 2_000_000_000
MAX_ENTRIES = 200_000
IMPORT_SCHEMA = 3  # SRP symlinks materialized as regular PNG copies


def _ar_members(stream):
    if stream.read(8) != b"!<arch>\n":
        raise ValueError("Invalid IPK ar header")
    string_table = b""
    entries = 0
    while True:
        header = stream.read(60)
        if not header:
            break
        if len(header) != 60 or header[58:60] != b"`\n":
            raise ValueError("Invalid IPK ar member header")
        entries += 1
        if entries > 64:
            raise ValueError("Too many IPK ar members")
        try:
            name = header[:16].decode("ascii").strip()
            size = int(header[48:58].decode("ascii").strip())
        except (UnicodeError, ValueError) as exc:
            raise ValueError("Invalid IPK ar metadata") from exc
        if size < 0 or size > MAX_IPK:
            raise ValueError("IPK member size outside limits")
        if name == "//":
            string_table = stream.read(size)
            if len(string_table) != size:
                raise ValueError("Truncated IPK string table")
            if size & 1:
                stream.read(1)
            continue
        if name.startswith("#1/"):
            length = int(name[3:])
            if length < 1 or length > 256 or length > size:
                raise ValueError("Invalid BSD ar filename")
            filename = stream.read(length).decode("utf-8", "strict")
            payload = stream.read(size - length)
        else:
            filename = name.rstrip("/")
            if filename.startswith("/") and filename[1:].isdigit() and string_table:
                offset = int(filename[1:])
                filename = string_table[offset:].split(b"/", 1)[0].decode("utf-8", "strict")
            payload = stream.read(size)
        if len(payload) != (size - (length if name.startswith("#1/") else 0)):
            raise ValueError("Truncated IPK ar member")
        if filename in ("data.tar", "data.tar.gz", "data.tar.xz", "data.tar.bz2", "data.tar.zst"):
            yield filename, payload
        if size & 1:
            stream.read(1)


def import_png_ipk(archive, originals_root):
    archive = Path(archive)
    size = archive.stat().st_size
    if size <= 0 or size > MAX_IPK:
        raise ValueError("IPK size outside safety limits")
    digest = hashlib.sha256()
    with archive.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    target_root = Path(originals_root)
    target = target_root / digest.hexdigest()
    if target.is_dir():
        return {"imported": 0, "skipped": sum(1 for p in target.rglob("*.png") if p.is_file())}
    target_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".warder-ipk-", dir=target_root))
    imported = skipped = total = seen_count = 0
    seen = set()
    links = []
    regular = set()
    try:
        with archive.open("rb") as stream:
            members = list(_ar_members(stream))
        if len(members) != 1:
            raise ValueError("IPK must contain exactly one data archive")
        with tarfile.open(fileobj=io.BytesIO(members[0][1]), mode="r:*") as tar:
            for member in tar:
                seen_count += 1
                if seen_count > MAX_ENTRIES:
                    raise ValueError("Too many IPK data entries")
                if not member.name.lower().endswith(".png"):
                    continue
                if member.issym() or member.islnk():
                    links.append(member)
                    continue
                if not member.isfile():
                    continue
                rel = PurePosixPath(member.name.replace("\\", "/"))
                if (rel.is_absolute() or not rel.parts or
                    any(part in ("", ".", "..") or ":" in part for part in rel.parts) or
                    member.size < 1 or member.size > MAX_MEMBER or
                    stat.S_IFMT(member.mode) not in (0, stat.S_IFREG)):
                    skipped += 1
                    continue
                key = "/".join(rel.parts).casefold()
                if key in seen:
                    skipped += 1
                    continue
                seen.add(key)
                total += member.size
                if total > MAX_TOTAL:
                    raise ValueError("IPK expands beyond safety limit")
                source = tar.extractfile(member)
                if source is None:
                    skipped += 1
                    continue
                dest = staging.joinpath(*rel.parts)
                dest.parent.mkdir(parents=True, exist_ok=True)
                written = 0
                with source, dest.open("xb") as output:
                    while True:
                        block = source.read(1024 * 1024)
                        if not block:
                            break
                        written += len(block)
                        if written > MAX_MEMBER:
                            raise ValueError("PNG expanded beyond entry limit")
                        output.write(block)
                if written != member.size:
                    raise ValueError("IPK PNG size mismatch")
                imported += 1
                regular.add(tuple(rel.parts))
            # TAR link targets are resolved only against regular PNG files extracted
            # within the same staging directory. Never create filesystem symlinks.
            import posixpath
            for member in links:
                raw = member.name.replace("\\", "/")
                rel = PurePosixPath(raw)
                if rel.is_absolute() or any(x in ("..", "") or ":" in x for x in rel.parts):
                    skipped += 1
                    continue
                if member.issym():
                    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(raw), member.linkname.replace("\\", "/")))
                else:
                    resolved = posixpath.normpath(member.linkname.replace("\\", "/"))
                source_rel = PurePosixPath(resolved)
                if (source_rel.is_absolute() or ".." in source_rel.parts or
                    ":" in resolved or tuple(source_rel.parts) not in regular or
                    not resolved.lower().endswith(".png")):
                    skipped += 1
                    continue
                dest = staging.joinpath(*rel.parts)
                source = staging.joinpath(*source_rel.parts)
                if dest.exists() or dest == source:
                    skipped += 1
                    continue
                total += source.stat().st_size
                if total > MAX_TOTAL:
                    raise ValueError("IPK expands beyond safety limit")
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, dest)
                imported += 1
        (staging / '.warder-import-schema').write_text(str(IMPORT_SCHEMA), encoding='ascii')
        os.replace(staging, target)
        return {"imported": imported, "skipped": skipped, "package_sha256": digest.hexdigest()}
    finally:
        if staging.exists():
            shutil.rmtree(staging)
