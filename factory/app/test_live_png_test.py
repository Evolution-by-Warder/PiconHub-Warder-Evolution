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


    def test_diverse_vhannibal_png_selection_from_actual_source_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            collisions = []
            for index, color in enumerate(((255, 0, 0, 255), (255, 0, 0, 255),
                                           (0, 255, 0, 255))):
                v = root / 'source-ingest' / 'originals' / 'vhannibal' / f'{index}.png'
                o = root / 'source-ingest' / 'originals' / 'openatv8' / f'{index}.png'
                v.parent.mkdir(parents=True, exist_ok=True)
                o.parent.mkdir(parents=True, exist_ok=True)
                Image.new('RGBA', (2, 2), color).save(v)
                Image.new('RGBA', (2, 2), (0, 0, 255, 255)).save(o)
                collisions.append({'candidate_service_ref': f'ref-{index}',
                                   'variants': [
                                       {'sha256': hashlib.sha256(v.read_bytes()).hexdigest(),
                                        'sources': [str(v)]},
                                       {'sha256': hashlib.sha256(o.read_bytes()).hexdigest(),
                                        'sources': [str(o)]}]})
            report = root / 'identity-collisions-test.json'
            report.write_text(json.dumps({'collisions': collisions}), encoding='utf-8')
            result = build_live_test(report, limit=2)
            with ZipFile(result['output']) as archive:
                cases = json.loads(archive.read('live-test-results.json'))['cases']
            self.assertEqual([c['service_reference'] for c in cases], ['ref-0', 'ref-2'])


if __name__ == '__main__':
    unittest.main()
