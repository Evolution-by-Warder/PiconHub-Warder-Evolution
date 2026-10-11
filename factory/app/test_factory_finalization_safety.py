"""Regression: local NEW candidate output is never an implicit approval."""
import hashlib
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from factory_finalization import finalize_new_candidates, STYLES


class FinalizationSafetyTests(unittest.TestCase):
    def test_idempotent_and_never_overwrites_existing_variant(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            work, final = base / "work", base / "final"
            sha = hashlib.sha256(b"immutable original").hexdigest()
            ref = "_".join(["1"] * 10)
            srcdir = work / sha[:2] / sha
            srcdir.mkdir(parents=True)
            for style in STYLES:
                Image.new("RGBA", (220, 132), (12, 30, 48, 255)).save(srcdir / (style + ".png"))
            matches = [{"service_reference": ref, "candidate_sha256": sha, "classification": "NEW"}]
            first = finalize_new_candidates(matches, {}, work, final, verified_shas={sha})
            self.assertEqual(first["copied"], 3)
            self.assertEqual(first["conflicts"], 0)
            second = finalize_new_candidates(matches, {}, work, final, verified_shas={sha})
            self.assertEqual(second["copied"], 0)
            self.assertEqual(second["already_present"], 1)
            protected = final / "NEW-CANDIDATES" / "black" / (ref + ".png")
            protected.write_bytes(b"protected local file")
            third = finalize_new_candidates(matches, {}, work, final, verified_shas={sha})
            self.assertEqual(third["copied"], 0)
            self.assertEqual(third["conflicts"], 1)
            self.assertEqual(protected.read_bytes(), b"protected local file")

    def test_missing_qa_is_not_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            sha = hashlib.sha256(b"unverified").hexdigest()
            ref = "_".join(["A"] * 10)
            result = finalize_new_candidates(
                [{"service_reference": ref, "candidate_sha256": sha, "classification": "NEW"}],
                {}, Path(temp) / "work", Path(temp) / "final", verified_shas=set())
            self.assertEqual(result["qa_blocked"], 1)
            self.assertEqual(result["copied"], 0)
            self.assertFalse((Path(temp) / "final").exists())


if __name__ == "__main__":
    unittest.main()
