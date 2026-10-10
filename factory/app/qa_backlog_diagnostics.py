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
    identity_variant_distribution = Counter()
    identity_unique_sha_distribution = Counter()
    identity_missing_sha_evidence = 0
    identity_repeated_sha_observations = 0
    identity_provenance_distribution = Counter()
    identity_cross_origin_tasks = 0
    identity_unknown_origin_tasks = 0
    identity_by_source = defaultdict(Counter)
    unresolved_examples = defaultdict(list)
    identity_examples = defaultdict(list)
    grouped_distinct_artworks = Counter()
    grouped_source_observations = 0
    artwork_review_subcauses = Counter()
    artwork_pixel_groups = Counter()
    artwork_pixel_triage = Counter()
    artwork_review_priorities = Counter()
    artwork_review_units = 0
    artwork_duplicate_sha_inspections_avoided = 0
    master_pixel_comparisons = Counter()
    artwork_tasks_with_all_units_matching_master = 0
    artwork_tasks_with_unavailable_master_evidence = 0
    master_exact_visual_units_avoided = 0
    artwork_units_requiring_master_comparison = 0
    artwork_tasks_with_verified_master_difference = 0
    artwork_pixel_examples = defaultdict(list)
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
            variants = item.get('variants') or []
            variant_hashes = [v.get('sha256') for v in variants if isinstance(v, dict) and isinstance(v.get('sha256'), str) and v.get('sha256')]
            identity_variant_distribution[str(len(variants))] += 1
            identity_unique_sha_distribution[str(len(set(variant_hashes)))] += 1
            identity_repeated_sha_observations += max(0, len(variant_hashes) - len(set(variant_hashes)))
            if len(variant_hashes) != len(variants):
                identity_missing_sha_evidence += 1
            from registry_triage import origin_of, _openatv_provenance
            variant_origins = set()
            provenance = set()
            unknown_provenance = False
            for variant in variants:
                if not isinstance(variant, dict):
                    unknown_provenance = True
                    continue
                sources = variant.get('sources') or []
                if not isinstance(sources, (list, tuple)) or not sources:
                    unknown_provenance = True
                    continue
                for source in sources:
                    if not isinstance(source, str) or not source:
                        unknown_provenance = True
                        continue
                    origin = origin_of(source)
                    variant_origins.add(origin)
                    if origin == 'openatv8':
                        bucket = _openatv_provenance(source)
                        if 'unknown' in bucket:
                            unknown_provenance = True
                        else:
                            provenance.add('openatv8:' + ':'.join(bucket))
                    elif origin == 'local-inbox':
                        unknown_provenance = True
                    else:
                        provenance.add(origin)
            if len(variant_origins) > 1:
                identity_cross_origin_tasks += 1
            if unknown_provenance or not provenance:
                identity_unknown_origin_tasks += 1
                identity_provenance_distribution['UNKNOWN_OR_INCOMPLETE_PROVENANCE'] += 1
            elif len(provenance) > 1:
                identity_provenance_distribution['MULTIPLE_VERIFIED_SOURCE_BUCKETS'] += 1
            else:
                identity_provenance_distribution['SINGLE_VERIFIED_SOURCE_BUCKET'] += 1
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
            if item.get('pixel_equivalence') == 'EXACT_RGBA_IDENTICAL' or (
                    item.get('distinct_pixel_artworks') == 1 and item.get('pixel_artwork_groups')):
                pixel_cause = 'ONE_VERIFIED_PIXEL_ARTWORK_REQUIRES_MASTER_REVIEW'
            elif item.get('pixel_grouping') == 'VERIFIED_RGBA_GROUPS':
                pixel_cause = 'MULTIPLE_VERIFIED_PIXEL_ARTWORKS_REQUIRE_COMPARISON'
            else:
                pixel_cause = 'PIXEL_EVIDENCE_INCOMPLETE_OR_UNAVAILABLE'
            artwork_pixel_triage[pixel_cause] += 1
            artwork_review_priorities[item.get('review_priority') or 'UNPRIORITIZED'] += 1
            units = item.get('artwork_review_units') or []
            artwork_review_units += len(units)
            statuses = [u.get('master_pixel_comparison', 'MASTER_PIXEL_EVIDENCE_UNAVAILABLE') for u in units]
            master_pixel_comparisons.update(statuses)
            master_exact_visual_units_avoided += statuses.count('PIXEL_EXACT_SAME_SERVICE_MASTER')
            artwork_units_requiring_master_comparison += statuses.count('NO_PIXEL_EXACT_SAME_SERVICE_MASTER')
            if 'NO_PIXEL_EXACT_SAME_SERVICE_MASTER' in statuses:
                artwork_tasks_with_verified_master_difference += 1
            if statuses and all(status == 'PIXEL_EXACT_SAME_SERVICE_MASTER' for status in statuses):
                artwork_tasks_with_all_units_matching_master += 1
            if not statuses or 'MASTER_PIXEL_EVIDENCE_UNAVAILABLE' in statuses:
                artwork_tasks_with_unavailable_master_evidence += 1
            artwork_duplicate_sha_inspections_avoided += sum(len(unit.get('duplicate_sha256') or []) for unit in units)
            if len(artwork_pixel_examples[pixel_cause]) < 10:
                artwork_pixel_examples[pixel_cause].append({
                    'review_id': item.get('review_id'),
                    'candidate_identity': item.get('candidate_identity'),
                    'distinct_sha256': distinct,
                    'distinct_pixel_artworks': item.get('distinct_pixel_artworks'),
                })
            if item.get('distinct_pixel_artworks') is not None:
                artwork_pixel_groups[str(item['distinct_pixel_artworks'])] += 1
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
        'artwork_distinct_pixel_group_distribution': dict(sorted(artwork_pixel_groups.items())),
        'artwork_pixel_triage': dict(sorted(artwork_pixel_triage.items())),
        'artwork_review_priorities': dict(sorted(artwork_review_priorities.items())),
        'verified_artwork_review_units': artwork_review_units,
        'duplicate_sha_inspections_avoided': artwork_duplicate_sha_inspections_avoided,
        'master_pixel_comparison_units': dict(sorted(master_pixel_comparisons.items())),
        'artwork_tasks_all_units_pixel_exact_master': artwork_tasks_with_all_units_matching_master,
        'master_exact_visual_units_avoided': master_exact_visual_units_avoided,
        'artwork_units_verified_different_from_master': artwork_units_requiring_master_comparison,
        'artwork_tasks_with_verified_master_difference': artwork_tasks_with_verified_master_difference,
        'artwork_tasks_missing_master_pixel_evidence': artwork_tasks_with_unavailable_master_evidence,
        'artwork_pixel_triage_examples': dict(sorted(artwork_pixel_examples.items())),
        'artwork_review_by_source': {origin: dict(sorted(causes.items())) for origin, causes in sorted(artwork_review_by_source.items())},
        'artwork_review_examples': dict(sorted(artwork_review_examples.items())),
        'identity_verification_subcauses': dict(sorted(identity_subcauses.items())),
        'identity_variant_count_distribution': dict(sorted(identity_variant_distribution.items())),
        'identity_provenance_distribution': dict(sorted(identity_provenance_distribution.items())),
        'identity_cross_origin_tasks': identity_cross_origin_tasks,
        'identity_unknown_origin_tasks': identity_unknown_origin_tasks,
        'identity_unique_sha_count_distribution': dict(sorted(identity_unique_sha_distribution.items())),
        'identity_tasks_missing_variant_sha_evidence': identity_missing_sha_evidence,
        'identity_repeated_sha_variant_observations': identity_repeated_sha_observations,
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
