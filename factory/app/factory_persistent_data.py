"""Crash-safe migration of mutable Factory state outside replaceable application code."""
from pathlib import Path
import os
import shutil
import sqlite3
import tempfile
from contextlib import closing

MUTABLE = ('sources.json', 'source-manifest.json', 'source-ingest',
           'master-current-paths.json', 'master-registry-cache.json',
           'output-cache.json', 'openatv-pixel-evidence-cache.json',
           'review-decisions.json')


def _atomic_copy(src, dst):
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return
    if src.is_dir():
        tmp = Path(tempfile.mkdtemp(prefix='.factory-migration-', dir=dst.parent))
        try:
            shutil.copytree(src, tmp / 'payload')
            if not dst.exists():
                os.replace(tmp / 'payload', dst)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        return
    fd, name = tempfile.mkstemp(prefix='.factory-migration-', dir=dst.parent)
    try:
        with os.fdopen(fd, 'wb') as target, src.open('rb') as original:
            shutil.copyfileobj(original, target)
            target.flush()
            os.fsync(target.fileno())
        if not dst.exists():
            os.replace(name, dst)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _migrate_sqlite(old, new):
    if new.exists() or not old.exists():
        return
    fd, name = tempfile.mkstemp(prefix='.factory-db-', suffix='.sqlite3', dir=new.parent)
    os.close(fd)
    try:
        with closing(sqlite3.connect('file:' + old.resolve().as_posix() + '?mode=ro', uri=True)) as source:
            with closing(sqlite3.connect(name)) as target:
                source.backup(target)
                result = target.execute('PRAGMA quick_check').fetchone()
                if result != ('ok',):
                    raise RuntimeError('Migrated database integrity check failed')
        if not new.exists():
            os.replace(name, new)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def migrate(app, data):
    app, data = Path(app), Path(data)
    data.mkdir(parents=True, exist_ok=True)
    _migrate_sqlite(app / 'factory.sqlite3', data / 'factory.sqlite3')
    for name in MUTABLE:
        old, new = app / name, data / name
        if old.exists():
            _atomic_copy(old, new)
    return data
