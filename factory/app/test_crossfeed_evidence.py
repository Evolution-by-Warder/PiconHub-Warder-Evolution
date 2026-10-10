import unittest
from review_queue import build_review_queue


class CrossFeedEvidenceTests(unittest.TestCase):
    def test_same_hash_from_two_sources_retains_both_origins(self):
        sha = 'a' * 64
        ref = '1_0_1_2_3_4_5_6_7_8'
        def match(origin):
            return {'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
                    'service_reference': ref, 'candidate_sha256': sha,
                    'candidate_source': 'C:/work/source-ingest/originals/' + origin + '/logo.png'}
        queue = build_review_queue({}, {}, [], [match('openatv8'), match('vhannibal')])
        self.assertEqual(queue['count'], 1)
        item = queue['items'][0]
        self.assertEqual(item['source_origins'], ['openatv8', 'vhannibal'])
        self.assertEqual(len(item['source_evidence']), 2)
        self.assertEqual(queue['consolidation']['registry_source_observations'], 2)
        self.assertEqual(queue['consolidation']['registry_duplicate_file_observations'], 1)
        self.assertEqual(queue['consolidation']['review_tasks_avoided'], 0)

    def test_different_hashes_keep_both_origins_and_graphics(self):
        ref = '1_0_1_2_3_4_5_6_7_8'
        rows = [
            {'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
             'service_reference': ref, 'candidate_sha256': sha * 64,
             'candidate_source': 'C:/work/source-ingest/originals/' + origin + '/logo.png'}
            for sha, origin in [('a', 'openatv8'), ('b', 'vhannibal')]
        ]
        queue = build_review_queue({}, {}, [], rows)
        self.assertEqual(queue['count'], 1)
        item = queue['items'][0]
        self.assertEqual(item['distinct_sha256'], 2)
        self.assertEqual(item['source_origins'], ['openatv8', 'vhannibal'])
        self.assertEqual(queue['consolidation']['review_tasks_avoided'], 1)


if __name__ == '__main__':
    unittest.main()
