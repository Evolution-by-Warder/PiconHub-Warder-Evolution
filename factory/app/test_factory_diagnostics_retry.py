"""Verified GitHub delivery controls local diagnostic report cleanup."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from factory_diagnostics_retry import retry_reports


class DiagnosticsRetryTests(unittest.TestCase):
    def test_newest_first_and_verified_reports_are_deleted(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            reports = folder / "reports"
            reports.mkdir()
            for n in (1, 2, 3):
                (reports / f"report-20261011-12000{n}-1.json").write_text("{}", encoding="utf-8")
            state = folder / "state.json"
            seen = []
            def send(path):
                seen.append(path.name)
                return {"status": "sent", "verified": True}
            with patch("factory_diagnostics_retry.upload_report", side_effect=send):
                first = retry_reports(reports, state, limit=2)
                second = retry_reports(reports, state, limit=2)
            self.assertEqual([item["status"] for item in first + second], ["sent"] * 3)
            self.assertEqual(seen, sorted(seen, reverse=True))
            self.assertEqual(list(reports.glob("report-*.json")), [])

    def test_failed_or_unverified_report_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            reports = Path(tmp)
            path = reports / "report-20261011-120001-1.json"
            path.write_text("{}", encoding="utf-8")
            with patch("factory_diagnostics_retry.upload_report", return_value={"status": "sent"}):
                result = retry_reports(reports, reports / "state.json")
            self.assertEqual(result[0]["status"], "verification_missing")
            self.assertTrue(path.exists())
            with patch("factory_diagnostics_retry.upload_report", return_value={"status": "http_error"}):
                result = retry_reports(reports, reports / "state.json")
            self.assertEqual(result[0]["status"], "http_error")
            self.assertTrue(path.exists())

    def test_missing_token_does_not_delete_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            reports = Path(tmp)
            path = reports / "report-20261011-120001-1.json"
            path.write_text("{}", encoding="utf-8")
            with patch("factory_diagnostics_retry.upload_report", return_value={"status": "not_configured"}):
                result = retry_reports(reports, reports / "state.json")
            self.assertEqual(result[0]["status"], "not_configured")
            self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
