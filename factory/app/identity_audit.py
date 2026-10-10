"""Read-only, conservative service-name collision audit.

A filename is a candidate identity, never a validated Warder Registry ID.
No file is deleted, renamed, approved, or published by this audit.
"""
from collections import defaultdict
from pathlib import Path
import re

SERVICE_REF = re.compile(r'^[0-9a-fA-F]+(?:_[0-9a-fA-F]+){5,}$')


def candidate_identity(path):
    """Recognize Enigma2 service-reference filename stems only."""
    stem = Path(path).stem
    if not SERVICE_REF.fullmatch(stem):
        return None
    return stem.lower()


def audit_collisions(paths_by_sha):
    """Return conflicting candidate service references with provenance.

    Input maps sha256 to an original path; equal hashes have already been
    deduplicated. Multiple different hashes for one reference are not merged.
    """
    records = [{'sha256': sha, 'source': str(path)} for sha, path in paths_by_sha.items()]
    return audit_collision_records(records)


def audit_collision_records(records):
    """Audit every source path while collapsing identical PNGs per identity."""
    groups = defaultdict(lambda: defaultdict(list))
    for record in records:
        sha, path = record['sha256'], record['source']
        ref = candidate_identity(path)
        if ref:
            groups[ref][sha].append(str(path))
    return [
        {'candidate_service_ref': ref, 'variants': [
            {'sha256': sha, 'sources': sorted(set(paths))}
            for sha, paths in sorted(by_hash.items())],
         'classification': 'IDENTITY_COLLISION_UNRESOLVED'}
        for ref, by_hash in sorted(groups.items()) if len(by_hash) > 1
    ]
