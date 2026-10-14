import base64
import hashlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image

from warder_identity_registry import (
    empty_approval_ledger, empty_registry, register_confirmed_identity,
    validate_master_store, validate_approval_ledger_transition,
)
from warder_master_store import (
    build_artwork_approval, build_identity_approval,
    build_approval_revocation,
    build_confirmed_identity_with_artwork,
    commit_master_transaction, validate_artwork_blob, validate_store_transition,
    BRANCH, REPOSITORY, REGISTRY_PATH, LEDGER_PATH,
)

EV = {"evidence_ref": "fixture:identity-proof", "evidence_sha256": "a" * 64,
      "occurred_at": "2026-10-14T00:00:00Z"}


class Response:
    def __init__(self, value): self.value = value
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self): return json.dumps(self.value).encode()


def png(color):
    stream = io.BytesIO()
    Image.new("RGBA", (220, 132), color).save(stream, format="PNG", optimize=False)
    return stream.getvalue()


class WarderMasterStoreTests(unittest.TestCase):
    def setUp(self):
        self.registry, self.wid = register_confirmed_identity(empty_registry(), {
            "identity_key": "fixture:service-a", "canonical_identity": {"service": "service-a"},
            "current_name": "Service A", "service_references": ["fixture-ref-a"]},
            evidence=EV, identity_confirmed=True)
        self.ledger = empty_approval_ledger()
        self.assets = {}
        for style, color in (("transparent", (0, 0, 0, 0)),
                             ("black", (0, 0, 0, 255)),
                             ("white", (255, 255, 255, 255))):
            path = f"factory/approved-picons/{self.wid}/v0001/{style}.png"
            self.assets[path] = png(color)
        self.variants = {style: hashlib.sha256(data).hexdigest()
                         for style, data in zip(("transparent", "black", "white"), self.assets.values())}
        self.paths = {style: path for style, path in zip(("transparent", "black", "white"), self.assets)}

    def approve(self, human=True):
        return build_artwork_approval(self.registry, self.ledger, warder_id=self.wid,
            approval_id="human-review-001", approved_at="2026-10-14T12:00:00Z",
            evidence_ref="review:fixture-001", evidence_sha256="b" * 64,
            review_evidence_sha256="c" * 64, variants=self.variants,
            asset_paths=self.paths, qa_evidence_ref="fixture:qa-001",
            qa_evidence_sha256="f" * 64, human_approved=human, qa_approved=True)

    def test_registry_approval_ledger_and_triplet_are_one_valid_store(self):
        registry, ledger, event = self.approve()
        self.assertEqual(validate_store_transition(self.registry, self.ledger, registry, ledger)["status"], "VALID")
        self.assertEqual(event["event_id"], registry["records"][self.wid]["approval_history_refs"][0])
        self.assertEqual(validate_master_store(registry, ledger,
            read_asset=lambda path: self.assets[path])["status"], "VALID")

    def test_new_identity_id_and_approvals_are_one_candidate_transaction(self):
        registry, ledger, wid, events = build_confirmed_identity_with_artwork(
            empty_registry(), empty_approval_ledger(), {
                "identity_key": "fixture:new-service", "canonical_identity": {"service": "new"},
                "current_name": "New Service", "service_references": ["new-ref"]},
            identity_evidence=EV, approval_id="new-service", approved_at=EV["occurred_at"],
            artwork_evidence_ref="fixture:artwork", artwork_evidence_sha256="b" * 64,
            review_evidence_sha256="c" * 64, variants=self.variants,
            asset_paths=self.paths, qa_evidence_ref="fixture:qa-new",
            qa_evidence_sha256="f" * 64, human_approved=True, qa_approved=True)
        self.assertEqual(wid, "WARDER-00000001")
        self.assertEqual(len(registry["history"]), 3)
        self.assertEqual(len(ledger["events"]), 2)
        self.assertEqual(validate_store_transition(empty_registry(), empty_approval_ledger(),
                                                   registry, ledger)["status"], "VALID")
        self.assertEqual(validate_master_store(registry, ledger,
            read_asset=lambda path: self.assets[path])["status"], "VALID")

    def test_local_or_implicit_approval_is_rejected(self):
        with self.assertRaises(PermissionError):
            self.approve(human=False)

    def test_identity_approval_is_separate_append_only_git_event(self):
        registry, ledger, event = build_identity_approval(self.registry, self.ledger,
            warder_id=self.wid, approval_id="human-identity-001",
            approved_at="2026-10-14T12:00:00Z", evidence_ref="review:identity-001",
            evidence_sha256="d" * 64, review_evidence_sha256="e" * 64,
            human_approved=True)
        self.assertEqual(event["decision"], "IDENTITY_APPROVED")
        self.assertEqual(registry["records"][self.wid]["approval_history_refs"], [event["event_id"]])
        self.assertEqual(validate_store_transition(self.registry, self.ledger, registry, ledger)["status"], "VALID")

    def test_revocation_appends_event_and_keeps_original_approval(self):
        registry, ledger, first = build_identity_approval(self.registry, self.ledger,
            warder_id=self.wid, approval_id="identity-approve", approved_at=EV["occurred_at"],
            evidence_ref="fixture:identity-review", evidence_sha256="b" * 64,
            review_evidence_sha256="c" * 64, human_approved=True)
        registry, ledger, revoked = build_approval_revocation(registry, ledger,
            warder_id=self.wid, revokes_event_id=first["event_id"],
            approval_id="identity-revoke", approved_at="2026-10-15T00:00:00Z",
            evidence_ref="fixture:revocation", evidence_sha256="f" * 64,
            review_evidence_sha256="e" * 64, human_approved=True)
        self.assertEqual(len(ledger["events"]), 2)
        self.assertEqual(ledger["events"][0], first)
        self.assertEqual(revoked["decision"], "APPROVAL_REVOKED")
        self.assertEqual(validate_master_store(registry, ledger)["status"], "VALID")

    def test_modified_approval_history_is_rejected(self):
        registry, ledger, _ = self.approve()
        modified = json.loads(json.dumps(ledger))
        modified["events"][0]["approved_at"] = "later"
        self.assertEqual(validate_approval_ledger_transition(ledger, modified)["status"], "INVALID")
        self.assertEqual(validate_store_transition(self.registry, self.ledger, registry, modified)["status"], "INVALID")

    def test_asset_byte_change_fails_sha_and_pixel_checks(self):
        data = self.assets[self.paths["transparent"]]
        with self.assertRaisesRegex(ValueError, "ARTWORK_SHA256_MISMATCH"):
            validate_artwork_blob(data + b"tampered", self.variants["transparent"])
        stream = io.BytesIO()
        Image.new("RGBA", (100, 100), (5, 6, 7, 255)).save(stream, format="PNG")
        wrong_size = stream.getvalue()
        with self.assertRaisesRegex(ValueError, "ARTWORK_NOT_220x132_RGBA_PNG"):
            validate_artwork_blob(wrong_size, hashlib.sha256(wrong_size).hexdigest())

    def test_fresh_clone_recovers_master_json_and_approved_png_exactly(self):
        registry, ledger, _ = self.approve()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            paths = {"factory/registry/warder-identity-registry.json":
                     json.dumps(registry, sort_keys=True, indent=2) + "\n",
                     "factory/registry/master-approval-ledger.json":
                     json.dumps(ledger, sort_keys=True, indent=2) + "\n"}
            for path, content in paths.items():
                destination = root / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(content, encoding="utf-8")
            for path, data in self.assets.items():
                destination = root / path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(data)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=fixture",
                            "-c", "user.email=fixture@example.invalid", "add", "."], check=True)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=fixture",
                            "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture master"], check=True)
            clone = Path(tmp) / "clean-clone"
            subprocess.run(["git", "clone", "-q", str(root), str(clone)], check=True)
            for path, content in paths.items():
                self.assertEqual((clone / path).read_text(encoding="utf-8"), content)
            for path, data in self.assets.items():
                self.assertEqual((clone / path).read_bytes(), data)
            self.assertEqual(validate_master_store(
                json.loads((clone / "factory/registry/warder-identity-registry.json").read_text()),
                json.loads((clone / "factory/registry/master-approval-ledger.json").read_text()),
                read_asset=lambda path: (clone / path).read_bytes())["status"], "VALID")

    def test_github_write_is_one_cas_guarded_development_commit(self):
        registry, ledger, _ = build_identity_approval(self.registry, self.ledger,
            warder_id=self.wid, approval_id="identity-approve", approved_at=EV["occurred_at"],
            evidence_ref="fixture:identity-review", evidence_sha256="b" * 64,
            review_evidence_sha256="c" * 64, human_approved=True)
        head, new_commit = "f" * 40, "e" * 40
        base_files = {REGISTRY_PATH: json.dumps(self.registry, sort_keys=True, indent=2) + "\n",
                      LEDGER_PATH: json.dumps(self.ledger, sort_keys=True, indent=2) + "\n"}
        new_files = {REGISTRY_PATH: json.dumps(registry, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                     LEDGER_PATH: json.dumps(ledger, ensure_ascii=False, sort_keys=True, indent=2) + "\n"}
        calls = []
        branch_count = 0
        blob_count = 0
        def opener(request, timeout):
            nonlocal branch_count, blob_count
            url, method = request.full_url, request.method
            payload = json.loads(request.data) if request.data else None
            calls.append((method, url, payload))
            if method == "GET" and "/branches/" in url:
                branch_count += 1
                commit = new_commit if branch_count == 3 else head
                return Response({"commit": {"sha": commit}})
            if method == "GET" and "/contents/" in url:
                path = urlparse(url).path.split("/contents/", 1)[1]
                selected = new_files if "ref=" + new_commit in url else base_files
                return Response({"encoding": "base64", "content": base64.b64encode(selected[path].encode()).decode()})
            if method == "POST" and url.endswith("/git/blobs"):
                blob_count += 1
                return Response({"sha": f"{blob_count:040x}"})
            if method == "GET" and url.endswith("/git/commits/" + head):
                return Response({"tree": {"sha": "d" * 40}})
            if method == "POST" and url.endswith("/git/trees"):
                return Response({"sha": "c" * 40})
            if method == "POST" and url.endswith("/git/commits"):
                self.assertEqual(payload["parents"], [head])
                return Response({"sha": new_commit})
            if method == "PATCH" and url.endswith("/git/refs/heads/" + BRANCH):
                self.assertEqual(payload, {"sha": new_commit, "force": False})
                return Response({})
            raise AssertionError((method, url))
        result = commit_master_transaction(token="mock-write-token", expected_head=head,
            registry=registry, approval_ledger=ledger, opener=opener)
        self.assertEqual(result["status"], "COMMITTED_VERIFIED")
        self.assertEqual(result["branch"], BRANCH)
        self.assertEqual(result["commit"], new_commit)
        self.assertEqual(result["paths"], sorted([REGISTRY_PATH, LEDGER_PATH]))
        self.assertTrue(all(REPOSITORY in url for _, url, _ in calls))
        self.assertFalse(any("warder-master-production" in url for _, url, _ in calls))

    def test_missing_write_token_keeps_decision_pending_without_network(self):
        with self.assertRaisesRegex(PermissionError, "PENDING"):
            commit_master_transaction(token="", expected_head="f" * 40,
                registry=self.registry, approval_ledger=self.ledger,
                opener=lambda *_args, **_kwargs: self.fail("must not contact GitHub"))

    def test_stale_expected_head_fails_before_reading_or_writing_master(self):
        calls = []
        def opener(request, timeout):
            calls.append((request.method, request.full_url))
            return Response({"commit": {"sha": "a" * 40}})
        with self.assertRaisesRegex(RuntimeError, "STALE_EXPECTED_HEAD"):
            commit_master_transaction(token="mock-write-token", expected_head="f" * 40,
                registry=self.registry, approval_ledger=self.ledger, opener=opener)
        self.assertEqual(len(calls), 1)
        self.assertIn("factory-warder-development", calls[0][1])


if __name__ == "__main__":
    unittest.main()
