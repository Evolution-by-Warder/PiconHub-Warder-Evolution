import unittest
from windows_exe_update import validate_manifest, version, REPO


def manifest(version_string="factory-v0.2.31"):
    return {"schema": 1, "version": version_string, "commit": "a" * 40,
            "url": "https://github.com/" + REPO + "/releases/download/" +
                   version_string + "/WARDER-PICON-FACTORY.exe",
            "size": 25000000, "sha256": "b" * 64}


class WindowsUpdateContract(unittest.TestCase):
    def test_newer_approved_release(self):
        self.assertEqual(validate_manifest(manifest(), "factory-v0.2.30")["version"],
                         "factory-v0.2.31")

    def test_same_version_different_commit_never_replaces(self):
        self.assertIsNone(validate_manifest(manifest("factory-v0.2.30"),
                                            "factory-v0.2.30", "c" * 40))

    def test_downgrade_blocked(self):
        self.assertIsNone(validate_manifest(manifest("factory-v0.2.29"),
                                            "factory-v0.2.30"))

    def test_reject_untrusted_url(self):
        obj = manifest()
        obj["url"] = "https://example.com/malware.exe"
        with self.assertRaises(ValueError):
            validate_manifest(obj, "factory-v0.2.30")

    def test_reject_invalid_hash(self):
        obj = manifest()
        obj["sha256"] = "invalid"
        with self.assertRaises(ValueError):
            validate_manifest(obj, "factory-v0.2.30")

    def test_reject_bool_size(self):
        obj = manifest()
        obj["size"] = True
        with self.assertRaises(ValueError):
            validate_manifest(obj, "factory-v0.2.30")

    def test_invalid_version(self):
        with self.assertRaises(ValueError):
            version("factory-v0.2.30-rc")
