import unittest
from review_queue import build_review_queue


class CrossFeedReviewGroupingTests(unittest.TestCase):
    def test_same_service_and_reason_across_feeds_is_one_review(self):
        rows = [
            {'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
             'service_reference': '1_0_1_2_3_4_5_6_7_8',
             'candidate_sha256': 'a'*64,
             'candidate_source': r'C:\\source-ingest\\originals\\openatv8\\a.png'},
            {'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
             'service_reference': '1_0_1_2_3_4_5_6_7_8',
             'candidate_sha256': 'b'*64,
             'candidate_source': r'C:\\source-ingest\\originals\\vhannibal\\b.png'},
        ]
        result = build_review_queue({}, {}, [], rows)
        self.assertEqual(result['count'], 1)
        item = result['items'][0]
        self.assertEqual(item['distinct_sha256'], 2)
        self.assertEqual(item['source_observations'], 2)
        self.assertEqual(len(item['source_evidence']), 2)
        self.assertEqual(item['decision'], 'PENDING')

    def test_different_references_remain_separate(self):
        rows = [
            {'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
             'service_reference': ref, 'candidate_sha256': sha*64,
             'candidate_source': r'C:\\source-ingest\\originals\\openatv8\\a.png'}
            for ref, sha in [('1_0_1_2_3_4_5_6_7_8', 'a'), ('1_0_1_9_3_4_5_6_7_8', 'b')]
        ]
        result = build_review_queue({}, {}, [], rows)
        self.assertEqual(result['count'], 2)


if __name__ == '__main__':
    unittest.main()
