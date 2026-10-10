"""Attach deterministic, read-only candidate links to OpenATV artwork variants.

Only byte-identical artwork to a unique Master reference can seed a link.
A name group with competing exact references is never linked.
"""
from collections import defaultdict
from pathlib import PureWindowsPath


def attach_name_candidates(matches):
    groups = defaultdict(lambda: {'refs': set(), 'rows': []})
    for row in matches:
        source = str(row.get('candidate_source', ''))
        parts = source.replace('/', '\\').lower().split('\\')
        if 'source-ingest' not in parts or 'openatv8' not in parts or row.get('classification') not in ('UNMAPPED', 'EVIDENCE_LINKED'):
            continue
        name = PureWindowsPath(source).name.casefold()
        group = groups[name]
        group['rows'].append(row)
        evidence = row.get('artwork_evidence') or {}
        if row.get('classification') == 'EVIDENCE_LINKED' and row.get('candidate_service_reference'):
            group['refs'].add(row['candidate_service_reference'])
        if evidence.get('status') in ('EXACT_ARTWORK_SINGLE_MASTER_REF', 'EXACT_ARTWORK_MULTIPLE_MASTER_REFS', 'PIXEL_EXACT_SINGLE_MASTER_REF', 'PIXEL_EXACT_MULTIPLE_MASTER_REFS', 'TRIM_EXACT_SINGLE_MASTER_REF', 'TRIM_EXACT_MULTIPLE_MASTER_REFS', 'SCALE_EXACT_SINGLE_MASTER_REF', 'SCALE_EXACT_MULTIPLE_MASTER_REFS'):
            group['refs'].update(evidence.get('possible_master_service_references') or [])
    counts = {'single_reference_names': 0, 'conflicting_names': 0, 'without_evidence_names': 0,
              'candidate_linked_files': 0, 'unlinked_files': 0}
    for name, group in groups.items():
        refs = sorted(group['refs'])
        if len(refs) == 1:
            counts['single_reference_names'] += 1
            status = 'NAME_GROUP_SINGLE_EXACT_ARTWORK_REFERENCE'
        elif refs:
            counts['conflicting_names'] += 1
            status = 'NAME_GROUP_CONFLICTING_REFERENCES'
        else:
            counts['without_evidence_names'] += 1
            status = 'NO_NAME_GROUP_EXACT_ARTWORK_EVIDENCE'
        for row in group['rows']:
            row['name_group_candidate'] = {
                'status': status, 'possible_master_service_references': refs,
                'identity_verified': False, 'filename': name,
                'evidence_type': 'MASTER_ARTWORK_EVIDENCE_WITHIN_SAME_OPENATV_FILENAME_GROUP',
            }
            if len(refs) == 1 and row.get('classification') == 'UNMAPPED':
                # An evidence-linked asset is no longer wholly unmapped, but
                # it is NOT an identity-verified service or an approved artwork.
                row['classification'] = 'EVIDENCE_LINKED'
                row['candidate_service_reference'] = refs[0]
                row['reason'] = 'UNVERIFIED_EXACT_ARTWORK_NAME_GROUP_LINK'
                counts['candidate_linked_files'] += 1
            elif row.get('classification') == 'UNMAPPED':
                counts['unlinked_files'] += 1
    return counts
