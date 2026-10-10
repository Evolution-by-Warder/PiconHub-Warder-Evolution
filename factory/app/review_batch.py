"""Deterministic, read-only batches for manual Warder artwork review.

A review batch is an inspection aid, not a decision, identity mapping or import.
"""
from collections import Counter


def artwork_review_batch(queue, limit=10, offset=0):
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise ValueError('Invalid review batch size')
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
        raise ValueError('Invalid review batch offset')
    pending = [item for item in queue.get('items', [])
               if isinstance(item, dict) and item.get('decision') == 'PENDING'
               and item.get('workstream') == 'ARTWORK_REVIEW']
    priority = {'P1_VERIFY_SINGLE_PIXEL_ARTWORK_AGAINST_MASTER': 0,
                'P2_COMPARE_DISTINCT_PIXEL_ARTWORKS': 1,
                'P3_COMPLETE_PIXEL_EVIDENCE': 2}
    pending.sort(key=lambda item: (priority.get(item.get('review_priority'), 3),
                                   str(item.get('review_id') or '')))
    batch = []
    for item in pending[offset:offset + limit]:
        units = []
        for unit in item.get('artwork_review_units') or []:
            if not isinstance(unit, dict):
                continue
            units.append({'representative_sha256': unit.get('representative_sha256'),
                          'pixel_sha256': unit.get('pixel_sha256'),
                          'master_pixel_comparison': unit.get('master_pixel_comparison'),
                          'duplicate_sha256': list(unit.get('duplicate_sha256') or [])})
        batch.append({'review_id': item.get('review_id'),
                      'service_reference': item.get('candidate_identity'),
                      'review_priority': item.get('review_priority'),
                      'master_pixel_evidence': item.get('master_pixel_evidence'),
                      'source_origins': sorted(set(item.get('source_origins') or
                                                   [item.get('source_origin') or 'unknown'])),
                      'master_locations': item.get('master_locations') or [],
                      'candidate_artworks': units,
                      'decision': 'PENDING'})
    return {'schema': 1, 'policy': 'READ_ONLY_MANUAL_REVIEW; NO_APPROVAL_OR_IDENTITY_INFERENCE',
            'total_pending_artwork_tasks': len(pending), 'offset': offset,
            'limit': limit, 'returned': len(batch), 'has_more': offset + limit < len(pending),
            'items': batch}
