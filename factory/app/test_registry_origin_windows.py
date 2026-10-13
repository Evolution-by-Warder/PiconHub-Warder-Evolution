import unittest
import tempfile
import hashlib
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from openatv_pixel_evidence import attach_pixel_evidence
from registry_triage import origin_of, summarize_registry_matches, _openatv_provenance, identity_level_triage, _openatv_provenance, identity_level_triage


class WindowsSourceProvenanceTests(unittest.TestCase):
    def test_report_paths_under_originals_are_classified(self):
        self.assertEqual(origin_of(r'D:\WARDER-PICON-FACTORY\02-ORIGINALS\openatv8\schema-3\f044684c32c051eb692305411225715b0c362f0bcae05c70eb3d155c1932022e\picon\jsports1.png'), 'openatv8')
        self.assertEqual(origin_of(r'D:\WARDER-PICON-FACTORY\02-ORIGINALS\vhannibal\162117cf31343e0a153b4fd5297c6545b13a85833f1481d5d9e02fbcad9435de4\PICON Vhannibal Motor 11 ott 2026\1_0_1.png'), 'vhannibal')
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

    def test_schema3_requires_digest_in_verified_package_slot(self):
        known='f044684c32c051eb692305411225715b0c362f0bcae05c70eb3d155c1932022e'
        styles={known:('srp','dark')}
        self.assertEqual(_openatv_provenance(rf'D:\\WARDER-PICON-FACTORY\\02-ORIGINALS\\openatv8\\schema-3\\{known}\\picon\\jsports1.png',styles),('srp','dark'))
        self.assertEqual(_openatv_provenance(rf'D:\\WARDER-PICON-FACTORY\\02-ORIGINALS\\openatv8\\schema-3\\{known}x\\picon\\a.png',styles),('unknown','unknown'))
        self.assertEqual(_openatv_provenance(rf'D:\\WARDER-PICON-FACTORY\\02-ORIGINALS\\openatv8\\picon\\{known}.png',styles),('unknown','unknown'))
        self.assertEqual(_openatv_provenance(rf'D:\\WARDER-PICON-FACTORY\\02-ORIGINALS\\vhannibal\\schema-3\\{known}\\a.png',styles),('unknown','unknown'))

    def test_style_provenance_is_diagnostic_not_identity_approval(self):
        dark='f044684c32c051eb692305411225715b0c362f0bcae05c70eb3d155c1932022e'
        light='162117cf31343e0a153b4fd5297c6545b13a85833f1481d5d9e02fbcad9435de'
        styles={dark:('srp','dark'),light:('srp','light')}
        ref='1_0_1_2_3_4_5_6_7_8'
        rows=[
            {'service_reference':ref,'candidate_sha256':'a'*64,'candidate_source':rf'D:\\WARDER-PICON-FACTORY\\02-ORIGINALS\\openatv8\\schema-3\\{dark}\\picon\\{ref}.png','classification':'REVIEW'},
            {'service_reference':ref,'candidate_sha256':'b'*64,'candidate_source':rf'D:\\WARDER-PICON-FACTORY\\02-ORIGINALS\\openatv8\\schema-3\\{light}\\picon\\{ref}.png','classification':'REVIEW'},
        ]
        result=identity_level_triage(rows,package_styles=styles)
        self.assertEqual(result['style_diagnostic_counts'].get('CROSS_STYLE_DIFFERENCE_ONLY'),1)
        self.assertEqual(result['identity_approval'],'NONE')

    def test_source_counts_not_misclassified_as_local_inbox(self):
        rows = [{'candidate_source': r'D:\WARDER-PICON-FACTORY\02-ORIGINALS\OPENATV8\a.png', 'classification': 'REVIEW'},
                {'candidate_source': r'D:\WARDER-PICON-FACTORY\02-ORIGINALS\openatv8\b.png', 'classification': 'UNMAPPED'}]
        result = summarize_registry_matches(rows)
        self.assertEqual(result['openatv8']['REVIEW'], 1)
        self.assertEqual(result['openatv8']['UNMAPPED'], 1)
        self.assertNotIn('local-inbox', result)


if __name__ == '__main__':
    unittest.main()
