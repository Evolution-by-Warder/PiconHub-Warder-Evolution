import unittest
from windows_exe_update import validate_manifest, version, REPO, install_verified_exe


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

    def test_atomic_install_preserves_previous(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            exe = Path(directory) / "WARDER-PICON-FACTORY.exe"
            exe.write_bytes(b"MZold")
            def downloader(info, target):
                target.write_bytes(b"MZnew")
            previous = install_verified_exe(manifest(), exe, downloader=downloader)
            self.assertEqual(exe.read_bytes(), b"MZnew")
            self.assertEqual(previous.read_bytes(), b"MZold")

    def test_failed_download_preserves_original(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            exe = Path(directory) / "WARDER-PICON-FACTORY.exe"
            exe.write_bytes(b"MZold")
            def downloader(info, target):
                target.write_bytes(b"partial")
                raise ValueError("corrupt")
            with self.assertRaises(ValueError):
                install_verified_exe(manifest(), exe, downloader=downloader)
            self.assertEqual(exe.read_bytes(), b"MZold")
            self.assertFalse(list(Path(directory).glob(".factory-download-*")))
