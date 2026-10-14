"""The configured external feeds are actually called from the scan pipeline."""
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import engine


class PeerSourceIntegrationTests(unittest.TestCase):
    def test_only_openatv_is_attempted_until_source_closes(self):
        with tempfile.TemporaryDirectory() as tmp:
            factory = object.__new__(engine.Factory)
            factory.emit = lambda *_: None; factory.log = lambda *_: None; factory.active_source = 'openatv8'
            openatv = types.ModuleType('openatv_feed')
            openatv.verified_package_styles = lambda *_: {}
            openatv.discover_current = lambda: {'index_sha1': 'abc', 'packages': []}
            openatv.naming_inventory = lambda _packages: {'srp': {'count': 0}, 'utf8snp': {'count': 0}}
            ipk = types.ModuleType('ipk_import'); ipk.IMPORT_SCHEMA = 3
            called = {'later_sources': 0}
            vhannibal = types.ModuleType('vhannibal_source')
            vhannibal.sync_vhannibal = lambda *_a, **_k: called.__setitem__('later_sources', called['later_sources'] + 1)
            chocho = types.ModuleType('chocholousek_source')
            chocho.sync_chocholousek = lambda *_a, **_k: called.__setitem__('later_sources', called['later_sources'] + 1)
            data = Path(tmp) / '00-STATE'; originals = Path(tmp) / '02-ORIGINALS'
            data.mkdir(); originals.mkdir()
            with patch.object(engine, 'SOURCE_INGEST', Path(tmp) / '01-SOURCES' / 'source-ingest'), \
                 patch.object(engine, 'DATA', data), patch.object(engine, 'APP_DATA', Path(tmp) / '11-APP' / '.factory-data'), \
                 patch.object(engine, 'ORIGINALS', originals), \
                 patch.dict('sys.modules', {'openatv_feed': openatv, 'ipk_import': ipk,
                                            }):
                stats = {}; factory.sync_peer_sources(stats)
            self.assertEqual(stats['active_source'], 'openatv8')
            self.assertEqual(stats['peer_sources']['vhannibal']['status'], 'deferred')
            self.assertEqual(stats['peer_sources']['chocholousek']['status'], 'deferred')
            self.assertEqual(called['later_sources'], 0)

    def test_openatv_archive_checkpoints_and_original_png_use_correct_categories(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_root = Path(tmp) / '01-SOURCES' / 'source-ingest'
            state_root = Path(tmp) / '00-STATE'
            originals = Path(tmp) / '02-ORIGINALS'
            source_root.mkdir(parents=True); state_root.mkdir(); originals.mkdir()
            package = {'sha256': 'a' * 64, 'version': 'fixture-1'}
            family_data = {'srp': {'count': 1}, 'utf8snp': {'count': 0}}
            openatv = types.ModuleType('openatv_feed')
            openatv.verified_package_styles = lambda *_: {}
            openatv.discover_current = lambda: {'index_sha1': 'fixture-index', 'packages': [package]}
            openatv.naming_inventory = lambda _packages: family_data
            def download(_package, target):
                target = Path(target); target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b'fixture archive')
            openatv.download_package = download
            observed = {}
            ipk = types.ModuleType('ipk_import'); ipk.IMPORT_SCHEMA = 3
            def import_ipk(archive, output_root):
                archive, output_root = Path(archive), Path(output_root)
                extracted = output_root / package['sha256']
                extracted.mkdir(parents=True)
                (extracted / '.warder-import-schema').write_text('3', encoding='ascii')
                (extracted / 'service.png').write_bytes(b'original PNG')
                observed.update(archive=archive, output_root=output_root)
                return {'imported': 1, 'skipped': 0}
            ipk.import_png_ipk = import_ipk
            factory = object.__new__(engine.Factory)
            factory.emit = lambda *_: None; factory.log = lambda *_: None; factory.check_cancelled = lambda: None; factory.active_source = 'openatv8'
            with patch.object(engine, 'SOURCE_INGEST', source_root), \
                 patch.object(engine, 'DATA', state_root), patch.object(engine, 'ORIGINALS', originals), \
                 patch.dict(engine._WORKSPACE, {'chocho_positions': state_root / 'positions.json'}), \
                 patch.dict('sys.modules', {'openatv_feed': openatv, 'ipk_import': ipk,
                                            }):
                stats = {}
                factory.sync_peer_sources(stats)
            self.assertEqual(observed['archive'], source_root / 'archives' / 'openatv8' / (package['sha256'] + '.ipk'))
            self.assertEqual(observed['output_root'], originals / 'openatv8' / 'schema-3')
            self.assertTrue((state_root / 'openatv8-state.json').is_file())
            self.assertFalse((source_root / 'originals').exists())
            self.assertEqual(stats['peer_sources']['openatv8']['imported'], 1)


    def test_vhannibal_waits_for_separate_owner_decision_even_if_ledger_advances(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); data=root/'00-STATE'; originals=root/'02-ORIGINALS'; data.mkdir();originals.mkdir()
            calls=[]; module=types.ModuleType('vhannibal_source')
            module.sync_vhannibal=lambda workspace,**kwargs:(calls.append((Path(workspace),kwargs)) or {'status':'unchanged','imported':0})
            factory=object.__new__(engine.Factory);factory.active_source='vhannibal'
            factory.emit=lambda *_:None;factory.log=lambda *_:None
            with patch.object(engine,'SOURCE_INGEST',root/'01-SOURCES'/'ingest'), \
                 patch.object(engine,'DATA',data),patch.object(engine,'ORIGINALS',originals), \
                 patch.object(engine,'APP_DATA',root/'11-APP'/'data'), \
                 patch.dict('sys.modules',{'vhannibal_source':module}):
                stats={};factory.sync_peer_sources(stats)
            self.assertEqual(len(calls),0)
            self.assertIsNone(stats['active_source'])
            self.assertEqual(stats['peer_sources']['vhannibal']['reason'],'OWNER_DECISION_REQUIRED')
            self.assertEqual(stats['peer_sources']['openatv8']['status'],'deferred')
            self.assertEqual(stats['peer_sources']['chocholousek']['status'],'deferred')

if __name__ == '__main__':
    unittest.main()
