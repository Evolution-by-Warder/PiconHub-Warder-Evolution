import json
import tempfile
import unittest
from pathlib import Path

from review_ui import latest_review
from source_cycle import LEGACY_QUEUE_COUNTS


class LegacyQueueUiTests(unittest.TestCase):
    def test_cancelled_queue_is_never_selected_after_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            old_items = []
            old_items.extend({"workstream": "IDENTITY_VERIFICATION"} for _ in range(LEGACY_QUEUE_COUNTS["IDENTITY_VERIFICATION"]))
            old_items.extend({"workstream": "ARTWORK_REVIEW"} for _ in range(LEGACY_QUEUE_COUNTS["ARTWORK_REVIEW"]))
            old_items.extend({"workstream": "TECHNICAL_QA"} for _ in range(LEGACY_QUEUE_COUNTS["TECHNICAL_QA"]))
            (folder / "review-queue-cancelled.json").write_text(
                json.dumps({"schema": 1, "count": len(old_items),
                            "workstream_counts": LEGACY_QUEUE_COUNTS, "items": old_items}), encoding="utf-8")
            valid = folder / "review-queue-current.json"
            valid.write_text(json.dumps({"schema": 1, "count": 1,
                                         "items": [{"review_id": "WR-0123456789ABCDEF"}]}), encoding="utf-8")
            self.assertEqual(latest_review(folder), valid)

    def test_18011_legacy_queue_is_not_reloaded_after_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            old_items = ([{"workstream": "IDENTITY_VERIFICATION"}] * 12133 +
                         [{"workstream": "ARTWORK_REVIEW"}] * 5877 +
                         [{"workstream": "TECHNICAL_QA"}])
            (folder / "review-queue-legacy-18011.json").write_text(json.dumps({
                "schema": 1, "count": 18011,
                "workstream_counts": {"IDENTITY_VERIFICATION": 12133,
                                      "ARTWORK_REVIEW": 5877, "TECHNICAL_QA": 1},
                "items": old_items}), encoding="utf-8")
            self.assertIsNone(latest_review(folder))


if __name__ == "__main__":
    unittest.main()
