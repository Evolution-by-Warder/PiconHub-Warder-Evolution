"""Focused safety tests for the local PNG finalizer."""
import tempfile
import unittest
from pathlib import Path
from PIL import Image
from factory_finalization import finalize_new_candidates

SHA = 'a' * 64
REF = '1_2_3_4_5_6_7_8_9_A'


class FinalizationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name) / 'work'
        self.final = Path(temp.name) / 'final'
        folder = self.work / SHA[:2] / SHA
        folder.mkdir(parents=True)
        for name in ('transparent', 'black', 'white'):
            Image.new('RGBA', (220, 132), (50, 90, 150, 255)).save(folder / (name + '.png'))

    def row(self, sha=SHA):
        return dict(service_reference=REF, candidate_sha256=sha, classification='NEW')

    def test_three_variants(self):
        result = finalize_new_candidates([self.row()], {}, self.work, self.final, verified_shas={SHA})
        self.assertEqual(result['copied'], 3)

    def test_conflict(self):
        result = finalize_new_candidates([self.row(), self.row('b' * 64)], {}, self.work, self.final)
        self.assertEqual(result['copied'], 0)

    def test_qa_gate(self):
        result = finalize_new_candidates([self.row()], {SHA: ['QA_ERROR']}, self.work, self.final)
        self.assertEqual(result['copied'], 0)

    def test_no_overwrite(self):
        target = self.final / 'NEW-CANDIDATES' / 'transparent' / (REF + '.png')
        target.parent.mkdir(parents=True)
        target.write_bytes(b'preserve')
        result = finalize_new_candidates([self.row()], {}, self.work, self.final, verified_shas={SHA})
        self.assertEqual(result['copied'], 0)
        self.assertEqual(target.read_bytes(), b'preserve')

    def test_missing_qa_proof_is_blocked(self):
        result = finalize_new_candidates([self.row()], {}, self.work, self.final)
        self.assertEqual(result['copied'], 0)

    def test_repeat_is_idempotent(self):
        first = finalize_new_candidates([self.row()], {}, self.work, self.final, verified_shas={SHA})
        second = finalize_new_candidates([self.row()], {}, self.work, self.final, verified_shas={SHA})
        self.assertEqual(first['copied'], 3)
        self.assertEqual(second['copied'], 0)
        self.assertEqual(second['already_present'], 1)

    def test_invalid_png_blocks_entire_trio(self):
        source = self.work / SHA[:2] / SHA / 'white.png'
        source.write_bytes(b'not a PNG')
        result = finalize_new_candidates([self.row()], {}, self.work, self.final, verified_shas={SHA})
        self.assertEqual(result['copied'], 0)
        self.assertEqual(len(list(self.final.rglob('*.png'))), 0)

    def test_existing_master_identity_is_blocked(self):
        row = self.row()
        row['classification'] = 'REVIEW'
        result = finalize_new_candidates([row], {}, self.work, self.final, verified_shas={SHA})
        self.assertEqual(result['copied'], 0)
