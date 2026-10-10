import unittest
from qa_backlog_diagnostics import explain_review_backlog


class BacklogDiagnosticsTests(unittest.TestCase):
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
