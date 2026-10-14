import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from windows_factory_update import UpdateError, install_update, installed_version


class StandaloneUpdaterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "WARDER-PICON-FACTORY"
        for name in ("00-STATE", "01-SOURCES", "02-ORIGINALS", "03-REGISTRY", "04-WORK",
                     "05-QA", "06-OUTPUT", "07-PUBLISH-STAGING", "08-REPORTS", "09-LOGS",
                     "10-TOOLS", "11-APP", "12-ARCHIVE"):
            (self.root / name).mkdir(parents=True)
        self.app = self.root / "11-APP" / "WARDER-PICON-FACTORY"
        self.app.mkdir()
        self.installed = self.app / "WARDER-PICON-FACTORY.exe"
        self.installed.write_bytes(b"MZ" + b"old factory executable".ljust(1100, b"!"))
        (self.app / ".factory-installed-version.json").write_text(
            json.dumps({"version": "factory-v0.2.60",
                        "commit": "58f047f688b925f5c912a01c931f6790b67f2ed9",
                        "sha256": hashlib.sha256(self.installed.read_bytes()).hexdigest(),
                        "bytes": self.installed.stat().st_size}), encoding="utf-8")
        self.payload = Path(self.temp.name) / "new.exe"
        self.payload.write_bytes(b"MZ" + b"new factory executable".ljust(1100, b"#"))
        self.build = {"version": "factory-v0.2.61", "commit": "c" * 40,
                      "ancestor_commits": ["58f047f688b925f5c912a01c931f6790b67f2ed9"],
                      "sha256": hashlib.sha256(self.payload.read_bytes()).hexdigest(),
                      "bytes": self.payload.stat().st_size}
        self.preserved = self.root / "02-ORIGINALS" / "original.png"
        self.preserved.write_bytes(b"source-original")

    def tearDown(self):
        self.temp.cleanup()

    def test_verified_update_replaces_only_exe_and_version_marker(self):
        before = hashlib.sha256(self.preserved.read_bytes()).hexdigest()
        result = install_update(self.root, self.payload, self.build, process_check=lambda: False)
        self.assertEqual(result["status"], "UPDATED")
        self.assertEqual(result["version"], "factory-v0.2.61")
        self.assertEqual(result["commit"], "c" * 40)
        self.assertEqual(self.installed.read_bytes(), self.payload.read_bytes())
        self.assertEqual(json.loads((self.app / ".factory-installed-version.json").read_text())["version"],
                         "factory-v0.2.61")
        self.assertEqual(hashlib.sha256(self.preserved.read_bytes()).hexdigest(), before)
        self.assertEqual(Path(result["previous_executable"]).read_bytes(), b"MZ" + b"old factory executable".ljust(1100, b"!"))

    def test_startup_failure_restores_old_exe_and_version(self):
        original_exe = self.installed.read_bytes()
        original_marker = (self.app / ".factory-installed-version.json").read_bytes()
        with self.assertRaisesRegex(UpdateError, "startup verification"):
            install_update(self.root, self.payload, self.build, process_check=lambda: False,
                           launch_check=lambda _path: False)
        self.assertEqual(self.installed.read_bytes(), original_exe)
        self.assertEqual((self.app / ".factory-installed-version.json").read_bytes(), original_marker)

    def test_bad_payload_and_non_newer_version_are_rejected_before_write(self):
        original = self.installed.read_bytes()
        invalid = dict(self.build, sha256="0" * 64)
        with self.assertRaisesRegex(UpdateError, "SHA-256"):
            install_update(self.root, self.payload, invalid, process_check=lambda: False)
        not_newer = dict(self.build, version="factory-v0.2.59")
        with self.assertRaisesRegex(UpdateError, "older than installed"):
            install_update(self.root, self.payload, not_newer, process_check=lambda: False)
        self.assertEqual(self.installed.read_bytes(), original)

    def test_same_version_update_requires_proven_descendant_commit(self):
        descendant = dict(self.build, version="factory-v0.2.60")
        result = install_update(self.root, self.payload, descendant, process_check=lambda: False)
        self.assertEqual(result["status"], "UPDATED")
        self.assertEqual(result["version"], "factory-v0.2.60")

    def test_same_version_unrelated_commit_is_rejected(self):
        unrelated = dict(self.build, version="factory-v0.2.60", ancestor_commits=[])
        original = self.installed.read_bytes()
        with self.assertRaisesRegex(UpdateError, "not a verified newer build"):
            install_update(self.root, self.payload, unrelated, process_check=lambda: False)
        self.assertEqual(self.installed.read_bytes(), original)

    def test_same_commit_with_different_payload_is_rejected(self):
        altered = dict(self.build, version="factory-v0.2.60",
                       commit="58f047f688b925f5c912a01c931f6790b67f2ed9",
                       ancestor_commits=[])
        with self.assertRaisesRegex(UpdateError, "not a verified newer build"):
            install_update(self.root, self.payload, altered, process_check=lambda: False)

    def test_same_version_uses_installed_payload_hash_to_trust_commit_marker(self):
        marker = self.app / ".factory-installed-version.json"
        data = json.loads(marker.read_text(encoding="utf-8"))
        data["sha256"] = "0" * 64
        marker.write_text(json.dumps(data), encoding="utf-8")
        original = self.installed.read_bytes()
        with self.assertRaisesRegex(UpdateError, "does not match its version marker"):
            install_update(self.root, self.payload,
                           dict(self.build, version="factory-v0.2.60"),
                           process_check=lambda: False)
        self.assertEqual(self.installed.read_bytes(), original)

    def test_running_factory_blocks_without_modifying_install(self):
        original = self.installed.read_bytes()
        with self.assertRaisesRegex(UpdateError, "Close WARDER"):
            install_update(self.root, self.payload, self.build, process_check=lambda: True)
        self.assertEqual(self.installed.read_bytes(), original)

    def test_older_one_file_install_can_be_version_checked_without_sidecar(self):
        marker = self.app / ".factory-installed-version.json"
        marker.unlink()
        self.installed.write_bytes(b"MZ" + b"factory-v0.2.59" + b"old build".ljust(1100, b"!"))
        self.assertEqual(installed_version(self.installed, marker), "factory-v0.2.59")


if __name__ == "__main__":
    unittest.main()
