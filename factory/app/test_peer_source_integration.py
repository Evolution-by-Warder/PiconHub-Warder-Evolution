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
            vhannibal.sync_vhannibal = lambda workspace: {'status': 'unchanged', 'imported': 0}
            openatv = types.ModuleType('openatv_feed')
            openatv.discover_current = lambda: {'index_sha1': 'abc', 'packages': []}
            openatv.download_package = lambda *_: self.fail('no packages expected')
            openatv.naming_inventory = lambda packages: {
                'srp': {'count': 0}, 'utf8snp': {'count': 0}}
            ipk = types.ModuleType('ipk_import')
            ipk.import_png_ipk = lambda *_: self.fail('no packages expected')
            ipk.IMPORT_SCHEMA = 1
            chocholousek = types.ModuleType('chocholousek_source')
            called = []
            chocholousek.sync_chocholousek = lambda workspace: (
                called.append(Path(workspace)) or
                {'status': 'updated', 'downloaded': 1, 'imported_png': 7})
            with patch.object(engine, 'SOURCE_INGEST', Path(tmp)), \
                 patch.dict('sys.modules', {
                     'vhannibal_source': vhannibal,
                     'openatv_feed': openatv,
                     'ipk_import': ipk,
                     'chocholousek_source': chocholousek,
                 }):
                stats = {}
                factory.sync_peer_sources(stats)
            self.assertEqual(len(called), 1)
            self.assertEqual(stats['peer_sources']['chocholousek']['imported_png'], 7)
            self.assertEqual(stats['peer_source_imports'], 7)
            self.assertEqual(stats.get('source_errors', 0), 0)
            self.assertTrue(any('Chocholousek: updated' in line for line in logs))


if __name__ == '__main__':
    unittest.main()
