"""Offline tests for backward-compatible country picon split ZIP packaging."""
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile


SCRIPT = Path(__file__).resolve().parents[1] / 'staging/batch-79-reviewed/helpers/import_queryfree.py'
spec = importlib.util.spec_from_file_location('radio_package_builder', str(SCRIPT))
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def radio_name(number):
    return '4097_0_2_%04X_ABCD_ED_0_0_0_0.png' % number


class SplitArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_small_country_remains_compatible_one_zip(self):
        photos = {radio_name(1): b'original-first', radio_name(2): b'original-second'}
        entry = builder.write_packages('AT', '220x132', 'white', photos, self.root, 4096)
        self.assertNotIn('parts', entry)
        self.assertTrue(entry['path'].endswith('iptv-at-white-220x132.zip'))
        with ZipFile(self.root / entry['path']) as archive:
            self.assertEqual({n: archive.read(n) for n in archive.namelist()}, photos)
        self.assertEqual(entry['files'], {name:hashlib.sha256(image).hexdigest() for name,image in photos.items()})

    def test_multi_country_produces_exact_partition_and_verified_bytes(self):
        photos = {radio_name(i): bytes([i])*3500 for i in range(1, 5)}
        entry = builder.write_packages('DE', '400x240', 'black', photos, self.root, 4096)
        self.assertEqual(len(entry['parts']), 4)
        self.assertNotIn('url', entry)
        self.assertEqual(set(entry['files']), set(photos))
        reconstructed = {}
        for number, part in enumerate(entry['parts'], 1):
            self.assertTrue(part['path'].endswith('-part%02d.zip' % number))
            raw=(self.root / part['path']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),part['sha256'])
            self.assertEqual(len(raw),part['bytes'])
            with ZipFile(io.BytesIO(raw)) as archive:
                self.assertEqual(set(archive.namelist()),set(part['files']))
                for name in archive.namelist():
                    self.assertNotIn(name,reconstructed)
                    reconstructed[name]=archive.read(name)
        self.assertEqual(reconstructed,photos)
        with patch.object(builder,'get', side_effect=lambda part:(self.root/part['path']).read_bytes()):
            self.assertEqual(builder.unzip(entry),photos)

    def test_repeated_build_is_byte_identical(self):
        photos={radio_name(i): bytes([i])*3500 for i in range(1, 5)}
        one=builder.write_packages('DE','220x132','transparent',photos,self.root/'first',4096)
        two=builder.write_packages('DE','220x132','transparent',photos,self.root/'second',4096)
        self.assertEqual(one,two)
        for part in one['parts']:
            self.assertEqual((self.root/'first'/part['path']).read_bytes(),
                             (self.root/'second'/part['path']).read_bytes())


if __name__ == '__main__':
    unittest.main()
