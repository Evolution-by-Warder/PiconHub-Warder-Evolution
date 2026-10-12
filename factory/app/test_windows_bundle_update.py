import tempfile
import unittest
from pathlib import Path

from windows_exe_update import COMPONENTS, validate_bundle_manifest, install_verified_bundle


class BundleUpdateTests(unittest.TestCase):
    def bundle(self):
        version = "factory-v0.2.32"
        return {"schema": 2, "version": version, "commit": "a"*40,
                "assets": {name: {"url": "https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/releases/download/" + version + "/" + name,
                                  "size": 5, "sha256": "b"*64} for name in COMPONENTS}}

    def test_reject_incomplete_bundle(self):
        manifest = self.bundle()
        del manifest["assets"]["windows_exe_update.py"]
        with self.assertRaises(ValueError):
            validate_bundle_manifest(manifest, "factory-v0.2.31")

    def test_valid_complete_bundle(self):
        self.assertEqual(len(validate_bundle_manifest(self.bundle(), "factory-v0.2.31")["assets"]), 5)

    def test_failed_download_never_changes_components(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for name in COMPONENTS:
                (directory/name).write_bytes(b"original")
            def broken(info, target):
                if "windows_exe_update.py" in str(target):
                    raise ValueError("bad download")
                target.write_bytes(b"updated")
            with self.assertRaises(ValueError):
                install_verified_bundle(self.bundle(), directory, downloader=broken)
            for name in COMPONENTS:
                self.assertEqual((directory/name).read_bytes(), b"original")

    def test_bundle_stages_launcher_for_next_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            for name in COMPONENTS:
                (directory/name).write_bytes(b"original")
            def download(info, target):
                target.write_bytes(b"updated")
            install_verified_bundle(self.bundle(), directory, downloader=download)
            self.assertEqual((directory/"SPUSTI-WARDER-EXE.cmd").read_bytes(), b"original")
            self.assertEqual((directory/"SPUSTI-WARDER-EXE.cmd.pending").read_bytes(), b"updated")
            self.assertEqual((directory/"WARDER-PICON-FACTORY.exe").read_bytes(), b"updated")

    def test_verified_bundle_download_checks_non_exe_without_mz(self):
        import hashlib
        import io
        from unittest.mock import patch
        from windows_exe_update import download_verified
        payload = b"@echo off\r\necho updated\r\n"
        class Response:
            headers = {"Content-Type": "application/octet-stream"}
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def geturl(self): return "https://release-assets.githubusercontent.com/asset"
            def read(self, size=-1):
                nonlocal payload
                chunk, payload = payload[:size], payload[size:]
                return chunk
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "launcher.cmd"
            original = b"@echo off\r\necho updated\r\n"
            download_verified({"url":"https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/releases/download/factory-v0.2.32/SPUSTI-WARDER-EXE.cmd",
                               "size":len(original),"sha256":hashlib.sha256(original).hexdigest()},
                              path, opener=lambda *a,**kw:Response())
            self.assertEqual(path.read_bytes(), original)
