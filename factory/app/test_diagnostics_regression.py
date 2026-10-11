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

    def test_aggregate_evidence_is_shared_without_identity_or_paths(self):
        report={'run':'20261011-092600-123','stats':{'qa_backlog_causes':{'EXACT':12,'C:/private/path':9,'name.png':4},'final_picons_on_disk':{'transparent':7}}}
        result=sanitized_summary(report)['summary']
        self.assertEqual(result['qa_backlog_causes'],{'EXACT':12})
        self.assertEqual(result['final_picons_on_disk']['transparent'],7)
        self.assertNotIn('private',json.dumps(result))

    def test_confirmed_delivery_removes_only_sent_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            sent = folder / 'report-20261011-092600-123.json'
            failed = folder / 'report-20261011-092601-123.json'
            sent.write_text('{}')
            failed.write_text('{}')
            def upload(path):
                return {'status': 'sent' if path == sent else 'http_error'}
            with patch('factory_diagnostics_retry.upload_report', side_effect=upload):
                result = retry_reports(folder, folder / 'delivered.json')
            self.assertEqual(len(result), 2)
            self.assertFalse(sent.exists())
            self.assertTrue(failed.exists())

    def test_old_receipt_cleans_leftover_without_resending(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            name = 'report-20261011-092600-123.json'
            (folder / name).write_text('{}')
            state = folder / 'delivered.json'
            state.write_text(json.dumps({'schema': 2, 'delivered': [name]}))
            with patch('factory_diagnostics_retry.upload_report') as upload:
                result = retry_reports(folder, state)
            self.assertEqual(result, [])
            upload.assert_not_called()
            self.assertFalse((folder / name).exists())

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
