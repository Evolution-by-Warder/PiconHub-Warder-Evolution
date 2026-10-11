import tempfile
import unittest
from pathlib import Path

from factory_update_transaction import begin, resolve


class UpdatePreservationTests(unittest.TestCase):
    def _stage(self, parent, name, payload):
        stage = parent / name
        stage.mkdir()
        (stage / "engine.py").write_text(payload, encoding="utf-8")
        (stage / ".verified-sha256").write_text("verified\n", encoding="ascii")
        return stage

    def test_confirmed_update_keeps_previous_app_and_unknown_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            app = parent / "WARDER-PICON-FACTORY"
            app.mkdir()
            (app / "engine.py").write_text("old app", encoding="utf-8")
            (app / "operator-notes.txt").write_bytes(b"keep me")
            stage = self._stage(parent, "stage", "new app")
            begin(stage, app, authorized=True)

            self.assertEqual(resolve(app, gui_ready=True), "confirmed")
            previous = list(parent.glob("WARDER-PICON-FACTORY.previous-*"))
            self.assertEqual(len(previous), 1)
            self.assertEqual((previous[0] / "engine.py").read_text(), "old app")
            self.assertEqual((previous[0] / "operator-notes.txt").read_bytes(), b"keep me")
            self.assertEqual((app / "engine.py").read_text(), "new app")

    def test_failed_start_rolls_back_without_deleting_new_or_previous_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            app = parent / "WARDER-PICON-FACTORY"
            app.mkdir()
            (app / "engine.py").write_text("old app", encoding="utf-8")
            stage = self._stage(parent, "stage", "new app")
            begin(stage, app, authorized=True)

            self.assertEqual(resolve(app, gui_ready=False), "rolled_back")
            self.assertEqual((app / "engine.py").read_text(), "old app")
            failed = list(parent.glob("WARDER-PICON-FACTORY.failed-*"))
            self.assertEqual(len(failed), 1)
            self.assertEqual((failed[0] / "engine.py").read_text(), "new app")
            self.assertEqual(list(parent.glob("WARDER-PICON-FACTORY.previous-*")), [])


if __name__ == "__main__":
    unittest.main()
