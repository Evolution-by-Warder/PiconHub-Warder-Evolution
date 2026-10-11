import unittest
from pathlib import Path

class TestStartup(unittest.TestCase):
    def test_external_runtime(self):
        script = Path(__file__).with_name('SPUSTI-WARDER.cmd').read_text()
        self.assertIn('.factory-runtime-venv', script)
        self.assertIn('factory_update_bootstrap.py', script)
        self.assertIn('gui_ready=False', script)
