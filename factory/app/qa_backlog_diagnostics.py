"""Read-only root-cause accounting for QA backlog, never an approval gate."""
from collections import Counter, defaultdict


def explain_review_backlog(queue):
    items = queue.get('items', [])
    reasons = Counter()
    workstreams = Counter()
    categories = Counter()
    source_origins = Counter()
    states = Counter()
    grouped = 0
    identity_subcauses = Counter()
    identity_observations = Counter()
    identity_by_source = defaultdict(Counter)
    unresolved_examples = defaultdict(list)
    identity_examples = defaultdict(list)
    grouped_distinct_artworks = Counter()
    grouped_source_observations = 0
    artwork_review_subcauses = Counter()
    artwork_review_by_source = defaultdict(Counter)
    artwork_review_examples = defaultdict(list)
    for item in items:
        state = item.get('decision', 'PENDING')
        states[state] += 1
        if state != 'PENDING':
            continue
        workstreams[item.get('workstream') or 'UNKNOWN'] += 1
        if item.get('workstream') == 'IDENTITY_VERIFICATION':
            reason = (item.get('reasons') or ['UNSPECIFIED'])[0]
            if item.get('category') == 'IDENTITY_COLLISION':
                identity_subcauses['SERVICE_REFERENCE_ARTWORK_COLLISION'] += 1
            elif not item.get('candidate_identity'):
                identity_subcauses['MISSING_SERVICE_REFERENCE'] += 1
            elif item.get('master_locations'):
                identity_subcauses['MASTER_PRESENT_REQUIRES_IDENTITY_REVIEW'] += 1
            else:
                identity_subcauses['NO_MASTER_LOCATION_FOR_CANDIDATE'] += 1
            identity_observations[reason] += 1
            if len(identity_examples[reason]) < 10:
                identity_examples[reason].append({
                    'review_id': item.get('review_id'),
                    'service_reference': item.get('candidate_identity'),
                    'source': item.get('source_origin'),
                    'master_locations': len(item.get('master_locations') or []),
                })
            for origin in set(item.get('source_origins') or [item.get('source_origin') or 'unknown']):
                identity_by_source[origin][reason] += 1
        if item.get('workstream') == 'ARTWORK_REVIEW':
            evidence = item.get('source_evidence') or ()
            if isinstance(evidence, dict):
                evidence = evidence.values()
            evidence_hashes = {
                entry.get('sha256') for entry in evidence
                if isinstance(entry, dict) and entry.get('sha256')
            }
            distinct = item.get('distinct_sha256') or len(evidence_hashes) or (1 if item.get('sha256') else 0)
            if distinct > 1:
                cause = 'MULTIPLE_CANDIDATE_ARTWORKS_SAME_REFERENCE'
            elif distinct == 1:
                cause = 'SINGLE_CANDIDATE_ARTWORK_DIFFERS_FROM_MASTER'
            else:
                cause = 'MISSING_CANDIDATE_ARTWORK_EVIDENCE'
            artwork_review_subcauses[cause] += 1
            origins = set(item.get('source_origins') or [item.get('source_origin') or 'unknown'])
            for origin in origins:
                artwork_review_by_source[origin][cause] += 1
            if len(artwork_review_examples[cause]) < 10:
                artwork_review_examples[cause].append({'review_id': item.get('review_id'),
                    'service_reference': item.get('candidate_identity'), 'distinct_artworks': distinct,
                    'source_origins': sorted(origins), 'master_locations': len(item.get('master_locations') or [])})
        categories[item.get('category') or 'UNKNOWN'] += 1
        for reason in set(item.get('reasons') or ['UNSPECIFIED']):
            reasons[reason] += 1
            if len(unresolved_examples[reason]) < 5:
                unresolved_examples[reason].append({
                    'review_id': item.get('review_id'),
                    'candidate_identity': item.get('candidate_identity'),
                    'sha256': item.get('sha256'),
                    'source_origin': item.get('source_origin'),
                    'source_observations': item.get('source_observations', 1),
                })
        for origin in set(item.get('source_origins') or [item.get('source_origin') or 'unknown']):
            source_origins[origin] += 1
        if item.get('source_observations', 0) > 1:
            grouped += 1
            grouped_source_observations += item['source_observations']
        if item.get('distinct_sha256', 0) > 1:
            grouped_distinct_artworks[item['distinct_sha256']] += 1
    pending = states['PENDING']
    return {
        'schema': 1,
        'policy': 'DIAGNOSTIC_ONLY; NO_APPROVAL_OR_IDENTITY_INFERENCE',
        'total_review_tasks': len(items),
        'pending_review_tasks': pending,
        'resolved_or_deferred_tasks': len(items) - pending,
        'decision_states': dict(sorted(states.items())),
        'pending_by_workstream': dict(sorted(workstreams.items())),
        'pending_by_category': dict(sorted(categories.items())),
        'artwork_review_subcauses': dict(sorted(artwork_review_subcauses.items())),
        'artwork_review_by_source': {origin: dict(sorted(causes.items())) for origin, causes in sorted(artwork_review_by_source.items())},
        'artwork_review_examples': dict(sorted(artwork_review_examples.items())),
        'identity_verification_subcauses': dict(sorted(identity_subcauses.items())),
        'identity_verification_reasons': dict(sorted(identity_observations.items())),
        'identity_examples_by_reason': dict(sorted(identity_examples.items())),
        'identity_reasons_by_source': {origin: dict(sorted(reasons.items())) for origin, reasons in sorted(identity_by_source.items())},
        'pending_by_reason': dict(sorted(reasons.items(), key=lambda pair: (-pair[1], pair[0]))),
        'pending_by_source_origin': dict(sorted(source_origins.items())),
        'pending_examples_by_reason': dict(sorted(unresolved_examples.items())),
        'pending_grouped_tasks': grouped,
        'pending_grouped_source_observations': grouped_source_observations,
        'grouped_distinct_artwork_distribution': {str(n): count for n, count in sorted(grouped_distinct_artworks.items())},
        'grouping_savings': queue.get('consolidation', {}),
        'note': 'Reasons can overlap: sum of reason counts need not equal pending tasks.',
    }
