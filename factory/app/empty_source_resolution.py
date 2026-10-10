"""Fail-closed provenance and replacement candidates for transparent PNG sources.

Only a byte-verified source can be substituted automatically. Same filenames
are evidence for manual investigation, never sufficient to overwrite artwork.
"""
from pathlib import Path
from collections import defaultdict
import hashlib


def empty_source_report(qa_issues, candidate_records, sources_by_sha):
    by_sha = defaultdict(list)
    by_name = defaultdict(list)
    for record in candidate_records:
        sha = record.get('sha256')
        path = record.get('source')
        if not isinstance(sha, str) or not isinstance(path, str):
            continue
        by_sha[sha].append(path)
        by_name[Path(path).name.casefold()].append((sha, path))
    items = []
    for sha, reasons in sorted(qa_issues.items()):
        if 'FULLY_TRANSPARENT' not in reasons:
            continue
        paths = sorted(set(by_sha.get(sha, [])))
        if not paths and sha in sources_by_sha:
            paths = [sources_by_sha[sha]]
        siblings = []
        for name in sorted({Path(p).name.casefold() for p in paths}):
            for other_sha, other_path in by_name[name]:
                if other_sha != sha:
                    siblings.append({'sha256': other_sha, 'source': other_path})
        items.append({'sha256': sha, 'sources': paths,
                      'same_filename_other_content': sorted(siblings, key=lambda x: (x['sha256'], x['source'])),
                      'automatic_replacement': False,
                      'reason': 'Source contains no visible artwork; filename similarity cannot verify replacement'})
    return {'schema': 1, 'blocking_count': len(items), 'items': items,
            'publication_authorized': False}


def build_empty_source_exclusion(empty_report, output_root):
    """Machine-readable fail-closed exclusion for all variants of empty art.

    Does not delete or alter files; output consumers must enforce this gate.
    """
    root = Path(output_root)
    excluded = []
    for item in empty_report['items']:
        sha = item['sha256']
        if not isinstance(sha, str) or len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
            raise ValueError('Invalid content SHA-256')
        for style in ('transparent', 'black', 'white'):
            excluded.append(str(root / sha[:2] / sha / (style + '.png')))
    return {'schema': 1, 'publication_authorized': False,
            'blocking_count': empty_report['blocking_count'],
            'excluded_source_sha256': sorted(item['sha256'] for item in empty_report['items']),
            'excluded_variant_paths': sorted(excluded),
            'note': 'Publication consumers MUST exclude these paths. No files were modified.'}
