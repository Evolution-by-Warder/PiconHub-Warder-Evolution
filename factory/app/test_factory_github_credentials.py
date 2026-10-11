import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from factory_github_credentials import load_token, save_token

class GitHubCredentialTests(unittest.TestCase):
    def test_missing_credentials_returns_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {'WARDER_DIAGNOSTICS_TOKEN': ''}):
                self.assertEqual(load_token(Path(directory) / 'missing.dpapi'), '')

    def test_env_override(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {'WARDER_DIAGNOSTICS_TOKEN': 'test-token'}):
                self.assertEqual(load_token(Path(directory) / 'missing.dpapi'), 'test-token')

    def test_reject_invalid_token_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'token.dpapi'
            with self.assertRaises(ValueError):
                save_token(path, 'not a token')
            self.assertFalse(path.exists())

if __name__ == '__main__':
    unittest.main()
