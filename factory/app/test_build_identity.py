import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import factory_build_info
from workspace_paths import WINDOWS_ROOT, resolve_root, workspace_paths


class BuildIdentityTests(unittest.TestCase):
    def test_packaged_build_commit_is_loaded_and_executable_is_absolute(self):
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp) / ".factory-build.json"
            marker.write_text(json.dumps({"commit": "1e656b81106d15dceee98d785404476054a0e857"}), encoding="utf-8")
            with patch.object(factory_build_info, "__file__", str(Path(temp) / "factory_build_info.py")):
                self.assertEqual(factory_build_info.build_commit(), "1e656b81106d15dceee98d785404476054a0e857")
        self.assertTrue(Path(factory_build_info.executable_path()).is_absolute())

    def test_windows_gui_and_engine_path_map_cannot_resolve_old_c_root(self):
        root = resolve_root(env={"WARDER_PICON_FACTORY_ROOT": r"C:\Users\PC\WARDER-PICONS"}, platform="nt")
        paths = workspace_paths(root)
        self.assertEqual(root, WINDOWS_ROOT)
        for key in ("root", "inbox", "output", "final", "logs", "app"):
            self.assertTrue(str(paths[key]).startswith(r"D:\WARDER-PICON-FACTORY"))
            self.assertNotIn(r"C:\Users\PC\WARDER-PICONS", str(paths[key]))

    def test_dashboard_displays_executable_commit_root_and_preflight(self):
        source = Path(__file__).with_name("factory_workspace.py").read_text(encoding="utf-8")
        self.assertIn("Build commit:", source)
        self.assertIn("Spustený EXE:", source)
        self.assertIn("Dátový koreň:", source)
        self.assertIn("Preflight:", source)
        engine = Path(__file__).with_name("engine.py").read_text(encoding="utf-8")
        self.assertIn('"executable_path":self.executable_path', engine)
        self.assertIn('"build_commit":self.build_commit', engine)
        self.assertIn('"data_root":str(ROOT)', engine)
        self.assertIn('"preflight":"ok"', engine)

    def test_factory_release_line_is_monotonic_with_existing_manifest(self):
        app_version = json.loads((Path(__file__).parent / ".factory-version.json").read_text(encoding="utf-8"))["version"]
        manifest = json.loads((Path(__file__).parents[1] / "update" / "manifest.json").read_text(encoding="utf-8"))["version"]
        def numbers(value):
            return tuple(int(part) for part in value.removeprefix("factory-v").split("."))
        self.assertEqual(numbers(manifest), (0, 2, 27))
        self.assertEqual(numbers(app_version), (0, 2, 30))
        self.assertGreater(numbers(app_version), numbers(manifest))

    def test_runtime_modules_do_not_contain_the_disallowed_c_root(self):
        app = Path(__file__).parent
        for name in ("workspace_paths.py", "factory_workspace.py", "engine.py", "factory_launcher.py", "package_windows_cmd.py"):
            source = (app / name).read_text(encoding="utf-8").casefold()
            self.assertNotIn(r"c:\users\pc\warder-picons", source, name)
            self.assertNotIn(r"%userprofile%\warder-picons", source, name)


if __name__ == "__main__":
    unittest.main()
