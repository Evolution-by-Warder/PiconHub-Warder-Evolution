"""Read-only, byte-exact evidence linking external artwork to Warder Master.

An identical logo does NOT prove a broadcast service identity. Never assign a
service reference to a UTF8SNP filename from an artwork hash alone.
"""
from collections import defaultdict, Counter


def master_artwork_index(registry):
    hashes = defaultdict(set)
    for ref, locations in registry.get('services', {}).items():
        for entry in locations:
            if entry.get('style') == 'transparent' and entry.get('sha256'):
                hashes[entry['sha256'].lower()].add(ref)
    return {sha: sorted(refs) for sha, refs in hashes.items()}


def attach_artwork_evidence(matches, registry):
    """Attach non-authoritative evidence; return counts for UI and JSON."""
    index = master_artwork_index(registry)
    counts = Counter()
    for row in matches:
        if row.get('classification') != 'UNMAPPED':
            continue
        sha = row.get('candidate_sha256', '').lower()
        refs = index.get(sha, [])
        if len(refs) == 1:
            status = 'EXACT_ARTWORK_SINGLE_MASTER_REF'
        elif refs:
            status = 'EXACT_ARTWORK_MULTIPLE_MASTER_REFS'
        else:
            status = 'NO_EXACT_MASTER_ARTWORK'
        row['artwork_evidence'] = {'status': status, 'possible_master_service_references': refs,
                                   'identity_verified': False}
        counts[status] += 1
    return dict(counts)
