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
        self.assertEqual(result['consolidation']['registry_sha_reviews_before_grouping'], 2)
        self.assertEqual(result['consolidation']['registry_review_tasks_after_grouping'], 1)
        self.assertEqual(result['consolidation']['review_tasks_avoided'], 1)
        item = result['items'][0]
        self.assertEqual(item['distinct_sha256'], 2)
        self.assertEqual(item['source_observations'], 2)
        self.assertEqual(len(item['source_evidence']), 2)
        self.assertEqual(item['decision'], 'PENDING')

    def test_pixel_identical_sha_variants_keep_pending_review_and_audit(self):
        rows = [{'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
                 'service_reference': 'service-a', 'candidate_sha256': sha * 64,
                 'candidate_source': sha + '.png'} for sha in ('a', 'b', 'c')]
        pixels = {'a' * 64: 'pixel-x', 'b' * 64: 'pixel-x', 'c' * 64: 'pixel-y'}
        result = build_review_queue({}, {}, [], rows, pixel_digests=pixels)
        self.assertEqual(result['count'], 1)
        item = result['items'][0]
        self.assertEqual(item['decision'], 'PENDING')
        self.assertEqual(item['distinct_sha256'], 3)
        self.assertEqual(item['distinct_pixel_artworks'], 2)
        self.assertEqual(item['pixel_grouping'], 'VERIFIED_RGBA_GROUPS')
        self.assertEqual(item['review_priority'], 'P2_COMPARE_DISTINCT_PIXEL_ARTWORKS')
        self.assertNotIn('pixel_equivalence', item)
        self.assertEqual(len(item['pixel_artwork_groups']), 2)
        self.assertEqual(result['consolidation']['pixel_duplicate_sha_observations'], 1)
        self.assertEqual(result['consolidation']['pixel_distinct_artworks_avoided'], 1)

    def test_full_pixel_equivalence_prioritizes_master_comparison_not_approval(self):
        rows = [{'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
                 'service_reference': 'service-a', 'candidate_sha256': sha * 64,
                 'candidate_source': sha + '.png'} for sha in ('a', 'b')]
        result = build_review_queue({}, {}, [], rows, pixel_digests={'a' * 64: 'same', 'b' * 64: 'same'})
        item = result['items'][0]
        self.assertEqual(item['review_priority'], 'P1_VERIFY_SINGLE_PIXEL_ARTWORK_AGAINST_MASTER')
        self.assertEqual(item['decision'], 'PENDING')
        self.assertEqual(result['count'], 1)

    def test_missing_pixel_proof_never_claims_pixel_equivalence(self):
        rows = [{'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
                 'service_reference': 'service-a', 'candidate_sha256': sha * 64,
                 'candidate_source': sha + '.png'} for sha in ('a', 'b')]
        result = build_review_queue({}, {}, [], rows, pixel_digests={'a' * 64: 'pixel-x'})
        self.assertNotIn('pixel_equivalence', result['items'][0])
        self.assertEqual(result['items'][0]['review_priority'], 'P3_COMPLETE_PIXEL_EVIDENCE')
        self.assertNotIn('pixel_artwork_groups', result['items'][0])
        self.assertEqual(result['consolidation']['pixel_distinct_artworks_avoided'], 0)

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
