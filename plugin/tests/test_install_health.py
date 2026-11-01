"""A zero opkg return code must not hide missing or half-installed payloads."""
import importlib.util
import io
import pathlib
import sys
import tempfile
import types
import unittest

PATH = pathlib.Path(__file__).parents[1]/'src/Plugins/Extensions/WarderPiconHub/warder_update.py'
spec = importlib.util.spec_from_file_location('piconhub_install_health_tests', PATH)
updates = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = updates
spec.loader.exec_module(updates)


class InstallHealthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        for name in ('plugin.py', '__init__.py', 'warder_gui.py', 'warder_engine.py', 'warder_update.py', 'warder_migrate.py'):
            (self.root/name).write_text('# installed\n')
        (self.root/'version.txt').write_text('0.1.33\n')

    def status(self, state='installed', version='0.1.33', package=updates.PACKAGE_ID):
        return lambda *a, **kw: types.SimpleNamespace(returncode=0, stdout=f'Package: {package}\nVersion: {version}\nStatus: install ok {state}\n')

    def test_complete_install_is_accepted(self):
        self.assertEqual(updates.verify_installation('0.1.33', self.status(), self.root), '0.1.33')

    def test_half_install_wrong_version_and_wrong_package_are_rejected(self):
        for runner in (self.status('half-installed'), self.status('unpacked'),
                       self.status(version='0.1.32'), self.status(package='other')):
            with self.assertRaises(updates.UpdateError):
                updates.verify_installation('0.1.33', runner, self.root)

    def test_current_version_file_cannot_hide_a_missing_entrypoint(self):
        (self.root/'plugin.py').unlink()
        with self.assertRaises(updates.UpdateError):
            updates.verify_installation('0.1.33', self.status(), self.root)

    def test_stale_runtime_version_is_rejected(self):
        (self.root/'version.txt').write_text('0.1.32')
        with self.assertRaises(updates.UpdateError):
            updates.verify_payload('0.1.33', self.root)

    def test_successful_manager_exit_still_propagates_failed_final_verification(self):
        from unittest.mock import patch
        release = updates.Release('0.1.33', 'url', 'a'*64, 1)
        def verify(version, **kwargs):
            raise updates.UpdateError('half-installed')
        with patch.object(updates, 'download_release', return_value=self.root/'unused.ipk'), patch.object(updates, 'validate_ipk'):
            with self.assertRaisesRegex(updates.UpdateError, 'half-installed'):
                updates.install_release(release, runner=self.status(), verifier=verify)


if __name__ == '__main__':
    unittest.main()
