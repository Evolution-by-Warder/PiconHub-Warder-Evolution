import json
import tempfile
import unittest
from pathlib import Path

from factory_workspace import (candidate_status, finalization_rows, latest_json, latest_master_registry, latest_registry_items,
                               latest_review_counts, parse_chocho_positions, source_rows)
from review_decisions import record_decision
from review_gallery import pending_items
from review_queue import save_review_queue


class FactoryWorkspaceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def test_source_rows_show_missing_and_persisted_checkpoint_states(self):
        ingest = self.root / "ingest"
        ingest.mkdir()
        (ingest / "vhannibal-state.json").write_text(json.dumps({"status": "updated", "imported": 9}), encoding="utf-8")
        inbox = self.root / "inbox"
        inbox.mkdir()
        (inbox / "one.zip").write_bytes(b"zip")
        (inbox / "one.png").write_bytes(b"png")
        snapshot = self.root / "master-current-paths.json"
        snapshot.write_text(json.dumps({"commit": "abc123", "paths": ["picons/13.0E/provider/transparent/ref.png"]}), encoding="utf-8")
        rows = source_rows(ingest, inbox, self.root / "manifest.json", master_snapshot=snapshot)
        self.assertEqual(rows[0][1], "updated")
        self.assertIn("imported: 9", rows[0][2])
        self.assertEqual(rows[1][1], "Ešte nesynchronizované")
        self.assertEqual(rows[-1][2], "1 ZIP · 1 PNG")
        self.assertEqual(next(row[1] for row in rows if row[0] == "Overené voliteľné zdroje"), "Nekonfigurované")
        self.assertEqual(next(row[1] for row in rows if row[0] == "Chocholousek · vybrané pozície"), "Čaká na výber")
        master_row = next(row for row in rows if row[0] == "Warder Master snapshot")
        self.assertEqual(master_row[1], "Dostupný")
        self.assertIn("abc123", master_row[2])

    def test_chocholousek_positions_require_explicit_satellite_format(self):
        self.assertEqual(parse_chocho_positions("13.0e, 5.0W, 13.0E"), ["13.0E", "5.0W"])
        with self.assertRaises(ValueError):
            parse_chocho_positions("all")

    def test_registry_and_review_panels_load_latest_real_reports(self):
        reports = self.root / "reports"
        reports.mkdir()
        old, new = reports / "registry-matches-1.json", reports / "registry-matches-2.json"
        old.write_text(json.dumps({"items": [{"classification": "OLD"}]}), encoding="utf-8")
        new.write_text(json.dumps({"items": [{"classification": "NEW", "service_reference": "ABC"}]}), encoding="utf-8")
        master_old = reports / "warder-master-index-1.json"
        master_new = reports / "warder-master-index-2.json"
        master_old.write_text(json.dumps({"services": {"OLD": []}}), encoding="utf-8")
        master_new.write_text(json.dumps({"service_count": 1, "asset_count": 3,
                                          "services": {"ABC": [{"position": "13.0E", "provider": "p", "style": "transparent"}]}}), encoding="utf-8")
        (reports / "review-queue-a.json").write_text(json.dumps({"count": 4, "workstream_counts": {"ARTWORK_REVIEW": 3}}), encoding="utf-8")
        path, items = latest_registry_items(reports)
        master_path, master, services = latest_master_registry(reports)
        _, counts = latest_review_counts(reports)
        self.assertEqual(path, new)
        self.assertEqual(items[0]["classification"], "NEW")
        self.assertEqual(master_path, master_new)
        self.assertEqual(master["asset_count"], 3)
        self.assertEqual(services["ABC"][0]["style"], "transparent")
        self.assertEqual(counts["total"], 4)
        self.assertEqual(counts["ARTWORK_REVIEW"], 3)

    def test_candidate_labels_are_conservative_and_qa_uses_real_engine_report(self):
        self.assertEqual(candidate_status("NEW"), "NEW")
        self.assertEqual(candidate_status("IDENTICAL"), "EXISTING")
        self.assertEqual(candidate_status("REVIEW", "different artwork", True), "EXISTING")
        self.assertEqual(candidate_status("REVIEW", "identity conflict", True), "CONFLICT")
        self.assertEqual(candidate_status("UNMAPPED"), "AMBIGUOUS")
        reports = self.root / "reports"
        reports.mkdir()
        report = reports / "report-20261011-120000.json"
        report.write_text(json.dumps({"stats": {"scanned": 12, "qa_repaired": 2}}), encoding="utf-8")
        self.assertEqual(latest_json(reports, "report-"), report)

    def test_finalized_local_decision_is_audited_and_hidden_on_reloads(self):
        item = {"review_id": "WR-1234567890123456", "candidate_identity": "service", "sha256": "a" * 64,
                "workstream": "TECHNICAL_QA", "reasons": ["verified"]}
        ledger = self.root / "decisions.json"
        decision = record_decision(ledger, item, "FINALIZED_LOCALLY", "saved locally", operator_confirmation=True)
        self.assertEqual(decision["decision"], "FINALIZED_LOCALLY")
        self.assertEqual(pending_items([item], ledger), [])
        changed = dict(item, reasons=["new evidence"])
        self.assertEqual(pending_items([changed], ledger), [changed])

    def test_finalization_panel_reads_engine_report_and_manual_audit(self):
        reports = self.root / "reports"
        reports.mkdir()
        (reports / "report-20261011-120000.json").write_text(json.dumps({"stats": {
            "new_candidate_finalization": {"copied": 2, "conflicts": 1, "qa_blocked": 3},
            "scanned": 18}}), encoding="utf-8")
        ledger = self.root / "decisions.json"
        record_decision(ledger, {"review_id": "WR-1234567890123456", "sha256": "a" * 64},
                        "FINALIZED_LOCALLY", "local QA done", operator_confirmation=True)
        rows = dict(finalization_rows(reports, ledger))
        self.assertEqual(rows["NEW kandidáti zapísaní"], "2")
        self.assertEqual(rows["Konflikty chránené pred zápisom"], "1")
        self.assertEqual(rows["Zablokované QA"], "3")
        self.assertEqual(rows["Ručné lokálne finalizácie"], "1")
        self.assertEqual(rows["Audit WR-1234567890123456"], "local QA done")

    def test_corrupt_json_is_reported_instead_of_displaying_false_zero_counts(self):
        from factory_workspace import finalization_rows, latest_review_counts
        reports = self.root / "reports"
        reports.mkdir()
        bad = reports / "review-queue-bad.json"
        bad.write_text("{broken", encoding="utf-8")
        path, counts = latest_review_counts(reports)
        self.assertEqual(path, bad)
        self.assertIn("error", counts)
        self.assertNotIn("total", counts)
        (reports / "report-bad.json").write_text("{broken", encoding="utf-8")
        rows = dict(finalization_rows(reports, self.root / "missing-ledger.json"))
        self.assertIn("CHYBA načítania", rows["NEW kandidáti zapísaní"])

    def test_5877_item_queue_loads_without_truncation(self):
        reports = self.root / "reports"
        reports.mkdir()
        items = [{"review_id": f"WR-{index:016X}", "category": "REGISTRY_MATCH",
                  "workstream": "ARTWORK_REVIEW", "candidate_identity": str(index),
                  "reasons": ["EXISTING_SERVICE_DIFFERENT_ART"], "decision": "PENDING"}
                 for index in range(5877)]
        save_review_queue(reports / "review-queue-large.json", {
            "schema": 1, "count": len(items), "items": items,
            "workstream_counts": {"ARTWORK_REVIEW": len(items)}})
        _, counts = latest_review_counts(reports)
        self.assertEqual(counts["total"], 5877)
        self.assertEqual(counts["ARTWORK_REVIEW"], 5877)
        self.assertEqual(len(pending_items(items, self.root / "no-decisions.json")), 5877)


if __name__ == "__main__":
    unittest.main()
