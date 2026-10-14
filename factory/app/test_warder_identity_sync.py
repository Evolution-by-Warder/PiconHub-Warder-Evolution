import base64
import binascii
import io
import urllib.error
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from warder_identity_registry import empty_approval_ledger, empty_registry
from review_gallery import format_git_sync_error
from warder_identity_sync import (API, APPROVAL_LEDGER_PATH, BRANCH, REPOSITORY, REGISTRY_PATH,
                                  fetch_registry_snapshot, load_cached_snapshot,
                                  sync_registry, validate_snapshot)


def encoded_registry(registry):
    return (json.dumps(registry, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def encoded_ledger(ledger):
    return (json.dumps(ledger, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


class Response:
    def __init__(self, value): self.value = value
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self): return json.dumps(self.value).encode()


class WarderIdentitySyncTests(unittest.TestCase):
    def test_git_snapshot_is_commit_pinned_and_sha256_verified(self):
        raw = encoded_registry(empty_registry())
        ledger_raw = encoded_ledger(empty_approval_ledger())
        commit = "a" * 40
        calls = []
        def opener(request, timeout):
            calls.append((request.full_url, timeout))
            if "/branches/" in request.full_url:
                return Response({"commit": {"sha": commit}})
            payload = ledger_raw if APPROVAL_LEDGER_PATH in request.full_url else raw
            self.assertIsNone(request.get_header("Authorization"))
            return Response({"encoding": "base64", "content": base64.b64encode(payload).decode()})
        snapshot = fetch_registry_snapshot(opener)
        self.assertEqual(snapshot["commit"], commit)
        self.assertEqual(snapshot["registry_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(snapshot["approval_ledger_sha256"], hashlib.sha256(ledger_raw).hexdigest())
        self.assertIn(commit, calls[1][0])
        self.assertIn(commit, calls[2][0])
        self.assertTrue(validate_snapshot(snapshot))

    def test_registry_endpoint_is_pinned_to_repository_branch_and_file(self):
        self.assertEqual(REPOSITORY, "Evolution-by-Warder/PiconHub-Warder-Evolution")
        self.assertEqual(BRANCH, "factory-warder-development")
        self.assertEqual(REGISTRY_PATH, "factory/registry/warder-identity-registry.json")
        self.assertEqual(APPROVAL_LEDGER_PATH, "factory/registry/master-approval-ledger.json")
        self.assertTrue(API.startswith("https://api.github.com/"))

    def test_offline_uses_only_checksum_verified_cache(self):
        raw = encoded_registry(empty_registry())
        ledger_raw = encoded_ledger(empty_approval_ledger())
        snapshot = {"schema": 2, "repository": REPOSITORY, "branch": BRANCH,
                    "commit": "b" * 40, "registry_sha256": hashlib.sha256(raw).hexdigest(),
                    "approval_ledger_sha256": hashlib.sha256(ledger_raw).hexdigest(),
                    "registry": empty_registry(), "approval_ledger": empty_approval_ledger()}
        with tempfile.TemporaryDirectory() as temp:
            cache = Path(temp) / "registry-cache.json"
            cache.write_text(json.dumps(snapshot), encoding="utf-8")
            result = sync_registry(cache, fetcher=lambda: (_ for _ in ()).throw(OSError("offline")))
            self.assertEqual(result["status"], "OFFLINE_VERIFIED_CACHE")
            self.assertEqual(load_cached_snapshot(cache)["commit"], "b" * 40)
            snapshot["registry"]["next_sequence"] = 99
            cache.write_text(json.dumps(snapshot), encoding="utf-8")
            self.assertIsNone(load_cached_snapshot(cache))

    def test_gui_preserves_exact_base64_diagnostic(self):
        error = "binascii.Error: Only base64 data is allowed"
        self.assertEqual(format_git_sync_error(error), error)

    def test_line_wrapped_github_contents_base64_is_decoded_strictly(self):
        raw = encoded_registry(empty_registry())
        ledger_raw = encoded_ledger(empty_approval_ledger())
        commit = "c" * 40
        def wrapped(payload):
            encoded = base64.b64encode(payload).decode("ascii")
            return "\n".join(encoded[i:i + 64] for i in range(0, len(encoded), 64)) + "\n"
        # Reproduce the exact failure from b64decode(validate=True) before the
        # fix: GitHub's legal line wrapping used to raise this message.
        with self.assertRaisesRegex(binascii.Error, "Only base64 data is allowed"):
            base64.b64decode(wrapped(raw), validate=True)
        def opener(request, timeout):
            if "/branches/" in request.full_url:
                return Response({"commit": {"sha": commit}})
            payload = ledger_raw if APPROVAL_LEDGER_PATH in request.full_url else raw
            return Response({"encoding": "base64", "content": wrapped(payload)})
        snapshot = fetch_registry_snapshot(opener)
        self.assertEqual(snapshot["commit"], commit)
        self.assertEqual(snapshot["registry_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertTrue(validate_snapshot(snapshot))

    def test_invalid_base64_keeps_precise_contents_api_diagnostic(self):
        raw = encoded_registry(empty_registry())
        ledger_raw = encoded_ledger(empty_approval_ledger())
        commit = "d" * 40
        def opener(request, timeout):
            if "/branches/" in request.full_url:
                return Response({"commit": {"sha": commit}})
            payload = ledger_raw if APPROVAL_LEDGER_PATH in request.full_url else raw
            return Response({"encoding": "base64", "content": "!!!!"})
        with tempfile.TemporaryDirectory() as temp:
            result = sync_registry(Path(temp) / "missing.json",
                                   fetcher=lambda: fetch_registry_snapshot(opener))
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertIn("GitHub Contents API base64 decode failed", result["error"])
        self.assertIn("Only base64 data is allowed", result["error"])

    def test_http_unauthorized_is_distinct_from_base64_and_network_errors(self):
        def opener(request, timeout):
            if "/branches/" in request.full_url:
                raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {}, io.BytesIO(b""))
            raise AssertionError("Registry fetch must stop after branch authorization failure")
        with tempfile.TemporaryDirectory() as temp:
            result = sync_registry(Path(temp) / "missing.json",
                                   fetcher=lambda: fetch_registry_snapshot(opener))
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertIn("401", result["error"])
        self.assertNotIn("base64", result["error"].lower())

    def test_no_cache_and_network_failure_is_explicitly_unavailable(self):
        with tempfile.TemporaryDirectory() as temp:
            result = sync_registry(Path(temp) / "missing.json",
                                   fetcher=lambda: (_ for _ in ()).throw(TimeoutError("timeout")))
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertIsNone(result["snapshot"])


if __name__ == "__main__":
    unittest.main()
