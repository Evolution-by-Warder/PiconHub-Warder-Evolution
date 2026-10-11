import unittest
from registry_triage import origin_of, summarize_registry_matches

class WindowsSourceProvenanceTests(unittest.TestCase):
    def test_mixed_case_windows_paths_keep_source_origin(self):
        self.assertEqual(origin_of(r'D:\\WARDER-PICON-FACTORY\\SOURCE-INGEST\\ORIGINALS\\OpenATV8\\picons\\1.png'), 'openatv8')
        self.assertEqual(origin_of(r'D:\\WARDER-PICON-FACTORY\\source-ingest\\Originals\\VHANNIBAL\\p.png'), 'vhannibal')
        self.assertEqual(origin_of(r'D:\\WARDER-PICON-FACTORY\\01-SOURCES\\LOCAL-INBOX\\p.png'), 'local-inbox')

    def test_source_counts_not_misclassified_as_local_inbox(self):
        rows = [{'candidate_source': r'D:\\SOURCE-INGEST\\ORIGINALS\\OPENATV8\\a.png', 'classification': 'REVIEW'},
                {'candidate_source': r'D:\\source-ingest\\originals\\openatv8\\b.png', 'classification': 'UNMAPPED'}]
        result = summarize_registry_matches(rows)
        self.assertEqual(result['openatv8']['REVIEW'], 1)
        self.assertEqual(result['openatv8']['UNMAPPED'], 1)
        self.assertNotIn('local-inbox', result)

if __name__ == '__main__':
    unittest.main()
