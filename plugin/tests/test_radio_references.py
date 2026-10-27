import unittest
from Plugins.Extensions.WarderPiconHub.radio_references import (
    picon_reference, collect_picon_references,
)


class RadioReferenceTests(unittest.TestCase):
    def test_dvb_radio(self):
        self.assertEqual(picon_reference('#SERVICE 1:0:2:1234:3:1:0:0:0:0:'),
                         '1_0_2_1234_3_1_0_0_0_0')

    def test_preserve_leading_zeroes(self):
        self.assertEqual(picon_reference('#SERVICE 1:0:2:000A:0001:1:0:0:0:0:'),
                         '1_0_2_000A_0001_1_0_0_0_0')

    def test_dab_style_service_type(self):
        self.assertEqual(picon_reference('#SERVICE 1013:0:2:1234:3:1:0:0:0:0:'),
                         '1013_0_2_1234_3_1_0_0_0_0')

    def test_stream_with_url(self):
        self.assertEqual(picon_reference('#SERVICE 4097:0:1:0:0:0:0:0:0:0:http%3a//radio.example/stream'),
                         '4097_0_1_0_0_0_0_0_0_0')

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

    def test_deduplication(self):
        contents = '#SERVICE 1:0:2:A:1:1:0:0:0:0:\n#SERVICE 1:0:2:a:1:1:0:0:0:0:\n'
        self.assertEqual(collect_picon_references(contents), ['1_0_2_A_1_1_0_0_0_0'])


if __name__ == '__main__':
    unittest.main()
