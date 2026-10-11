import hashlib
import tempfile
import unittest
from pathlib import Path

from source_pipeline import ingest_current_sources


class SourcePipelinePathTests(unittest.TestCase):
    def test_archives_originals_and_checkpoints_use_their_authoritative_categories(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "WARDER-PICON-FACTORY"
            sources = root / "01-SOURCES" / "source-ingest"
            state = root / "00-STATE"
            originals = root / "02-ORIGINALS"
            for path in (sources, state, originals):
                path.mkdir(parents=True)
            payload = b"synthetic verified ZIP payload"
            digest = hashlib.sha256(payload).hexdigest()
            manifest = {"schema": 1, "sources": [{
                "key": "vhannibal", "url": "https://example.test/current.zip",
                "sha256": digest, "version": "fixture-1"}]}

            def downloader(_url, _digest, target, _allowed_hosts):
                target = Path(target)
                target.parent.mkdir(parents=True)
                target.write_bytes(payload)

            def importer(_archive, target):
                target = Path(target)
                target.mkdir(parents=True)
                (target / "service.png").write_bytes(b"original PNG bytes")
                return {"imported": 1, "skipped": 0}

            result = ingest_current_sources(manifest, sources, {"example.test"},
                                            downloader=downloader, importer=importer,
                                            state_dir=state, originals_dir=originals)
            archive = sources / "archives" / "vhannibal" / (digest + ".zip")
            original = originals / "vhannibal" / "service.png"
            checkpoint = state / "source-state.json"
            self.assertEqual(result["processed"][0]["imported"], 1)
            self.assertTrue(archive.is_file())
            self.assertTrue(original.is_file())
            self.assertTrue(checkpoint.is_file())
            self.assertFalse((sources / "originals").exists())
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), digest)
            self.assertEqual(original.read_bytes(), b"original PNG bytes")


if __name__ == "__main__":
    unittest.main()
