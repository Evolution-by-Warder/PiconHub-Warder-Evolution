"""Offline-safe preparation of a Factory update; never installs or deletes a live app.

Expected hash MUST come from independently trusted release metadata, not from
inside the downloaded ZIP. A staged package is not authorization to install.
"""
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile

MAX_PACKAGE = 512 * 1024 * 1024
MAX_FILES = 2000
MAX_UNPACKED = 1024 * 1024 * 1024

class UpdateRejected(ValueError):
    pass


def stage_verified_zip(package, expected_sha256, staging_root):
    package = Path(package)
    root = Path(staging_root)
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64 or any(c not in '0123456789abcdefABCDEF' for c in expected_sha256):
        raise UpdateRejected('Missing trusted SHA-256')
    if not package.is_file() or not 0 < package.stat().st_size <= MAX_PACKAGE:
        raise UpdateRejected('Invalid package size')
    digest = hashlib.sha256()
    with package.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    if digest.hexdigest() != expected_sha256.lower():
        raise UpdateRejected('SHA-256 mismatch')
    root.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix='.factory-stage-', dir=root))
    try:
        with zipfile.ZipFile(package) as archive:
            members = archive.infolist()
            if not members or len(members) > MAX_FILES or sum(m.file_size for m in members) > MAX_UNPACKED:
                raise UpdateRejected('Unsafe archive limits')
            seen = {}
            for entry in members:
                name = entry.filename
                path = PurePosixPath(name)
                if (not name or '\\' in name or name.startswith('/') or ':' in name or
                    any(part in ('', '.', '..') for part in path.parts) or
                    (entry.external_attr >> 16) & 0o170000 == 0o120000):
                    raise UpdateRejected('Unsafe archive path or symlink')
                key = name.rstrip('/').casefold()
                # A file may not also be the parent of another archive entry.
                parents = { '/'.join(key.split('/')[:i]) for i in range(1, len(key.split('/'))) }
                if any(parent in seen and seen[parent] == 'file' for parent in parents):
                    raise UpdateRejected('Archive file/directory collision')
                if not entry.is_dir() and any(old.startswith(key + '/') for old in seen):
                    raise UpdateRejected('Archive file/directory collision')
                if key in seen:
                    raise UpdateRejected('Duplicate archive path')
                seen[key] = 'dir' if entry.is_dir() else 'file'
                if not entry.is_dir():
                    target = temp.joinpath(*path.parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(entry) as src, target.open('wb') as dst:
                        shutil.copyfileobj(src, dst, 1024 * 1024)
        (temp / '.verified-sha256').write_text(digest.hexdigest() + '\n', encoding='ascii')
        return temp
    except Exception:
        shutil.rmtree(temp, ignore_errors=True)
        raise
