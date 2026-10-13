import unittest
import tempfile
import hashlib
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from openatv_pixel_evidence import attach_pixel_evidence
from registry_triage import origin_of, summarize_registry_matches


class WindowsSourceProvenanceTests(unittest.TestCase):
    def test_report_paths_under_originals_are_classified(self):
        self.assertEqual(origin_of(r'D:\WARDER-PICON-FACTORY\02-ORIGINALS\openatv8\schema-3\f044684c32c051eb692305411225715b0c362f0bcae05c70eb3d155c1932022e\picon\jsports1.png'), 'openatv8')
        self.assertEqual(origin_of(r'D:\WARDER-PICON-FACTORY\02-ORIGINALS\vhannibal\d0c29c6bdbe7b7ff641443dba2257ec2902b835182d8fb1d24a392155aa28bb4\PICON Vhannibal Motor 11 ott 2026\1_0_1.png'), 'vhannibal')
        self.assertEqual(origin_of(r'D:\WARDER-PICON-FACTORY\02-ORIGINALS\archives\PiconHub-Warder-Evolution.zip\picons\1.png'), 'piconhub')

    def test_old_ingest_and_local_inbox_layouts_remain_supported(self):
        self.assertEqual(origin_of(r'D:\WARDER-PICON-FACTORY\SOURCE-INGEST\ORIGINALS\OpenATV8\picons\1.png'), 'openatv8')
        self.assertEqual(origin_of(r'D:\WARDER-PICON-FACTORY\source-ingest\Originals\VHANNIBAL\p.png'), 'vhannibal')
        self.assertEqual(origin_of(r'D:\WARDER-PICON-FACTORY\01-SOURCES\LOCAL-INBOX\p.png'), 'local-inbox')

    def test_slash_styles_case_and_archived_paths(self):
        self.assertEqual(origin_of('d:/warder-picon-factory/02-originals/OPENATV8/archives/pack.zip/picon/a.png'), 'openatv8')
        self.assertEqual(origin_of(r'D:\WARDER-PICON-FACTORY\02-ORIGINALS\PICONHUB-WARDER-EVOLUTION\archive\p.png'), 'piconhub')

    def test_unknown_provenance_is_never_local_or_verified(self):
        self.assertEqual(origin_of(r'D:\WARDER-PICON-FACTORY\02-ORIGINALS\unrecognized-provider\a.png'), 'unknown')
        self.assertEqual(origin_of(r'C:\Users\PC\Downloads\openatv8-logo.png'), 'unknown')

    def test_pixel_evidence_reads_real_originals_and_reuses_duplicate_sha(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / '02-ORIGINALS' / 'OpenATV8' / 'schema-3' / 'archive' / 'picon' / 'one.png'
            source.parent.mkdir(parents=True)
            Image.new('RGBA', (220, 132), (18, 36, 54, 255)).save(source)
            sha = hashlib.sha256(source.read_bytes()).hexdigest()
            rows = [
                {'classification': 'UNMAPPED', 'candidate_source': str(source), 'candidate_sha256': sha},
                {'classification': 'UNMAPPED', 'candidate_source': str(source), 'candidate_sha256': sha},
            ]
            with patch('openatv_pixel_evidence._digest', wraps=__import__('openatv_pixel_evidence')._digest) as digest:
                counts = attach_pixel_evidence(rows, {'services': {}}, root, root / 'pixel-cache.json')
            self.assertEqual(digest.call_count, 1)
            self.assertEqual(counts['NO_PIXEL_EXACT_MASTER_ARTWORK'], 2)
            self.assertTrue(all(row['artwork_evidence']['identity_verified'] is False for row in rows))

    def test_source_counts_not_misclassified_as_local_inbox(self):
        rows = [{'candidate_source': r'D:\WARDER-PICON-FACTORY\02-ORIGINALS\OPENATV8\a.png', 'classification': 'REVIEW'},
                {'candidate_source': r'D:\WARDER-PICON-FACTORY\02-ORIGINALS\openatv8\b.png', 'classification': 'UNMAPPED'}]
        result = summarize_registry_matches(rows)
        self.assertEqual(result['openatv8']['REVIEW'], 1)
        self.assertEqual(result['openatv8']['UNMAPPED'], 1)
        self.assertNotIn('local-inbox', result)


if __name__ == '__main__':
    unittest.main()
