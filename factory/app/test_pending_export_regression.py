"""Regression checks for pending export and review decisions."""
import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from factory_pending_export import export_pending


class PendingExportTests(unittest.TestCase):
    def test_requires_existing_queue(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(FileNotFoundError):
                export_pending(root, root, root / 'pending.zip')

    def test_does_not_overwrite_existing_archive(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'pending.zip'
            target.write_bytes(b'original')
            with patch('factory_pending_export.latest_review', return_value=root / 'review.json'):
                with patch('factory_pending_export.load_review_queue', return_value={'items': []}):
                    with self.assertRaises(FileExistsError):
                        export_pending(root, root, target)
            self.assertEqual(target.read_bytes(), b'original')

    def test_deferred_review_stays_in_export(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            item = {'review_id': 'WR-1234567890ABCDEF', 'decision': 'PENDING',
                    'sha256': 'a' * 64, 'original': ''}
            ledger = root / 'decisions.json'
            with patch('review_decisions.evidence_hash', return_value='unchanged'):
                ledger.write_text(json.dumps({'decisions': {item['review_id']: {
                    'decision': 'DEFERRED', 'evidence_hash': 'unchanged'}}}))
                with patch('factory_pending_export.latest_review', return_value=root / 'review.json'):
                    with patch('factory_pending_export.load_review_queue', return_value={'items': [item]}):
                        result = export_pending(root, root, root / 'pending.zip', ledger_path=ledger)
            self.assertEqual(result['tasks'], 1)

    def test_rejects_symlink_destination(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / 'pending.zip'
            try:
                target.symlink_to(root / 'other.zip')
            except (OSError, NotImplementedError):
                self.skipTest('Symlink creation unavailable')
            with patch('factory_pending_export.latest_review', return_value=root / 'review.json'):
                with patch('factory_pending_export.load_review_queue', return_value={'items': []}):
                    with self.assertRaises(ValueError):
                        export_pending(root, root, target)


if __name__ == '__main__':
    unittest.main()
