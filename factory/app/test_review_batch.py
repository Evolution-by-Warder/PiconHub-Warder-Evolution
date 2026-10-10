import unittest
from review_batch import artwork_review_batch


class ReviewBatchTests(unittest.TestCase):
    def test_stable_first_ten_preserve_master_and_candidate_evidence(self):
        queue = {'items': [
            {'review_id': 'WR-Z', 'workstream': 'ARTWORK_REVIEW', 'decision': 'PENDING',
             'review_priority': 'P2_COMPARE_DISTINCT_PIXEL_ARTWORKS',
             'candidate_identity': 'ref-z', 'master_locations': [{'path': 'master.png'}],
             'source_origins': ['vhannibal', 'openatv8'],
             'artwork_review_units': [{'representative_sha256': 'a'*64,
                                       'master_pixel_comparison': 'NO_PIXEL_EXACT_SAME_SERVICE_MASTER',
                                       'duplicate_sha256': ['b'*64]}]},
            {'review_id': 'WR-A', 'workstream': 'ARTWORK_REVIEW', 'decision': 'PENDING',
             'review_priority': 'P1_VERIFY_SINGLE_PIXEL_ARTWORK_AGAINST_MASTER'},
            {'review_id': 'WR-C', 'workstream': 'IDENTITY_VERIFICATION', 'decision': 'PENDING'},
            {'review_id': 'WR-B', 'workstream': 'ARTWORK_REVIEW', 'decision': 'APPROVED'},
        ]}
        before = repr(queue)
        report = artwork_review_batch(queue, 10)
        self.assertEqual(repr(queue), before)
        self.assertEqual(report['total_pending_artwork_tasks'], 2)
        self.assertEqual([x['review_id'] for x in report['items']], ['WR-A', 'WR-Z'])
        self.assertEqual(report['items'][1]['source_origins'], ['openatv8', 'vhannibal'])
        self.assertEqual(report['items'][1]['candidate_artworks'][0]['duplicate_sha256'], ['b'*64])
        self.assertEqual(report['items'][1]['master_locations'], [{'path': 'master.png'}])
        self.assertFalse(report['has_more'])

    def test_pagination_and_invalid_input(self):
        queue = {'items': [{'review_id': f'WR-{n:02}', 'decision': 'PENDING',
                            'workstream': 'ARTWORK_REVIEW'} for n in range(12)]}
        first = artwork_review_batch(queue)
        second = artwork_review_batch(queue, offset=10)
        self.assertEqual(first['returned'], 10)
        self.assertTrue(first['has_more'])
        self.assertEqual(second['returned'], 2)
        self.assertFalse(second['has_more'])
        for bad in (0, -1, 101, True):
            with self.assertRaises(ValueError):
                artwork_review_batch(queue, limit=bad)


if __name__ == '__main__':
    unittest.main()
