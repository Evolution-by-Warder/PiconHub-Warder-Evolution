import unittest
from pathlib import Path

class TestStartup(unittest.TestCase):
    def test_external_runtime(self):
        script = Path(__file__).with_name('SPUSTI-WARDER.cmd').read_text()
        self.assertIn('.factory-runtime-venv', script)
        self.assertIn('factory_update_bootstrap.py', script)
        self.assertIn('gui_ready=False', script)

    def test_order(self):
        script = Path(__file__).with_name('SPUSTI-WARDER.cmd').read_text()
        a = script.index('factory_update_bootstrap.py')
        b = script.index('requirements-runtime.txt', a)
        c = script.index('factory_launcher.py', b)
        self.assertLess(a, b)
        self.assertLess(b, c)

    def test_unique_labels(self):
        import re
        script = Path(__file__).with_name('SPUSTI-WARDER.cmd').read_text()
        labels = re.findall(r'^:([a-z_]+)$', script, re.MULTILINE)
        self.assertEqual(len(labels), len(set(labels)))

    def test_python_version(self):
        script = Path(__file__).with_name('SPUSTI-WARDER.cmd').read_text()
        self.assertIn('sys.version_info[:2] == (3,12)', script)

    def test_setup_only_failure_is_not_reported_as_success(self):
        script = Path(__file__).with_name('SPUSTI-WARDER.cmd').read_text()
        self.assertIn('if errorlevel 1 goto :failure', script)
        self.assertNotIn('exit /b %ERRORLEVEL%', script)

    def test_stable_bootstrap_is_outside_app(self):
        script = Path(__file__).with_name('SPUSTI-WARDER.cmd').read_text()
        self.assertIn('FACTORY-STABLE-START.cmd', script)
        self.assertIn('WARDER_FACTORY_STABLE_BOOTSTRAP', script)
        self.assertLess(script.index('FACTORY-STABLE-START.cmd'), script.index('factory_update_bootstrap.py'))

    def test_external_bootstrap_error_propagates(self):
        script = Path(__file__).with_name('SPUSTI-WARDER.cmd').read_text()
        self.assertIn('if errorlevel 1 exit /b 1', script)
