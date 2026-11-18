"""Issue #91: validate embedded PiconHub hooks without building an IPK."""
import ast
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools/build_ipk.py"
BAR = "*" * 66


def extract():
    raw = BUILDER.read_text(encoding="utf-8")
    tree = ast.parse(raw)
    result = {}
    for item in ast.walk(tree):
        if not isinstance(item, ast.Assign):
            continue
        for target in item.targets:
            if isinstance(target, ast.Name) and target.id in ("preinst", "postinst", "prerm", "postrm"):
                if isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
                    result[target.id] = item.value.value
    return result, raw


def execute(script, event, stage=False):
    env = os.environ.copy()
    if stage:
        env["D"] = "/tmp/warder-issue91-staging"
    else:
        env.pop("D", None)
    proc = subprocess.run(["sh", "-c", script, "warder-hook", event],
                          env=env, capture_output=True, text=True, check=True, timeout=8)
    return proc.stdout


class PiconHubHookMessages(unittest.TestCase):
    def test_four_hooks_are_packaged_and_valid(self):
        data, source = extract()
        self.assertEqual(set(data), {"preinst", "postinst", "prerm", "postrm"})
        compile(source, str(BUILDER), "exec")
        for name, code in data.items():
            with self.subTest(name=name):
                self.assertTrue(code.startswith("#!/bin/sh\n"))
                self.assertIn('echo "' + BAR + '"', code)
                subprocess.run(["sh", "-n"], input=code, text=True, check=True)
                self.assertIn('("' + name + '",' + name + '.encode(),0o755)', source)

    def test_only_real_remove_shows_uninstall(self):
        data, _ = extract()
        self.assertEqual(execute(data["postrm"], "upgrade"), "")
        self.assertEqual(execute(data["postrm"], "failed-upgrade"), "")
        self.assertIn("upgrade/reinstall", execute(data["prerm"], "upgrade"))
        self.assertNotIn("Removing", execute(data["prerm"], "upgrade"))
        self.assertIn("Removing PiconHub Warder Evolution", execute(data["prerm"], "remove"))
        self.assertIn("Removal finished: PiconHub Warder Evolution", execute(data["postrm"], "remove"))
        self.assertTrue(execute(data["postrm"], "remove").startswith(BAR + "\n"))

    def test_staging_and_original_migration_are_preserved(self):
        data, _ = extract()
        for name in data:
            self.assertEqual(execute(data[name], "install", stage=True), "")
        self.assertIn("legacy-transition-needed", data["preinst"])
        self.assertIn("warder_migrate.py", data["postinst"])
        self.assertLess(data["postinst"].index("--verify-installed-files"),
                        data["postinst"].index("Install/upgrade/reinstall finished"))
        self.assertIn("Please restart GUI to activate changes.", data["postinst"])
        self.assertIn("Saved PiconHub user settings, profiles and picons", data["postrm"])


if __name__ == "__main__":
    unittest.main()
