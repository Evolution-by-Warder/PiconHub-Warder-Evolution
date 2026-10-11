"""Regression tests for end-of-run source rehashing."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from artifact_audit import audit_artifacts


class SourceIntegrityTests(unittest.TestCase):
    def test_source_changed_after_initial_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'source.png'
            source.write_bytes(b'original source bytes')
            original_sha = hashlib.sha256(source.read_bytes()).hexdigest()
            source.write_bytes(b'modified source bytes')
            result = audit_artifacts({original_sha: source}, Path(temp) / 'work',
                                     source_hashes_verified=False)
            self.assertTrue(any(issue['reason'] == 'SOURCE_CHANGED'
                                and issue['sha256'] == original_sha
                                for issue in result['issues']))

    def test_missing_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'missing.png'
            sha = hashlib.sha256(b'missing').hexdigest()
            result = audit_artifacts({sha: source}, Path(temp) / 'work',
                                     source_hashes_verified=False)
            self.assertTrue(any(issue['reason'] == 'SOURCE_UNREADABLE'
                                for issue in result['issues']))
