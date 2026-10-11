"""Regression checks for the release authority and safe update decisions."""
import unittest

from factory_auto_update import validate_manifest, version_tuple, REPO


class FactoryUpdateContractTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            "schema": 1,
            "version": "factory-v9.1.0",
            "url": f"https://github.com/{REPO}/releases/download/factory-v9.1.0/warder-picon-factory-9.1.0.zip",
            "size": 8192,
            "sha256": "a" * 64,
        }

    def test_newer_verified_release_is_selected(self):
        self.assertEqual(validate_manifest(self.manifest, (9, 0, 0))["version"], "factory-v9.1.0")

    def test_installed_or_older_release_is_ignored(self):
        self.assertIsNone(validate_manifest(self.manifest, (9, 1, 0)))
        self.assertIsNone(validate_manifest(self.manifest, (10, 0, 0)))

    def test_cross_repository_release_is_rejected(self):
        data = dict(self.manifest, url="https://github.com/other/repo/releases/download/factory-v9.1.0/warder-picon-factory-9.1.0.zip")
        with self.assertRaises(ValueError):
            validate_manifest(data, (9, 0, 0))

    def test_tampered_or_missing_integrity_is_rejected(self):
        for field, value in (("sha256", "invalid"), ("size", 0), ("size", True), ("schema", 2)):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    validate_manifest(dict(self.manifest, **{field: value}), (9, 0, 0))

    def test_versions_are_numeric_not_lexicographic(self):
        self.assertGreater(version_tuple("factory-v10.0.0"), version_tuple("factory-v9.99.99"))


    def test_release_url_requires_exact_versioned_asset(self):
        data = dict(self.manifest)
        data["url"] += "?download=1"
        with self.assertRaises(ValueError):
            validate_manifest(data, (9, 0, 0))

    def test_release_hash_rejects_uppercase_or_short_values(self):
        for digest in ("A" * 64, "a" * 63):
            with self.subTest(digest=digest):
                with self.assertRaises(ValueError):
                    validate_manifest(dict(self.manifest, sha256=digest), (9, 0, 0))


if __name__ == "__main__":
    unittest.main()
