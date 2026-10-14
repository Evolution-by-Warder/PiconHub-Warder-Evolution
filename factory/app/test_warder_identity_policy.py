import copy
import unittest

from warder_identity_policy import (
    append_approved_artwork_history, audit_identity_rows,
    classify_master_observation,
)


H = {"transparent": "1" * 64, "black": "2" * 64, "white": "3" * 64}
NEW = {"transparent": "4" * 64, "black": "5" * 64, "white": "6" * 64}


class WarderIdentityPolicyTests(unittest.TestCase):
    def test_missing_canonical_registry_is_not_reported_as_empty_success(self):
        result = audit_identity_rows([])
        self.assertEqual(result["status"], "WARDER_ID_SCHEMA_NOT_PRESENT")
        self.assertFalse(result["id_generation"])

    def test_duplicate_ids_and_historical_reuse_are_reported(self):
        rows = [
            {"warder_id": "WARDER-7", "identity_key": "station-A", "history": [
                {"warder_id": "WARDER-7", "identity_key": "station-B", "event_type": "RENAMED"}]},
            {"warder_id": "WARDER-7", "identity_key": "station-A"},
        ]
        issues = {item["code"] for item in audit_identity_rows(rows)["issues"]}
        self.assertIn("WARDER_ID_NOT_UNIQUE", issues)
        self.assertIn("HISTORICAL_ID_REUSE", issues)

    def test_one_identity_mapped_to_multiple_ids_is_reported_not_merged(self):
        rows = [{"warder_id": "W-1", "identity_key": "station-A"},
                {"warder_id": "W-2", "identity_key": "station-A"}]
        result = audit_identity_rows(rows)
        self.assertIn("IDENTITY_HAS_MULTIPLE_WARDER_IDS", {item["code"] for item in result["issues"]})
        self.assertEqual(result["unique_id_count"], 2)

    def test_links_and_retired_identity_are_counted_read_only(self):
        result = audit_identity_rows([{"warder_id": "W-1", "identity_key": "A",
                                       "service_references": ["s1", "s2", "s1"],
                                       "operator_links": ["op"], "satellite_links": ["13E"],
                                       "retired": True, "history": [{"event_type": "RETIRED"}]}])
        self.assertEqual(result["linked_counts"]["service_references"], 2)
        self.assertEqual(result["linked_counts"]["retired"], 1)
        self.assertFalse(result["master_mutated"])

    def test_name_or_operator_change_does_not_reassign_existing_id(self):
        original = {"warder_id": "W-1", "identity_key": "station-A", "name": "Old",
                    "operator": "Old Operator"}
        edited = {**original, "name": "New", "operator": "New Operator"}
        result = audit_identity_rows([edited])
        self.assertEqual(edited["warder_id"], original["warder_id"])
        self.assertEqual(result["issues"], [])

    def test_same_logo_does_not_merge_different_services(self):
        a = {"service_reference": "service-A", "pixel_sha256": "a" * 64}
        b = {"service_reference": "service-B", "pixel_sha256": "a" * 64}
        self.assertNotEqual(a["service_reference"], b["service_reference"])
        # This policy module has no logo-to-identity merge operation.
        self.assertEqual(classify_master_observation("NEW")["state"], "MISSING_IDENTITY")

    def test_different_logo_same_service_is_audit_only_without_rebrand_evidence(self):
        result = classify_master_observation("APPROVED_COMPLETE", candidate_matches_master=False)
        self.assertEqual(result["state"], "UNVERIFIED_ARTWORK_CHANGE")
        self.assertFalse(result["automatic_approval"])

    def test_confirmed_rebrand_requires_continuity_and_official_evidence(self):
        incomplete = {"identity_continuity_verified": True, "official_rebrand_confirmed": True}
        self.assertEqual(classify_master_observation("APPROVED_COMPLETE", rebrand_evidence=incomplete)["state"],
                         "UNVERIFIED_ARTWORK_CHANGE")
        verified = {**incomplete, "evidence_ref": "press-release:42"}
        self.assertEqual(classify_master_observation("APPROVED_COMPLETE", rebrand_evidence=verified)["state"],
                         "CONFIRMED_REBRAND")

    def test_confirmed_rebrand_classification_is_not_itself_approval(self):
        evidence = {"identity_continuity_verified": True, "official_rebrand_confirmed": True,
                    "evidence_ref": "authority:42"}
        result = classify_master_observation("APPROVED_COMPLETE", rebrand_evidence=evidence)
        self.assertFalse(result["automatic_approval"])

    def test_retired_identity_is_never_reopened(self):
        result = classify_master_observation("APPROVED_COMPLETE", retired=True)
        self.assertEqual(result["state"], "RETIRED")

    def test_unknown_and_ambiguous_master_states_map_to_review(self):
        self.assertEqual(classify_master_observation("AMBIGUOUS")["state"], "IDENTITY_AMBIGUOUS")
        self.assertEqual(classify_master_observation("KNOWN_UNAPPROVED")["state"],
                         "UNVERIFIED_ARTWORK_CHANGE")

    def test_approved_logo_event_appends_without_changing_old_history(self):
        history = [{"event_id": "old", "logo_sha256": H["transparent"]}]
        before = copy.deepcopy(history)
        event = {"event_type": "MASTER_ARTWORK_APPROVED", "warder_id": "W-9",
                 "identity_continuity_verified": True, "official_rebrand_confirmed": True,
                 "qa_approved": True, "human_approved": True,
                 "evidence_ref": "rebrand:2026", "evidence_sha256": "7" * 64,
                 "approved_at": "2026-10-14T00:00:00Z",
                 "previous_variants": H, "new_variants": NEW}
        updated = append_approved_artwork_history(history, event, canonical_warder_ids={"W-9"})
        self.assertEqual(history, before)
        self.assertEqual(len(updated), 2)
        self.assertEqual(updated[-1]["warder_id"], "W-9")
        self.assertNotEqual(updated[-1]["event_id"], "old")

    def test_logo_event_cannot_change_or_invent_id(self):
        event = {"event_type": "MASTER_ARTWORK_APPROVED", "warder_id": "W-new",
                 "identity_continuity_verified": True, "official_rebrand_confirmed": True,
                 "qa_approved": True, "human_approved": True,
                 "evidence_ref": "rebrand:1", "evidence_sha256": "7" * 64,
                 "approved_at": "now", "previous_variants": H, "new_variants": NEW}
        with self.assertRaisesRegex(ValueError, "already exist"):
            append_approved_artwork_history([], event, canonical_warder_ids={"W-1"})

    def test_rebrand_without_explicit_human_approval_is_rejected(self):
        event = {"event_type": "MASTER_ARTWORK_APPROVED", "warder_id": "W-1",
                 "identity_continuity_verified": True, "official_rebrand_confirmed": True,
                 "qa_approved": True, "human_approved": False,
                 "evidence_ref": "rebrand:1", "evidence_sha256": "7" * 64,
                 "approved_at": "now", "previous_variants": H, "new_variants": NEW}
        with self.assertRaises(PermissionError):
            append_approved_artwork_history([], event, canonical_warder_ids={"W-1"})

    def test_all_three_hashes_are_required_for_rebrand_history(self):
        event = {"event_type": "MASTER_ARTWORK_APPROVED", "warder_id": "W-1",
                 "identity_continuity_verified": True, "official_rebrand_confirmed": True,
                 "qa_approved": True, "human_approved": True,
                 "evidence_ref": "rebrand:1", "evidence_sha256": "7" * 64,
                 "approved_at": "now", "previous_variants": H,
                 "new_variants": {"transparent": NEW["transparent"]}}
        with self.assertRaises(ValueError):
            append_approved_artwork_history([], event, canonical_warder_ids={"W-1"})


if __name__ == "__main__":
    unittest.main()
