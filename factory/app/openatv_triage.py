"""Compact, non-destructive OpenATV triage by station and distinct artwork.

Never promote filename or visual similarity to a service identity.
"""
from collections import defaultdict
from pathlib import PureWindowsPath
from openatv_candidate_link import _station_key


def build_openatv_triage(rows):
    groups = defaultdict(lambda: {'sources': 0, 'artworks': defaultdict(lambda: {'copies': 0, 'candidate_refs': set(), 'evidence': set()})})
    for row in rows:
        source = str(row.get('candidate_source') or '')
        parts = source.replace('/', '\\').casefold().split('\\')
        if 'source-ingest' not in parts or 'openatv8' not in parts:
            continue
        name = PureWindowsPath(source).name.casefold()
        sha = row.get('candidate_sha256')
        if not name.endswith('.png') or not sha:
            continue
        key = _station_key(name)
        if key is None:
            continue
        group = groups[key]
        group['sources'] += 1
        art = group['artworks'][sha]
        art['copies'] += 1
        evidence = row.get('artwork_evidence') or {}
        refs = set(evidence.get('possible_master_service_references') or [])
        candidate = row.get('name_group_candidate') or {}
        refs.update(candidate.get('possible_master_service_references') or [])
        crossname = row.get('crossname_artwork_candidate') or {}
        refs.update(crossname.get('possible_master_service_references') or [])
        if row.get('candidate_service_reference'):
            refs.add(row['candidate_service_reference'])
        art['candidate_refs'].update(refs)
        if refs:
            art['evidence'].add('UNVERIFIED_ARTWORK_OR_NAME_GROUP')
    entries = []
    totals = {'station_names': len(groups), 'source_files': 0, 'distinct_station_artworks': 0,
              'repeated_source_files': 0, 'no_candidate_stations': 0,
              'single_candidate_stations': 0, 'conflicting_candidate_stations': 0}
    for name, group in sorted(groups.items()):
        artwork = group['artworks']
        refs = sorted(set().union(*(a['candidate_refs'] for a in artwork.values())))
        status = ('CONFLICTING_CANDIDATES' if len(refs) > 1 else
                  'UNVERIFIED_SINGLE_CANDIDATE' if refs else 'NO_IDENTITY_EVIDENCE')
        totals[{'CONFLICTING_CANDIDATES':'conflicting_candidate_stations',
                'UNVERIFIED_SINGLE_CANDIDATE':'single_candidate_stations',
                'NO_IDENTITY_EVIDENCE':'no_candidate_stations'}[status]] += 1
        totals['source_files'] += group['sources']
        totals['distinct_station_artworks'] += len(artwork)
        entries.append({'station_filename': name, 'status': status, 'identity_verified': False,
                        'source_copies': group['sources'], 'artwork_count': len(artwork),
                        'candidate_references': refs,
                        'artworks': [{'sha256': sha, 'copies': a['copies'],
                                      'candidate_references': sorted(a['candidate_refs'])}
                                     for sha, a in sorted(artwork.items())]})
    totals['repeated_source_files'] = totals['source_files'] - totals['distinct_station_artworks']
    return {'schema': 1, 'policy': 'READ_ONLY; NO_IDENTITY_ASSIGNED; NO_MASTER_WRITE',
            'summary': totals, 'stations': entries}
