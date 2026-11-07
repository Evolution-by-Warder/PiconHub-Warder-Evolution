"""Regression tests for shallow Git cache selection, using actual Git objects."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import reproduce_on_github as runner


class SingletonSourceCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='warder-cache-test-')
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.command('init', '--quiet')
        self.raw = b'Immutable pinned renderer fixture.\n'
        self.blob = self.command('hash-object', '-w', '--stdin', input=self.raw).decode().strip()
        tree = self.command('mktree', input=('100644 blob ' + self.blob + '\tfixture.txt\n').encode()).decode().strip()
        env = dict(os.environ, GIT_AUTHOR_NAME='Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
                   GIT_COMMITTER_NAME='Fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid')
        self.commit = subprocess.run(['git', '-C', str(self.repo), 'commit-tree', tree], input=b'Pinned fixture\n',
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, env=env).stdout.decode().strip()
        self.resource = dict(commit=self.commit, git_blob=self.blob, path='fixture.txt',
                             sha256=hashlib.sha256(self.raw).hexdigest(), bytes=len(self.raw))

    def command(self, *args, input=None):
        return subprocess.run(['git', '-C', str(self.repo), *args], input=input,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout

    def test_blob_present_without_pinned_commit_is_cache_miss(self):
        resource = dict(self.resource, commit='1' * 40)
        self.assertEqual(self.command('cat-file', '-t', self.blob).strip(), b'blob')
        self.assertFalse(runner.cache_resource_available(self.repo, resource))

    def test_matching_pinned_commit_and_blob_are_read_exactly(self):
        self.assertTrue(runner.cache_resource_available(self.repo, self.resource))
        self.assertEqual(runner.read_resource(self.repo, self.resource), self.raw)

    def test_pinned_commit_without_expected_blob_is_cache_miss(self):
        self.assertFalse(runner.cache_resource_available(self.repo, dict(self.resource, git_blob='2' * 40)))

    def test_existing_blob_at_wrong_pinned_path_fails_closed(self):
        resource = dict(self.resource, path='missing.txt')
        self.assertTrue(runner.cache_resource_available(self.repo, resource))
        with self.assertRaisesRegex(ValueError, 'Pinned path/blob mismatch'):
            runner.read_resource(self.repo, resource)

    def test_different_present_blob_fails_pinned_tree_path_check(self):
        other = self.command('hash-object', '-w', '--stdin', input=b'Other present object.\n').decode().strip()
        resource = dict(self.resource, git_blob=other)
        self.assertTrue(runner.cache_resource_available(self.repo, resource))
        with self.assertRaisesRegex(ValueError, 'Pinned path/blob mismatch'):
            runner.read_resource(self.repo, resource)

    def test_matching_git_objects_with_corrupt_sha_metadata_fail_closed(self):
        resource = dict(self.resource, sha256='0' * 64)
        self.assertTrue(runner.cache_resource_available(self.repo, resource))
        with self.assertRaisesRegex(ValueError, 'Pinned SHA256/size mismatch'):
            runner.read_resource(self.repo, resource)


if __name__ == '__main__':
    unittest.main()
