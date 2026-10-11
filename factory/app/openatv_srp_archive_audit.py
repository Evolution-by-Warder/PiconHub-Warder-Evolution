"""Read-only audit of locally cached SRP and UTF8SNP IPK payloads."""
from __future__ import annotations
import io
import json
import os
import re
import tarfile
from collections import Counter
from pathlib import Path
from ipk_import import _ar_members
from workspace_paths import resolve_root, workspace_paths, read_only_preflight

SRP = re.compile(r'^[0-9a-fA-F]+(?:_[0-9a-fA-F]+){9}\.png$')

def audit_archive(path):
    path = Path(path)
    counts = Counter()
    examples = {'regular_srp': [], 'regular_named': [], 'symlink_srp': [], 'hardlink_srp': [], 'other_links': []}
    with path.open('rb') as f:
        members = list(_ar_members(f))
    if len(members) != 1:
        raise ValueError('Expected exactly one IPK data archive')
    with tarfile.open(fileobj=io.BytesIO(members[0][1]), mode='r:*') as tar:
        for m in tar:
            if not m.name.lower().endswith('.png'):
                continue
            srp = bool(SRP.fullmatch(Path(m.name).name))
            kind = 'regular' if m.isfile() else 'symlink' if m.issym() else 'hardlink' if m.islnk() else 'other'
            counts[f'{kind}_{"srp" if srp else "named"}'] += 1
            key = f'{kind}_srp' if srp and kind in ('regular','symlink','hardlink') else 'regular_named' if kind == 'regular' else 'other_links'
            if len(examples[key]) < 5:
                examples[key].append({'name': m.name, 'target': m.linkname if m.issym() or m.islnk() else None})
    return {'archive': str(path), 'counts': dict(counts), 'examples': examples}

def audit_workspace(workspace, state_dir=None):
    workspace = Path(workspace)
    state = Path(state_dir) / 'openatv8-state.json' if state_dir is not None else workspace / 'openatv8-state.json'
    if not state.is_file():
        raise FileNotFoundError(state)
    data = json.loads(state.read_text(encoding='utf-8'))
    reports = []
    for p in data.get('packages', []):
        archive = workspace/'archives'/'openatv8'/(p['sha256']+'.ipk')
        result = {'package': p['filename'], 'sha256': p['sha256'], 'present': archive.is_file()}
        if archive.is_file():
            try:
                result.update(audit_archive(archive))
            except Exception as exc:
                result['error'] = f'{type(exc).__name__}: {exc}'
        reports.append(result)
    return {'packages': reports}

if __name__ == '__main__':
    import sys
    paths = workspace_paths(resolve_root())
    preflight = read_only_preflight(paths['root'])
    if not preflight.ok:
        raise SystemExit('Read-only workspace preflight failed; audit report not written: ' + '; '.join(preflight.findings[-2:]))
    workspace = Path(sys.argv[1]) if len(sys.argv) > 1 else paths['ingest']
    report = audit_workspace(workspace, state_dir=paths['state'])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else paths['reports'] / 'openatv-srp-archive-audit.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print('SRP archive audit:', out)
    for p in report['packages']:
        print(Path(p['package']).name, p.get('counts', p.get('error', 'ARCHIVE MISSING')))
