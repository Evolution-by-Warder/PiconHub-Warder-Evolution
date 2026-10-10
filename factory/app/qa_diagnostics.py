"""Deterministic QA triage: distinguish proven corruption from visual heuristics.

This never approves an asset or hides findings from the complete audit report.
"""
from collections import Counter

ADVISORY = frozenset({'LOW_CONTRAST_WHITE', 'LOW_CONTRAST_BLACK'})

def summarize(issues_by_sha):
    if not isinstance(issues_by_sha, dict):
        raise TypeError('QA findings must be a dictionary')
    blocking = {}
    advisory = {}
    reasons = Counter()
    for sha, issues in issues_by_sha.items():
        if not isinstance(issues, (list, tuple)):
            raise TypeError('QA findings must be a list')
        reasons.update(set(issues))
        critical = sorted(set(issues) - ADVISORY)
        hints = sorted(set(issues) & ADVISORY)
        if critical:
            blocking[sha] = critical
        if hints:
            advisory[sha] = hints
    return {'blocking': blocking, 'advisory': advisory,
            'blocking_count': len(blocking), 'advisory_count': len(advisory),
            'reasons': dict(reasons)}
