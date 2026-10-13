import base64
import re
import unittest
from pathlib import Path


class ReadOnlyDiagnosticPackageTests(unittest.TestCase):
    def test_single_cmd_collects_runtime_identity_without_touching_factory_data(self):
        cmd = Path(__file__).with_name("DIAGNOSTIKA-WARDER-PICON-FACTORY.cmd").read_text(encoding="ascii")
        match = re.search(r"-EncodedCommand\s+([A-Za-z0-9+/=]+)", cmd)
        self.assertIsNotNone(match)
        powershell = base64.b64decode(match.group(1)).decode("utf-16le")
        for expected in (r"D:\WARDER-PICON-FACTORY", "Get-CimInstance Win32_Process", "WARDER-PICON-FACTORY.exe",
                         "SHA256", "WARDER-PICON-FACTORY.previous-*", "WARDER_DIAG_OUT"):
            self.assertIn(expected, powershell)
        lowered = powershell.casefold()
        self.assertIn("function get-sha256", lowered)
        self.assertNotIn("get-filehash", lowered)
        workflow = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "factory-regression.yml"
        self.assertIn("SHA256:\\s+[0-9a-f]{64}", workflow.read_text(encoding="utf-8"))
        for forbidden in ("remove-item", "move-item", "copy-item", "new-item", "set-content",
                          "stop-process", "start-process", "invoke-webrequest", "set-itemproperty"):
            self.assertNotIn(forbidden, lowered)
        self.assertIn("[io.file]::writealllines($out", lowered)
        self.assertIn(r"c:\users\pc\warder-picons", lowered)
        self.assertIn("warder_diag_no_pause", cmd.casefold())


if __name__ == "__main__":
    unittest.main()
