"""Explicit human decisions, isolated from production and publishing."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from source_registry import atomic_json

DECISIONS = frozenset({'APPROVED_FOR_REVIEW', 'REJECTED', 'DEFERRED'})

def evidence_hash(item):
    """A decision is valid only for unchanged review evidence."""
    evidence = {key: value for key, value in item.items()
                if key not in ('decision', 'decision_note', 'decided_at', 'evidence_hash')}
    canonical = json.dumps(evidence, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

def record_decision(ledger_path, item, decision, note, operator_confirmation):
    if not operator_confirmation:
        raise PermissionError('Explicit operator confirmation required')
    if decision not in DECISIONS:
        raise ValueError('Unknown decision')
    review_id = item.get('review_id', '')
    if not review_id.startswith('WR-') or len(review_id) != 19:
        raise ValueError('Invalid review ID')
    if not isinstance(note, str) or len(note) > 2000:
        raise ValueError('Invalid note')
    ledger_path = Path(ledger_path)
    ledger = json.loads(ledger_path.read_text(encoding='utf-8')) if ledger_path.exists() else {'schema': 1, 'decisions': {}}
    if ledger.get('schema') != 1 or not isinstance(ledger.get('decisions'), dict):
        raise ValueError('Invalid decision ledger')
    ledger['decisions'][review_id] = {'decision': decision, 'note': note,
                                     'evidence_hash': evidence_hash(item)}
    atomic_json(ledger_path, ledger)
    return ledger['decisions'][review_id]

def _legacy_registry_decision(item, decisions):
    """Recover a pre-reason-aware decision only with exact old evidence.

    Never carry a decision between different reasons or grouped artwork sets.
    """
    if item.get('category') != 'REGISTRY_MATCH' or not item.get('sha256'):
        return None
    from review_queue import stable_review_id
    legacy_id = stable_review_id('REGISTRY_MATCH', item.get('candidate_identity') or '', item['sha256'])
    old_item = dict(item, review_id=legacy_id)
    previous = decisions.get(legacy_id)
    if previous and previous.get('evidence_hash') == evidence_hash(old_item):
        return previous
    return None


def apply_decisions(queue, ledger_path):
    """Carry decisions across runs only when the reviewed evidence is identical."""
    ledger_path = Path(ledger_path)
    if not ledger_path.exists():
        return queue
    ledger = json.loads(ledger_path.read_text(encoding='utf-8'))
    if ledger.get('schema') != 1 or not isinstance(ledger.get('decisions'), dict):
        raise ValueError('Invalid decision ledger')
    result = {**queue, 'items': []}
    for item in queue['items']:
        item = dict(item)
        previous = ledger['decisions'].get(item['review_id'])
        valid = bool(previous and previous.get('evidence_hash') == evidence_hash(item))
        if not valid:
            previous = _legacy_registry_decision(item, ledger['decisions'])
            valid = previous is not None
        if valid and previous.get('decision') in DECISIONS:
            item['decision'] = previous['decision']
            item['decision_note'] = previous.get('note', '')
        result['items'].append(item)
    return result
