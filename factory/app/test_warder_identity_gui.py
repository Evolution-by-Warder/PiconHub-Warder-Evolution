import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from factory_workspace import identity_search_rows, load_warder_identity_rows
from warder_identity_registry import empty_approval_ledger, empty_registry, register_confirmed_identity
from warder_identity_sync import BRANCH, REPOSITORY


class WarderIdentityGuiTests(unittest.TestCase):
    def test_gui_reads_verified_git_cache_and_keeps_approval_separate(self):
        evidence = {"evidence_ref": "test", "evidence_sha256": "a" * 64,
                    "occurred_at": "2026-10-14T00:00:00Z"}
        registry, wid = register_confirmed_identity(empty_registry(),
            {"identity_key": "station:a", "current_name": "Alpha TV",
             "service_references": ["ref-a"], "operator_links": ["Provider A"],
             "satellite_positions": ["13.0E"]}, evidence=evidence,
            identity_confirmed=True)
        raw = (json.dumps(registry, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
        ledger_raw = (json.dumps(empty_approval_ledger(), ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
        snapshot = {"schema": 2, "repository": REPOSITORY, "branch": BRANCH,
                    "commit": "c" * 40, "registry_sha256": hashlib.sha256(raw).hexdigest(),
                    "approval_ledger_sha256": hashlib.sha256(ledger_raw).hexdigest(),
                    "registry": registry, "approval_ledger": empty_approval_ledger()}
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp) / "cache.json"
            cache.write_text(json.dumps(snapshot), encoding="utf-8")
            approval = Path(temp) / "approval.json"
            approval.write_text(json.dumps({"services": {"ref-a": {
                "identity_verified": True, "artwork_approved": True,
                "variants": {"transparent": "1" * 64, "black": "2" * 64,
                             "white": "3" * 64}}}}), encoding="utf-8")
            loaded, rows, error = load_warder_identity_rows(cache, approval)
        self.assertIsNone(error)
        self.assertEqual(loaded["commit"], "c" * 40)
        self.assertEqual(rows[0]["warder_id"], wid)
        self.assertEqual(rows[0]["approval"], "NO_GIT_APPROVAL")
        self.assertEqual(identity_search_rows(rows, "provider a"), rows)
        self.assertEqual(identity_search_rows(rows, "not found"), [])

    def test_missing_git_registry_is_reported_without_fake_empty_success(self):
        with tempfile.TemporaryDirectory() as temp:
            snapshot, rows, error = load_warder_identity_rows(Path(temp) / "missing.json",
                                                              Path(temp) / "no-approval.json")
        self.assertIsNone(snapshot)
        self.assertEqual(rows, [])
        self.assertIn("nie je dostupný", error)


if __name__ == "__main__":
    unittest.main()
