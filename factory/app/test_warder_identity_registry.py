import copy
import unittest

from warder_identity_registry import (
    append_identity_event, audit_master_migration, empty_registry,
    normalize_change_watch_event, register_confirmed_identity,
    resolve_service_reference, validate_registry, validate_registry_transition,
)


EV = {"evidence_ref": "fixture:verified-record", "evidence_sha256": "a" * 64,
      "occurred_at": "2026-10-14T00:00:00Z"}


class WarderIdentityRegistryTests(unittest.TestCase):
    def create(self, identity_key="station:alpha", refs=None):
        identity = {"identity_key": identity_key,
                    "canonical_identity": {"station": "Alpha TV"},
                    "current_name": "Alpha TV", "service_references": refs or [],
                    "operator_links": ["provider-a"], "satellite_positions": ["13.0E"]}
        return register_confirmed_identity(empty_registry(), identity, evidence=EV,
                                           identity_confirmed=True)

    def test_owner_defined_identity_document_is_valid_and_has_one_authority(self):
        self.assertEqual(validate_registry(empty_registry())["status"], "VALID")
        self.assertEqual(empty_registry()["authority"], "WARDER_ID")

    def test_id_allocated_only_after_explicit_identity_confirmation(self):
        with self.assertRaises(PermissionError):
            register_confirmed_identity(empty_registry(), {"identity_key": "x"}, evidence=EV)
        registry, wid = self.create()
        self.assertEqual(wid, "WARDER-00000001")
        self.assertEqual(validate_registry(registry)["status"], "VALID")

    def test_id_never_changes_for_name_provider_reference_or_logo_changes(self):
        registry, wid = self.create(refs=["ref-old"])
        changed = append_identity_event(registry, {
            **EV, "event_type": "NAME_CHANGED", "warder_id": wid,
            "identity_continuity_confirmed": True, "new_name": "Alpha Plus"},
            human_confirmed=True)
        self.assertEqual(changed["records"][wid]["warder_id"], wid)
        self.assertEqual(changed["records"][wid]["historical_names"], ["Alpha TV"])
        changed = append_identity_event(changed, {
            **EV, "event_type": "PROVIDER_CHANGED", "warder_id": wid,
            "identity_continuity_confirmed": True, "operator_links": ["provider-b"]},
            human_confirmed=True)
        changed = append_identity_event(changed, {
            **EV, "event_type": "SERVICE_REFERENCE_CHANGED", "warder_id": wid,
            "identity_continuity_confirmed": True,
            "previous_service_references": ["ref-old"], "service_references": ["ref-new"]},
            human_confirmed=True)
        self.assertEqual(resolve_service_reference(changed, "ref-old"),
                         {"status": "EXACT", "warder_ids": [wid]})
        self.assertEqual(resolve_service_reference(changed, "ref-new"),
                         {"status": "EXACT", "warder_ids": [wid]})

    def test_id_not_recycled_after_retirement_and_sequence_is_monotonic(self):
        registry, old = self.create()
        retired = append_identity_event(registry, {
            **EV, "event_type": "IDENTITY_RETIRED", "warder_id": old,
            "identity_continuity_confirmed": True}, human_confirmed=True)
        new_registry, new = register_confirmed_identity(retired,
            {"identity_key": "station:beta", "current_name": "Beta"}, evidence=EV,
            identity_confirmed=True)
        self.assertEqual(retired["records"][old]["status"], "retired")
        self.assertNotEqual(old, new)
        self.assertEqual(new, "WARDER-00000002")

    def test_shared_logo_does_not_merge_identities(self):
        registry, first = self.create("station:alpha")
        registry, second = register_confirmed_identity(registry,
            {"identity_key": "station:beta", "current_name": "Beta",
             "artwork_current": {"transparent": "b" * 64}}, evidence=EV,
            identity_confirmed=True)
        self.assertNotEqual(first, second)

    def test_three_graphic_variants_belong_to_one_identity(self):
        registry, wid = self.create()
        record = registry["records"][wid]
        record["artwork_current"] = {"transparent": "1" * 64,
                                     "black": "2" * 64, "white": "3" * 64}
        record["artwork_asset_paths"] = {
            style: f"factory/approved-picons/{wid}/v0001/{style}.png"
            for style in ("transparent", "black", "white")}
        self.assertEqual(validate_registry(registry)["status"], "VALID")

    def test_rebrand_requires_explicit_confirmation_and_preserves_old_hashes(self):
        registry, wid = self.create()
        old = {"transparent": "1" * 64, "black": "2" * 64, "white": "3" * 64}
        record = registry["records"][wid]
        record["artwork_current"] = dict(old)
        record["artwork_asset_paths"] = {
            style: f"factory/approved-picons/{wid}/v0001/{style}.png"
            for style in ("transparent", "black", "white")}
        record["approval_history_refs"] = ["AP-fixture-approval"]
        event = {**EV, "event_type": "ARTWORK_REBRANDED", "warder_id": wid,
                 "identity_continuity_confirmed": True, "official_rebrand_confirmed": True,
                 "qa_approved": True, "human_approved": True,
                 "previous_variants": old,
                 "new_variants": {"transparent": "4" * 64, "black": "5" * 64, "white": "6" * 64},
                 "asset_paths": {style: f"factory/approved-picons/{wid}/v0002/{style}.png"
                                 for style in ("transparent", "black", "white")},
                 "approval_ledger_event_id": "AP-fixture-next"}
        with self.assertRaises(PermissionError):
            append_identity_event(registry, event, human_confirmed=False)
        changed = append_identity_event(registry, event, human_confirmed=True)
        self.assertEqual(changed["records"][wid]["artwork_history"][0]["previous_variants"], old)
        self.assertEqual(changed["records"][wid]["warder_id"], wid)
        self.assertEqual(validate_registry(changed)["status"], "VALID")

    def test_artwork_difference_alone_cannot_become_rebrand(self):
        registry, wid = self.create()
        with self.assertRaises(PermissionError):
            append_identity_event(registry, {**EV, "event_type": "ARTWORK_REBRANDED",
                "warder_id": wid, "identity_continuity_confirmed": True}, human_confirmed=True)

    def test_approval_evidence_is_referenced_separately(self):
        registry, wid = self.create()
        record = registry["records"][wid]
        self.assertIn("approval_history_refs", record)
        self.assertNotIn("approval_status", record)

    def test_master_migration_only_maps_exact_current_or_historical_service_refs(self):
        registry, wid = self.create(refs=["known-ref"])
        report = audit_master_migration({"known-ref": [], "new-ref": []}, registry)
        self.assertEqual(report["counts"], {"AUTO_MAPPABLE": 1, "AMBIGUOUS": 0,
                                            "CONFLICT": 0, "NEW_ID_REQUIRED": 1})
        self.assertEqual(report["decisions"][0]["warder_ids"], [wid])
        self.assertFalse(report["decisions"][1]["new_id_allocated"])

    def test_same_service_reference_on_two_ids_is_conflict_not_merge(self):
        registry, _ = self.create("station:a", refs=["shared-ref"])
        duplicate = copy.deepcopy(registry)
        second = copy.deepcopy(duplicate["records"]["WARDER-00000001"])
        second["warder_id"] = "WARDER-00000002"
        second["identity_key"] = "station:b"
        duplicate["records"]["WARDER-00000002"] = second
        duplicate["issued_ids"].append("WARDER-00000002")
        duplicate["next_sequence"] = 3
        self.assertEqual(validate_registry(duplicate)["status"], "INVALID")
        decision = audit_master_migration({"shared-ref": []}, duplicate)["decisions"][0]
        self.assertEqual(decision["classification"], "CONFLICT")

    def test_names_and_artwork_are_never_used_for_automatic_migration(self):
        registry, _ = self.create()
        report = audit_master_migration({"new-ref": [{"name": "Alpha TV", "sha256": "a" * 64}]}, registry)
        self.assertEqual(report["decisions"][0]["classification"], "NEW_ID_REQUIRED")

    def test_ambiguous_and_contradictory_evidence_fail_closed(self):
        registry, wid = self.create()
        result = audit_master_migration({"unclear": []}, registry,
            {"unclear": {"candidate_warder_ids": [wid, "WARDER-99999999"]}})
        self.assertEqual(result["decisions"][0]["classification"], "AMBIGUOUS")

    def test_repeated_import_is_idempotent_and_source_order_independent(self):
        registry, wid = self.create(refs=["ref-a", "ref-b"])
        one = audit_master_migration({"ref-a": [], "ref-b": []}, registry)
        two = audit_master_migration({"ref-b": [], "ref-a": []}, registry)
        self.assertEqual(one, two)
        self.assertEqual([r["warder_ids"] for r in one["decisions"]], [[wid], [wid]])

    def test_change_watch_is_validated_but_never_applied_automatically(self):
        item = normalize_change_watch_event({"event_id": "cw-1", "event_type": "CONFIRMED_REBRAND",
            "observed_at": "2026-10-14T00:00:00Z", "source_ref": "press:1",
            "evidence_sha256": "c" * 64, "warder_id": "WARDER-00000001"})
        self.assertFalse(item["applied_to_registry"])
        with self.assertRaises(ValueError):
            normalize_change_watch_event({"event_type": "UNKNOWN"})

    def test_git_transition_accepts_new_evidenced_identity_and_rejects_reuse(self):
        base = empty_registry()
        current, wid = self.create()
        self.assertEqual(validate_registry_transition(base, current)["status"], "VALID")
        tampered = copy.deepcopy(current)
        tampered["issued_ids"] = ["WARDER-00000009"]
        tampered["records"][wid]["warder_id"] = "WARDER-00000009"
        self.assertEqual(validate_registry_transition(base, tampered)["status"], "INVALID")

    def test_git_transition_requires_append_only_event_for_existing_identity_edit(self):
        base, wid = self.create()
        tampered = copy.deepcopy(base)
        tampered["records"][wid]["current_name"] = "Unlogged rename"
        codes = {item["code"] for item in validate_registry_transition(base, tampered)["issues"]}
        self.assertIn("UNAUTHORIZED_EXISTING_IDENTITY_EDIT", codes)
        valid = append_identity_event(base, {**EV, "event_type": "NAME_CHANGED",
            "warder_id": wid, "identity_continuity_confirmed": True,
            "new_name": "Approved rename"}, human_confirmed=True)
        self.assertEqual(validate_registry_transition(base, valid)["status"], "VALID")

    def test_git_transition_rejects_history_rewrite(self):
        base, wid = self.create()
        edited = copy.deepcopy(base)
        edited["history"][0]["evidence_ref"] = "tampered"
        result = validate_registry_transition(base, edited)
        self.assertEqual(result["status"], "INVALID")
        self.assertIn("HISTORY_REWRITTEN_OR_REORDERED", {i["code"] for i in result["issues"]})


if __name__ == "__main__":
    unittest.main()
