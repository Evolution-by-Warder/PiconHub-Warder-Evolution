import unittest
from qa_backlog_diagnostics import explain_review_backlog


class BacklogDiagnosticsTests(unittest.TestCase):
    def test_pending_causes_count_tasks_without_inventing_approvals(self):
        queue = {'consolidation': {'review_tasks_avoided': 5}, 'items': [
            {'decision': 'PENDING', 'workstream': 'ARTWORK_REVIEW',
             'category': 'REGISTRY_MATCH', 'reasons': ['EXISTING_SERVICE_DIFFERENT_ART'],
             'source_origins': ['openatv8', 'vhannibal'], 'source_observations': 3},
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
        self.assertEqual(report['grouping_savings']['review_tasks_avoided'], 5)


if __name__ == '__main__':
    unittest.main()
