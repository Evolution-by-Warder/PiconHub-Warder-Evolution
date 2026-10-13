import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from factory_png_evidence import upload_png_evidence


class PngEvidenceRegression(unittest.TestCase):
    def test_raw_png_upload_is_disabled_with_or_without_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            opener = Mock(side_effect=AssertionError('network must not be used'))
            result = upload_png_evidence(directory, opener=opener)
        self.assertEqual(result['status'], 'disabled_by_privacy_policy')
        self.assertEqual(result['attempted'], 0)
        self.assertEqual(result['sent'], 0)
        opener.assert_not_called()

    def test_compatibility_entrypoint_never_reads_local_review_or_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'private-review.png'
            path.write_bytes(b'private source evidence')
            result = upload_png_evidence(directory, state_path=path)
            self.assertTrue(path.exists())
        self.assertEqual(result['status'], 'disabled_by_privacy_policy')
        self.assertEqual(result['attempted'], 0)


if __name__ == '__main__':
    unittest.main()
