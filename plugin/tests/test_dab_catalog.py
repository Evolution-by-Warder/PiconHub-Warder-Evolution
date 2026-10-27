"""Offline DAB preview catalog tests; no external station artwork."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / 'picons' / 'DAB' / 'build_catalog.py'
spec = importlib.util.spec_from_file_location('dab_catalog_builder', str(SCRIPT))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DABCatalogTests(unittest.TestCase):
    def test_manifest_with_two_exact_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            preview = root / 'preview'
            names = ('4115_0_2_A_1_1_0_0_0_0.png',
                     '4115_0_2_B_1_1_0_0_0_0.png')
            for variant in ('transparent', 'white', 'black'):
                (preview / variant).mkdir(parents=True)
                for name in names:
                    (preview / variant / name).write_bytes(b'example')
            mapping = root / 'mapping.csv'
            mapping.write_text(
                'bouquet,station,picon_filename\n'
                + ''.join('DAB test,Station,%s\n' % name for name in names),
                encoding='utf-8')
            catalog = module.build_catalog(mapping, preview)
            self.assertEqual(catalog['station_count'], 1)
            self.assertEqual(catalog['reference_count'], 2)
            self.assertEqual(catalog['status'], 'preview_only')
            self.assertTrue(all(not row['logo_verified'] for row in catalog['records']))
            self.assertTrue(all(not row['approved_master_v9'] for row in catalog['records']))

    def test_duplicate_references_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mapping = root / 'mapping.csv'
            mapping.write_text(
                'bouquet,station,picon_filename\n'
                'DAB,One,4115_0_2_A_1_1_0_0_0_0.png\n'
                'DAB,Two,4115_0_2_A_1_1_0_0_0_0.png\n',
                encoding='utf-8')
            preview = root / 'preview'
            for variant in ('transparent', 'white', 'black'):
                (preview / variant).mkdir(parents=True)
                (preview / variant / '4115_0_2_A_1_1_0_0_0_0.png').write_bytes(b'example')
            with self.assertRaises(ValueError):
                module.build_catalog(mapping, preview)


if __name__ == '__main__':
    unittest.main()
