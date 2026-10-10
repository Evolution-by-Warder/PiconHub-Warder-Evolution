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
    unresolved_examples = defaultdict(list)
    for item in items:
        state = item.get('decision', 'PENDING')
        states[state] += 1
        if state != 'PENDING':
            continue
        workstreams[item.get('workstream') or 'UNKNOWN'] += 1
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
        'pending_by_reason': dict(sorted(reasons.items(), key=lambda pair: (-pair[1], pair[0]))),
        'pending_by_source_origin': dict(sorted(source_origins.items())),
        'pending_examples_by_reason': dict(sorted(unresolved_examples.items())),
        'pending_grouped_tasks': grouped,
        'grouping_savings': queue.get('consolidation', {}),
        'note': 'Reasons can overlap: sum of reason counts need not equal pending tasks.',
    }
