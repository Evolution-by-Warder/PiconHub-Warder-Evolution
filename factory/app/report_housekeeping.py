"""Conservative startup retention for Factory-generated per-run JSON reports."""
from pathlib import Path
import re

# Only artifacts written by engine.py. Never touch unknown/user files.
PREFIXES = (
    'warder-master-index', 'identity-collisions', 'registry-matches',
    'qa', 'empty-source', 'publication-exclusions', 'review-queue',
    'integrity', 'report', 'qa-backlog-causes', 'artwork-review-batch-10',
    'openatv-triage', 'openatv-identity-triage', 'warder-live-png-test',
)
# Run IDs: YYYYMMDD-HHMMSS-<numeric nonce>
_RUN = re.compile(r'^(' + '|'.join(re.escape(p) for p in PREFIXES) +
                  r')-(\d{8}-\d{6}-\d+)\.json$', re.ASCII)


def cleanup_reports(folder, keep_runs=3):
    """Delete old regular report files only; retain newest complete run groups.

    Symlinks, directories, unrelated files, and all non-JSON files are ignored.
    Errors are returned for logging, never interrupt startup.
    """
    folder = Path(folder)
    if keep_runs < 1:
        raise ValueError('keep_runs must be positive')
    groups = {}
    errors = []
    if not folder.is_dir():
        return {'deleted': 0, 'retained_runs': 0, 'errors': errors}
    try:
        children = list(folder.iterdir())
    except OSError as exc:
        return {'deleted': 0, 'retained_runs': 0, 'errors': [str(exc)]}
    for path in children:
        if path.is_symlink() or not path.is_file():
            continue
        match = _RUN.fullmatch(path.name)
        if match:
            groups.setdefault(match.group(2), []).append(path)
    # Preserve every review queue: the latest queue may be required for manual
    # decisions and exports even if a newer run is incomplete.
    # Keep summary reports for diagnostics retry; clean only disposable audits.
    # Retain complete recent run groups; never remove current or unknown files.
    retained = set(sorted(groups, reverse=True)[:keep_runs])
    deleted = 0
    for run, paths in groups.items():
        if run in retained:
            continue
        for path in paths:
            # Never discard run summaries: they are the local retry source
            # when optional private GitHub diagnostics delivery fails.
            if path.name.startswith(('report-', 'review-queue-')):
                continue
            try:
                path.unlink()
                deleted += 1
            except OSError as exc:
                errors.append(f'{path.name}: {exc}')
    return {'deleted': deleted, 'retained_runs': len(retained), 'errors': errors}
