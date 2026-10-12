import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import hashlib
import io
import urllib.error
import base64
from factory_diagnostics_retry import retry_reports

from factory_diagnostics import sanitized_summary, upload_report
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

    def test_confirmed_delivery_records_receipt_and_preserves_every_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            sent = folder / 'report-20261011-092600-123.json'
            failed = folder / 'report-20261011-092601-123.json'
            sent.write_text('{}')
            failed.write_text('{}')
            def upload(path):
                return {'status': 'sent', 'verified': True} if path == sent else {'status': 'http_error'}
            with patch('factory_diagnostics_retry.upload_report', side_effect=upload):
                result = retry_reports(folder, folder / 'delivered.json')
            self.assertEqual(len(result), 2)
            self.assertFalse(sent.exists())
            self.assertTrue(failed.exists())
            self.assertFalse((folder / 'delivered.json').exists())

    def test_old_receipt_preserves_report_without_resending(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            name = 'report-20261011-092600-123.json'
            (folder / name).write_text('{}')
            state = folder / 'delivered.json'
            state.write_text(json.dumps({'schema': 2, 'delivered': [name]}))
            with patch('factory_diagnostics_retry.upload_report') as upload:
                result = retry_reports(folder, state)
            self.assertEqual(len(result), 1)
            upload.assert_called_once()
            self.assertTrue((folder / name).exists())

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

    def test_report_retry_accepts_existing_identical_blob_without_put(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report-20261011-092600-123.json'
            path.write_text(json.dumps({'run': '20261011-092600-123', 'stats': {'scanned': 5}}))
            payload = sanitized_summary(json.loads(path.read_text()))
            content = json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8') + b'\n'
            blob_sha = hashlib.sha1(b'blob ' + str(len(content)).encode('ascii') + b'\0' + content).hexdigest()
            class Response:
                status = 200
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def read(self, *args): return json.dumps({'sha': blob_sha}).encode()
            calls = []
            def opener(request, timeout):
                calls.append(request)
                return Response()
            with patch.dict('os.environ', {'WARDER_DIAGNOSTICS_TOKEN': 'test-token'}):
                result = upload_report(path, opener=opener)
            self.assertEqual(result['status'], 'sent')
            self.assertTrue(result['already_present'])
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0].get_method(), 'GET')

    def test_new_report_is_uploaded_only_after_remote_404(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report-20261011-092600-123.json'
            path.write_text(json.dumps({'run': '20261011-092600-123', 'stats': {'scanned': 5}}))
            class Response:
                status = 201
                def __enter__(self): return self
                def __exit__(self, *args): pass
            calls = []
            def opener(request, timeout):
                calls.append(request)
                if request.get_method() == 'GET':
                    raise urllib.error.HTTPError(request.full_url, 404, 'missing', {}, io.BytesIO(b''))
                return Response()
            with patch.dict('os.environ', {'WARDER_DIAGNOSTICS_TOKEN': 'test-token'}):
                result = upload_report(path, opener=opener)
            self.assertEqual(result['status'], 'sent')
            self.assertEqual(result['status'], 'offline_or_failed')
            self.assertEqual([item.get_method() for item in calls], ['GET', 'PUT', 'GET'])

    def test_existing_different_report_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report-20261011-092600-123.json'
            path.write_text(json.dumps({'run': '20261011-092600-123', 'stats': {'scanned': 5}}))
            class Response:
                status = 200
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def read(self, *args): return b'{"sha":"different"}'
            calls = []
            def opener(request, timeout):
                calls.append(request)
                return Response()
            with patch.dict('os.environ', {'WARDER_DIAGNOSTICS_TOKEN': 'test-token'}):
                result = upload_report(path, opener=opener)
            self.assertEqual(result['status'], 'http_error')
            self.assertEqual(result['code'], 422)
            self.assertEqual([item.get_method() for item in calls], ['GET'])

    def test_legacy_timestamp_retry_accepts_same_run_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'report-20261011-092600-123.json'
            path.write_text(json.dumps({'run': '20261011-092600-123', 'stats': {'scanned': 5}}))
            payload = sanitized_summary(json.loads(path.read_text()))
            payload['created_utc'] = '2026-10-11T09:26:00+00:00'
            encoded = base64.b64encode(json.dumps(payload).encode()).decode()
            class Response:
                status = 200
                def __enter__(self): return self
                def __exit__(self, *args): pass
                def read(self, *args):
                    return json.dumps({'sha': 'older-blob-sha', 'encoding': 'base64',
                                       'content': encoded}).encode()
            with patch.dict('os.environ', {'WARDER_DIAGNOSTICS_TOKEN': 'test-token'}):
                result = upload_report(path, opener=lambda *_args, **_kwargs: Response())
            self.assertEqual(result['status'], 'sent')
            self.assertTrue(result['already_present'])


if __name__ == '__main__':
    unittest.main()
