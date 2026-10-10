import unittest
from qa_backlog_diagnostics import explain_review_backlog


class BacklogDiagnosticsTests(unittest.TestCase):
    def test_artwork_pixel_triage_is_exhaustive_and_never_approves(self):
        queue = {'items': [
            {'decision': 'PENDING', 'workstream': 'ARTWORK_REVIEW',
             'pixel_equivalence': 'EXACT_RGBA_IDENTICAL', 'distinct_pixel_artworks': 1},
            {'decision': 'PENDING', 'workstream': 'ARTWORK_REVIEW',
             'pixel_grouping': 'VERIFIED_RGBA_GROUPS', 'distinct_pixel_artworks': 2},
            {'decision': 'PENDING', 'workstream': 'ARTWORK_REVIEW'},
            {'decision': 'APPROVED', 'workstream': 'ARTWORK_REVIEW'},
        ]}
        report = explain_review_backlog(queue)
        self.assertEqual(report['pending_review_tasks'], 3)
        self.assertEqual(report['artwork_pixel_triage'], {
            'MULTIPLE_VERIFIED_PIXEL_ARTWORKS_REQUIRE_COMPARISON': 1,
            'ONE_VERIFIED_PIXEL_ARTWORK_REQUIRES_MASTER_REVIEW': 1,
            'PIXEL_EVIDENCE_INCOMPLETE_OR_UNAVAILABLE': 1,
        })

    def test_verified_pixel_group_distribution_is_diagnostic_only(self):
        report = explain_review_backlog({'items': [
            {'decision': 'PENDING', 'workstream': 'ARTWORK_REVIEW',
             'distinct_sha256': 3, 'distinct_pixel_artworks': 2},
            {'decision': 'PENDING', 'workstream': 'ARTWORK_REVIEW',
             'distinct_sha256': 2, 'distinct_pixel_artworks': 1},
        ]})
        self.assertEqual(report['artwork_distinct_pixel_group_distribution'], {'1': 1, '2': 1})
        self.assertEqual(report['pending_review_tasks'], 2)

    def test_string_and_mixed_source_evidence_do_not_crash(self):
        queue = {'items': [
            {'decision': 'PENDING', 'workstream': 'ARTWORK_REVIEW',
             'source_evidence': ['feed-a', {'sha256': 'abc'}, None, {'sha256': 'def'}]},
            {'decision': 'PENDING', 'workstream': 'ARTWORK_REVIEW',
             'source_evidence': {'feed': 'some-text', 'other': {'sha256': 'abc'}}},
            {'decision': 'PENDING', 'workstream': 'ARTWORK_REVIEW',
             'source_evidence': 'unstructured evidence', 'sha256': 'abc'},
        ]}
        report = explain_review_backlog(queue)
        self.assertEqual(report['pending_review_tasks'], 3)
        self.assertEqual(report['artwork_review_subcauses']['MULTIPLE_CANDIDATE_ARTWORKS_SAME_REFERENCE'], 1)
        self.assertEqual(report['artwork_review_subcauses']['SINGLE_CANDIDATE_ARTWORK_DIFFERS_FROM_MASTER'], 2)

    def test_master_exact_inspection_savings_are_not_approvals(self):
        queue = {'items': [
            {'decision': 'PENDING', 'workstream': 'ARTWORK_REVIEW',
             'artwork_review_units': [
                 {'master_pixel_comparison': 'PIXEL_EXACT_SAME_SERVICE_MASTER',
                  'duplicate_sha256': ['b']},
                 {'master_pixel_comparison': 'PIXEL_EXACT_SAME_SERVICE_MASTER',
                  'duplicate_sha256': []}]},
            {'decision': 'PENDING', 'workstream': 'ARTWORK_REVIEW',
             'artwork_review_units': [
                 {'master_pixel_comparison': 'NO_PIXEL_EXACT_SAME_SERVICE_MASTER',
                  'duplicate_sha256': []}]},
        ]}
        report = explain_review_backlog(queue)
        self.assertEqual(report['pending_review_tasks'], 2)
        self.assertEqual(report['verified_artwork_review_units'], 3)
        self.assertEqual(report['duplicate_sha_inspections_avoided'], 1)
        self.assertEqual(report['artwork_tasks_all_units_pixel_exact_master'], 1)
        self.assertEqual(report['master_pixel_comparison_units']['PIXEL_EXACT_SAME_SERVICE_MASTER'], 2)
        self.assertEqual(report['master_pixel_comparison_units']['NO_PIXEL_EXACT_SAME_SERVICE_MASTER'], 1)
        self.assertEqual(report['artwork_units_verified_different_from_master'], 1)
        self.assertEqual(report['artwork_tasks_with_verified_master_difference'], 1)

    def test_identity_variant_sha_multiplicity_does_not_approve_collisions(self):
        queue = {'items': [
            {'decision': 'PENDING', 'workstream': 'IDENTITY_VERIFICATION',
             'category': 'IDENTITY_COLLISION', 'reasons': ['UNVERIFIED_REGISTRY_ID'],
             'variants': [{'sha256': 'aaa'}, {'sha256': 'aaa'}, {'sha256': 'bbb'}]},
            {'decision': 'PENDING', 'workstream': 'IDENTITY_VERIFICATION',
             'category': 'IDENTITY_COLLISION', 'reasons': ['UNVERIFIED_REGISTRY_ID'],
             'variants': [{'sha256': 'ccc'}, {'sources': ['unverified']}]},
        ]}
        report = explain_review_backlog(queue)
        self.assertEqual(report['pending_review_tasks'], 2)
        self.assertEqual(report['identity_variant_count_distribution'], {'2': 1, '3': 1})
        self.assertEqual(report['identity_unique_sha_count_distribution'], {'1': 1, '2': 1})
        self.assertEqual(report['identity_tasks_missing_variant_sha_evidence'], 1)
        self.assertEqual(report['identity_repeated_sha_variant_observations'], 1)

    def test_identity_provenance_keeps_unknown_source_unresolved(self):
        queue = {'items': [
            {'decision': 'PENDING', 'workstream': 'IDENTITY_VERIFICATION',
             'category': 'IDENTITY_COLLISION', 'reasons': ['UNVERIFIED_REGISTRY_ID'],
             'variants': [{'sha256': 'a', 'sources': ['source-ingest/originals/vhannibal/a.png']},
                          {'sha256': 'b', 'sources': ['source-ingest/originals/vhannibal/b.png']}]},
            {'decision': 'PENDING', 'workstream': 'IDENTITY_VERIFICATION',
             'category': 'IDENTITY_COLLISION', 'reasons': ['UNVERIFIED_REGISTRY_ID'],
             'variants': [{'sha256': 'c', 'sources': ['source-ingest/originals/vhannibal/c.png']},
                          {'sha256': 'd', 'sources': ['unknown.png']}]},
        ]}
        report = explain_review_backlog(queue)
        self.assertEqual(report['pending_review_tasks'], 2)
        self.assertEqual(report['identity_provenance_distribution']['SINGLE_VERIFIED_SOURCE_BUCKET'], 1)
        self.assertEqual(report['identity_provenance_distribution']['UNKNOWN_OR_INCOMPLETE_PROVENANCE'], 1)
        self.assertEqual(report['identity_unknown_origin_tasks'], 1)
        self.assertEqual(report['identity_cross_origin_tasks'], 1)

    def test_live_windows_paths_report_both_real_collision_origins(self):
        queue = {'items': [{
            'decision': 'PENDING', 'workstream': 'IDENTITY_VERIFICATION',
            'category': 'IDENTITY_COLLISION', 'candidate_identity': '1_0_1_TEST',
            'reasons': ['UNVERIFIED_REGISTRY_ID'],
            'variants': [
                {'sha256': 'a'*64, 'sources': [
                    r'D:\\WARDER-PICON-FACTORY\\11-APP\\.factory-data\\source-ingest\\originals\\vhannibal\\archive\\logo.png']},
                {'sha256': 'b'*64, 'sources': [
                    r'D:\\WARDER-PICON-FACTORY\\11-APP\\.factory-data\\source-ingest\\originals\\openatv8\\bf8cb399d92f16682bb81639588894dbaed8f7bda7af3ecbc80cbc9a3b15e0ad\\picon\\logo.png']},
            ],
        }]}
        report = explain_review_backlog(queue)
        self.assertEqual(report['identity_cross_origin_tasks'], 1)
        self.assertEqual(report['identity_reasons_by_source']['vhannibal']['UNVERIFIED_REGISTRY_ID'], 1)
        self.assertEqual(report['identity_reasons_by_source']['openatv8']['UNVERIFIED_REGISTRY_ID'], 1)
        self.assertEqual(report['pending_by_source_origin']['vhannibal'], 1)
        self.assertEqual(report['pending_by_source_origin']['openatv8'], 1)
        self.assertEqual(report['identity_examples_by_reason']['UNVERIFIED_REGISTRY_ID'][0]['source_origins'],
                         ['openatv8', 'vhannibal'])
        self.assertEqual(report['pending_review_tasks'], 1)

    def test_pending_causes_count_tasks_without_inventing_approvals(self):
        queue = {'consolidation': {'review_tasks_avoided': 5}, 'items': [
            {'decision': 'PENDING', 'workstream': 'ARTWORK_REVIEW',
             'category': 'REGISTRY_MATCH', 'reasons': ['EXISTING_SERVICE_DIFFERENT_ART'],
             'source_origins': ['openatv8', 'vhannibal'], 'source_observations': 3, 'distinct_sha256': 2},
            {'decision': 'PENDING', 'workstream': 'IDENTITY_VERIFICATION',
             'category': 'IDENTITY_COLLISION', 'reasons': ['UNVERIFIED_REGISTRY_ID']},
            {'decision': 'APPROVED_FOR_REVIEW', 'workstream': 'ARTWORK_REVIEW',
             'reasons': ['EXISTING_SERVICE_DIFFERENT_ART']},
        ]}
        report = explain_review_backlog(queue)
        self.assertEqual(report['total_review_tasks'], 3)
        self.assertEqual(report['pending_review_tasks'], 2)
        self.assertEqual(report['pending_by_reason']['EXISTING_SERVICE_DIFFERENT_ART'], 1)
        self.assertEqual(report['pending_by_reason']['UNVERIFIED_REGISTRY_ID'], 1)
        self.assertEqual(report['pending_by_source_origin']['openatv8'], 1)
        self.assertEqual(report['pending_by_source_origin']['vhannibal'], 1)
        self.assertEqual(report['pending_grouped_tasks'], 1)
        self.assertEqual(report['pending_grouped_source_observations'], 3)
        self.assertEqual(report['grouped_distinct_artwork_distribution']['2'], 1)
        self.assertEqual(len(report['identity_examples_by_reason']['UNVERIFIED_REGISTRY_ID']), 1)
        self.assertEqual(report['identity_verification_subcauses']['SERVICE_REFERENCE_ARTWORK_COLLISION'], 1)
        self.assertEqual(report['identity_verification_reasons']['UNVERIFIED_REGISTRY_ID'], 1)
        self.assertEqual(report['identity_reasons_by_source']['unknown']['UNVERIFIED_REGISTRY_ID'], 1)
        self.assertEqual(len(report['pending_examples_by_reason']['EXISTING_SERVICE_DIFFERENT_ART']), 1)
        self.assertEqual(len(report['pending_examples_by_reason']['UNVERIFIED_REGISTRY_ID']), 1)
        self.assertEqual(report['grouping_savings']['review_tasks_avoided'], 5)


if __name__ == '__main__':
    unittest.main()
