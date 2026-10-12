"""Regression tests for embedded artwork evidence, without a display server."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from review_gallery import evidence_digests, variant_paths, matches_evidence_sha, source_candidates


class GalleryEvidenceTests(unittest.TestCase):
    def test_grouped_evidence_and_variants_are_both_counted(self):
        first = "a" * 64
        second = "b" * 64
        item = {
            "sha256": None,
            "source_evidence": [{"sha256": first, "source": "first.png"}],
            "variants": [{"sha256": second, "sources": ["second.png"]}],
        }
        self.assertEqual(evidence_digests(item), [first, second])

    def test_output_variant_paths_are_derived_from_sha(self):
        digest = "a" * 64
        with tempfile.TemporaryDirectory() as folder:
            paths = variant_paths(Path(folder), {"sha256": digest})
            self.assertEqual(paths["transparent"], Path(folder) / digest[:2] / digest / "transparent.png")
            self.assertEqual(paths["black"], Path(folder) / digest[:2] / digest / "black.png")
            self.assertEqual(paths["white"], Path(folder) / digest[:2] / digest / "white.png")

    def test_uppercase_digest_normalizes_output_path(self):
        digest = 'A' * 64
        with tempfile.TemporaryDirectory() as folder:
            paths = variant_paths(folder, {'sha256': digest})
            self.assertEqual(paths['black'], Path(folder) / 'aa' / ('a' * 64) / 'black.png')

    def test_malformed_source_digest_is_not_a_path(self):
        with tempfile.TemporaryDirectory() as folder:
            item = {'source_evidence': [{'sha256': '../../escape'}]}
            self.assertEqual(evidence_digests(item), [])
            self.assertEqual(variant_paths(folder, item), {})

    def test_collision_source_candidates_are_digest_scoped(self):
        first, second = 'a' * 64, 'b' * 64
        item = {'sha256': first, 'original': 'first-original.png',
                'source_evidence': [{'sha256': first, 'source': 'first.png'}],
                'variants': [{'sha256': second, 'sources': ['second.png', 'second-alt.png']}]}
        self.assertEqual(source_candidates(item, first), ['first.png', 'first-original.png'])
        self.assertEqual(source_candidates(item, second), ['second.png', 'second-alt.png'])

    def test_source_candidates_ignore_malformed_sources(self):
        digest = 'a' * 64
        item = {'source_evidence': [{'sha256': digest, 'sources': 'not-a-list.png'}]}
        self.assertEqual(source_candidates(item, digest), [])

    def test_source_candidates_case_insensitive_digest(self):
        digest = 'a' * 64
        item = {'variants': [{'sha256': digest.upper(), 'sources': ['valid.png']}]}
        self.assertEqual(source_candidates(item, digest), ['valid.png'])

    def test_original_source_requires_matching_sha(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'source.png'
            path.write_bytes(b'original source bytes')
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertTrue(matches_evidence_sha(path, digest.upper()))
            self.assertFalse(matches_evidence_sha(path, '0' * 64))
            self.assertFalse(matches_evidence_sha(Path(folder) / 'missing.png', digest))

    def test_bad_digest_never_resolves_an_output_path(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(variant_paths(folder, {"sha256": "../bad"}), {})


if __name__ == "__main__":
    unittest.main()
