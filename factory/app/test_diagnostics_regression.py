import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from factory_diagnostics_retry import retry_reports

from factory_diagnostics import sanitized_summary
from report_housekeeping import cleanup_reports


class FactoryDiagnosticsSafety(unittest.TestCase):
    def test_only_allowed_fields_are_sent(self):
        report = {'run': '20261011-092600-123', 'stats': {
            'scanned': 10, 'review_workstreams': {'ARTWORK_REVIEW': 3},
            'secret': 'DO_NOT_SEND', 'paths': ['private-file.png']}}
        result = sanitized_summary(report)
        self.assertEqual(result['summary']['scanned'], 10)
        self.assertEqual(result['summary']['review_workstreams']['ARTWORK_REVIEW'], 3)
        self.assertNotIn('DO_NOT_SEND', json.dumps(result))
        self.assertNotIn('private-file.png', json.dumps(result))

    def test_cleanup_preserves_reports_and_review_queues(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            for i in range(5):
                run = '20261011-09260%d-123' % i
                for prefix in ('report', 'review-queue', 'qa'):
                    (folder / (prefix + '-' + run + '.json')).write_text('{}')
            result = cleanup_reports(folder, keep_runs=2)
            self.assertEqual(result['deleted'], 3)
            self.assertEqual(len(list(folder.glob('report-*.json'))), 5)
            self.assertEqual(len(list(folder.glob('review-queue-*.json'))), 5)


if __name__ == '__main__':
    unittest.main()
