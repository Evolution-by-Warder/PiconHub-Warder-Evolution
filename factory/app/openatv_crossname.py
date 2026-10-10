"""Read-only cross-filename exact-SHA evidence; never assigns a service identity."""
from collections import defaultdict
from pathlib import PureWindowsPath


def attach_crossname_artwork_candidates(rows):
    """Propagate only candidate evidence, not identities, across byte-identical PNGs.

    Existing verified source references are never modified. Ambiguous SHA groups
    retain all candidates and are explicitly marked conflicting.
    """
    sha_groups = defaultdict(lambda: {'refs': set(), 'names': set(), 'rows': []})
    for row in rows:
        path = str(row.get('candidate_source') or '')
        parts = path.replace('/', '\\').casefold().split('\\')
        if 'source-ingest' not in parts or 'openatv8' not in parts:
            continue
        sha = row.get('candidate_sha256')
        name = PureWindowsPath(path).name.casefold()
        if not isinstance(sha, str) or not name.endswith('.png') or len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha.casefold()):
            continue
        group = sha_groups[sha.casefold()]
        group['names'].add(name)
        group['rows'].append(row)
        evidence = row.get('artwork_evidence') or {}
        group['refs'].update(evidence.get('possible_master_service_references') or [])
        candidate = row.get('name_group_candidate') or {}
        group['refs'].update(candidate.get('possible_master_service_references') or [])
        if row.get('candidate_service_reference'):
            group['refs'].add(row['candidate_service_reference'])
    stats = {'unique_sha': len(sha_groups), 'shared_sha_across_names': 0,
             'crossname_candidate_files': 0, 'ambiguous_shared_sha': 0}
    for sha, group in sha_groups.items():
        if len(group['names']) < 2:
            continue
        stats['shared_sha_across_names'] += 1
        refs = sorted(group['refs'])
        if len(refs) > 1:
            stats['ambiguous_shared_sha'] += 1
        if not refs:
            continue
        for row in group['rows']:
            current = set((row.get('name_group_candidate') or {}).get('possible_master_service_references') or [])
            if not current.issuperset(refs):
                stats['crossname_candidate_files'] += 1
            row['crossname_artwork_candidate'] = {
                'status': 'AMBIGUOUS_EXACT_SHA' if len(refs) > 1 else 'UNVERIFIED_EXACT_SHA',
                'possible_master_service_references': refs,
                'same_artwork_station_names': sorted(group['names']),
                'identity_verified': False,
                'evidence_type': 'BYTE_IDENTICAL_ARTWORK_ACROSS_OPENATV_FILENAMES',
            }
    return stats
