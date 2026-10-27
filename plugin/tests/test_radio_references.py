import unittest
import importlib.util
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'src' / 'Plugins' / 'Extensions' / 'WarderPiconHub' / 'radio_references.py'
spec = importlib.util.spec_from_file_location('warder_radio_references', str(SOURCE))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
picon_reference = module.picon_reference
collect_picon_references = module.collect_picon_references
analyze_bouquet = module.analyze_bouquet
picon_filename_is_reference = module.picon_filename_is_reference


class RadioReferenceTests(unittest.TestCase):
    def test_picon_filename_inventory(self):
        self.assertTrue(picon_filename_is_reference('1_0_2_AB_1_1_0_0_0_0.png'))
        self.assertTrue(picon_filename_is_reference('4097_0_1_AB_1_2_0_0_0_0.png'))
        self.assertTrue(picon_filename_is_reference('1013_0_2_AB_1_2_0_0_0_0.png'))
        self.assertFalse(picon_filename_is_reference('radio_station.png'))
        self.assertFalse(picon_filename_is_reference('1_0_2_AB.png'))
        self.assertFalse(picon_filename_is_reference('1_64_0_0_0_0_0_0_0_0.png'))

    def test_dvb_radio(self):
        self.assertEqual(picon_reference('#SERVICE 1:0:2:1234:3:1:0:0:0:0:'),
                         '1_0_2_1234_3_1_0_0_0_0')

    def test_preserve_leading_zeroes(self):
        self.assertEqual(picon_reference('#SERVICE 1:0:2:000A:0001:1:0:0:0:0:'),
                         '1_0_2_000A_0001_1_0_0_0_0')

    def test_real_dab_bundes_and_wdr_references(self):
        # Anonymization-safe identity fields from receiver bouquet samples.
        examples = (
            ('#SERVICE 4115:0:2:1019:C98:3:EB0000:1019:100D:10BC:dab%3a//239.128.43.43%3a50043',
             '4115_0_2_1019_C98_3_EB0000_1019_100D_10BC'),
            ('#SERVICE 4115:0:2:1019:5:85:C00000:1019:100D:10BC:dab%3a//239.128.43.43%3a50043',
             '4115_0_2_1019_5_85_C00000_1019_100D_10BC'),
            ('#SERVICE 4115:0:2:BB8:402:1:C00000:BB8:D492:10FA:dab%3a//228.10.2.5%3a10010',
             '4115_0_2_BB8_402_1_C00000_BB8_D492_10FA'),
        )
        for service, expected in examples:
            self.assertEqual(picon_reference(service), expected)
            self.assertTrue(picon_filename_is_reference(expected + '.png'))

    def test_dab_style_service_type(self):
        self.assertEqual(picon_reference('#SERVICE 1013:0:2:1234:3:1:0:0:0:0:'),
                         '1013_0_2_1234_3_1_0_0_0_0')

    def test_stream_with_url(self):
        self.assertIsNone(picon_reference('#SERVICE 4097:0:1:0:0:0:0:0:0:0:http%3a//radio.example/stream'))

    def test_stream_with_unique_identity(self):
        self.assertEqual(picon_reference('#SERVICE 4097:0:1:AB:1:2:0:0:0:0:http%3a//radio.example/stream'),
                         '4097_0_1_AB_1_2_0_0_0_0')

    def test_markers_and_bouquet_references(self):
        for line in ('#SERVICE 1:64:0:0:0:0:0:0:0:0:',
                     '#SERVICE 1:7:1:0:0:0:0:0:0:0:',
                     '#DESCRIPTION Radio',
                     '#SERVICE 1:0:2:xyz:0:0:0:0:0:0:'):
            self.assertIsNone(picon_reference(line))

    def test_non_service_lines_and_directory(self):
        self.assertIsNone(picon_reference('#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET'))
        self.assertIsNone(picon_reference('#SERVICE 1:64:0:0:0:0:0:0:0:0:'))
        self.assertIsNone(picon_reference('#SERVICE 0:0:0:0:0:0:0:0:0:0:'))

    def test_reject_truncated_reference(self):
        self.assertIsNone(picon_reference('#SERVICE 1:0:2:1234:3:1'))

    def test_diagnostic_never_exposes_stream_url(self):
        contents = ('#SERVICE 1:0:2:A:1:1:0:0:0:0:\n'
                    '#SERVICE 4097:0:1:0:0:0:0:0:0:0:http%3a//private.example/secret\n'
                    '#DESCRIPTION Private Radio\n')
        result = analyze_bouquet(contents)
        self.assertEqual(result['service_entries'], 2)
        self.assertEqual(result['accepted_unique'], 1)
        self.assertEqual(result['skipped_entries'], 1)
        self.assertNotIn('private.example', repr(result))

    def test_deduplication(self):
        contents = '#SERVICE 1:0:2:A:1:1:0:0:0:0:\n#SERVICE 1:0:2:a:1:1:0:0:0:0:\n'
        self.assertEqual(collect_picon_references(contents), ['1_0_2_A_1_1_0_0_0_0'])


if __name__ == '__main__':
    unittest.main()
