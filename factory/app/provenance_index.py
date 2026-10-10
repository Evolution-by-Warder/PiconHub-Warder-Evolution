"""Read-only, reproducible provenance and identity candidate index.

No source wins by order, and ambiguous identities remain explicitly ambiguous.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import tempfile
from collections import defaultdict
from pathlib import Path

PEERS = frozenset({'vhannibal', 'openatv8', 'chocholousek'})
SERVICE_REF = re.compile(r'^[0-9a-fA-F]+(?:_[0-9a-fA-F]+){5,}$')


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def scan_originals(originals, *, max_files=300_000):
    """Index only real PNG files under recognized peer roots, without mutations."""
    root = Path(originals)
    entries = []
    for peer in sorted(PEERS):
        folder = root / peer
        if not folder.is_dir():
            continue
        for base, dirs, files in os.walk(folder, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not (Path(base) / d).is_symlink())
            for filename in sorted(files):
                path = Path(base) / filename
                if path.suffix.lower() != '.png' or path.is_symlink():
                    continue
                if len(entries) >= max_files:
                    raise ValueError('Original inventory limit exceeded')
                rel = path.relative_to(folder).as_posix()
                stem = path.stem
                candidate = stem.lower() if SERVICE_REF.fullmatch(stem) else None
                entries.append({'source': peer, 'path': rel, 'sha256': sha256_file(path),
                                'candidate_identity': candidate})
    return entries


def analyze_inventory(entries):
    by_hash = defaultdict(list)
    by_identity = defaultdict(lambda: defaultdict(list))
    for item in entries:
        by_hash[item['sha256']].append({'source': item['source'], 'path': item['path']})
        if item['candidate_identity']:
            by_identity[item['candidate_identity']][item['sha256']].append(
                {'source': item['source'], 'path': item['path']})
    return {
        'schema': 1,
        'files': len(entries),
        'unique_content': len(by_hash),
        'duplicate_groups': [
            {'sha256': digest, 'files': sorted(group, key=lambda x: (x['source'], x['path']))}
            for digest, group in sorted(by_hash.items()) if len(group) > 1
        ],
        'candidate_conflicts': [
            {'identity': identity, 'alternatives': [
                {'sha256': digest, 'files': sorted(group, key=lambda x: (x['source'], x['path']))}
                for digest, group in sorted(variants.items())]}
            for identity, variants in sorted(by_identity.items()) if len(variants) > 1
        ],
        'note': 'Filename identities are candidates, not approved Warder Master Registry identities.'
    }


def save_report(path, report):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.provenance-', suffix='.tmp', dir=target.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(report, out, ensure_ascii=False, indent=2, sort_keys=True)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def build_report(originals, output):
    report = analyze_inventory(scan_originals(originals))
    save_report(output, report)
    return report
