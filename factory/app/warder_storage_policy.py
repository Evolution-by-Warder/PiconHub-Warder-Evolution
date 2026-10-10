"""Canonical two-location policy for WARDER PICON FACTORY.

This module never deletes source PNGs and never writes to GitHub.
"""
from pathlib import Path
import hashlib
import os
import shutil
import tempfile


class StoragePolicy:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.work = self.root / '04-WORK' / 'PICONS'
        self.final = self.root / '06-OUTPUT' / 'PICONS'

    def ensure(self):
        self.work.mkdir(parents=True, exist_ok=True)
        self.final.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _validate(name):
        if not isinstance(name, str) or not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in name):
            raise ValueError('Invalid picon identity')
        return name

    def path(self, identity, variant, *, approved=False):
        identity = self._validate(identity)
        if variant not in ('transparent', 'black', 'white'):
            raise ValueError('Invalid variant')
        return (self.final if approved else self.work) / variant / (identity + '.png')

    def publish_local(self, identity, variant, source, *, qa_approved=False):
        """Copy validated QA-approved PNG atomically to final store.

        Never removes original/work evidence; caller can later clean verified derivatives.
        """
        if not qa_approved:
            raise PermissionError('Explicit QA approval required')
        source = Path(source).resolve(strict=True)
        if not source.is_file() or source.suffix.lower() != '.png':
            raise ValueError('PNG source required')
        # Basic PNG signature validation, not a full image integrity audit.
        with source.open('rb') as f:
            if f.read(8) != b'\x89PNG\r\n\x1a\n':
                raise ValueError('Invalid PNG signature')
        dest = self.path(identity, variant, approved=True)
        dest.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix='.incoming-', suffix='.png', dir=dest.parent)
        try:
            with os.fdopen(fd, 'wb') as out, source.open('rb') as inp:
                shutil.copyfileobj(inp, out)
                out.flush(); os.fsync(out.fileno())
            if self._sha(tmp) != self._sha(source):
                raise IOError('SHA-256 mismatch')
            # Exclusive creation: a concurrent publisher must never be overwritten.
            try:
                os.link(tmp, dest)
            except FileExistsError:
                if self._sha(dest) != self._sha(source):
                    raise
            # The temporary file is removed in finally.
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
        return dest

    @staticmethod
    def _sha(path):
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                h.update(chunk)
        return h.hexdigest()
