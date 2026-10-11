"""Regression checks for pending export and review decisions."""
import unittest
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
