"""Transactional, peer-neutral archive ingestion; no production writes.

The caller supplies an independently verified manifest of CURRENT archives.
Never guess provider endpoints or prefer one provider's art over another.
"""
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from hardening import import_png_zip
from source_inventory import plan_downloads, stream_verified_archive, commit_source_state, SourceError

KEY_PATTERN = re.compile(r'^[a-z][a-z0-9_-]{1,32}$')


def _read_state(path):
    try:
        with Path(path).open(encoding='utf-8') as f:
            value = json.load(f)
        if not isinstance(value, dict):
            raise SourceError('Invalid checkpoint')
        return value
    except FileNotFoundError:
        return {}


def _hash(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''):
            digest.update(part)
    return digest.hexdigest()


def ingest_current_sources(manifest, workspace, allowed_hosts, downloader=None, importer=None, notify=None):
    """Download changed archives, import safely, checkpoint each successful source.

    Archives are content addressed, so an older version cannot be silently overwritten.
    Failed downloads/imports leave source checkpoint untouched for retry.
    """
    workspace = Path(workspace)
    state_path = workspace / 'source-state.json'
    state = _read_state(state_path)
    plan = plan_downloads(manifest, state)
    downloader = downloader or stream_verified_archive
    importer = importer or import_png_zip
    notify = notify or (lambda *_: None)
    results = []
    for source in plan:
        key = source['key']
        if not KEY_PATTERN.fullmatch(key):
            raise SourceError('Invalid provider key')
        digest = source['sha256']
        archive = workspace / 'archives' / key / (digest + '.zip')
        if archive.exists() and _hash(archive) != digest:
            raise SourceError('Cached archive checksum mismatch: ' + key)
        if not archive.exists():
            notify(key, 'downloading')
            downloader(source['url'], digest, archive, allowed_hosts)
        if not archive.exists() or _hash(archive) != digest:
            raise SourceError('Archive not verified: ' + key)
        notify(key, 'importing')
        # Isolate sources even if ZIP basenames are identical.
        outcome = importer(archive, workspace / 'originals' / key)
        state = commit_source_state(state_path, state, source, digest)
        results.append({'source': key, 'version': source['version'], 'sha256': digest,
                        'imported': outcome['imported'], 'skipped': outcome['skipped']})
        notify(key, 'done')
    return {'processed': results, 'unchanged': sorted(set(s['key'] for s in manifest['sources']) - set(r['source'] for r in results))}
