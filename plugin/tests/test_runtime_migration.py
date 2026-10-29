"""Exercise the receiver path transition, including the running old updater."""
import importlib.util
import pathlib
import tempfile
import unittest

ROOT=pathlib.Path(__file__).parents[1]/'src/Plugins/Extensions/WarderPiconHub'
spec=importlib.util.spec_from_file_location('migration_contracts',ROOT/'warder_migrate.py')
migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)


class RuntimeMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=pathlib.Path(self.temp.name);self.extensions=self.root/'Extensions';self.extensions.mkdir()
        self.current=self.extensions/migration.NEW_NAME;self.current.mkdir()
        (self.current/'version.txt').write_text('0.1.7\n');(self.current/'plugin.py').write_text('# new entrypoint\n')
        self.old=self.extensions/migration.OLD_NAME;self.state=self.root/'state'

    def test_old_runtime_is_preserved_outside_discovery_and_tick_can_read_version(self):
        self.old.mkdir();(self.old/'plugin.py').write_text('# running old plugin\n')
        (self.old/'custom.cfg').write_text('keep my custom data')
        (self.old/'version.txt').write_text('0.1.6\n')
        settings=self.root/'settings';settings.write_text('config.plugins.chocholousekpicons_id=1\n')
        backup=migration.migrate(self.extensions,self.state)
        self.assertEqual((pathlib.Path(backup)/'custom.cfg').read_text(),'keep my custom data')
        self.assertEqual((self.old/'version.txt').read_text().strip(),'0.1.7')
        self.assertEqual([p.parent.name for p in self.extensions.glob('*/plugin.py')],['WarderPiconHub'])
        self.assertEqual(settings.read_text(),'config.plugins.chocholousekpicons_id=1\n')
        self.assertEqual(migration.migrate(self.extensions,self.state),backup)
        self.assertEqual(len(list((self.state/'previous-runtime').iterdir())),1)
        self.assertTrue(migration.cleanup_compatibility(self.extensions))
        self.assertFalse(self.old.exists());self.assertTrue((self.current/'plugin.py').exists())

    def test_old_clock_can_read_during_every_migration_move_and_version_replace(self):
        from unittest.mock import patch
        self.old.mkdir();version=self.old/'version.txt';version.write_text('0.1.6\n')
        (self.old/'plugin.py').write_text('# old')
        move=migration.shutil.move
        replace=pathlib.Path.replace
        def observe_move(*args,**kwargs):
            self.assertEqual(version.read_text().strip(),'0.1.6')
            result=move(*args,**kwargs)
            self.assertEqual(version.read_text().strip(),'0.1.6')
            return result
        def observe_replace(path,target):
            self.assertEqual(version.read_text().strip(),'0.1.6')
            result=replace(path,target)
            self.assertEqual(version.read_text().strip(),'0.1.7')
            return result
        with patch.object(migration.shutil,'move',side_effect=observe_move), patch.object(pathlib.Path,'replace',observe_replace):
            migration.migrate(self.extensions,self.state)

    def test_failed_version_replace_removes_partial_file_and_preserves_old_version(self):
        from unittest.mock import patch
        self.old.mkdir();(self.old/'version.txt').write_text('0.1.6\n')
        with patch.object(pathlib.Path,'replace',side_effect=OSError('disk error')):
            with self.assertRaises(OSError):migration.migrate(self.extensions,self.state)
        self.assertEqual((self.old/'version.txt').read_text(),'0.1.6\n')
        self.assertEqual([p.name for p in self.old.iterdir()],['version.txt'])

    def test_transition_marker_works_if_opkg_already_removed_the_old_directory(self):
        self.state.mkdir();(self.state/'legacy-transition-needed').touch()
        migration.migrate(self.extensions,self.state)
        self.assertEqual((self.old/'version.txt').read_text().strip(),'0.1.7')
        self.assertFalse((self.state/'legacy-transition-needed').exists())
        self.assertTrue(migration.cleanup_compatibility(self.extensions))

    def test_package_resource_paths_are_relative_to_the_new_runtime(self):
        import sys,types
        from unittest.mock import patch
        module=types.ModuleType('Components.Language')
        module.language=types.SimpleNamespace(addCallback=lambda callback:None)
        spec=importlib.util.spec_from_file_location('new_runtime_init',ROOT/'__init__.py',submodule_search_locations=[str(ROOT)])
        package=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'new_runtime_init':package,'Components.Language':module}):
            spec.loader.exec_module(package)
            self.assertEqual(pathlib.Path(package.PLUGIN_PATH),ROOT.resolve())
            self.assertEqual(pathlib.Path(package.PluginLanguagePath),ROOT.resolve()/'locale')
        source=(ROOT/'plugin.py').read_text()
        self.assertNotIn('from Plugins.Extensions.ChocholousekPicons',source)
        self.assertIn("translate('Sťahovanie a správa piconov')",source)

    def test_fresh_install_does_not_create_an_old_runtime(self):
        self.assertIsNone(migration.migrate(self.extensions,self.state))
        self.assertFalse(self.old.exists())

    def test_import_in_the_still_running_old_gui_does_not_remove_the_bridge(self):
        import os
        from unittest.mock import patch
        self.state.mkdir();(self.state/'legacy-transition-needed').touch()
        with patch.object(migration,'running_gui_pid',return_value=os.getpid()):
            migration.migrate(self.extensions,self.state)
        self.assertFalse(migration.cleanup_compatibility(self.extensions))
        self.assertEqual((self.old/'version.txt').read_text().strip(),'0.1.7')
        with patch.object(migration.os,'getpid',return_value=os.getpid()+1):
            self.assertTrue(migration.cleanup_compatibility(self.extensions))

    def test_cleanup_never_removes_unknown_user_files(self):
        self.state.mkdir();(self.state/'legacy-transition-needed').touch()
        migration.migrate(self.extensions,self.state)
        (self.old/'user-file').write_text('keep')
        self.assertFalse(migration.cleanup_compatibility(self.extensions))
        self.assertEqual((self.old/'user-file').read_text(),'keep')

    def test_old_symlink_is_archived_without_modifying_its_target(self):
        target=self.root/'external';target.mkdir();(target/'keep').write_text('safe')
        self.old.symlink_to(target,target_is_directory=True)
        backup=migration.migrate(self.extensions,self.state)
        self.assertTrue(pathlib.Path(backup).is_symlink())
        self.assertEqual((target/'keep').read_text(),'safe')
        self.assertFalse(self.old.is_symlink())
        self.assertTrue(migration.cleanup_compatibility(self.extensions))
