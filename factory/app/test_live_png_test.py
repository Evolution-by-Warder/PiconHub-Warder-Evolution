import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from PIL import Image

from live_png_test import build_live_test


class LivePngTest(unittest.TestCase):
    def test_real_png_pixels_and_sha_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sources = []
            for name, color in [('openatv8', (255, 255, 255, 255)),
                                ('vhannibal', (0, 0, 0, 255))]:
                p = root / 'source-ingest' / 'originals' / name / 'logo.png'
                p.parent.mkdir(parents=True)
                Image.new('RGBA', (2, 2), color).save(p)
                sources.append((p, hashlib.sha256(p.read_bytes()).hexdigest()))
            report = root / 'identity-collisions-test.json'
            report.write_text(json.dumps({'collisions': [{
                'candidate_service_ref': 'test',
                'variants': [{'sha256': sha, 'sources': [str(path)]}
                             for path, sha in sources]
            }]}), encoding='utf-8')
            result = build_live_test(report)
            self.assertEqual(result['summary'], {'PIXEL_DIFFERENT': 1})
            with ZipFile(result['output']) as z:
                self.assertEqual(len([n for n in z.namelist() if n.endswith('.png')]), 2)
                details = json.loads(z.read('live-test-results.json'))
                self.assertEqual(details['cases'][0]['pixel_result'], 'PIXEL_DIFFERENT')
            sources[0][0].write_bytes(b'not-a-png')
            result = build_live_test(report)
            self.assertEqual(result['summary'], {'UNDETERMINED': 1})
            with ZipFile(result['output']) as z:
                details = json.loads(z.read('live-test-results.json'))
                self.assertEqual(details['cases'][0]['variants'][0]['sources'][0]['status'],
                                 'SHA_MISMATCH')


if __name__ == '__main__':
    unittest.main()
