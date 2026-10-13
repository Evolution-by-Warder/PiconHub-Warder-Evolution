import unittest
from registry_triage import prioritized_new_reference_review_batches


def ref(n):
    return '_'.join([format(n, 'X')] + ['0'] * 9)


class PrioritizedNewReferenceTests(unittest.TestCase):
    def test_order_stability_and_no_approval(self):
        sha1, sha2 = 'a' * 64, 'b' * 64
        triage = {'single_artwork': [
            {'service_reference': ref(3), 'artwork_sha256': [sha1], 'source_origins': ['openatv8']},
            {'service_reference': ref(2), 'artwork_sha256': [sha1], 'source_origins': ['vhannibal', 'openatv8']}],
            'conflicting_artwork': [
            {'service_reference': ref(1), 'artwork_sha256': [sha1, sha2], 'source_origins': ['openatv8']}]}
        before = repr(triage)
        report = prioritized_new_reference_review_batches(triage, batch_size=2)
        self.assertEqual(repr(triage), before)
        self.assertEqual(report['total_references'], 3)
        self.assertEqual([i['priority'] for page in report['review_batches'] for i in page['items']],
                         ['P1_CROSS_SOURCE', 'P2_SINGLE_ARTWORK', 'P3_CONFLICT'])
        self.assertEqual([page['item_count'] for page in report['review_batches']], [2, 1])
        self.assertTrue(all(i['decision'] == 'PENDING_HUMAN_REVIEW'
                            for page in report['review_batches'] for i in page['items']))
        self.assertEqual(prioritized_new_reference_review_batches(triage, 1)['review_batches'][0]['items'][0]['review_item_id'],
                         report['review_batches'][0]['items'][0]['review_item_id'])

    def test_reject_corrupt_evidence(self):
        item = {'service_reference': ref(1), 'artwork_sha256': ['a' * 64], 'source_origins': []}
        for invalid in (0, True, 101):
            with self.assertRaises(ValueError):
                prioritized_new_reference_review_batches({'single_artwork': [item]}, invalid)
        with self.assertRaises(ValueError):
            prioritized_new_reference_review_batches({'single_artwork': [item, item]})
        with self.assertRaises(ValueError):
            prioritized_new_reference_review_batches({'single_artwork': [dict(item, artwork_sha256=['bad'])]})


if __name__ == '__main__':
    unittest.main()
