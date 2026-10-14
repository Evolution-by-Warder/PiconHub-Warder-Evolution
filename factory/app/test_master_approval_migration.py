import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from master_approval_migration import migrate_approval_evidence, write_manifest_new


REF = "1_0_1_100_1_1_D72CF4_0_0_0"
OTHER = "1_0_1_101_1_1_D72CF4_0_0_0"
COMMIT = "a" * 40
HASHES = {"transparent": "1" * 64, "black": "2" * 64, "white": "3" * 64}


def master_index(refs=(REF,)):
    return {"services": {ref: [{"style": style, "sha256": sha} for style, sha in HASHES.items()]
                         for ref in refs}}


def approval(ref=REF, variants=None):
    return {"event_type": "MASTER_ARTWORK_APPROVED", "service_reference": ref,
            "master_approved": True, "identity_verified": True, "artwork_approved": True,
            "approval_ref": "audit-2026-0042", "master_commit": COMMIT,
            "variants": variants or HASHES}


class ApprovalMigrationTests(unittest.TestCase):
    def test_explicit_current_approval_migrates_with_source_digest(self):
        record = approval()
        result = migrate_approval_evidence(master_index(), [record], master_commit=COMMIT)
        self.assertEqual(result["counts"]["VERIFIED"], 1)
        entry = result["manifest"]["services"][REF]
        material = {key: value for key, value in record.items() if key != "evidence_sha256"}
        self.assertEqual(entry["evidence_sha256"], hashlib.sha256(json.dumps(
            material, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest())
        self.assertTrue(result["read_only"])
        self.assertFalse(result["automatic_approval"])

    def test_partial_approval_is_preserved_as_partial(self):
        record = approval(variants={"transparent": HASHES["transparent"], "black": HASHES["black"]})
        result = migrate_approval_evidence(master_index(), [record], master_commit=COMMIT)
        self.assertEqual(result["counts"]["PARTIAL"], 1)
        self.assertEqual(set(result["manifest"]["services"][REF]["variants"]), {"transparent", "black"})

    def test_png_or_service_presence_without_approval_is_not_evidence(self):
        result = migrate_approval_evidence(master_index(), [], master_commit=COMMIT)
        self.assertEqual(result["counts"]["NO_EVIDENCE"], 1)
        self.assertEqual(result["manifest"]["services"], {})

    def test_review_stage_decisions_are_not_master_approval(self):
        ledger = {"schema": 1, "decisions": {"WR-123": {"decision": "APPROVED_FOR_REVIEW",
                                                             "evidence_hash": "f" * 64}}}
        result = migrate_approval_evidence(master_index(), [ledger], master_commit=COMMIT)
        self.assertEqual(result["counts"]["NO_EVIDENCE"], 1)

    def test_old_master_commit_is_conflict(self):
        record = approval()
        record["master_commit"] = "b" * 40
        result = migrate_approval_evidence(master_index(), [record], master_commit=COMMIT)
        self.assertEqual(result["counts"]["CONFLICT"], 1)

    def test_stale_variant_hash_is_conflict(self):
        record = approval()
        record["variants"] = {**HASHES, "white": "e" * 64}
        result = migrate_approval_evidence(master_index(), [record], master_commit=COMMIT)
        self.assertEqual(result["counts"]["CONFLICT"], 1)

    def test_bad_source_record_digest_is_conflict(self):
        record = approval()
        record["evidence_sha256"] = "f" * 64
        result = migrate_approval_evidence(master_index(), [record], master_commit=COMMIT)
        self.assertEqual(result["counts"]["CONFLICT"], 1)

    def test_missing_identity_approval_flag_is_not_imported(self):
        record = approval()
        record["identity_verified"] = False
        result = migrate_approval_evidence(master_index(), [record], master_commit=COMMIT)
        self.assertEqual(result["counts"]["NO_EVIDENCE"], 1)
        self.assertEqual(result["manifest"]["services"], {})

    def test_new_service_is_not_assigned_an_id_or_master_approval(self):
        record = approval(OTHER)
        result = migrate_approval_evidence(master_index(), [record], master_commit=COMMIT)
        self.assertEqual(result["counts"]["NEW"], 1)
        self.assertNotIn(OTHER, result["manifest"]["services"])

    def test_conflicting_source_approvals_block_migration(self):
        good = approval()
        stale = approval()
        stale["master_commit"] = "b" * 40
        result = migrate_approval_evidence(master_index(), [good, stale], master_commit=COMMIT)
        self.assertEqual(result["counts"]["CONFLICT"], 1)
        self.assertEqual(result["manifest"]["services"], {})

    def test_existing_manifest_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "approval.json"
            path.write_text("keep", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                write_manifest_new(path, {"schema": 1})
            self.assertEqual(path.read_text(encoding="utf-8"), "keep")

    def test_write_creates_manifest_only_at_explicit_new_local_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "new" / "approval.json"
            write_manifest_new(path, {"schema": 1, "services": {}})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["schema"], 1)

    def test_manifest_writer_refuses_git_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            (root / ".git").mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "outside a Git checkout"):
                write_manifest_new(root / "factory" / "03-REGISTRY" / "master-approval-evidence.json",
                                   {"schema": 1})


if __name__ == "__main__":
    unittest.main()
