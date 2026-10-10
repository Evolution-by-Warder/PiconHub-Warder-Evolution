"""Deterministic, read-only human review queue; no implicit approvals."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from source_registry import atomic_json
from qa_diagnostics import ADVISORY


def stable_review_id(kind: str, identity: str, sha: str) -> str:
    token = '\0'.join((kind, identity, sha)).encode('utf-8')
    return 'WR-' + hashlib.sha256(token).hexdigest()[:16].upper()



def _proven_openatv_style_only(collision):
    """Suppress a redundant identity *task*, not its immutable collision audit.

    Every observation must belong to a recognized OpenATV package; each
    package/format/style bucket must have exactly one SHA. Other feeds,
    unknown packages, or conflicting same-style art fail closed.
    """
    from registry_triage import _openatv_provenance, origin_of
    buckets = {}
    variants = collision.get('variants', ())
    if len(variants) < 2:
        return False
    for variant in variants:
        sha = variant.get('sha256')
        sources = variant.get('sources', ())
        if not sha or not sources:
            return False
        for source in sources:
            if origin_of(source) != 'openatv8':
                return False
            bucket = _openatv_provenance(source)
            if 'unknown' in bucket:
                return False
            previous = buckets.setdefault(bucket, sha)
            if previous != sha:
                return False
    return len(buckets) > 1

def build_review_queue(qa_issues: dict, originals: dict, collisions: list, registry_reviews=None, pixel_digests=None) -> dict:
    """Never mark technical QA as semantic approval."""
    items = []
    pixel_digests = pixel_digests or {}
    for sha, reasons in sorted(qa_issues.items()):
        # Visual heuristics are retained in the QA audit but are not a mandatory
        # manual approval task unless there is an independently proven defect.
        if not set(reasons).difference(ADVISORY):
            continue
        items.append({
            'review_id': stable_review_id('TECHNICAL_QA', '', sha),
            'category': 'TECHNICAL_QA', 'workstream': 'TECHNICAL_QA', 'sha256': sha,
            'original': str(originals.get(sha, '')),
            'reasons': sorted(set(reasons)), 'decision': 'PENDING',
        })
    style_only_suppressed = 0
    for collision in collisions:
        if _proven_openatv_style_only(collision):
            style_only_suppressed += 1
            continue
        identity = collision['candidate_service_ref']
        hashes = sorted(v['sha256'] for v in collision['variants'])
        items.append({
            'review_id': stable_review_id('IDENTITY_COLLISION', identity, '|'.join(hashes)),
            'category': 'IDENTITY_COLLISION', 'workstream': 'IDENTITY_VERIFICATION', 'candidate_identity': identity,
            'variants': collision['variants'], 'reasons': ['UNVERIFIED_REGISTRY_ID'],
            'decision': 'PENDING',
        })
    registry_items = {}
    for match in registry_reviews or ():
        if match.get('classification') != 'REVIEW':
            continue
        # Unknown filename/service-reference mapping is a discovery backlog,
        # not a request to manually approve thousands of unidentified assets.
        if match.get('reason') == 'UNRECOGNIZED_SERVICE_REFERENCE':
            continue
        identity = match.get('service_reference') or ''
        sha = match.get('candidate_sha256') or ''
        source = match.get('candidate_source', '')
        origin = 'local inbox'
        parts = tuple(source.replace('\\', '/').split('/'))
        if 'source-ingest' in parts:
            ix = parts.index('source-ingest')
            if ix + 2 < len(parts):
                origin = parts[ix + 2]
        reason = match.get('reason', 'REGISTRY_MATCH_REVIEW')
        workstream = 'ARTWORK_REVIEW' if reason == 'EXISTING_SERVICE_DIFFERENT_ART' else 'IDENTITY_VERIFICATION'
        review_id = stable_review_id('REGISTRY_MATCH', identity, sha + '|' + workstream + '|' + reason)
        item = {
            'review_id': review_id,
            'category': 'REGISTRY_MATCH', 'workstream': workstream, 'candidate_identity': identity or None,
            'sha256': sha, 'original': source, 'source_origin': origin,
            'reasons': [reason],
            'master_locations': match.get('master_locations', []),
            'proposed_resolution': 'Porovnať služobnú referenciu a varianty s Warder Master; bez automatického priradenia.',
            'decision': 'PENDING',
        }
        previous = registry_items.get(review_id)
        if previous:
            sources = set(previous.get('source_evidence', [previous['original']]))
            sources.add(source)
            previous['source_evidence'] = sorted(sources)
            previous['source_origins'] = sorted(set(previous.get('source_origins', [previous['source_origin']])) | {origin})
        else:
            registry_items[review_id] = item
    pre_group_registry_reviews = len(registry_items)
    pixel_equivalent_groups = 0
    pixel_equivalent_sha_observations = 0
    pixel_duplicate_sha_observations = 0
    pixel_distinct_artworks_avoided = 0
    registry_source_observations = sum(len(item.get('source_evidence', [item['original']])) for item in registry_items.values())
    # Source files are observations, not independent decisions. Group identical
    # service-reference/reason reviews across all source feeds, retaining each
    # original SHA and source. This reduces review actions, NOT approval gates.
    # Never group unidentified assets or different reasons/workstreams.
    grouped = {}
    for item in registry_items.values():
        source = item.get('original', '')
        identity = item.get('candidate_identity')
        if not identity:
            items.append(item)
            continue
        key = (identity, item['workstream'], tuple(item['reasons']))
        grouped.setdefault(key, []).append(item)
    for (identity, workstream, reasons), members in sorted(grouped.items()):
        if len(members) == 1:
            items.append(members[0])
            continue
        pixel_keys = {pixel_digests.get(member['sha256']) for member in members}
        pixel_equivalent = len(pixel_keys) == 1 and None not in pixel_keys
        verified_pixel_keys = [pixel_digests.get(member['sha256']) for member in members if pixel_digests.get(member['sha256'])]
        pixel_duplicate_sha_observations += len(verified_pixel_keys) - len(set(verified_pixel_keys))
        if len(verified_pixel_keys) == len(members):
            pixel_distinct_artworks_avoided += len(members) - len(pixel_keys)
        if pixel_equivalent:
            pixel_equivalent_groups += 1
            pixel_equivalent_sha_observations += len(members)
        evidence = {}
        for member in members:
            for source in member.get('source_evidence', [member['original']]):
                evidence[(member['sha256'], source)] = {'sha256': member['sha256'], 'source': source}
        entries = [evidence[k] for k in sorted(evidence)]
        grouped_item = {
            'review_id': stable_review_id('REGISTRY_EVIDENCE_GROUP', identity, workstream + '|' + '|'.join(reasons)),
            'category': 'REGISTRY_MATCH', 'workstream': workstream, 'candidate_identity': identity,
            'sha256': None, 'original': members[0]['original'],
            'source_origin': 'multiple' if len({origin for m in members for origin in m.get('source_origins', [m.get('source_origin', '')])}) > 1 else members[0].get('source_origin'),
            'source_origins': sorted({origin for m in members for origin in m.get('source_origins', [m.get('source_origin', '')])}), 'reasons': list(reasons),
            'master_locations': [json.loads(v) for v in sorted({json.dumps(loc, sort_keys=True, ensure_ascii=False) for m in members for loc in m.get('master_locations', [])})],
            'source_evidence': entries,
            'source_observations': len(entries),
            'distinct_sha256': len({entry['sha256'] for entry in entries}),
            'proposed_resolution': 'Kontrola celej referencie a všetkých grafických variantov; bez automatického schválenia.',
            'decision': 'PENDING',
        }
        if len(verified_pixel_keys) == len(members):
            grouped_item['distinct_pixel_artworks'] = len(pixel_keys)
            grouped_item['pixel_equivalence'] = 'EXACT_RGBA_IDENTICAL' if pixel_equivalent else 'VERIFIED_RGBA_GROUPS'
            grouped_item['pixel_artwork_groups'] = [
                {'pixel_sha256': digest, 'candidate_sha256': sorted(m['sha256'] for m in members if pixel_digests.get(m['sha256']) == digest)}
                for digest in sorted(pixel_keys)
            ]
        items.append(grouped_item)
    counts = {lane: sum(item.get('workstream') == lane for item in items) for lane in ('IDENTITY_VERIFICATION', 'ARTWORK_REVIEW', 'TECHNICAL_QA')}
    registry_review_groups = sum(item.get('category') == 'REGISTRY_MATCH' for item in items)
    consolidation = {'registry_source_observations': registry_source_observations,
                     'registry_duplicate_file_observations': max(0, registry_source_observations - pre_group_registry_reviews),
                     'registry_sha_reviews_before_grouping': pre_group_registry_reviews,
                     'registry_review_tasks_after_grouping': registry_review_groups,
                     'review_tasks_avoided': max(0, pre_group_registry_reviews - registry_review_groups),
                     'openatv_style_only_identity_tasks_avoided': style_only_suppressed,
                     'pixel_equivalent_review_groups': pixel_equivalent_groups,
                     'pixel_equivalent_sha_observations': pixel_equivalent_sha_observations,
                     'pixel_duplicate_sha_observations': pixel_duplicate_sha_observations,
                     'pixel_distinct_artworks_avoided': pixel_distinct_artworks_avoided,
                     'policy': 'EVIDENCE_GROUPING_ONLY; NO_AUTOMATIC_APPROVAL'}
    return {
        'workstream_counts': counts, 'consolidation': consolidation,
        'schema': 1, 'policy': 'READ_ONLY_REVIEW; NO_AUTOMATIC_APPROVAL_OR_PUBLICATION',
        'count': len(items), 'items': sorted(items, key=lambda x: (x['category'], x['review_id']))
    }


def save_review_queue(path: Path, queue: dict) -> None:
    if queue.get('count') != len(queue.get('items', [])):
        raise ValueError('Inconsistent review queue')
    atomic_json(path, queue)


def load_review_queue(path: Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if payload.get('schema') != 1 or payload.get('count') != len(payload.get('items', [])):
        raise ValueError('Invalid review queue')
    return payload
