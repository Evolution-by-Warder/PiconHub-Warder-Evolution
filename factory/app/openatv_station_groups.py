"""Deterministic OpenATV station groups; never equate a filename with a service ID."""
from collections import defaultdict
from pathlib import PureWindowsPath
from openatv_candidate_link import _station_key


def group_openatv_stations(rows):
    groups = defaultdict(list)
    for row in rows:
        source = str(row.get('candidate_source', ''))
        parts = source.replace('/', '\\').lower().split('\\')
        if 'source-ingest' not in parts or 'openatv8' not in parts:
            continue
        name = PureWindowsPath(source).name.casefold()
        key = _station_key(name)
        if key is not None:
            groups[key].append(row)
    result = {'station_names': len(groups), 'files': sum(map(len, groups.values())),
              'linked_station_names': 0, 'unlinked_station_names': 0,
              'conflicting_station_names': 0, 'distinct_unlinked_artworks': 0,
              'station_groups': []}
    for name, items in sorted(groups.items()):
        refs = set()
        hashes = set()
        for item in items:
            if item.get('candidate_sha256'):
                hashes.add(item['candidate_sha256'])
            if item.get('classification') == 'EVIDENCE_LINKED':
                ref = item.get('candidate_service_reference')
                if ref:
                    refs.add(ref)
            elif item.get('classification') in ('IDENTICAL', 'REVIEW'):
                ref = item.get('service_reference')
                if ref:
                    refs.add(ref)
            evidence = item.get('artwork_evidence') or {}
            refs.update(evidence.get('possible_master_service_references') or ())
        status = 'CONFLICT' if len(refs) > 1 else 'CANDIDATE' if refs else 'UNLINKED'
        result[{'CONFLICT':'conflicting_station_names', 'CANDIDATE':'linked_station_names',
                'UNLINKED':'unlinked_station_names'}[status]] += 1
        if status == 'UNLINKED':
            result['distinct_unlinked_artworks'] += len(hashes)
        result['station_groups'].append({'filename': name, 'status': status,
            'file_count': len(items), 'distinct_sha256_count': len(hashes),
            'candidate_references': sorted(refs), 'identity_verified': False})
    return result
