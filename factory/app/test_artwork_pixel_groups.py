import tempfile
import unittest
from pathlib import Path
from PIL import Image
from artwork_pixel_groups import candidate_pixel_digests
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
