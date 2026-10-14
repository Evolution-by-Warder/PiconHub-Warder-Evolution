import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from warder_identity_registry import empty_approval_ledger, empty_registry, validate_master_store
from warder_review_store import (
    apply_git_review_decisions, build_review_batch, clear_pending_batch,
    commit_review_batch, load_pending_batches, stage_pending_batch,
    validate_progress,
)
from review_decision_groups import build_decision_groups


HEAD = "a" * 40


def item(index=0, **changes):
    value = {
        "review_id": "WR-" + f"{index:016x}",
        "workstream": "ARTWORK_REVIEW",
        "candidate_identity": "service-ref-" + str(index),
        "sha256": f"{index + 1:064x}",
        "reasons": ["ARTWORK_CONFLICT"],
    }
    value.update(changes)
    return value


def one_scope(value):
    group = build_decision_groups({"items": [value]})["groups"][0]
    return {"decision_group_id": group["decision_group_id"],
            "group_evidence_sha256": group["group_evidence_hash"], "items": [value]}


class WarderGitReviewDecisionTests(unittest.TestCase):
    def test_review_decision_is_bound_to_exact_evidence_and_hides_only_after_commit(self):
        row = item()
        scope = one_scope(row)
        batch = build_review_batch([scope], "APPROVED_FOR_REVIEW", timestamp="2026-10-14T00:00:00Z")
        self.assertEqual(len(batch["events"]), 1)
        ledger = {"schema": 1, "authority": "WARDER_MASTER_APPROVAL_LEDGER",
                  "events": batch["events"]}
        self.assertEqual(validate_master_store(empty_registry(), ledger)["status"], "VALID")
        self.assertEqual(apply_git_review_decisions([row], batch["events"]), [])
        changed = dict(row, sha256="f" * 64)
        self.assertEqual(len(apply_git_review_decisions([changed], batch["events"])), 1)

    def test_ten_approvals_are_one_git_transaction_and_checkpoint(self):
        rows = [item(i) for i in range(10)]
        group_id = "DG-" + "b" * 24
        batch = build_review_batch([{"decision_group_id": group_id, "items": rows}],
                                   "APPROVED_FOR_REVIEW", timestamp="2026-10-14T00:00:00Z")
        snapshot = {"commit": HEAD, "registry": empty_registry(),
                    "approval_ledger": empty_approval_ledger()}
        calls = []
        def transaction(**kwargs):
            calls.append(kwargs)
            return {"status": "COMMITTED_VERIFIED", "commit": "b" * 40}
        with patch("warder_review_store.fetch_master_snapshot", return_value=snapshot):
            result = commit_review_batch("token", batch, expected_head=HEAD, transaction=transaction)
        self.assertEqual(result["status"], "COMMITTED_VERIFIED")
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(calls[0]["approval_ledger"]["events"]), 10)
        checkpoint = calls[0]["additional_json"]["factory/registry/project-progress.json"]
        self.assertEqual(checkpoint["processed"], 10)
        self.assertEqual(checkpoint["last_batch"], batch["batch_id"])

    def test_stale_head_fails_closed_without_transaction(self):
        row = item()
        batch = build_review_batch([one_scope(row)], "REJECTED", timestamp="2026-10-14T00:00:00Z")
        snapshot = {"commit": HEAD, "registry": empty_registry(),
                    "approval_ledger": empty_approval_ledger()}
        called = []
        with patch("warder_review_store.fetch_master_snapshot", return_value=snapshot):
            result = commit_review_batch("token", batch, expected_head="c" * 40,
                                         transaction=lambda **kwargs: called.append(kwargs))
        self.assertEqual(result["status"], "CONFLICT")
        self.assertEqual(called, [])

    def test_duplicate_submit_is_idempotent_after_commit(self):
        row = item()
        batch = build_review_batch([one_scope(row)], "REJECTED", timestamp="2026-10-14T00:00:00Z")
        snapshot = {"commit": HEAD, "registry": empty_registry(),
                    "approval_ledger": {"schema": 1, "authority": "WARDER_MASTER_APPROVAL_LEDGER",
                                        "events": copy.deepcopy(batch["events"])}}
        called = []
        with patch("warder_review_store.fetch_master_snapshot", return_value=snapshot):
            result = commit_review_batch("token", batch, expected_head=HEAD,
                                         transaction=lambda **kwargs: called.append(kwargs))
        self.assertEqual(result["status"], "ALREADY_COMMITTED")
        self.assertEqual(called, [])

    def test_pending_batch_survives_retry_and_clears_only_after_confirmed_write(self):
        row = item()
        batch = build_review_batch([one_scope(row)], "APPROVED_FOR_REVIEW", timestamp="2026-10-14T00:00:00Z")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "pending.json"
            stage_pending_batch(path, batch)
            self.assertEqual(load_pending_batches(path)[0]["batch_id"], batch["batch_id"])
            clear_pending_batch(path, batch["batch_id"])
            self.assertEqual(load_pending_batches(path), [])

    def test_exported_event_contains_no_user_path_or_png_bytes(self):
        row = item(original=r"C:\Users\PC\source.png", candidate_bytes="synthetic PNG payload must stay local")
        event = build_review_batch([one_scope(row)], "REJECTED",
                                   timestamp="2026-10-14T00:00:00Z")["events"][0]
        serialized = str(event)
        self.assertNotIn("C:\\Users", serialized)
        self.assertNotIn("candidate_bytes", serialized)
        self.assertNotIn("source.png", serialized)

    def test_ambiguous_decision_is_durable_but_never_master_approval(self):
        row = item(workstream="IDENTITY_VERIFICATION")
        batch = build_review_batch([one_scope(row)], "IDENTITY_AMBIGUOUS",
                                   timestamp="2026-10-14T00:00:00Z")
        event = batch["events"][0]
        self.assertEqual(event["event_type"], "MASTER_REVIEW_DECISION")
        self.assertNotIn("warder_id", event)
        self.assertNotIn("variants", event)
        self.assertEqual(validate_master_store(empty_registry(),
            {"schema": 1, "authority": "WARDER_MASTER_APPROVAL_LEDGER", "events": [event]})["status"], "VALID")

    def test_identity_approval_updates_registry_and_ledger_in_same_commit(self):
        from warder_review_store import commit_identity_approval
        row = item(11, workstream="IDENTITY_VERIFICATION")
        batch = build_review_batch([one_scope(row)], "APPROVED_FOR_REVIEW",
                                   timestamp="2026-10-14T00:00:00Z")
        snapshot = {"commit": HEAD, "registry": empty_registry(),
                    "approval_ledger": empty_approval_ledger()}
        identity = {
            "identity_key": "service:synthetic:11",
            "current_name": "Synthetic TV",
            "canonical_identity": {"service_reference": "1_0_1_11"},
            "service_references": ["1_0_1_11"],
            "operator_links": ["provider:synthetic"],
            "satellite_positions": ["19.2E"],
            "source_provenance": ["review:" + row["review_id"]],
            "first_seen": {"review_id": row["review_id"]},
        }
        calls = []
        def transaction(**kwargs):
            calls.append(kwargs)
            return {"status": "COMMITTED_VERIFIED", "commit": "c" * 40}
        with patch("warder_review_store.fetch_master_snapshot", return_value=snapshot):
            result = commit_identity_approval("token", identity=identity, batch=batch,
                                              expected_head=HEAD, transaction=transaction)
        self.assertEqual(result["status"], "COMMITTED_VERIFIED")
        self.assertEqual(result["warder_id"], "WARDER-00000001")
        self.assertEqual(len(calls), 1)
        registry = calls[0]["registry"]
        ledger = calls[0]["approval_ledger"]
        self.assertIn("WARDER-00000001", registry["records"])
        self.assertEqual(len(ledger["events"]), 2)
        self.assertEqual(validate_master_store(registry, ledger)["status"], "VALID")

    def test_artwork_master_approval_writes_registry_ledger_and_three_assets_atomically(self):
        from PIL import Image
        from io import BytesIO
        from warder_review_store import commit_artwork_approval
        from warder_identity_registry import register_confirmed_identity
        from warder_master_store import build_identity_approval
        row = item(12, workstream="ARTWORK_REVIEW")
        scope = one_scope(row)
        batch = build_review_batch([scope], "APPROVED_FOR_REVIEW",
                                   timestamp="2026-10-14T00:00:00Z")
        registry = empty_registry()
        evidence = {"evidence_ref":"fixture:identity", "evidence_sha256":"d"*64,
                    "occurred_at":"2026-10-13T00:00:00Z"}
        identity = {"identity_key":"service:synthetic:12","current_name":"Synthetic Artwork",
                    "service_references":["1_0_1_12"]}
        registry, wid = register_confirmed_identity(registry, identity, evidence=evidence,
                                                    identity_confirmed=True)
        registry, ledger, _ = build_identity_approval(registry, empty_approval_ledger(),
            warder_id=wid, approval_id="identity-test", approved_at=evidence["occurred_at"],
            evidence_ref=evidence["evidence_ref"], evidence_sha256=evidence["evidence_sha256"],
            review_evidence_sha256="e"*64, human_approved=True)
        blobs = {}
        for style in ("transparent","black","white"):
            image = Image.new("RGBA", (220,132), (20,40,60,255))
            stream = BytesIO(); image.save(stream, format="PNG"); blobs[style] = stream.getvalue()
        snapshot = {"commit":HEAD,"registry":registry,"approval_ledger":ledger}
        calls=[]
        def transaction(**kwargs):
            calls.append(kwargs)
            return {"status":"COMMITTED_VERIFIED","commit":"d"*40}
        with patch("warder_review_store.fetch_master_snapshot", return_value=snapshot):
            result=commit_artwork_approval("token",warder_id=wid,variant_blobs=blobs,
                batch=batch,expected_head=HEAD,transaction=transaction)
        self.assertEqual(result["status"],"COMMITTED_VERIFIED")
        self.assertEqual(len(calls),1)
        self.assertEqual(len(calls[0]["artwork_blobs"]),3)
        self.assertEqual(calls[0]["registry"]["records"][wid]["artwork_current"].keys(),
                         {"transparent","black","white"})
        self.assertEqual(validate_master_store(calls[0]["registry"],calls[0]["approval_ledger"],
            read_asset=lambda path: calls[0]["artwork_blobs"][path])["status"],"VALID")

    def test_progress_is_recomputed_from_git_events(self):
        row = item()
        batch = build_review_batch([one_scope(row)], "REJECTED", timestamp="2026-10-14T00:00:00Z")
        ledger = {"schema": 1, "authority": "WARDER_MASTER_APPROVAL_LEDGER", "events": batch["events"]}
        checkpoint = {
            "schema": 1, "authority": "DERIVED_FROM_GIT_MASTER_LEDGER",
            "processed": 1, "approved_identities": 0, "approved_artwork": 0,
            "rejected": 1, "ambiguous": 0, "conflicts": 0,
            "review_accepted_count": 0, "registry_identity_count": 0,
            "remaining": None, "remaining_status": "NOT_DURABLE_QUEUE_NOT_YET_EXPORTED",
            "last_commit": HEAD, "last_batch": batch["batch_id"],
        }
        self.assertEqual(validate_progress(empty_registry(), ledger, checkpoint)["status"], "VALID")
        checkpoint["rejected"] = 0
        self.assertEqual(validate_progress(empty_registry(), ledger, checkpoint)["status"], "INVALID")


if __name__ == "__main__":
    unittest.main()
