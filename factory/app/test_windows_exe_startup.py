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
                              return_value={"schema":1,"version":"factory-v0.2.31",
                                            "commit":"a"*40}):
                self.assertEqual(windows_exe_startup.run(exe, meta), "UP_TO_DATE")
            self.assertEqual(exe.read_bytes(), b"MZexisting")
