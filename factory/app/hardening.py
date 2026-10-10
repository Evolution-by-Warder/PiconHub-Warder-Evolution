"""Atomic, bounded ZIP ingestion; original source trees are never overwritten."""
from pathlib import Path, PurePosixPath
import hashlib
import os
import shutil
import stat
import tempfile
import zipfile

MAX_ENTRY = 30_000_000
MAX_ARCHIVE_UNCOMPRESSED = 2_000_000_000
MAX_ENTRIES = 100_000


def import_png_zip(archive, originals_root):
    archive = Path(archive)
    originals_root = Path(originals_root)
    # Content identity, not local machine path identity.
    digest = hashlib.sha256()
    with archive.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    target = originals_root / digest.hexdigest()
    if target.is_dir():
        return {'imported': 0, 'skipped': sum(1 for p in target.rglob('*.png') if p.is_file())}
    if target.exists():
        raise ValueError('Import destination is not a directory')
    originals_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.warder-import-', dir=originals_root))
    imported = skipped = 0
    try:
        with zipfile.ZipFile(archive) as z:
            infos = z.infolist()
            if len(infos) > MAX_ENTRIES:
                raise ValueError('Too many archive entries')
            if sum(i.file_size for i in infos) > MAX_ARCHIVE_UNCOMPRESSED:
                raise ValueError('Archive expands beyond safety limit')
            seen = set()
            for info in infos:
                if info.is_dir() or not info.filename.lower().endswith('.png'):
                    continue
                name = info.filename.replace('\\', '/')
                rel = PurePosixPath(name)
                mode = info.external_attr >> 16
                if (rel.is_absolute() or not rel.parts or
                    any(part in ('', '.', '..') or ':' in part for part in rel.parts) or
                    info.file_size > MAX_ENTRY or
                    stat.S_IFMT(mode) not in (0, stat.S_IFREG)):
                    skipped += 1
                    continue
                # Reject case-insensitive collisions on Windows.
                collision_key = '/'.join(rel.parts).casefold()
                if collision_key in seen:
                    skipped += 1
                    continue
                seen.add(collision_key)
                dest = staging.joinpath(*rel.parts)
                dest.parent.mkdir(parents=True, exist_ok=True)
                with z.open(info) as inp, dest.open('xb') as out:
                    count = 0
                    while True:
                        block = inp.read(1024 * 1024)
                        if not block:
                            break
                        count += len(block)
                        if count > MAX_ENTRY:
                            raise ValueError('Decompressed entry too large')
                        out.write(block)
                if count != info.file_size:
                    raise ValueError('Archive entry size mismatch')
                imported += 1
        if target.exists():
            raise ValueError('Concurrent import destination exists')
        os.replace(staging, target)
        return {'imported': imported, 'skipped': skipped}
    finally:
        if staging.exists():
            shutil.rmtree(staging)
