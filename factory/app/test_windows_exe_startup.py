import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import windows_exe_startup


class WindowsStartupTests(unittest.TestCase):
    def test_missing_exe_does_not_touch_workspace(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(windows_exe_startup.run(root / "WARDER-PICON-FACTORY.exe",
                                                     root / "version.json"), "NO_INSTALLED_EXE")

    def test_no_version_metadata_preserves_exe(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            exe = root / "WARDER-PICON-FACTORY.exe"
            exe.write_bytes(b"MZexisting")
            with patch.object(windows_exe_startup, "identify_legacy_exe", return_value=None):
                self.assertEqual(windows_exe_startup.run(exe, root / "version.json"),
                                 "NO_VERSION_METADATA")
            self.assertEqual(exe.read_bytes(), b"MZexisting")

    def test_up_to_date_never_replaces_exe(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            exe = root / "WARDER-PICON-FACTORY.exe"
            exe.write_bytes(b"MZexisting")
            meta = root / "version.json"
            meta.write_text('{"version":"factory-v0.2.31","commit":"abc"}')
            with patch.object(windows_exe_startup, "read_manifest",
                              return_value={"schema":2,"version":"factory-v0.2.31",
                                            "commit":"a"*40,"assets":{}}):
                self.assertEqual(windows_exe_startup.run(exe, meta), "UP_TO_DATE")
            self.assertEqual(exe.read_bytes(), b"MZexisting")

    def test_verified_build_identity_bootstraps_without_metadata(self):
        import hashlib
        import json
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            exe = root / "WARDER-PICON-FACTORY.exe"
            payload = b"MZverified-build"
            exe.write_bytes(payload)
            (root / "BUILD-IDENTITY.json").write_text(json.dumps({
                "version": "factory-v0.2.33", "commit": "a"*40,
                "filename": exe.name, "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "smoke_test": "passed"
            }))
            with patch.object(windows_exe_startup, "read_manifest",
                              return_value={"schema": 2, "version": "factory-v0.2.33",
                                            "commit": "a"*40, "assets": {}}):
                self.assertEqual(windows_exe_startup.run(exe, root / "version.json"),
                                 "UP_TO_DATE")

    def test_tampered_build_identity_refuses_bootstrap(self):
        import json
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            exe = root / "WARDER-PICON-FACTORY.exe"
            exe.write_bytes(b"MZtampered")
            (root / "BUILD-IDENTITY.json").write_text(json.dumps({
                "version": "factory-v0.2.33", "commit": "a"*40,
                "filename": exe.name, "bytes": exe.stat().st_size,
                "sha256": "0"*64, "smoke_test": "passed"
            }))
            self.assertEqual(windows_exe_startup.run(exe, root / "version.json"),
                             "NO_VERSION_METADATA")

    def test_legacy_release_digest_identification(self):
        import hashlib
        import json
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            exe = root / "WARDER-PICON-FACTORY.exe"
            exe.write_bytes(b"MZlegacy-installed")
            catalog = [{"tag_name": "factory-v0.2.36", "target_commitish": "a"*40,
                        "assets": [{"name": exe.name, "size": exe.stat().st_size,
                                    "digest": "sha256:" + hashlib.sha256(exe.read_bytes()).hexdigest()}]}]
            response = MagicMock()
            response.geturl.return_value = (
                "https://api.github.com/repos/Evolution-by-Warder/PiconHub-Warder-Evolution/releases?per_page=100")
            response.read.return_value = json.dumps(catalog).encode()
            response.__enter__.return_value = response
            with patch("urllib.request.urlopen", return_value=response), patch.object(
                    windows_exe_startup, "read_manifest",
                    return_value={"schema": 2, "version": "factory-v0.2.36",
                                  "commit": "a"*40, "assets": {}}):
                self.assertEqual(windows_exe_startup.run(exe, root / "version.json"), "UP_TO_DATE")

    def test_unknown_legacy_digest_preserves_exe(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            exe = root / "WARDER-PICON-FACTORY.exe"
            exe.write_bytes(b"MZunknown-legacy")
            with patch.object(windows_exe_startup, "identify_legacy_exe", return_value=None):
                self.assertEqual(windows_exe_startup.run(exe, root / "version.json"),
                                 "NO_VERSION_METADATA")
            self.assertEqual(exe.read_bytes(), b"MZunknown-legacy")
