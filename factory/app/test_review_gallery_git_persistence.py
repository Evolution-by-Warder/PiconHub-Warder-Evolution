import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from review_decision_groups import build_decision_groups
from review_gallery import ReviewGallery


def identity_item(index):
    return {
        "review_id": "WR-" + f"{index:016x}",
        "workstream": "IDENTITY_VERIFICATION",
        "candidate_identity": "same-service-reference",
        "observed_candidate_sha256": ["a" * 64],
        "reasons": ["IDENTITY_COLLISION"],
        "decision": "PENDING",
    }


class ReviewGalleryGitPersistenceTests(unittest.TestCase):
    def test_ui_submits_more_than_ten_selected_exception_groups_without_a_manual_page(self):
        rows = [dict(identity_item(index), candidate_identity=f"service-{index}")
                for index in range(1, 12)]
        groups = build_decision_groups({"items": rows})["groups"]
        selected = {group["decision_group_id"]: SimpleNamespace(get=lambda: True) for group in groups}
        submit = Mock()
        gallery = SimpleNamespace(
            write_enabled=lambda: True,
            groups=groups,
            selected_scopes=selected,
            _scope=lambda group: {"decision_group_id": group["decision_group_id"],
                                  "group_evidence_sha256": group["group_evidence_hash"],
                                  "items": [row for row in rows if row["review_id"] in group["member_review_ids"]]},
            batch_decision=SimpleNamespace(get=lambda: "DEFERRED"),
            _submit_scopes=submit,
        )
        with patch("review_gallery.messagebox.askyesno", return_value=True):
            ReviewGallery.submit_selected_batch(gallery)
        self.assertEqual(len(submit.call_args.args[0]), 11)
        self.assertEqual(submit.call_args.args[1], "DEFERRED")

    def test_group_decision_stages_git_transaction_and_does_not_write_local_or_hide_items(self):
        rows = [identity_item(1), identity_item(2)]
        group = build_decision_groups({"items": rows})["groups"][0]
        scope = {
            "decision_group_id": group["decision_group_id"],
            "group_evidence_sha256": group["group_evidence_hash"],
            "items": rows,
        }
        submit = Mock()
        with tempfile.TemporaryDirectory() as tmp:
            local_ledger = Path(tmp) / "legacy-decisions.json"
            gallery = SimpleNamespace(
                write_enabled=lambda: True,
                items=rows,
                groups=[group],
                ledger_path=local_ledger,
                _scope=lambda _group: scope,
                _submit_scopes=submit,
                reload=Mock(),
            )
            with patch("review_gallery.messagebox.askyesno", return_value=True):
                ReviewGallery.decide_group(
                    gallery, group, "IDENTITY_AMBIGUOUS", "Owner recorded ambiguity"
                )
            submit.assert_called_once_with([scope], "IDENTITY_AMBIGUOUS")
            self.assertEqual(gallery.items, rows)
            self.assertFalse(local_ledger.exists())

    def test_uncommitted_git_result_keeps_saved_review_items_visible(self):
        rows = [identity_item(1)]
        status = Mock()
        gallery = SimpleNamespace(
            items=rows,
            git_status=status,
        )
        ReviewGallery._git_write_done(
            gallery,
            {"batch_id": "BATCH-fixture"},
            {"status": "FAILED", "error": "offline"},
        )
        self.assertEqual(gallery.items, rows)
        status.configure.assert_called_once()
        self.assertIn("FAILED / UNSAVED", status.configure.call_args.kwargs["text"])


if __name__ == "__main__":
    unittest.main()
