"""Fail-closed cleanup of interrupted Factory atomic writes.

Only stale, regular, explicitly named temporary artifacts within the work tree
are eligible. No recursion into source/original/final directories, no symlinks.
"""
from pathlib import Path
import os
import re
import time

_TEMP = re.compile(r'^(?:black|white|transparent)\.png\.partial$|^(?:black|white)\.template-sha256\.partial$', re.ASCII)


def cleanup_interrupted_renders(work_picons, *, min_age_seconds=86400, now=None, dry_run=False):
    root = Path(work_picons)
    if root.name.upper() != 'PICONS' or root.parent.name != '04-WORK':
        raise ValueError('Only canonical 04-WORK/PICONS can be cleaned')
    if min_age_seconds < 3600:
        raise ValueError('Minimum age must be at least one hour')
    report = {'deleted': [], 'errors': [], 'skipped': 0}
    if not root.is_dir() or root.is_symlink():
        return report
    cutoff = (time.time() if now is None else now) - min_age_seconds
    # Only files in the known SHA256 layout: PICONS/<2 hex>/<64 hex>/file.
    for prefix in root.iterdir():
        if prefix.is_symlink() or not prefix.is_dir() or not re.fullmatch('[0-9a-f]{2}', prefix.name):
            continue
        for folder in prefix.iterdir():
            if folder.is_symlink() or not folder.is_dir() or not re.fullmatch('[0-9a-f]{64}', folder.name) or not folder.name.startswith(prefix.name):
                continue
            for candidate in folder.iterdir():
                if candidate.is_symlink() or not candidate.is_file() or not _TEMP.fullmatch(candidate.name):
                    report['skipped'] += 1
                    continue
                try:
                    stat = candidate.stat(follow_symlinks=False)
                    if stat.st_mtime > cutoff:
                        report['skipped'] += 1
                        continue
                    if not dry_run:
                        candidate.unlink()
                    report['deleted'].append(str(candidate))
                except OSError as exc:
                    report['errors'].append(f'{candidate}: {exc}')
    return report
