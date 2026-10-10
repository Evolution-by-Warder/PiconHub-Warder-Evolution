"""Read-only integrity audit for generated variants and their immutable source."""
from __future__ import annotations
import hashlib
from pathlib import Path

VARIANTS = ('transparent', 'black', 'white')


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def audit_artifacts(sources, output_root, source_hashes_verified=False):
    """Audit unique sha256->source mappings; never modify files.

    Does not claim that a visually legible logo or a service ID is approved.
    """
    root = Path(output_root)
    issues = []
    checked = 0
    for sha, source in sorted(sources.items()):
        checked += 1
        if len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
            issues.append({'sha256': sha, 'reason': 'INVALID_CONTENT_ID'})
            continue
        try:
            source_path = Path(source)
            if not source_path.is_file():
                issues.append({'sha256': sha, 'reason': 'SOURCE_UNREADABLE', 'error': 'source file missing'})
                continue
            if not source_hashes_verified and file_sha256(source_path) != sha:
                issues.append({'sha256': sha, 'reason': 'SOURCE_CHANGED', 'source': str(source)})
                continue
        except (OSError, ValueError) as exc:
            issues.append({'sha256': sha, 'reason': 'SOURCE_UNREADABLE', 'error': str(exc)[:160]})
            continue
        folder = root / sha[:2] / sha
        for variant in VARIANTS:
            path = folder / (variant + '.png')
            try:
                if not path.is_file() or path.stat().st_size == 0:
                    issues.append({'sha256': sha, 'reason': 'VARIANT_MISSING_OR_EMPTY', 'variant': variant})
            except OSError:
                issues.append({'sha256': sha, 'reason': 'VARIANT_UNREADABLE', 'variant': variant})
    return {'schema': 1, 'checked': checked, 'issue_count': len(issues), 'issues': issues,
            'publication_authorized': False, 'note': 'Read-only file integrity, not visual or registry approval.'}
