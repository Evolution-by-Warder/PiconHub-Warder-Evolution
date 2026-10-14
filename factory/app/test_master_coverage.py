"""Regression tests for fail-closed MASTER-FIRST coverage filtering."""
import unittest
import hashlib
import io
from PIL import Image

from master_coverage import (build_master_coverage, apply_master_first_coverage,
                             approval_evidence_from_git_master)
from warder_identity_registry import empty_approval_ledger, empty_registry, register_confirmed_identity
from warder_master_store import build_identity_approval, build_artwork_approval
from review_queue import build_review_queue, stable_review_id

REF_A = "1_0_1_100_1_1_D72CF4_0_0_0"
REF_B = "1_0_1_101_1_1_D72CF4_0_0_0"
MASTER_COMMIT = "a" * 40
HASHES = {"transparent": "1" * 64, "black": "2" * 64, "white": "3" * 64}


def registry(refs=(REF_A, REF_B), hashes=None, conflicts=None):
    hashes = hashes or HASHES
    return {
        "services": {
            ref: [{"style": style, "sha256": sha, "path": f"picons/13.0e/test/{style}/{ref}.png"}
                  for style, sha in hashes.items()]
            for ref in refs
        },
        "conflicts": conflicts or [],
    }


def approval(ref, variants=None):
    return {"identity_verified": True, "artwork_approved": True,
            "approval_ref": "human-review:QA-42", "evidence_sha256": "9" * 64,
            "variants": variants or HASHES}


def queue_item(ref, lane="ARTWORK_REVIEW", sha="4" * 64):
    return {"review_id": stable_review_id("REGISTRY_MATCH", ref, sha),
            "category": "REGISTRY_MATCH", "candidate_identity": ref,
            "workstream": lane, "sha256": sha, "decision": "PENDING",
            "reasons": ["EXISTING_SERVICE_DIFFERENT_ART"], "source_origin": "vhannibal"}


class MasterCoverageTests(unittest.TestCase):
    def test_exact_explicit_master_approval_is_complete(self):
        evidence = {"schema": 1, "master_commit": MASTER_COMMIT,
                    "services": {REF_A: approval(REF_A)}}
        result = build_master_coverage(registry((REF_A,)), evidence, master_commit=MASTER_COMMIT)
        row = result["services"][REF_A]
        self.assertEqual(row["status"], "APPROVED_COMPLETE")
        self.assertEqual(row["covered_styles"], ["black", "transparent", "white"])
        self.assertEqual(result["counts"]["APPROVED_COMPLETE"], 1)

    def test_png_and_service_reference_without_approval_remain_unapproved(self):
        result = build_master_coverage(registry((REF_A,)), None, master_commit=MASTER_COMMIT,
                                      candidate_refs=(REF_B,))
        self.assertEqual(result["services"][REF_A]["status"], "KNOWN_UNAPPROVED")
        self.assertEqual(result["services"][REF_A]["reason"], "APPROVAL_EVIDENCE_MISSING")

    def test_approved_identity_with_missing_variants_is_incomplete(self):
        partial = {"transparent": HASHES["transparent"], "black": HASHES["black"]}
        evidence = {"schema": 1, "master_commit": MASTER_COMMIT,
                    "services": {REF_A: approval(REF_A, partial)}}
        row = build_master_coverage(registry((REF_A,)), evidence,
                                    master_commit=MASTER_COMMIT)["services"][REF_A]
        self.assertEqual(row["status"], "APPROVED_INCOMPLETE")
        self.assertEqual(row["missing_styles"], ["white"])

    def test_changed_master_hash_invalidates_approval(self):
        changed = dict(HASHES, white="f" * 64)
        evidence = {"schema": 1, "master_commit": MASTER_COMMIT,
                    "services": {REF_A: approval(REF_A)}}
        row = build_master_coverage(registry((REF_A,), changed), evidence,
                                    master_commit=MASTER_COMMIT)["services"][REF_A]
        self.assertEqual(row["status"], "KNOWN_UNAPPROVED")
        self.assertEqual(row["reason"], "APPROVAL_EVIDENCE_STALE_OR_INVALID")

    def test_master_style_conflict_is_ambiguous_even_with_approval(self):
        conflict = [{"service_reference": REF_A, "style": "white", "reason": "MASTER_STYLE_CONFLICT"}]
        evidence = {"schema": 1, "master_commit": MASTER_COMMIT,
                    "services": {REF_A: approval(REF_A)}}
        row = build_master_coverage(registry((REF_A,), conflicts=conflict), evidence,
                                    master_commit=MASTER_COMMIT)["services"][REF_A]
        self.assertEqual(row["status"], "AMBIGUOUS")

    def test_approval_for_different_master_commit_is_rejected(self):
        evidence = {"schema": 1, "master_commit": "b" * 40,
                    "services": {REF_A: approval(REF_A)}}
        row = build_master_coverage(registry((REF_A,)), evidence,
                                    master_commit=MASTER_COMMIT)["services"][REF_A]
        self.assertEqual(row["status"], "KNOWN_UNAPPROVED")
        self.assertEqual(row["reason"], "MASTER_COMMIT_MISMATCH")

    def test_approval_without_a_hashed_audit_record_is_not_trusted(self):
        incomplete = approval(REF_A)
        incomplete.pop("evidence_sha256")
        evidence = {"schema": 1, "master_commit": MASTER_COMMIT,
                    "services": {REF_A: incomplete}}
        row = build_master_coverage(registry((REF_A,)), evidence,
                                    master_commit=MASTER_COMMIT)["services"][REF_A]
        self.assertEqual(row["status"], "KNOWN_UNAPPROVED")
        self.assertEqual(row["reason"], "APPROVAL_AUDIT_REFERENCE_OR_HASH_MISSING")

    def test_new_service_and_unknown_approval_are_distinguished(self):
        result = build_master_coverage(registry((REF_A,)), None, master_commit=MASTER_COMMIT,
                                      candidate_refs=(REF_B,))
        self.assertEqual(result["services"][REF_B]["status"], "NEW")
        self.assertEqual(result["services"][REF_A]["status"], "KNOWN_UNAPPROVED")

    def test_only_pending_artwork_for_exact_complete_service_is_covered_and_audited(self):
        evidence = {"schema": 1, "master_commit": MASTER_COMMIT,
                    "services": {REF_A: approval(REF_A)}}
        coverage = build_master_coverage(registry(), evidence, master_commit=MASTER_COMMIT)
        covered = queue_item(REF_A)
        identity = queue_item(REF_A, "IDENTITY_VERIFICATION", "5" * 64)
        other_service = queue_item(REF_B)
        decided = queue_item(REF_A, "ARTWORK_REVIEW", "6" * 64)
        decided["decision"] = "DEFERRED"
        queue = {"count": 4, "items": [covered, identity, other_service, decided],
                 "workstream_counts": {"ARTWORK_REVIEW": 3, "IDENTITY_VERIFICATION": 1}}
        result = apply_master_first_coverage(queue, coverage)
        self.assertEqual(result["count"], 3)
        self.assertEqual(len(result["covered_items"]), 1)
        audit = result["covered_items"][0]
        self.assertEqual(audit["coverage_status"], "COVERED_BY_APPROVED_MASTER")
        self.assertTrue(audit["coverage_evidence_hash"])
        self.assertEqual(audit["review_id"], covered["review_id"])
        self.assertEqual({item["review_id"] for item in result["items"]},
                         {identity["review_id"], other_service["review_id"], decided["review_id"]})
        self.assertEqual(result["master_coverage_summary"]["automatic_identity_approvals"], 0)
        self.assertEqual(result["workstream_counts"], {"ARTWORK_REVIEW": 1, "IDENTITY_VERIFICATION": 1})

    def test_source_order_does_not_change_service_coverage(self):
        manifest = {"schema": 1, "master_commit": MASTER_COMMIT,
                    "services": {REF_A: approval(REF_A)}}
        coverage_a = build_master_coverage(registry((REF_A,)), manifest, master_commit=MASTER_COMMIT,
                                           candidate_refs=(REF_A,))
        coverage_b = build_master_coverage(registry((REF_A,)), manifest, master_commit=MASTER_COMMIT,
                                           candidate_refs=(REF_A,))
        feeds = [
            {"classification": "REVIEW", "reason": "EXISTING_SERVICE_DIFFERENT_ART",
             "service_reference": REF_A, "candidate_sha256": "7" * 64,
             "candidate_source": "vhannibal/service.png"},
            {"classification": "REVIEW", "reason": "EXISTING_SERVICE_DIFFERENT_ART",
             "service_reference": REF_A, "candidate_sha256": "8" * 64,
             "candidate_source": "openatv8/service.png"},
        ]
        outputs = []
        for ordered_feeds, coverage in ((feeds, coverage_a), (list(reversed(feeds)), coverage_b)):
            queue = build_review_queue({}, {}, [], ordered_feeds)
            filtered = apply_master_first_coverage(queue, coverage)
            outputs.append((
                [item["review_id"] for item in filtered["items"]],
                [item["review_id"] for item in filtered["covered_items"]],
                [tuple(row["source_evidence"]) for row in queue["items"]],
            ))
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[0][0], [])
        self.assertEqual(len(outputs[0][1]), 1)

    def test_only_git_identity_and_artwork_approvals_cover_service(self):
        evidence = {"evidence_ref": "fixture:identity", "evidence_sha256": "a" * 64,
                    "occurred_at": "2026-10-14T00:00:00Z"}
        identities, wid = register_confirmed_identity(empty_registry(), {
            "identity_key": "fixture:service", "current_name": "Service",
            "service_references": [REF_A]}, evidence=evidence, identity_confirmed=True)
        ledger = empty_approval_ledger()
        identities, ledger, _ = build_identity_approval(identities, ledger,
            warder_id=wid, approval_id="identity-approve", approved_at=evidence["occurred_at"],
            evidence_ref="fixture:identity-review", evidence_sha256="b" * 64,
            review_evidence_sha256="c" * 64, human_approved=True)
        variants, paths = {}, {}
        for style, color in (("transparent", (20, 30, 40, 0)),
                             ("black", (0, 0, 0, 255)),
                             ("white", (255, 255, 255, 255))):
            stream = io.BytesIO()
            Image.new("RGBA", (220, 132), color).save(stream, format="PNG")
            variants[style] = hashlib.sha256(stream.getvalue()).hexdigest()
            paths[style] = f"factory/approved-picons/{wid}/v0001/{style}.png"
        identities, ledger, _ = build_artwork_approval(identities, ledger,
            warder_id=wid, approval_id="art-approve", approved_at=evidence["occurred_at"],
            evidence_ref="fixture:art-review", evidence_sha256="d" * 64,
            review_evidence_sha256="e" * 64, variants=variants, asset_paths=paths,
            qa_evidence_ref="fixture:qa-review", qa_evidence_sha256="f" * 64,
            human_approved=True, qa_approved=True)
        master_index = registry((REF_A,), variants)
        git_evidence, status = approval_evidence_from_git_master(
            identities, ledger, master_commit=MASTER_COMMIT)
        self.assertEqual(status["status"], "GIT_LEDGER")
        covered = build_master_coverage(master_index, git_evidence, master_commit=MASTER_COMMIT)
        self.assertEqual(covered["services"][REF_A]["status"], "APPROVED_COMPLETE")

    def test_artwork_approval_without_identity_approval_does_not_cover(self):
        evidence = {"evidence_ref": "fixture:identity", "evidence_sha256": "a" * 64,
                    "occurred_at": "2026-10-14T00:00:00Z"}
        identities, wid = register_confirmed_identity(empty_registry(), {
            "identity_key": "fixture:service", "current_name": "Service",
            "service_references": [REF_A]}, evidence=evidence, identity_confirmed=True)
        ledger = empty_approval_ledger()
        variants, paths = {}, {}
        for style, color in (("transparent", (20, 30, 40, 0)),
                             ("black", (0, 0, 0, 255)),
                             ("white", (255, 255, 255, 255))):
            stream = io.BytesIO()
            Image.new("RGBA", (220, 132), color).save(stream, format="PNG")
            variants[style] = hashlib.sha256(stream.getvalue()).hexdigest()
            paths[style] = f"factory/approved-picons/{wid}/v0001/{style}.png"
        identities, ledger, _ = build_artwork_approval(identities, ledger,
            warder_id=wid, approval_id="art-only", approved_at=evidence["occurred_at"],
            evidence_ref="fixture:art-review", evidence_sha256="d" * 64,
            review_evidence_sha256="e" * 64, variants=variants, asset_paths=paths,
            qa_evidence_ref="fixture:qa-review", qa_evidence_sha256="f" * 64,
            human_approved=True, qa_approved=True)
        git_evidence, _ = approval_evidence_from_git_master(identities, ledger,
                                                            master_commit=MASTER_COMMIT)
        self.assertEqual(git_evidence["services"], {})


if __name__ == "__main__":
    unittest.main()
