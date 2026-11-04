import gzip
import json
from pathlib import Path
import tempfile
import unittest
from country_catalogue import export_packages


class CountryPackagesTests(unittest.TestCase):
    def setUp(self):
        self.rows = [dict(name='Station '+str(i), url='https://radio.example/'+str(i),
                          reference=str(i), group='Slovensko' if i < 89 else 'Čechy') for i in range(120)]
        self.index = [dict(name='Slovensko', countrycode='SK', stations=89),
                      dict(name='Čechy', countrycode='CZ', stations=31)]

    def test_roundtrip_and_unchanged_country_has_identical_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = export_packages(self.rows, self.index, root)
            again = export_packages(self.rows, self.index, root)
            self.assertEqual(first, again)
            restored = []
            for entry in first['countries']:
                self.assertEqual((root / entry['path']).read_bytes()[9],255)
                restored += json.loads(gzip.decompress((root / entry['path']).read_bytes()))
            self.assertEqual(restored, self.rows)
            self.rows[-1]['name'] = 'Changed Czech station'
            changed = export_packages(self.rows, self.index, root)
            self.assertEqual(first['countries'][0], changed['countries'][0])
            self.assertNotEqual(first['countries'][1]['version'], changed['countries'][1]['version'])
            self.assertTrue((root / first['countries'][1]['path']).exists())

    def test_counts_duplicates_and_unknown_groups_stop_publication(self):
        for rows, index in [(self.rows[:-1], self.index), (self.rows + [self.rows[0]], self.index),
                            (self.rows, self.index[:1])]:
            with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
                export_packages(rows, index, Path(directory))

    def test_original_source_is_an_independent_last_package(self):
        self.rows[-1]['group'] = 'HDF Radio zoznam'
        self.index[1]['stations'] -= 1
        self.index.append(dict(name='HDF Radio zoznam', stations=1, original_source_view=True))
        with tempfile.TemporaryDirectory() as directory:
            manifest = export_packages(self.rows, self.index, Path(directory))
            self.assertEqual(manifest['countries'][-1]['id'], 'SOURCE')
            self.assertEqual(manifest['countries'][-1]['kind'], 'source')

    def test_unsafe_country_ids_are_rejected(self):
        self.index[0]['countrycode'] = '../outside'
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            export_packages(self.rows, self.index, Path(directory))
