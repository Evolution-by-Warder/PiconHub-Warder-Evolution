import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from workspace_paths import DIRECTORIES, WINDOWS_ROOT, read_only_preflight, resolve_root, workspace_paths


def synthetic_workspace(root):
    root = Path(root)
    for name, _ in DIRECTORIES:
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


class WorkspaceArchitectureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def test_windows_resolves_only_the_authoritative_d_drive_root(self):
        for env in ({}, {"WARDER_PICON_FACTORY_ROOT": r"C:\Users\PC\WARDER-PICONS"},
                    {"WARDER_PICON_FACTORY_ROOT": r"D:\WARDER-PICONS"}):
            self.assertEqual(resolve_root(env=env, platform="nt", home=self.base), WINDOWS_ROOT)

    def test_windows_ignores_every_environment_root_override(self):
        sandbox = self.base / "synthetic"
        self.assertEqual(resolve_root(env={"WARDER_FACTORY_TEST_MODE": "1",
                                           "WARDER_PICON_FACTORY_TEST_ROOT": str(sandbox),
                                           "WARDER_PICON_FACTORY_ROOT": str(sandbox)},
                                      platform="nt", home=self.base), WINDOWS_ROOT)

    def test_exact_thirteen_category_mapping_and_operational_roles(self):
        root = WINDOWS_ROOT
        paths = workspace_paths(root)
        self.assertEqual(tuple(name for name, _ in DIRECTORIES), tuple(f"{i:02d}-{label}" for i, label in [
            (0, "STATE"), (1, "SOURCES"), (2, "ORIGINALS"), (3, "REGISTRY"), (4, "WORK"),
            (5, "QA"), (6, "OUTPUT"), (7, "PUBLISH-STAGING"), (8, "REPORTS"), (9, "LOGS"),
            (10, "TOOLS"), (11, "APP"), (12, "ARCHIVE")]))
        expected = {
            "state": "00-STATE", "inbox": "01-SOURCES/LOCAL-INBOX", "originals": "02-ORIGINALS",
            "registry": "03-REGISTRY", "output": "04-WORK/PICONS", "exceptions": "05-QA/EXCEPTIONS",
            "final": "06-OUTPUT/PICONS", "publish": "07-PUBLISH-STAGING", "reports": "08-REPORTS",
            "logs": "09-LOGS", "tools": "10-TOOLS", "app": "11-APP/WARDER-PICON-FACTORY",
            "archive": "12-ARCHIVE",
        }
        for key, suffix in expected.items():
            self.assertEqual(str(paths[key]).replace("\\", "/").replace("D:/WARDER-PICON-FACTORY/", ""), suffix)
        self.assertEqual(paths["db"], root / "00-STATE" / "factory.sqlite3")
        self.assertEqual(paths["source_manifest"], root / "01-SOURCES" / "source-manifest.json")
        self.assertEqual(paths["ledger_path"], root / "05-QA" / "review-decisions.json")
        self.assertEqual(paths["legacy_ledger"], root / "11-APP" / ".factory-data" / "review-decisions.json")
        self.assertEqual(paths["master_root"], root / "03-REGISTRY" / "MASTER-SNAPSHOTS")
        self.assertEqual(paths["chocho_positions"], root / "11-APP" / ".factory-data" / "chocholousek-positions.json")

    def test_missing_d_and_missing_root_block_read_only_preflight(self):
        root = self.base / "drive-D" / "WARDER-PICON-FACTORY"
        result = read_only_preflight(root)
        self.assertFalse(result.ok)
        self.assertEqual(result.checked, 0)
        self.assertEqual(len(result.missing), 13)
        self.assertFalse(root.exists())

    def test_incomplete_structure_is_inventory_only_and_never_completed_automatically(self):
        root = self.base / "WARDER-PICON-FACTORY"
        (root / "00-STATE").mkdir(parents=True)
        marker = root / "00-STATE" / "existing-checkpoint.json"
        marker.write_text('{"run":"kept"}\n', encoding="utf-8")
        digest = hashlib.sha256(marker.read_bytes()).hexdigest()
        result = read_only_preflight(root)
        self.assertFalse(result.ok)
        self.assertEqual(len(result.missing), 12)
        self.assertEqual(hashlib.sha256(marker.read_bytes()).hexdigest(), digest)
        self.assertEqual(sorted(p.name for p in root.iterdir()), ["00-STATE"])

    def test_reparse_point_inside_workspace_blocks_preflight(self):
        root = synthetic_workspace(self.base / "WARDER-PICON-FACTORY")
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "secret.png").write_bytes(b"do not traverse")
        link = root / "02-ORIGINALS" / "external"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation is unavailable")
        result = read_only_preflight(root)
        self.assertFalse(result.ok)
        self.assertTrue(any("UNSAFE_REPARSE" in item for item in result.unreadable))
        self.assertFalse(any(str(outside) in item for item in result.unreadable if item.endswith("secret.png")))

    def test_engine_refuses_incomplete_workspace_before_creating_state(self):
        from unittest.mock import patch
        import engine
        root = self.base / "WARDER-PICON-FACTORY"
        synthetic_workspace(root)
        paths = workspace_paths(root)
        (root / "12-ARCHIVE").rmdir()
        patch_values = {
            "ROOT": root, "APP": paths["app"], "APP_DATA": paths["app_data"],
            "INBOX": paths["inbox"], "SOURCE_INGEST": paths["ingest"],
            "ORIGINALS": paths["originals"], "REGISTRY": paths["registry"],
            "MASTER_ROOT": paths["master_root"], "OUTPUT": paths["output"],
            "FINAL_PICONS": paths["final"], "EXCEPTIONS": paths["exceptions"],
            "REPORTS": paths["reports"], "LOGS": paths["logs"], "DB": paths["db"],
        }
        with patch.multiple(engine, **patch_values):
            with self.assertRaises(PermissionError):
                engine.Factory(lambda *_: None)
        self.assertFalse(paths["app"].exists())
        self.assertFalse(paths["db"].exists())
        self.assertEqual({p.name for p in root.iterdir()}, {name for name, _ in DIRECTORIES if name != "12-ARCHIVE"})

    def test_legacy_app_database_is_read_only_fallback_not_migrated(self):
        import engine
        canonical = sqlite3.connect(":memory:")
        legacy_path = self.base / "11-APP" / ".factory-data" / "factory.sqlite3"
        legacy_path.parent.mkdir(parents=True)
        legacy = sqlite3.connect(legacy_path)
        schema = "CREATE TABLE files (path TEXT PRIMARY KEY, sha256 TEXT, size INTEGER, modified_ns INTEGER, status TEXT, last_run TEXT)"
        for connection in (canonical, legacy):
            connection.execute(schema)
        legacy.execute("INSERT INTO files VALUES (?,?,?,?,?,?)", ("service.png", "abc", 5, 10, "DONE", "old"))
        legacy.commit(); legacy.close()
        legacy_sha = hashlib.sha256(legacy_path.read_bytes()).hexdigest()
        factory = object.__new__(engine.Factory)
        factory.db = canonical
        factory.legacy_db = sqlite3.connect(legacy_path.as_uri() + "?mode=ro", uri=True)
        self.addCleanup(canonical.close)
        self.addCleanup(factory.legacy_db.close)
        self.assertEqual(factory.cached_file(("sha256", "size"), "service.png"), ("abc", 5))
        self.assertIsNone(canonical.execute("SELECT * FROM files WHERE path='service.png'").fetchone())
        self.assertEqual(hashlib.sha256(legacy_path.read_bytes()).hexdigest(), legacy_sha)

    def test_full_preflight_reads_inventory_without_changing_sha256_or_tree(self):
        root = synthetic_workspace(self.base / "WARDER-PICON-FACTORY")
        files = {
            root / "00-STATE" / "vhannibal-state.json": b'{"status":"updated"}',
            root / "01-SOURCES" / "motor.zip": b"archive bytes",
            root / "02-ORIGINALS" / "logo.png": b"original image bytes",
            root / "03-REGISTRY" / "warder-master.json": b"approved registry",
            root / "04-WORK" / "candidate.png": b"rendered candidate",
            root / "05-QA" / "review-queue.json": b"manual queue",
            root / "06-OUTPUT" / "approved.png": b"approved output",
            root / "12-ARCHIVE" / "historical.dat": b"history",
        }
        for path, content in files.items():
            path.write_bytes(content)
        hashes_before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}
        names_before = {path.relative_to(root).as_posix() for path in root.rglob("*")}
        result = read_only_preflight(root, full_scan=True)
        self.assertTrue(result.ok, result.findings)
        self.assertEqual(result.checked, 13)
        self.assertEqual(result.inventory["01-SOURCES"]["archives"], 1)
        self.assertEqual(result.inventory["02-ORIGINALS"]["png"], 1)
        self.assertEqual(result.inventory["06-OUTPUT"]["png"], 1)
        self.assertEqual({path: hashlib.sha256(path.read_bytes()).hexdigest() for path in files}, hashes_before)
        self.assertEqual({path.relative_to(root).as_posix() for path in root.rglob("*")}, names_before)

    def test_dashboard_counts_read_state_and_qa_from_authoritative_categories(self):
        from factory_workspace import latest_review_counts, source_rows
        root = synthetic_workspace(self.base / "WARDER-PICON-FACTORY")
        paths = workspace_paths(root)
        paths["state"].joinpath("vhannibal-state.json").write_text(
            json.dumps({"status": "updated", "imported_png": 21}), encoding="utf-8")
        paths["inbox"].mkdir()
        paths["inbox"].joinpath("local.zip").write_bytes(b"ZIP")
        paths["exceptions"].mkdir(parents=True, exist_ok=True)
        items = [{"review_id": f"WR-{index:016X}", "category": "REGISTRY_MATCH",
                  "workstream": ("IDENTITY_VERIFICATION" if index < 2 else "ARTWORK_REVIEW" if index < 6 else "TECHNICAL_QA"),
                  "candidate_identity": f"ref-{index}", "reasons": ["fixture"], "decision": "PENDING"}
                 for index in range(8)]
        paths["exceptions"].joinpath("review-queue-current.json").write_text(json.dumps({
            "count": 8, "items": items,
            "workstream_counts": {"IDENTITY_VERIFICATION": 2, "ARTWORK_REVIEW": 4, "TECHNICAL_QA": 2},
        }), encoding="utf-8")
        rows = source_rows(paths["ingest"], paths["inbox"], paths["source_manifest"],
                           paths["chocho_positions"], paths["master_paths"], paths["state"], paths["app_data"])
        _, counts = latest_review_counts(paths["exceptions"], paths["reports"])
        self.assertEqual(rows[0][1], "updated")
        self.assertIn("imported_png: 21", rows[0][2])
        self.assertEqual(rows[-1][2], "1 ZIP · 0 PNG")
        self.assertEqual(counts, {"total": 8, "IDENTITY_VERIFICATION": 2,
                                  "ARTWORK_REVIEW": 4, "TECHNICAL_QA": 2,
                                  "technical_items": 8})
        self.assertTrue(read_only_preflight(root).ok)

    def test_startup_preflight_does_not_walk_large_nested_png_trees(self):
        from unittest.mock import patch
        root = synthetic_workspace(self.base / "WARDER-PICON-FACTORY")
        nested = root / "02-ORIGINALS" / "package" / "picon"
        nested.mkdir(parents=True)
        for index in range(250):
            (nested / f"{index}.png").write_bytes(b"png")
        with patch("workspace_paths._category_counts", side_effect=AssertionError("recursive scan called")):
            result = read_only_preflight(root)
        self.assertTrue(result.ok, result.findings)
        self.assertEqual(result.inventory["02-ORIGINALS"]["scan"], "STRUCTURE_ONLY")
        self.assertEqual(result.inventory["02-ORIGINALS"]["png"], 0)

    def test_dashboard_reads_existing_app_checkpoints_without_moving_them(self):
        from factory_workspace import source_rows
        root = synthetic_workspace(self.base / "WARDER-PICON-FACTORY")
        paths = workspace_paths(root)
        paths["app_data"].mkdir(parents=True)
        legacy = paths["app_data"] / "vhannibal-state.json"
        legacy.write_text(json.dumps({"status": "updated", "imported_png": 17}), encoding="utf-8")
        original_sha = hashlib.sha256(legacy.read_bytes()).hexdigest()
        rows = source_rows(paths["ingest"], paths["inbox"], paths["source_manifest"],
                           paths["chocho_positions"], paths["master_paths"], paths["state"], paths["app_data"])
        self.assertEqual(rows[0][1], "updated")
        self.assertIn("imported_png: 17", rows[0][2])
        self.assertEqual(hashlib.sha256(legacy.read_bytes()).hexdigest(), original_sha)
        self.assertFalse(paths["state"].joinpath("vhannibal-state.json").exists())


if __name__ == "__main__":
    unittest.main()
