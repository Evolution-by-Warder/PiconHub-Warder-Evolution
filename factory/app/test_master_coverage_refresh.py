"""No-scan MASTER-first refresh regressions."""
import unittest

from master_coverage_refresh import (recalculate_master_first, format_master_refresh_result)
from warder_identity_registry import empty_approval_ledger, empty_registry
from review_queue import stable_review_id

COMMIT = "a" * 40
REF = "1_0_1_100_1_1_D72CF4_0_0_0"


def row(workstream, ref=REF, sha="1" * 64, reason="EVIDENCE"):
    return {"review_id": stable_review_id(workstream, ref, sha),
            "category": workstream, "workstream": workstream,
            "candidate_identity": ref, "sha256": sha,
            "reasons": [reason], "decision": "PENDING"}


class MasterCoverageRefreshTests(unittest.TestCase):
    def snapshot(self):
        return {"commit": COMMIT, "registry": empty_registry(),
                "approval_ledger": empty_approval_ledger(), "events": []}

    def test_recalculates_saved_queue_without_scanning_or_rendering(self):
        technical = row("TECHNICAL_QA", "", "2" * 64, "FULLY_TRANSPARENT")
        technical["candidate_identity"] = "ilsole24ore tv"
        technical["reasons"] = ["FULLY_TRANSPARENT", "QA_ERROR: OUTPUT_CHANGED_DURING_QA"]
        artwork = row("ARTWORK_REVIEW")
        queue = {"schema": 1, "count": 2, "items": [technical, artwork],
                 "workstream_counts": {"TECHNICAL_QA": 1, "ARTWORK_REVIEW": 1},
                 "covered_items": []}
        result = recalculate_master_first(queue, self.snapshot())
        refreshed = result["queue"]
        self.assertEqual(refreshed["count"], 2)
        self.assertEqual(len(refreshed["items"]), 2)
        self.assertEqual(refreshed["master_first_refresh"]["pngs_read"], 0)
        self.assertFalse(refreshed["master_first_refresh"]["rendering_performed"])
        self.assertEqual(refreshed["master_first_refresh"]["automatic_identity_approvals"], 0)
        held = next(i for i in refreshed["items"] if i["workstream"] == "TECHNICAL_QA")
        self.assertEqual(held["candidate_identity"], "ilsole24ore tv")
        self.assertEqual(held["reasons"], ["FULLY_TRANSPARENT", "QA_ERROR: OUTPUT_CHANGED_DURING_QA"])

    def test_unavailable_or_invalid_git_snapshot_fails_closed(self):
        queue = {"schema": 1, "count": 1, "items": [row("ARTWORK_REVIEW")]}
        with self.assertRaisesRegex(ValueError, "valid pinned commit"):
            recalculate_master_first(queue, {"registry": empty_registry(),
                                             "approval_ledger": empty_approval_ledger()})
        bad = self.snapshot()
        bad["registry"]["next_sequence"] = -1
        with self.assertRaisesRegex(ValueError, "failed validation"):
            recalculate_master_first(queue, bad)

    def test_previous_coverage_is_recomputed_not_permanently_hidden(self):
        item = row("ARTWORK_REVIEW")
        covered = dict(item, decision="COVERED_BY_APPROVED_MASTER",
                       coverage_status="COVERED_BY_APPROVED_MASTER",
                       coverage_evidence_hash="f" * 64)
        queue = {"schema": 1, "count": 0, "items": [], "covered_items": [covered],
                 "workstream_counts": {"ARTWORK_REVIEW": 0}}
        result = recalculate_master_first(queue, self.snapshot())
        self.assertEqual(result["queue"]["count"], 1)
        self.assertEqual(result["queue"]["items"][0]["review_id"], item["review_id"])

    def test_queue_count_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "item count"):
            recalculate_master_first({"schema": 1, "count": 0, "items": [row("ARTWORK_REVIEW")]},
                                     self.snapshot())




    def test_workflow_summary_keeps_unresolved_items_visible_and_never_approves_identity(self):
        identity = row("IDENTITY_VERIFICATION")
        identity["source_provenance"] = ["synthetic-openatv"]
        artwork = row("ARTWORK_REVIEW")
        technical = row("TECHNICAL_QA", "", "2" * 64, "FULLY_TRANSPARENT")
        queue = {"schema": 1, "count": 3, "items": [identity, artwork, technical]}
        result = recalculate_master_first(queue, self.snapshot())
        workflow = result["queue"]["processing_workflow"]
        self.assertEqual(workflow["counts"]["READY_FOR_HUMAN_APPROVAL"], 2)
        self.assertEqual(workflow["counts"]["TECHNICAL_QA"], 1)
        self.assertEqual(workflow["counts"]["AUTO_RESOLVED_VERIFIED"], 0)
        self.assertEqual(workflow["automatic_identity_approvals"], 0)
        self.assertEqual(len(workflow["task_statuses"]), 3)

    def test_refresh_confirmation_explains_unchanged_front(self):
        result = {"source_active_items": 9932, "active_items": 9932,
                  "covered_this_refresh": 0, "master_commit": COMMIT,
                  "elapsed_seconds": 1.25, "decision_groups": 1,
                  "processing_workflow": {"unique_decision_groups": 1,
                                          "counts": {"READY_FOR_HUMAN_APPROVAL": 1}},
                  "unchanged_reason": "no exact approval evidence"}
        text = format_master_refresh_result(result)
        self.assertIn("9932 → 9932", text)
        self.assertIn("0", text)
        self.assertIn("skupiny 1", text)
        self.assertIn("človek 1", text)
        self.assertIn("BEZ RENDERU", text)
        self.assertIn("no exact approval evidence", text)


if __name__ == "__main__":
    unittest.main()
