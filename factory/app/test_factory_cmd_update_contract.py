"""Guard the CMD update bootstrap against runtime deletion and missing dependencies."""
import unittest
from pathlib import Path


class CmdUpdateContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = Path(__file__).with_name('SPUSTI-WARDER.cmd').read_text(encoding='utf-8')

    def test_runtime_is_outside_replaceable_application(self):
        self.assertIn('11-APP\\.factory-runtime-venv', self.script)
        self.assertNotIn('".venv\\Scripts\\python.exe"', self.script)

    def test_update_precedes_dependency_refresh_and_gui(self):
        script = self.script
        update = script.index('"factory_update_bootstrap.py"')
        deps = script.index('-r "requirements-runtime.txt"', update)
        launch = script.index('"factory_launcher.py"', deps)
        self.assertLess(update, deps)
        self.assertLess(deps, launch)

    def test_dependency_failure_rolls_back_pending_update(self):
        self.assertIn('if errorlevel 1 goto :dependency_failure', self.script)
        self.assertIn('resolve(workspace_paths(resolve_root())', self.script)
        self.assertIn('gui_ready=False', self.script)

    def test_no_production_registry_paths_in_installer(self):
        self.assertNotIn('warder-master-production', self.script)
        self.assertNotIn('git push', self.script)


if __name__ == '__main__':
    unittest.main()
