import base64
import gzip
import hashlib
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from urllib.parse import urlsplit

from artwork_pixel_groups import pixel_fingerprints_for_queue
from PIL import Image
from review_decision_groups import build_decision_groups
from review_evidence_export import build_review_evidence_export
from review_evidence_upload import upload_review_evidence, retry_review_evidence_exports, _validate_no_private_payload

def review(review_id, ref, sha):
    return {
        "review_id": review_id, "workstream": "ARTWORK_REVIEW", "decision": "PENDING",
        "category": "REGISTRY_MATCH", "candidate_identity": ref,
        "reasons": ["EXISTING_SERVICE_DIFFERENT_ART"], "source_origin": "openatv8",
        "source_origins": ["openatv8"], "sha256": sha,
        "original": r"C:\Users\Private\02-ORIGINALS\openatv8\schema-3\secret-name.png",
        "service_label": "BBC One",
        "source_evidence": [{"sha256": sha, "source": r"C:\Users\Private\02-ORIGINALS\openatv8\schema-3\secret-name.png"}],
        "master_locations": [{"style": "transparent", "sha256": "f"*64}],
        "artwork_review_units": [{
            "representative_sha256": sha, "pixel_sha256": "1"*64,
            "master_pixel_sha256": ["2"*64],
            "master_sha256": ["f"*64],
            "master_pixel_comparison": "NO_PIXEL_EXACT_SAME_SERVICE_MASTER",
        }],
    }

class Response:
    def __init__(self, body=b"", status=200):
        self.body, self.status = body, status
    def read(self): return self.body
    def __enter__(self): return self
    def __exit__(self, *args): return False

class MemoryGitHub:
    def __init__(self): self.values = {}
    def __call__(self, request, timeout=30):
        url = urlsplit(request.full_url)
        path = url.path.rsplit("/contents/", 1)[-1]
        if request.method == "GET":
            if path not in self.values:
                raise urllib.error.HTTPError(request.full_url, 404, "missing", {}, None)
            body = {"encoding": "base64",
                    "content": base64.b64encode(self.values[path]).decode("ascii")}
            return Response(json.dumps(body).encode())
        data = json.loads(request.data.decode())
        value = base64.b64decode(data["content"])
        self.values[path] = value
        return Response(b"{}", 201)

class ReviewEvidenceTests(unittest.TestCase):
    def test_export_is_one_record_per_active_task_and_anonymized(self):
        items = [review("WR-ONE", "1:0:1:2:3:4:5:6:7:8:9:10", "a"*64)]
        groups = build_decision_groups({"items": items})
        queue = {"items": items, "decision_groups": groups["groups"]}
        report = build_review_evidence_export(queue, "20261013-161546-118977",
            pixel_evidence={"a"*64: "1"*64})
        self.assertEqual(report["active_review_tasks"], 1)
        self.assertEqual(len(report["records"]), 1)
        record = report["records"][0]
        self.assertEqual(record["review_id"], "WR-ONE")
        self.assertTrue(record["service_reference"].startswith("sha256:"))
        self.assertEqual(record["candidate_artworks"][0]["decoded_pixel_sha256"], "1"*64)
        raw = json.dumps(report)
        self.assertNotIn("C:\\Users", raw)
        self.assertNotIn("secret-name", raw)
        self.assertNotIn("1:0:1:2:3", raw)
        self.assertFalse(report["privacy"]["images_uploaded"])
        _validate_no_private_payload(report)

    def test_exact_pixel_duplicate_is_reported_across_review_tasks(self):
        first = review("WR-A", "service-a", "a"*64)
        second = review("WR-B", "service-b", "b"*64)
        queue = {"items": [first, second],
                 "decision_groups": build_decision_groups({"items": [first, second]})["groups"]}
        report = build_review_evidence_export(queue, "20261013-161546-118977",
            pixel_evidence={"a"*64: "1"*64, "b"*64: "1"*64})
        self.assertTrue(all(row["pixel_identical_with_another_candidate"]
                            for row in report["records"]))
        self.assertEqual(report["decision_group_count"], 2)

    def test_master_covered_observation_is_audited_without_private_paths(self):
        row = review("WR-COVERED", "service-covered", "c" * 64)
        row.update({"decision": "COVERED_BY_APPROVED_MASTER",
                    "coverage_evidence_hash": "d" * 64,
                    "master_coverage_evidence_hash": "e" * 64,
                    "master_locations": [{"style": "transparent", "sha256": "f" * 64}]})
        queue = {"items": [], "covered_items": [row], "decision_groups": []}
        report = build_review_evidence_export(queue, "20261013-161546-118977")
        self.assertEqual(report["active_review_tasks"], 0)
        self.assertEqual(report["covered_observation_count"], 1)
        item = report["covered_observations"][0]
        self.assertEqual(item["review_id"], "WR-COVERED")
        self.assertEqual(item["coverage_status"], "COVERED_BY_APPROVED_MASTER")
        self.assertTrue(item["service_reference"].startswith("sha256:"))
        self.assertNotIn("C:\\Users", json.dumps(report))
        self.assertNotIn("secret-name", json.dumps(report))
        _validate_no_private_payload(report)

    def test_pixel_fingerprint_ignores_png_compression_and_reports_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shas = ["a"*64, "b"*64, "c"*64]
            image = Image.new("RGBA", (220, 132), (0, 0, 0, 0))
            image.paste((20, 80, 160, 255), (30, 20, 90, 100))
            for sha, level in zip(shas[:2], (0, 9)):
                folder = root / sha[:2] / sha
                folder.mkdir(parents=True)
                image.save(folder / "transparent.png", compress_level=level)
            broken = root / shas[2][:2] / shas[2]
            broken.mkdir(parents=True)
            (broken / "transparent.png").write_bytes(b"not a PNG")
            queue = {"items": [{"sha256": sha, "decision": "PENDING"} for sha in shas]}
            fingerprints = pixel_fingerprints_for_queue(queue, root)
            self.assertEqual(fingerprints[shas[0]], fingerprints[shas[1]])
            self.assertNotIn(shas[2], fingerprints)

    def test_upload_chunks_large_report_hashes_and_reads_back_without_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "review-evidence-20261013-161546-118977.json"
            report = {"run": "20261013-161546-118977", "active_review_tasks": 200,
                      "decision_group_count": 20,
                      "privacy": {"images_uploaded": False},
                      "records": [{"review_id": "WR-%04d"%n,
                                   "note": hashlib.sha512(str(n).encode()).hexdigest()*4}
                                  for n in range(200)]}
            path.write_text(json.dumps(report), encoding="utf-8")
            remote = MemoryGitHub()
            result = upload_review_evidence(path, token="test-token", opener=remote, chunk_bytes=1024)
            self.assertEqual(result["status"], "sent")
            self.assertTrue(result["verified"])
            self.assertGreater(result["chunks"], 1)
            manifest = json.loads(remote.values[result["manifest_path"]])
            self.assertEqual(manifest["record_count"], 200)
            chunks = b"".join(remote.values[entry["path"]] for entry in manifest["chunks"])
            self.assertEqual(hashlib.sha256(gzip.decompress(chunks)).hexdigest(),
                             manifest["uncompressed_sha256"])
            self.assertFalse(any(name.lower().endswith(".png") for name in remote.values))

    def test_offline_retry_keeps_report_for_later_without_rescan(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp); path = folder / "review-evidence-20261013-161546-118977.json"
            path.write_text(json.dumps({"run":"20261013-161546-118977","active_review_tasks":0,
                "decision_group_count":0,"privacy":{},"records":[]}), encoding="utf-8")
            def offline(*args, **kwargs): raise urllib.error.URLError("offline")
            results = retry_review_evidence_exports(folder, folder / "state.json",
                token="test-token", opener=offline, limit=1)
            self.assertEqual(results[0]["status"], "offline_or_failed")
            self.assertTrue(path.is_file())

if __name__ == "__main__":
    unittest.main()
