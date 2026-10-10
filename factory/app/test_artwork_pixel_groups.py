import tempfile
import unittest
from pathlib import Path
from PIL import Image
from artwork_pixel_groups import candidate_pixel_digests, attach_master_pixel_comparisons, master_artwork_pixel_digests
from review_queue import build_review_queue


class PixelGroupingEvidenceTests(unittest.TestCase):
    def test_different_png_hashes_identical_rgba_are_evidence_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            shas=['a'*64,'b'*64]
            for sha in shas:
                path=root/sha[:2]/sha/'transparent.png'
                path.parent.mkdir(parents=True)
                Image.new('RGBA',(220,132),(30,40,190,255)).save(path)
            matches=[{'classification':'REVIEW','reason':'EXISTING_SERVICE_DIFFERENT_ART',
                      'candidate_sha256':sha,'candidate_source':f'/source-ingest/originals/openatv8/{sha}.png',
                      'service_reference':'ref'} for sha in shas]
            digests=candidate_pixel_digests(matches,root)
            self.assertEqual(digests[shas[0]],digests[shas[1]])
            queue=build_review_queue({}, {}, [], matches, pixel_digests=digests)
            self.assertEqual(queue['count'],1)
            self.assertEqual(queue['items'][0]['decision'],'PENDING')
            self.assertEqual(queue['items'][0]['pixel_equivalence'],'EXACT_RGBA_IDENTICAL')
            self.assertEqual(queue['consolidation']['pixel_equivalent_review_groups'],1)

    def test_master_pixel_index_reuses_existing_cache_and_is_service_scoped(self):
        import json
        from openatv_pixel_evidence import _digest
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            png = root / 'master.png'
            Image.new('RGBA', (220, 132), (12, 34, 56, 255)).save(png)
            cache = root / 'pixel-cache.json'
            registry = {'services': {'ref-a': [{'style': 'transparent', 'path': 'master.png'}],
                                     'ref-b': [{'style': 'black', 'path': 'master.png'}]}}
            expected = _digest(png)
            first = master_artwork_pixel_digests(registry, root, cache)
            second = master_artwork_pixel_digests(registry, root, cache)
            self.assertEqual(first, second)
            self.assertEqual(first, {'ref-a': [expected]})
            self.assertIn(str(png.resolve()), json.loads(cache.read_text(encoding='utf-8')))

    def test_corrupt_cached_digest_is_recomputed(self):
        import json
        from openatv_pixel_evidence import _digest
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            png = root / 'master.png'
            Image.new('RGBA', (220, 132), (12, 34, 56, 255)).save(png)
            stat = png.stat()
            cache = root / 'pixel-cache.json'
            cache.write_text(json.dumps({str(png.resolve()): {
                'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns,
                'pixel_sha256': None}}), encoding='utf-8')
            registry = {'services': {'ref': [{'style': 'transparent', 'path': 'master.png'}]}}
            self.assertEqual(master_artwork_pixel_digests(registry, root, cache),
                             {'ref': [_digest(png)]})
            self.assertEqual(json.loads(cache.read_text(encoding='utf-8'))[str(png.resolve())]['pixel_sha256'],
                             _digest(png))

    def test_master_comparison_is_service_scoped_and_read_only(self):
        queue = {'items': [
            {'workstream': 'ARTWORK_REVIEW', 'decision': 'PENDING',
             'candidate_identity': 'service-a', 'artwork_review_units': [
                 {'pixel_sha256': 'same', 'representative_sha256': 'a'},
                 {'pixel_sha256': 'other', 'representative_sha256': 'b'}]},
            {'workstream': 'ARTWORK_REVIEW', 'decision': 'PENDING',
             'candidate_identity': 'service-b', 'artwork_review_units': [
                 {'pixel_sha256': 'same', 'representative_sha256': 'c'}]},
        ]}
        counts = attach_master_pixel_comparisons(queue, {'service-a': ['same'], 'service-b': ['different']}, {})
        self.assertEqual(counts['PIXEL_EXACT_SAME_SERVICE_MASTER'], 1)
        self.assertEqual(counts['NO_PIXEL_EXACT_SAME_SERVICE_MASTER'], 2)
        self.assertTrue(all(item['decision'] == 'PENDING' for item in queue['items']))

    def test_master_exact_review_is_still_pending(self):
        queue = {'items': [
            {'workstream': 'ARTWORK_REVIEW', 'decision': 'PENDING',
             'candidate_identity': 'service-a', 'artwork_review_units': [
                 {'pixel_sha256': 'same', 'representative_sha256': 'a'},
                 {'pixel_sha256': 'same', 'representative_sha256': 'b'}]}
        ]}
        attach_master_pixel_comparisons(queue, {'service-a': ['same']}, {})
        item = queue['items'][0]
        self.assertEqual(item['master_pixel_evidence'], 'ALL_REVIEW_UNITS_EXACT_SAME_SERVICE_MASTER')
        self.assertEqual(item['decision'], 'PENDING')

    def test_invalid_sha_types_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            matches = [
                {'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
                 'candidate_sha256': ['bad']},
                {'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
                 'candidate_sha256': 123},
                {'classification': 'REVIEW', 'reason': 'EXISTING_SERVICE_DIFFERENT_ART',
                 'candidate_sha256': 'not-a-sha'},
            ]
            self.assertEqual(candidate_pixel_digests(matches, Path(folder)), {})

    def test_distinct_pixels_not_mislabeled(self):
        matches=[{'classification':'REVIEW','reason':'EXISTING_SERVICE_DIFFERENT_ART',
                  'candidate_sha256':sha,'candidate_source':sha,'service_reference':'ref'} for sha in ('a'*64,'b'*64)]
        queue=build_review_queue({}, {}, [], matches, pixel_digests={'a'*64:'x','b'*64:'y'})
        self.assertNotIn('pixel_equivalence',queue['items'][0])
        self.assertEqual(queue['count'],1)

if __name__=='__main__':
    unittest.main()
