"""Bootstrap must never update an active or unconfirmed Factory installation."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import factory_update_bootstrap as bootstrap


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.app = self.root / '11-APP' / 'WARDER-PICON-FACTORY'
        self.app.mkdir(parents=True)
        self.paths = {'app': self.app}

    def call(self, updater):
        messages = []
        with patch.object(bootstrap, 'resolve_root', return_value=self.root), \
             patch.object(bootstrap, 'workspace_paths', return_value=self.paths):
            result = bootstrap.run(updater=updater, reporter=messages.append)
        return result, messages

    def test_pending_transaction_is_not_overwritten(self):
        (self.app.parent / '.factory-pending-update.json').write_text('{}')
        result, _ = self.call(lambda *a, **k: self.fail('update called'))
        self.assertEqual(result, 'pending_gui_confirmation')

    def test_updater_runs_once_with_lock(self):
        calls = []
        def update(app, reporter):
            calls.append(app)
            return 'up_to_date'
        result, messages = self.call(update)
        self.assertEqual(result, 'up_to_date')
        self.assertEqual(calls, [self.app])
        self.assertIn('FACTORY UPDATE: up_to_date', messages)

    def test_running_factory_defers_update(self):
        from factory_single_instance import exclusive_launcher
        lock = self.root / '11-APP' / '.factory-launch.lock'
        with exclusive_launcher(lock):
            result, _ = self.call(lambda *a, **k: self.fail('update called'))
        self.assertEqual(result, 'already_running')


if __name__ == '__main__':
    unittest.main()
