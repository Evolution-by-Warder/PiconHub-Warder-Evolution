"""The configured external feeds are actually called from the scan pipeline."""
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import engine


class PeerSourceIntegrationTests(unittest.TestCase):
    def test_vhannibal_openatv_and_chocholousek_are_attempted(self):
        with tempfile.TemporaryDirectory() as tmp:
            logs = []
            factory = object.__new__(engine.Factory)
            factory.emit = lambda *_: None
            factory.log = logs.append

            vhannibal = types.ModuleType('vhannibal_source')
            source_roots = {}
            vhannibal.sync_vhannibal = lambda workspace, **kwargs: (
                source_roots.update(vhannibal=(Path(workspace), Path(kwargs['state_dir']), Path(kwargs['originals_dir']))) or
                {'status': 'unchanged', 'imported': 0})
            openatv = types.ModuleType('openatv_feed')
            openatv.verified_package_styles = lambda *_: {}
            openatv.discover_current = lambda: {'index_sha1': 'abc', 'packages': []}
            openatv.download_package = lambda *_: self.fail('no packages expected')
            openatv.naming_inventory = lambda packages: {
                'srp': {'count': 0}, 'utf8snp': {'count': 0}}
            ipk = types.ModuleType('ipk_import')
            ipk.import_png_ipk = lambda *_: self.fail('no packages expected')
            ipk.IMPORT_SCHEMA = 1
            chocholousek = types.ModuleType('chocholousek_source')
            called = []
            chocholousek.sync_chocholousek = lambda workspace, **kwargs: (
                called.append((Path(workspace), kwargs.get('selected_positions'),
                               Path(kwargs['state_dir']), Path(kwargs['originals_dir']))) or
                {'status': 'updated', 'downloaded': 1, 'imported_png': 7})
            data = Path(tmp) / 'data'
            data.mkdir()
            originals = Path(tmp) / '02-ORIGINALS'
            originals.mkdir()
            positions = data / 'chocholousek-positions.json'
            positions.write_text('{"schema":1,"positions":["13.0E"]}', encoding='utf-8')
            with patch.object(engine, 'SOURCE_INGEST', Path(tmp) / 'source-ingest'), \
                 patch.object(engine, 'DATA', data), \
                 patch.object(engine, 'ORIGINALS', originals), \
                 patch.dict(engine._WORKSPACE, {'chocho_positions': positions}), \
                 patch.dict('sys.modules', {
                     'vhannibal_source': vhannibal,
                     'openatv_feed': openatv,
                     'ipk_import': ipk,
                     'chocholousek_source': chocholousek,
                 }):
                stats = {}
                factory.sync_peer_sources(stats)
            self.assertEqual(len(called), 1)
            self.assertEqual(called[0][1], ['13.0E'])
            self.assertEqual(called[0][0], Path(tmp) / 'source-ingest')
            self.assertEqual(source_roots['vhannibal'], (Path(tmp) / 'source-ingest', data, originals))
            self.assertEqual(called[0][2:], (data, originals))
            self.assertEqual(stats['peer_sources']['chocholousek']['imported_png'], 7)
            self.assertEqual(stats['peer_source_imports'], 7)
            self.assertEqual(stats.get('source_errors', 0), 0)
            self.assertTrue(any('Chocholousek: updated' in line for line in logs))

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
            vhannibal = types.ModuleType('vhannibal_source')
            vhannibal.sync_vhannibal = lambda *_a, **_k: {'status': 'unchanged', 'imported': 0}
            chocho = types.ModuleType('chocholousek_source')
            chocho.sync_chocholousek = lambda *_a, **_k: {'status': 'selection_required', 'downloaded': 0, 'imported_png': 0}
            factory = object.__new__(engine.Factory)
            factory.emit = lambda *_: None; factory.log = lambda *_: None
            with patch.object(engine, 'SOURCE_INGEST', source_root), \
                 patch.object(engine, 'DATA', state_root), patch.object(engine, 'ORIGINALS', originals), \
                 patch.dict(engine._WORKSPACE, {'chocho_positions': state_root / 'positions.json'}), \
                 patch.dict('sys.modules', {'openatv_feed': openatv, 'ipk_import': ipk,
                                            'vhannibal_source': vhannibal, 'chocholousek_source': chocho}):
                stats = {}
                factory.sync_peer_sources(stats)
            self.assertEqual(observed['archive'], source_root / 'archives' / 'openatv8' / (package['sha256'] + '.ipk'))
            self.assertEqual(observed['output_root'], originals / 'openatv8' / 'schema-3')
            self.assertTrue((state_root / 'openatv8-state.json').is_file())
            self.assertFalse((source_root / 'originals').exists())
            self.assertEqual(stats['peer_sources']['openatv8']['imported'], 1)


if __name__ == '__main__':
    unittest.main()
