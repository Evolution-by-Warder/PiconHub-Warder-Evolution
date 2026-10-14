import gzip
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

from openatv_rendered_candidates import CandidateBundleError, RenderedCandidateBundle


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _png(style):
    image = Image.new("RGBA", (220, 132), (0, 0, 0, 0))
    if style == "transparent":
        ImageDraw.Draw(image).rectangle((40, 30, 180, 100), fill=(235, 30, 60, 255))
    elif style == "white":
        image.paste((255, 255, 255, 255), (0, 0, 220, 132))
        ImageDraw.Draw(image).rectangle((40, 30, 180, 100), fill=(0, 0, 0, 255))
    else:
        image.paste((0, 0, 0, 255), (0, 0, 220, 132))
        ImageDraw.Draw(image).rectangle((40, 30, 180, 100), fill=(255, 255, 255, 255))
    result = io.BytesIO()
    image.save(result, format="PNG")
    return result.getvalue()


def _make_bundle(root):
    date = "20261014"
    run_id = date + "-openatv-test"
    source_sha = "a" * 64
    outputs = {style: _png(style) for style in ("transparent", "white", "black")}
    row_outputs = {
        style: {"bytes": len(data), "path": f"candidates/aa/{source_sha}/{style}.png", "sha256": _sha(data)}
        for style, data in outputs.items()
    }
    row = {"source_artwork_sha256": source_sha, "source_id": "openatv8",
           "status": "TECHNICAL_CANDIDATE_QA_PASS", "outputs": row_outputs}
    candidate_ledger = gzip.compress((json.dumps(row, sort_keys=True) + "\n").encode(), mtime=0)
    source_ledger = gzip.compress((json.dumps({"source_id": "openatv8"}) + "\n").encode(), mtime=0)
    summary = {"source_id": "openatv8", "status": "COMPLETED", "run_id": run_id,
               "unique_candidate_artwork": 1, "qa_pass_triplets": 1,
               "output_png_count": 3, "source_png_count_sha_verified": 1}
    summary_bytes = (json.dumps(summary, sort_keys=True) + "\n").encode()
    names = {
        "candidate": f"WARDER-OPENATV-CANDIDATE-LEDGER-{date}.jsonl.gz",
        "source": f"WARDER-OPENATV-SOURCE-OBSERVATIONS-{date}.jsonl.gz",
        "summary": f"WARDER-OPENATV-PRODUCTION-SUMMARY-{date}.json",
    }
    part_paths = {}
    for index in range(1, 5):
        path = root / f"WARDER-OPENATV-TECHNICAL-CANDIDATES-{date}-PART-{index:02d}-OF-04.zip"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            member_names = []
            if index == 1:
                for style, data in outputs.items():
                    member = row_outputs[style]["path"]
                    archive.writestr(member, data)
                    member_names.append(member)
            metadata = {"run_id": run_id, "part": index, "parts": 4,
                        "status": "TECHNICAL_CANDIDATE_NOT_APPROVED",
                        "png_count": len(member_names), "triplet_count": int(index == 1)}
            archive.writestr("part-metadata.json", json.dumps(metadata))
        part_paths[index] = path
    checksum_rows = []
    for path in part_paths.values():
        checksum_rows.append(f"{_sha(path.read_bytes())}  {path.name}")
    manifest_members = {
        names["candidate"]: candidate_ledger,
        names["source"]: source_ledger,
        names["summary"]: summary_bytes,
    }
    checksum_rows.extend(f"{_sha(data)}  {name}" for name, data in manifest_members.items())
    manifest_path = root / f"WARDER-OPENATV-PRODUCTION-MANIFESTS-{date}.zip"
    with zipfile.ZipFile(manifest_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in manifest_members.items():
            archive.writestr(name, data)
        archive.writestr("SHA256SUMS.txt", "\n".join(checksum_rows) + "\n")
    return part_paths, manifest_path, source_sha, outputs


class RenderedCandidateBundleTests(unittest.TestCase):
    def test_verified_bundle_imports_a_complete_triplet_and_resumes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "bundle"
            root.mkdir()
            _, _, source_sha, outputs = _make_bundle(root)
            checkpoint = Path(tmp) / "candidate-checkpoint.json"
            bundle = RenderedCandidateBundle.load(root, checkpoint_path=checkpoint)
            self.assertEqual(len(bundle.rows), 1)
            output_root = Path(tmp) / "output"
            kwargs = {"render_revision": "test-render-revision",
                      "template_sha256": {"white": "b" * 64, "black": "c" * 64}}
            self.assertEqual(bundle.install_triplet(source_sha, output_root, **kwargs), "IMPORTED")
            folder = output_root / source_sha[:2] / source_sha
            for style, expected in outputs.items():
                self.assertEqual(hashlib.sha256((folder / (style + ".png")).read_bytes()).hexdigest(), _sha(expected))
                self.assertEqual((folder / (style + ".render-revision")).read_text(), "test-render-revision")
            bundle.close()
            resumed = RenderedCandidateBundle.load(root, checkpoint_path=checkpoint)
            self.assertEqual(resumed.install_triplet(source_sha, output_root, **kwargs), "ALREADY_PRESENT")
            resumed.close()

    def test_archive_digest_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "bundle"
            root.mkdir()
            parts, _, _, _ = _make_bundle(root)
            with parts[1].open("ab") as stream:
                stream.write(b"tampered")
            with self.assertRaisesRegex(CandidateBundleError, "ARCHIVE_SHA256_MISMATCH"):
                RenderedCandidateBundle.load(root)


if __name__ == "__main__":
    unittest.main()
