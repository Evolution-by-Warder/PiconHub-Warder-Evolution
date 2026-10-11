"""Exercise the real source-to-local-finalization backend with an isolated fixture.

This deliberately calls the production importer, renderer, registry classifier,
QA worker, review queue/ledger, and local finalizer. Network feeds and the live
production registry are not contacted or modified.
"""
import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

from engine import qa_png_task, render_png_task
from factory_finalization import finalize_new_candidates
from hardening import import_png_zip
from master_registry import classify_candidate, index_master_tree
from review_decisions import apply_decisions, record_decision
from review_queue import build_review_queue
from review_queue import save_review_queue
from workspace_paths import DIRECTORIES, read_only_preflight, workspace_paths

NEW_REF = '1_0_1_100_1_1_D72CF4_0_0_0'
EXISTING_REF = '1_0_1_101_1_1_D72CF4_0_0_0'


def make_logo(color):
    image = Image.new('RGBA', (220, 132), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((58, 42, 162, 90), radius=8, fill=color)
    draw.rectangle((78, 55, 142, 76), fill=(255, 255, 255, 255))
    return image


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class EndToEndPipelineTests(unittest.TestCase):
    def test_zip_to_review_and_safe_local_finalization(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'WARDER-PICON-FACTORY'
            for category, _purpose in DIRECTORIES:
                (root / category).mkdir(parents=True, exist_ok=True)
            paths = workspace_paths(root)
            before = read_only_preflight(root)
            self.assertTrue(before.ok, before.findings)
            inbox = paths['inbox']
            inbox.mkdir()
            archive = inbox / 'fixture.zip'
            new_png = make_logo((210, 25, 40, 255))
            changed_existing_png = make_logo((20, 75, 205, 255))
            master_png = make_logo((30, 150, 70, 255))
            with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
                for ref, image in ((NEW_REF, new_png), (EXISTING_REF, changed_existing_png)):
                    temp_png = paths['tools'] / (ref + '.png')
                    image.save(temp_png, format='PNG')
                    bundle.write(temp_png, ref + '.png')

            originals_root = paths['originals']
            imported = import_png_zip(archive, originals_root)
            self.assertEqual(imported['imported'], 2)
            extracted_root = originals_root / sha256(archive)
            source_paths = sorted(extracted_root.glob('*.png'))
            self.assertEqual(len(source_paths), 2)
            source_hashes = {path.stem: sha256(path) for path in source_paths}
            original_bytes = {path: path.read_bytes() for path in source_paths}

            master_root = paths['master_root'] / 'fixture-commit'
            master_path = master_root / 'picons' / '13.0e' / 'fixture' / 'transparent' / (EXISTING_REF + '.png')
            master_path.parent.mkdir(parents=True)
            master_png.save(master_path, format='PNG')
            master_digest = sha256(master_path)
            registry = index_master_tree(master_root)
            self.assertEqual(registry['service_count'], 1)

            output_root = paths['output']
            matches = []
            for path in source_paths:
                sha = source_hashes[path.stem]
                ok, created, error = render_png_task((str(path), str(output_root), sha))
                self.assertTrue(ok, error)
                self.assertEqual(created, 3)
                qa_sha, issues = qa_png_task((sha, str(output_root)))
                self.assertEqual(qa_sha, sha)
                self.assertEqual(issues, [])
                matches.append(classify_candidate(path, sha, registry))

            by_ref = {item['service_reference']: item for item in matches}
            self.assertEqual(by_ref[NEW_REF]['classification'], 'NEW')
            self.assertEqual(by_ref[EXISTING_REF]['classification'], 'REVIEW')

            queue = build_review_queue({}, {row['candidate_sha256']: row['candidate_source'] for row in matches},
                                      [], matches)
            review_items = [item for item in queue['items'] if item['candidate_identity'] == EXISTING_REF]
            self.assertEqual(len(review_items), 1)
            self.assertEqual(review_items[0]['decision'], 'PENDING')
            queue_path = paths['exceptions'] / 'review-queue-synthetic.json'
            save_review_queue(queue_path, queue)
            from review_queue import load_review_queue
            self.assertEqual(load_review_queue(queue_path)['count'], len(queue['items']))
            ledger_path = paths['ledger_path']
            record_decision(ledger_path, review_items[0], 'DEFERRED', 'Artwork differs from Warder Master.', True)
            resumed = apply_decisions(queue, ledger_path)
            resumed_item = next(item for item in resumed['items'] if item['candidate_identity'] == EXISTING_REF)
            self.assertEqual(resumed_item['decision'], 'DEFERRED')

            final_root = paths['final']
            finalized = finalize_new_candidates(
                matches, {}, output_root, final_root,
                verified_shas=set(source_hashes.values()))
            self.assertEqual(finalized['copied'], 3)
            self.assertEqual(finalized['conflicts'], 1)
            for variant in ('transparent', 'black', 'white'):
                target = final_root / 'NEW-CANDIDATES' / variant / (NEW_REF + '.png')
                with Image.open(target) as image:
                    self.assertEqual(image.size, (220, 132))
                    self.assertEqual(image.mode, 'RGBA')
                self.assertFalse((final_root / 'NEW-CANDIDATES' / variant / (EXISTING_REF + '.png')).exists())

            # Idempotent re-import and immutable source/master evidence.
            repeated = import_png_zip(archive, originals_root)
            self.assertEqual(repeated['imported'], 0)
            self.assertEqual(repeated['skipped'], 2)
            self.assertEqual({path: path.read_bytes() for path in source_paths}, original_bytes)
            self.assertEqual(sha256(master_path), master_digest)
            again = finalize_new_candidates(matches, {}, output_root, final_root,
                                            verified_shas=set(source_hashes.values()))
            self.assertEqual(again['copied'], 0)
            self.assertEqual(again['already_present'], 1)
            self.assertTrue(read_only_preflight(root).ok)


if __name__ == '__main__':
    unittest.main()
