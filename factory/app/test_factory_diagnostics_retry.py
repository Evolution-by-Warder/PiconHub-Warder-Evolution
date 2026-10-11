"""Diagnostics delivery is resumable and does not upload the same report twice."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from factory_diagnostics_retry import retry_reports


class DiagnosticsRetryTests(unittest.TestCase):
    def test_newest_first_and_success_is_persisted(self):
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
                return {"status": "sent"}
            with patch("factory_diagnostics_retry.upload_report", side_effect=send):
                first = retry_reports(reports, state, limit=2)
                second = retry_reports(reports, state, limit=2)
            self.assertEqual([item["status"] for item in first + second], ["sent"] * 3)
            self.assertEqual(seen, sorted(seen, reverse=True))
            self.assertEqual(len(json.loads(state.read_text())["delivered"]), 3)

    def test_missing_token_does_not_mark_report_delivered(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            reports = folder / "reports"
            reports.mkdir()
            (reports / "report-20261011-120001-1.json").write_text("{}", encoding="utf-8")
            state = folder / "state.json"
            with patch("factory_diagnostics_retry.upload_report", return_value={"status": "not_configured"}):
                result = retry_reports(reports, state)
            self.assertEqual(result[0]["status"], "not_configured")
            self.assertEqual(json.loads(state.read_text())["delivered"], [])


if __name__ == "__main__":
    unittest.main()
