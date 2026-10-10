"""Read-only name-level aggregation of exact transparent artwork evidence.

Evidence is not a service identity and must never be written to the registry.
"""
from collections import defaultdict, Counter
from pathlib import PureWindowsPath
from openatv_candidate_link import _station_key


def summarize_openatv_name_evidence(matches, sample_limit=25):
    groups = defaultdict(lambda: {'files': 0, 'hashes': set(), 'exact_refs': set(), 'exact_files': 0, 'exact_hashes': set()})
    for row in matches:
        source = str(row.get('candidate_source', ''))
        parts = source.replace('/', '\\').lower().split('\\')
        if 'source-ingest' not in parts or 'openatv8' not in parts:
            continue
        if row.get('classification') not in ('UNMAPPED', 'EVIDENCE_LINKED'):
            continue
        name = PureWindowsPath(source).name.casefold()
        key = _station_key(name)
        if key is None:
            continue
        g = groups[key]
        g['files'] += 1
        sha = row.get('candidate_sha256')
        if sha:
            g['hashes'].add(sha.lower())
        evidence = row.get('artwork_evidence') or {}
        refs = evidence.get('possible_master_service_references') or []
        if evidence.get('status') == 'EXACT_ARTWORK_SINGLE_MASTER_REF' and len(refs) == 1:
            g['exact_files'] += 1
            g['exact_refs'].add(refs[0])
            if sha:
                g['exact_hashes'].add(sha.lower())
    categories = Counter()
    samples = []
    total_exact_files = 0
    mixed = 0
    for name, g in sorted(groups.items()):
        n = len(g['exact_refs'])
        if n == 0:
            status = 'NO_EXACT_EVIDENCE'
        elif n == 1:
            status = 'SINGLE_REF_ARTWORK_EVIDENCE'
        else:
            status = 'CONFLICTING_ARTWORK_EVIDENCE'
        categories[status] += 1
        total_exact_files += g['exact_files']
        if n == 1 and len(g['hashes'] - g['exact_hashes']) > 0:
            mixed += 1
        if n and len(samples) < sample_limit:
            samples.append({'filename': name, 'status': status, 'possible_master_service_references': sorted(g['exact_refs']), 'files': g['files'], 'exact_match_files': g['exact_files'], 'distinct_artwork_hashes': len(g['hashes']), 'identity_verified': False})
    return {'distinct_names': len(groups), 'total_files': sum(g['files'] for g in groups.values()), 'exact_match_files': total_exact_files, 'name_categories': dict(categories), 'single_ref_names_with_other_artwork_variants': mixed, 'samples': samples, 'identity_verified': False, 'policy': 'READ_ONLY_ARTWORK_EVIDENCE_NOT_SERVICE_IDENTITY'}
