"""Regression coverage for QA repair accounting, cache safety, and scan completion."""
from contextlib import ExitStack
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

import engine
from workspace_paths import DIRECTORIES, workspace_paths


class RepairAccountingTests(unittest.TestCase):
    def test_zero_repairs_does_not_iterate_integer_and_keeps_signatures(self):
        repaired_count = 0
        repaired_shas = set()
        current = {"a": {"transparent": "old"}}
        engine._refresh_repaired_signatures(repaired_shas, current, {})
        self.assertEqual(repaired_count, 0)
        self.assertEqual(current["a"], {"transparent": "old"})

    def test_one_and_multiple_successful_repairs_refresh_only_verified_sha(self):
        repaired_count = 0
        repaired_shas = set()
        repaired_signatures = {}
        current = {"a": "old-a", "b": "old-b", "c": "untouched"}
        for sha, signature in (("a", "new-a"), ("b", "new-b")):
            if engine._record_repaired_sha(sha, True, [], repaired_shas):
                repaired_count += 1
                repaired_signatures[sha] = signature
        engine._refresh_repaired_signatures(repaired_shas, current, repaired_signatures)
        self.assertEqual(repaired_count, 2)
        self.assertEqual(repaired_shas, {"a", "b"})
        self.assertEqual(current, {"a": "new-a", "b": "new-b", "c": "untouched"})

    def test_failed_repair_or_remaining_qa_finding_is_not_counted(self):
        repaired_shas = set()
        self.assertFalse(engine._record_repaired_sha("failed", False, [], repaired_shas))
        self.assertFalse(engine._record_repaired_sha("still-bad", True, ["CORRUPT_BLACK"], repaired_shas))
        self.assertEqual(repaired_shas, set())

    def test_output_signature_uses_content_not_timestamp_as_authority(self):
        before = {"transparent": {"sha256": "pixels-a", "stat": [1, 2, 3, 4]},
                  "black": {"sha256": "pixels-b", "stat": [1, 2, 3, 4]},
                  "white": {"sha256": "pixels-c", "stat": [1, 2, 3, 4]},
                  "black_template_sha256": "template-b", "white_template_sha256": "template-w"}
        metadata_only = {"transparent": {"sha256": "pixels-a", "stat": [1, 2, 3, 99]},
                         "black": {"sha256": "pixels-b", "stat": [1, 2, 3, 99]},
                         "white": {"sha256": "pixels-c", "stat": [1, 2, 3, 99]},
                         "black_template_sha256": "template-b", "white_template_sha256": "template-w"}
        changed_bytes = dict(metadata_only, transparent={"sha256": "pixels-x", "stat": [1, 2, 3, 99]})
        self.assertTrue(engine._qa_signature_unchanged(before, metadata_only))
        self.assertFalse(engine._qa_signature_unchanged(before, changed_bytes))
        self.assertFalse(engine._qa_signature_unchanged(None, None))

    def test_qa_cache_requires_matching_source_output_rules_and_schema(self):
        current = {
            "transparent": {"sha256": "sig-a", "stat": [1, 2, 3, 4]},
            "black": {"sha256": "sig-b", "stat": [1, 2, 3, 4]},
            "white": {"sha256": "sig-c", "stat": [1, 2, 3, 4]},
            "black_template_sha256": "template-a", "white_template_sha256": "template-w",
        }
        metadata_only = {
            "transparent": {"sha256": "sig-a", "stat": [1, 2, 3, 99]},
            "black": {"sha256": "sig-b", "stat": [1, 2, 3, 99]},
            "white": {"sha256": "sig-c", "stat": [1, 2, 3, 99]},
            "black_template_sha256": "template-a", "white_template_sha256": "template-w",
        }
        entry = {"source_sha256": "sha-a", "signatures": current,
                 "qa_schema": engine.QA_SCHEMA, "issues": []}
        self.assertTrue(engine._qa_cache_entry_compatible(entry, metadata_only, "sha-a"))
        changed = dict(metadata_only, black_template_sha256="template-b")
        self.assertFalse(engine._qa_cache_entry_compatible(entry, changed, "sha-a"))
        self.assertFalse(engine._qa_cache_entry_compatible(entry, current, "sha-b"))
        old_rules = dict(entry, qa_schema=engine.QA_SCHEMA - 1)
        self.assertFalse(engine._qa_cache_entry_compatible(old_rules, current, "sha-a"))
        changed["transparent"] = {"sha256": "corrupt", "stat": [1, 2, 3, 99]}
        self.assertFalse(engine._qa_cache_entry_compatible(entry, changed, "sha-a"))
        self.assertFalse(engine._qa_cache_entry_compatible(None, current, "sha-a"))


class FailedRunGuiStateTests(unittest.TestCase):
    def test_failure_clears_successful_progress_appearance(self):
        class Status:
            def set(self, value):
                self.value = value
        class Label:
            def configure(self, **kwargs):
                self.options = kwargs
        app = engine.App.__new__(engine.App)
        app.status = Status()
        app.status_label = Label()
        app.bar = {"maximum": 100, "value": 100}
        app._set_run_state("failed", "ZLYHANIE")
        self.assertEqual(app.run_state, "failed")
        self.assertEqual(app.bar, {"maximum": 1, "value": 0})
        self.assertEqual(app.status.value, "ZLYHANIE")
        self.assertEqual(app.status_label.options["foreground"], "#b00020")


class EmptyWorkspaceScanRegressionTests(unittest.TestCase):
    def test_empty_scan_completes_qa_review_audit_finalization_and_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "WARDER-PICON-FACTORY"
            for name, _purpose in DIRECTORIES:
                (root / name).mkdir(parents=True, exist_ok=True)
            paths = workspace_paths(root)
            aliases = {
                "ROOT": root,
                "_WORKSPACE": paths,
                "APP": paths["app"],
                "APP_DATA": paths["app_data"],
                "INBOX": paths["inbox"],
                "ORIGINALS": paths["originals"],
                "OUTPUT": paths["output"],
                "FINAL_PICONS": paths["final"],
                "EXCEPTIONS": paths["exceptions"],
                "REPORTS": paths["reports"],
                "REGISTRY": paths["registry"],
                "MASTER_ROOT": paths["master_root"],
                "LOGS": paths["logs"],
                "DB": paths["db"],
                "DATA": paths["data"],
                "SOURCE_STATE": paths["source_state"],
                "SOURCE_MANIFEST": paths["source_manifest"],
                "SOURCE_INGEST": paths["ingest"],
            }
            events = []
            with ExitStack() as stack:
                for name, value in aliases.items():
                    stack.enter_context(mock.patch.object(engine, name, value))
                offline_update = types.ModuleType("factory_auto_update")
                offline_update.MANIFEST_URL = "https://invalid.example/manifest.json"
                offline_update.fetch = mock.Mock(side_effect=OSError("offline"))
                offline_update.validate_manifest = mock.Mock(return_value=None)
                offline_update.version_tuple = lambda value: (0, 0, 0)
                stack.enter_context(mock.patch.dict("sys.modules", {"factory_auto_update": offline_update}))
                factory = engine.Factory(lambda kind, value: events.append((kind, value)))
                factory.fetch_sources = lambda: None
                factory.sync_peer_sources = lambda stats: None
                factory.master_paths = []
                try:
                    factory.scan()
                finally:
                    factory.db.close()
            done = [value for kind, value in events if kind == "done"]
            self.assertEqual(len(done), 1)
            stats, report_path = done[0]
            self.assertEqual(stats["scanned"], 0)
            self.assertEqual(stats["qa_repaired"], 0)
            self.assertTrue(Path(report_path).is_file())
            self.assertIn("qa_seconds", stats["phase_timings_seconds"])
            self.assertIn("review_queue_items", stats)
            self.assertIn("integrity_issues", stats)
            self.assertIn("new_candidate_finalization", stats)


if __name__ == "__main__":
    unittest.main()
