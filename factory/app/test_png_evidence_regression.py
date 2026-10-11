import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from factory_png_evidence import upload_png_evidence

class PngEvidenceRegression(unittest.TestCase):
    def test_no_token_does_not_upload(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict('os.environ', {'WARDER_DIAGNOSTICS_TOKEN': ''}):
                result = upload_png_evidence(directory)
            self.assertEqual(result['status'], 'not_configured')
            self.assertEqual(result['attempted'], 0)

    def test_missing_review_is_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict('os.environ', {'WARDER_DIAGNOSTICS_TOKEN': 'test'}):
                result = upload_png_evidence(directory)
            self.assertEqual(result['status'], 'no_review')
            self.assertEqual(result['sent'], 0)

if __name__ == '__main__':
    unittest.main()
