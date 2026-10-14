"""Canonical, fail-closed Warder ID registry and append-only history helpers.

The authoritative registry is tracked in the project's Git repository. A local
Factory may cache a verified Git snapshot, separate from both the read-only
Master index and master-approval-evidence.json. Nothing here infers identity
from artwork, name, operator, satellite position, or a service reference alone.
Mutations are pure transformations; a candidate is not an issued authority
until its validated change is committed to the development branch.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter, defaultdict

SCHEMA = 1
AUTHORITY = "WARDER_ID"
ID_PATTERN = re.compile(r"^WARDER-(\d{8})$")
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
STYLES = ("transparent", "black", "white")
WATCH_EVENTS = frozenset({
    "NEW_SERVICE", "SERVICE_REMOVED", "NAME_CHANGE", "PROVIDER_CHANGE",
    "SERVICE_REFERENCE_CHANGE", "CONFIRMED_REBRAND", "SATELLITE_CHANGE",
})
REGISTRY_EVENTS = frozenset({
    "IDENTITY_CREATED", "NAME_CHANGED", "PROVIDER_CHANGED",
    "SATELLITE_CHANGED", "SERVICE_REFERENCE_CHANGED", "SERVICE_REMOVED", "SOURCE_OBSERVED",
    "IDENTITY_RETIRED", "IDENTITY_APPROVED", "APPROVAL_REVOKED",
    "ARTWORK_APPROVED", "ARTWORK_REBRANDED",
})


def canonical_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def sha256_json(value):
    return hashlib.sha256(canonical_json(value)).hexdigest()


def empty_registry():
    """Return an empty authority document; callers must explicitly persist it."""
    return {"schema": SCHEMA, "authority": AUTHORITY,
            "id_format": "WARDER-{sequence:08d}", "next_sequence": 1,
            "issued_ids": [], "records": {}, "history": []}


def validate_registry_transition(previous, current):
    """Reject ID reuse, record removal, unaudited edits, and history rewrites.

    GitHub CI runs this against the parent revision. Changes to an existing
    identity must carry the matching evidence-backed event; merge/review policy
    remains the human authorization boundary.
    """
    before = validate_registry(previous)
    after = validate_registry(current)
    issues = []
    if before["status"] != "VALID":
        issues.append({"code": "BASE_REGISTRY_INVALID"})
    if after["status"] != "VALID":
        issues.append({"code": "CURRENT_REGISTRY_INVALID"})
    old_records, new_records = previous.get("records", {}), current.get("records", {})
    old_ids, new_ids = set(old_records), set(new_records)
    if not old_ids.issubset(new_ids):
        issues.append({"code": "ISSUED_ID_REMOVED", "warder_ids": sorted(old_ids - new_ids)})
    if not set(previous.get("issued_ids", [])).issubset(set(current.get("issued_ids", []))):
        issues.append({"code": "ISSUED_ID_REUSED_OR_REMOVED"})
    if current.get("next_sequence", 0) < previous.get("next_sequence", 0):
        issues.append({"code": "ID_SEQUENCE_MOVED_BACKWARD"})
    previous_issued = set(previous.get("issued_ids", []))
    added_in_issue_order = [wid for wid in current.get("issued_ids", []) if wid not in previous_issued]
    start = previous.get("next_sequence", 1)
    expected_new = [f"WARDER-{sequence:08d}" for sequence in
                    range(start, start + len(added_in_issue_order))]
    if added_in_issue_order != expected_new:
        issues.append({"code": "NEW_ID_SEQUENCE_NOT_DETERMINISTIC",
                       "expected": expected_new, "actual": added_in_issue_order})
    old_history = previous.get("history", [])
    new_history = current.get("history", [])
    if new_history[:len(old_history)] != old_history:
        issues.append({"code": "HISTORY_REWRITTEN_OR_REORDERED"})
    appended = new_history[len(old_history):] if new_history[:len(old_history)] == old_history else []
    events_by_id = defaultdict(list)
    for event in appended:
        if isinstance(event, dict):
            events_by_id[event.get("warder_id")].append(event)
    for wid in sorted(old_ids & new_ids):
        before_row, after_row = old_records[wid], new_records[wid]
        if before_row.get("warder_id") != after_row.get("warder_id") or before_row.get("identity_key") != after_row.get("identity_key"):
            issues.append({"code": "EXISTING_IDENTITY_REASSIGNED", "warder_id": wid})
            continue
        events = events_by_id.get(wid, [])
        kinds = set()
        for event in events:
            kind = event.get("event_type")
            matches_after = {
                "NAME_CHANGED": event.get("new_name") == after_row.get("current_name"),
                "PROVIDER_CHANGED": event.get("operator_links") == after_row.get("operator_links"),
                "SATELLITE_CHANGED": event.get("satellite_positions") == after_row.get("satellite_positions"),
                "SERVICE_REFERENCE_CHANGED": event.get("service_references") == after_row.get("service_references"),
                "SERVICE_REMOVED": event.get("service_reference") in before_row.get("service_references", []) and
                    event.get("service_reference") not in after_row.get("service_references", []),
                "SOURCE_OBSERVED": event.get("source_ref") in after_row.get("source_provenance", []),
                "IDENTITY_RETIRED": after_row.get("status") == "retired",
                "IDENTITY_APPROVED": event.get("approval_ledger_event_id") in after_row.get("approval_history_refs", []),
                "APPROVAL_REVOKED": event.get("approval_ledger_event_id") in after_row.get("approval_history_refs", []),
                "ARTWORK_REBRANDED": event.get("new_variants") == after_row.get("artwork_current"),
                "ARTWORK_APPROVED": event.get("variants") == after_row.get("artwork_current"),
            }.get(kind, False)
            if matches_after:
                kinds.add(kind)
            else:
                issues.append({"code": "CHANGE_EVENT_DOES_NOT_MATCH_RECORD", "warder_id": wid,
                               "event_id": event.get("event_id")})
        unchanged_fields = {"warder_id", "identity_key"}
        event_fields = {
            "NAME_CHANGED": {"current_name", "historical_names"},
            "PROVIDER_CHANGED": {"operator_links"},
            "SATELLITE_CHANGED": {"satellite_positions"},
            "SERVICE_REFERENCE_CHANGED": {"service_references", "historical_service_references"},
            "SERVICE_REMOVED": {"service_references", "historical_service_references"},
            "SOURCE_OBSERVED": {"source_provenance"},
            "IDENTITY_RETIRED": {"status"},
            "IDENTITY_APPROVED": {"approval_history_refs"},
            "APPROVAL_REVOKED": {"approval_history_refs"},
            "ARTWORK_REBRANDED": {"artwork_current", "artwork_asset_paths", "artwork_history", "approval_history_refs"},
            "ARTWORK_APPROVED": {"artwork_current", "artwork_asset_paths", "approval_history_refs"},
        }
        authorized = set().union(*(event_fields.get(kind, set()) for kind in kinds)) if kinds else set()
        allowed = unchanged_fields | authorized | {"history_refs"}
        for field in set(before_row) | set(after_row):
            if before_row.get(field) != after_row.get(field) and field not in allowed:
                issues.append({"code": "UNAUTHORIZED_EXISTING_IDENTITY_EDIT", "warder_id": wid,
                               "field": field})
        if before_row.get("current_name") != after_row.get("current_name") and "NAME_CHANGED" not in kinds:
            issues.append({"code": "NAME_CHANGE_WITHOUT_EVENT", "warder_id": wid})
        if before_row.get("operator_links") != after_row.get("operator_links") and "PROVIDER_CHANGED" not in kinds:
            issues.append({"code": "PROVIDER_CHANGE_WITHOUT_EVENT", "warder_id": wid})
        if before_row.get("satellite_positions") != after_row.get("satellite_positions") and "SATELLITE_CHANGED" not in kinds:
            issues.append({"code": "SATELLITE_CHANGE_WITHOUT_EVENT", "warder_id": wid})
        refs_changed = any(before_row.get(key) != after_row.get(key)
                           for key in ("service_references", "historical_service_references"))
        if refs_changed and not kinds.intersection({"SERVICE_REFERENCE_CHANGED", "SERVICE_REMOVED"}):
            issues.append({"code": "SERVICE_REFERENCE_CHANGE_WITHOUT_EVENT", "warder_id": wid})
        if before_row.get("status") != after_row.get("status") and "IDENTITY_RETIRED" not in kinds:
            issues.append({"code": "STATUS_CHANGE_WITHOUT_EVENT", "warder_id": wid})
        art_changed = any(before_row.get(key) != after_row.get(key)
                          for key in ("artwork_current", "artwork_asset_paths", "artwork_history"))
        if art_changed and not kinds.intersection({"ARTWORK_REBRANDED", "ARTWORK_APPROVED"}):
            issues.append({"code": "ARTWORK_CHANGE_WITHOUT_REBRAND_EVENT", "warder_id": wid})
        if (before_row.get("approval_history_refs") != after_row.get("approval_history_refs") and
                not kinds.intersection({"IDENTITY_APPROVED", "APPROVAL_REVOKED", "ARTWORK_REBRANDED", "ARTWORK_APPROVED"})):
            issues.append({"code": "APPROVAL_REFERENCE_CHANGE_WITHOUT_EVENT", "warder_id": wid})
    for wid in sorted(new_ids - old_ids):
        events = events_by_id.get(wid, [])
        creations = [event for event in events if event.get("event_type") == "IDENTITY_CREATED"]
        if len(creations) != 1 or not events or events[0].get("event_type") != "IDENTITY_CREATED" or creations[0].get("human_confirmed") is not True:
            issues.append({"code": "NEW_ID_WITHOUT_CONFIRMED_CREATION_EVENT", "warder_id": wid})
    return {"status": "VALID" if not issues else "INVALID", "issues": issues,
            "new_ids": sorted(new_ids - old_ids), "retained_ids": len(old_ids & new_ids),
            "history_appended": max(0, len(new_history) - len(old_history))}


def _valid_sha(value):
    return isinstance(value, str) and bool(SHA256_PATTERN.fullmatch(value))


def _valid_asset_path(warder_id, value):
    if not isinstance(value, str) or ".." in value or "\\" in value or value.startswith("/"):
        return False
    return bool(re.fullmatch(r"factory/approved-picons/" + re.escape(warder_id) +
                             r"/v[0-9]{4}/(?:transparent|black|white)\.png", value))


def _unique_strings(value):
    return isinstance(value, list) and all(isinstance(item, str) and item.strip()
                                           for item in value) and len(value) == len(set(value))


def _privacy_issues(value, path="$", issues=None):
    issues = [] if issues is None else issues
    forbidden = re.compile(r"token|secret|password|credential|username|authorization", re.I)
    local_path = re.compile(r"(?:^[A-Za-z]:[\\/]|\\\\[^\\]+\\|/(?:home|Users)/)")
    if isinstance(value, dict):
        for key, child in value.items():
            if forbidden.search(str(key)):
                issues.append({"code": "SENSITIVE_FIELD_NAME", "field": path + "." + str(key)})
            _privacy_issues(child, path + "." + str(key), issues)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _privacy_issues(child, f"{path}[{index}]", issues)
    elif isinstance(value, str) and local_path.search(value.strip()):
        issues.append({"code": "LOCAL_ABSOLUTE_PATH", "field": path})
    return issues


def validate_registry(registry):
    """Return a structural/invariant audit without repairing the input."""
    issues = []
    if not isinstance(registry, dict):
        return {"status": "INVALID", "record_count": 0, "issues": [{"code": "ROOT_NOT_OBJECT"}]}
    if registry.get("schema") != SCHEMA or registry.get("authority") != AUTHORITY:
        issues.append({"code": "SCHEMA_OR_AUTHORITY_MISMATCH"})
    issues.extend(_privacy_issues(registry))
    records = registry.get("records")
    if not isinstance(records, dict):
        records = {}
        issues.append({"code": "RECORDS_NOT_OBJECT"})
    issued = registry.get("issued_ids")
    if not _unique_strings(issued):
        issued = []
        issues.append({"code": "ISSUED_IDS_INVALID"})
    if set(issued) != set(records):
        issues.append({"code": "ISSUED_IDS_RECORDS_MISMATCH"})
    by_identity = {}
    refs = defaultdict(set)
    retired = ambiguous = 0
    for warder_id, row in records.items():
        if not isinstance(warder_id, str) or not ID_PATTERN.fullmatch(warder_id):
            issues.append({"code": "INVALID_WARDER_ID", "warder_id": warder_id})
            continue
        if not isinstance(row, dict) or row.get("warder_id") != warder_id:
            issues.append({"code": "RECORD_ID_MISMATCH", "warder_id": warder_id})
            continue
        required = ("canonical_identity", "current_name", "historical_names",
                    "service_references", "historical_service_references",
                    "operator_links", "satellite_positions", "artwork_current",
                    "artwork_history", "source_provenance", "approval_history_refs",
                    "status", "created_at", "first_seen", "history_refs",
                    "artwork_asset_paths")
        missing = [field for field in required if field not in row]
        if missing:
            issues.append({"code": "RECORD_FIELDS_MISSING", "warder_id": warder_id,
                           "fields": missing})
        if not isinstance(row.get("canonical_identity"), dict) or not isinstance(row.get("first_seen"), dict):
            issues.append({"code": "INVALID_IDENTITY_METADATA", "warder_id": warder_id})
        if not isinstance(row.get("current_name"), str) or not isinstance(row.get("created_at"), str):
            issues.append({"code": "INVALID_NAME_OR_CREATION_TIME", "warder_id": warder_id})
        for field in ("historical_names", "source_provenance", "artwork_history"):
            if not isinstance(row.get(field), list):
                issues.append({"code": "INVALID_RECORD_LIST", "warder_id": warder_id,
                               "field": field})
        identity_key = row.get("identity_key")
        if not isinstance(identity_key, str) or not identity_key.strip():
            issues.append({"code": "IDENTITY_KEY_MISSING", "warder_id": warder_id})
        elif identity_key in by_identity:
            issues.append({"code": "IDENTITY_KEY_DUPLICATE", "identity_key": identity_key,
                           "warder_ids": sorted([by_identity[identity_key], warder_id])})
        else:
            by_identity[identity_key] = warder_id
        if row.get("status") not in {"active", "retired", "ambiguous", "pending"}:
            issues.append({"code": "INVALID_STATUS", "warder_id": warder_id})
        retired += row.get("status") == "retired"
        ambiguous += row.get("status") == "ambiguous"
        for field in ("service_references", "historical_service_references",
                      "operator_links", "satellite_positions", "history_refs",
                      "approval_history_refs"):
            values = row.get(field, [])
            if not _unique_strings(values):
                issues.append({"code": "INVALID_COLLECTION", "warder_id": warder_id,
                               "field": field})
        for ref in row.get("service_references", []) + row.get("historical_service_references", []):
            refs[ref].add(warder_id)
        artwork = row.get("artwork_current", {})
        if not isinstance(artwork, dict):
            issues.append({"code": "INVALID_ARTWORK_CURRENT", "warder_id": warder_id})
        else:
            for style, digest in artwork.items():
                if style not in STYLES or not _valid_sha(digest):
                    issues.append({"code": "INVALID_ARTWORK_HASH", "warder_id": warder_id,
                                   "style": style})
        paths = row.get("artwork_asset_paths", {})
        if not isinstance(paths, dict) or set(paths) - set(STYLES):
            issues.append({"code": "INVALID_ARTWORK_ASSET_PATHS", "warder_id": warder_id})
        elif any(not _valid_asset_path(warder_id, path) for path in paths.values()):
            issues.append({"code": "UNSAFE_ARTWORK_ASSET_PATH", "warder_id": warder_id})
        if isinstance(artwork, dict) and artwork and set(artwork) != set(paths):
            issues.append({"code": "ARTWORK_HASH_PATH_MISMATCH", "warder_id": warder_id})
    for ref, ids in refs.items():
        if len(ids) > 1:
            issues.append({"code": "SERVICE_REFERENCE_COLLISION", "service_reference": ref,
                           "warder_ids": sorted(ids)})
    history = registry.get("history")
    if not isinstance(history, list):
        history = []
        issues.append({"code": "HISTORY_NOT_LIST"})
    event_ids = set()
    linked_history = defaultdict(list)
    for event in history:
        if not isinstance(event, dict):
            issues.append({"code": "INVALID_HISTORY_EVENT"})
            continue
        event_id = event.get("event_id")
        wid = event.get("warder_id")
        if not isinstance(event_id, str) or event_id in event_ids:
            issues.append({"code": "HISTORY_EVENT_ID_INVALID_OR_DUPLICATE", "event_id": event_id})
        event_ids.add(event_id)
        if wid not in records:
            issues.append({"code": "HISTORY_UNKNOWN_WARDER_ID", "warder_id": wid})
        else:
            linked_history[wid].append(event_id)
        if event.get("event_type") not in REGISTRY_EVENTS:
            issues.append({"code": "UNKNOWN_HISTORY_EVENT", "event_id": event_id})
        body = {key: value for key, value in event.items() if key != "event_id"}
        if not isinstance(event_id, str) or event_id != "WE-" + sha256_json(body)[:24]:
            issues.append({"code": "HISTORY_EVENT_HASH_MISMATCH", "event_id": event_id})
        if not _evidence_ok(event):
            issues.append({"code": "HISTORY_EVIDENCE_INVALID", "event_id": event_id})
        kind = event.get("event_type")
        if kind == "IDENTITY_CREATED":
            if event.get("human_confirmed") is not True or (wid in records and event.get("identity_key") != records[wid].get("identity_key")):
                issues.append({"code": "IDENTITY_CREATION_UNCONFIRMED_OR_MISMATCHED", "event_id": event_id})
        elif kind in REGISTRY_EVENTS:
            if event.get("identity_continuity_confirmed") is not True:
                issues.append({"code": "IDENTITY_CONTINUITY_NOT_CONFIRMED", "event_id": event_id})
        if kind == "NAME_CHANGED" and (not isinstance(event.get("new_name"), str) or not event["new_name"].strip()):
            issues.append({"code": "NAME_CHANGE_EVENT_INCOMPLETE", "event_id": event_id})
        if kind == "PROVIDER_CHANGED" and not _unique_strings(event.get("operator_links")):
            issues.append({"code": "PROVIDER_CHANGE_EVENT_INCOMPLETE", "event_id": event_id})
        if kind == "SATELLITE_CHANGED" and not _unique_strings(event.get("satellite_positions")):
            issues.append({"code": "SATELLITE_CHANGE_EVENT_INCOMPLETE", "event_id": event_id})
        if kind == "SERVICE_REFERENCE_CHANGED" and not all(_unique_strings(event.get(field)) for field in
                ("previous_service_references", "service_references")):
            issues.append({"code": "SERVICE_REFERENCE_EVENT_INCOMPLETE", "event_id": event_id})
        if kind == "SERVICE_REMOVED" and not isinstance(event.get("service_reference"), str):
            issues.append({"code": "SERVICE_REMOVED_EVENT_INCOMPLETE", "event_id": event_id})
        if kind == "ARTWORK_REBRANDED" and not all(event.get(key) is True for key in
                ("official_rebrand_confirmed", "qa_approved", "human_approved")):
            issues.append({"code": "REBRAND_APPROVAL_EVIDENCE_INCOMPLETE", "event_id": event_id})
        if kind == "ARTWORK_REBRANDED" and not all(
                isinstance(event.get(field), dict) and all(_valid_sha(event[field].get(style)) for style in STYLES)
                for field in ("previous_variants", "new_variants")):
            issues.append({"code": "REBRAND_VARIANT_HASHES_INCOMPLETE", "event_id": event_id})
    for wid, row in records.items():
        if isinstance(row, dict) and set(row.get("history_refs", [])) != set(linked_history.get(wid, [])):
            issues.append({"code": "HISTORY_REFERENCE_MISMATCH", "warder_id": wid})
    sequence = registry.get("next_sequence")
    max_sequence = max((int(match.group(1)) for wid in issued
                        if isinstance(wid, str) and (match := ID_PATTERN.fullmatch(wid))), default=0)
    if not isinstance(sequence, int) or sequence != max_sequence + 1:
        issues.append({"code": "ID_SEQUENCE_NOT_MONOTONIC"})
    return {"status": "VALID" if not issues else "INVALID", "record_count": len(records),
            "active": sum(isinstance(row, dict) and row.get("status") == "active" for row in records.values()),
            "retired": retired, "ambiguous": ambiguous,
            "service_references": len(refs),
            "service_references_with_multiple_ids": sum(len(ids) > 1 for ids in refs.values()),
            "ids_with_multiple_providers": sum(isinstance(row, dict) and len(row.get("operator_links", [])) > 1 for row in records.values()),
            "ids_with_historical_references": sum(isinstance(row, dict) and bool(row.get("historical_service_references")) for row in records.values()),
            "history_events": len(history), "issues": issues}


def resolve_service_reference(registry, service_reference):
    """Resolve exact current/historical aliases; never infer from artwork or labels."""
    hits = sorted(wid for wid, row in registry.get("records", {}).items()
                  if service_reference in row.get("service_references", []) + row.get("historical_service_references", []))
    if not hits:
        return {"status": "NO_MATCH", "warder_ids": []}
    if len(hits) > 1:
        return {"status": "CONFLICT", "warder_ids": hits}
    return {"status": "EXACT", "warder_ids": hits}


def audit_master_migration(master_services, registry, assertions=None):
    """Fail-closed migration classification for a Master index.

    Assertions may only disambiguate through an explicit existing Warder ID or
    establish a new identity with an explicit human confirmation and evidence.
    An unmatched service ref is never auto-assigned an ID.
    """
    assertions = assertions if isinstance(assertions, dict) else {}
    services = master_services if isinstance(master_services, dict) else {}
    if validate_registry(registry)["status"] != "VALID":
        decisions = [{"service_reference": str(ref), "classification": "CONFLICT",
                      "reason": "WARDER_ID_REGISTRY_INVALID_FAIL_CLOSED",
                      "warder_ids": [], "identity_verified": False,
                      "new_id_allocated": False} for ref in sorted(services)]
        return {"schema": SCHEMA, "read_only": True, "automatic_id_assignment": False,
                "counts": {"AUTO_MAPPABLE": 0, "AMBIGUOUS": 0,
                           "CONFLICT": len(decisions), "NEW_ID_REQUIRED": 0},
                "decisions": decisions}
    decisions = []
    for ref in sorted(services):
        assertion = assertions.get(ref, {})
        assertion = assertion if isinstance(assertion, dict) else {}
        explicit_ids = assertion.get("candidate_warder_ids", [])
        explicit_ids = sorted(set(v for v in explicit_ids if isinstance(v, str))) if isinstance(explicit_ids, list) else []
        direct = resolve_service_reference(registry, ref)
        if direct["status"] == "CONFLICT":
            category, reason, matched = "CONFLICT", "SERVICE_REFERENCE_LINKED_TO_MULTIPLE_IDS", []
        elif len(explicit_ids) > 1:
            category, reason, matched = "AMBIGUOUS", "MULTIPLE_EXPLICIT_ID_CANDIDATES", []
        elif direct["status"] == "EXACT":
            wid = direct["warder_ids"][0]
            if explicit_ids and explicit_ids != [wid]:
                category, reason, matched = "CONFLICT", "ASSERTION_CONTRADICTS_CANONICAL_LINK", []
            else:
                category, reason, matched = "AUTO_MAPPABLE", "EXACT_CURRENT_OR_HISTORICAL_REFERENCE_LINK", [wid]
        elif explicit_ids:
            wid = explicit_ids[0]
            if wid not in registry.get("records", {}):
                category, reason, matched = "CONFLICT", "ASSERTION_REFERENCES_UNKNOWN_WARDER_ID", []
            elif not (assertion.get("identity_continuity_confirmed") is True and
                      isinstance(assertion.get("evidence_ref"), str) and assertion.get("evidence_ref").strip() and
                      _valid_sha(assertion.get("evidence_sha256"))):
                category, reason, matched = "AMBIGUOUS", "EXPLICIT_LINK_LACKS_CONTINUITY_EVIDENCE", []
            else:
                category, reason, matched = "AUTO_MAPPABLE", "EXPLICIT_CONTINUITY_EVIDENCE", [wid]
        elif assertion.get("ambiguous") is True or assertion.get("conflict") is True:
            category, reason, matched = "AMBIGUOUS", "SOURCE_ASSERTS_AMBIGUOUS_MAPPING", []
        else:
            category, reason, matched = "NEW_ID_REQUIRED", "NO_CANONICAL_ID_LINK_REQUIRES_HUMAN_IDENTITY_CHECK", []
        decisions.append({"service_reference": str(ref), "classification": category,
                          "reason": reason, "warder_ids": matched,
                          "identity_verified": category == "AUTO_MAPPABLE",
                          "new_id_allocated": False,
                          "evidence_ref": assertion.get("evidence_ref") if category == "AUTO_MAPPABLE" else None})
    counts = Counter(row["classification"] for row in decisions)
    return {"schema": SCHEMA, "read_only": True, "automatic_id_assignment": False,
            "counts": {key: counts.get(key, 0) for key in
                       ("AUTO_MAPPABLE", "AMBIGUOUS", "CONFLICT", "NEW_ID_REQUIRED")},
            "decisions": decisions}


def _evidence_ok(evidence):
    return (isinstance(evidence, dict) and isinstance(evidence.get("evidence_ref"), str) and
            bool(evidence["evidence_ref"].strip()) and _valid_sha(evidence.get("evidence_sha256")) and
            isinstance(evidence.get("occurred_at"), str) and bool(evidence["occurred_at"].strip()))


def register_confirmed_identity(registry, identity, *, evidence, identity_confirmed=False):
    """Pure allocation of the next never-reused ID after explicit confirmation."""
    validation = validate_registry(registry)
    if validation["status"] != "VALID":
        raise ValueError("Cannot allocate from an invalid Warder ID registry")
    if identity_confirmed is not True or not _evidence_ok(evidence):
        raise PermissionError("Explicit human identity confirmation and hashed evidence are required")
    if not isinstance(identity, dict) or not isinstance(identity.get("identity_key"), str) or not identity["identity_key"].strip():
        raise ValueError("Canonical identity_key is required")
    identity_key = identity["identity_key"].strip()
    if any(row.get("identity_key") == identity_key for row in registry["records"].values()):
        raise ValueError("Canonical identity_key already has a Warder ID")
    result = copy.deepcopy(registry)
    sequence = result["next_sequence"]
    wid = f"WARDER-{sequence:08d}"
    if wid in result["issued_ids"]:
        raise ValueError("ID sequence would reuse a previously issued Warder ID")
    event = {"event_type": "IDENTITY_CREATED", "warder_id": wid,
             "identity_key": identity_key, "evidence_ref": evidence["evidence_ref"].strip(),
             "evidence_sha256": evidence["evidence_sha256"].lower(),
             "occurred_at": evidence["occurred_at"], "human_confirmed": True}
    event["event_id"] = "WE-" + sha256_json(event)[:24]
    row = {"warder_id": wid, "identity_key": identity_key,
           "canonical_identity": copy.deepcopy(identity.get("canonical_identity", {})),
           "current_name": str(identity.get("current_name", "")).strip(),
           "historical_names": [], "operator_links": sorted(set(identity.get("operator_links", []))),
           "satellite_positions": sorted(set(identity.get("satellite_positions", []))),
           "service_references": sorted(set(identity.get("service_references", []))),
           "historical_service_references": [], "artwork_current": {}, "artwork_history": [],
           "artwork_asset_paths": {},
           "source_provenance": copy.deepcopy(identity.get("source_provenance", [])),
           "approval_history_refs": [], "status": "active",
           "created_at": evidence["occurred_at"], "first_seen": copy.deepcopy(identity.get("first_seen", {})),
           "history_refs": [event["event_id"]]}
    result["records"][wid] = row
    result["issued_ids"].append(wid)
    result["next_sequence"] = sequence + 1
    result["history"].append(event)
    if validate_registry(result)["status"] != "VALID":
        raise ValueError("New identity does not satisfy Warder ID registry invariants")
    return result, wid


def append_identity_event(registry, event, *, human_confirmed=False):
    """Return a new registry with one evidence-backed event; never edit history."""
    if validate_registry(registry)["status"] != "VALID":
        raise ValueError("Cannot update an invalid Warder ID registry")
    if not isinstance(event, dict) or event.get("event_type") not in REGISTRY_EVENTS - {"IDENTITY_CREATED"}:
        raise ValueError("A supported post-creation registry event is required")
    wid = event.get("warder_id")
    if wid not in registry["records"]:
        raise ValueError("Warder ID must already exist")
    if not _evidence_ok(event):
        raise ValueError("Evidence reference, SHA-256, and timestamp are required")
    if human_confirmed is not True or event.get("identity_continuity_confirmed") is not True:
        raise PermissionError("Explicit human confirmation of identity continuity is required")
    clean = copy.deepcopy(event)
    clean["evidence_sha256"] = clean["evidence_sha256"].lower()
    kind = clean["event_type"]
    if kind == "NAME_CHANGED":
        clean["new_name"] = str(clean.get("new_name", "")).strip()
    elif kind == "PROVIDER_CHANGED" and isinstance(clean.get("operator_links"), list):
        clean["operator_links"] = sorted(set(clean["operator_links"]))
    elif kind == "SATELLITE_CHANGED" and isinstance(clean.get("satellite_positions"), list):
        clean["satellite_positions"] = sorted(set(clean["satellite_positions"]))
    elif kind == "SERVICE_REFERENCE_CHANGED":
        for field in ("previous_service_references", "service_references"):
            if isinstance(clean.get(field), list):
                clean[field] = sorted(set(clean[field]))
    elif kind == "SOURCE_OBSERVED":
        clean["source_ref"] = str(clean.get("source_ref", "")).strip()
    elif kind in ("ARTWORK_APPROVED", "ARTWORK_REBRANDED"):
        for field in ("previous_variants", "new_variants", "variants"):
            if isinstance(clean.get(field), dict):
                clean[field] = {style: value.lower() if isinstance(value, str) else value
                                for style, value in clean[field].items()}
    clean["event_id"] = "WE-" + sha256_json(clean)[:24]
    if any(old.get("event_id") == clean["event_id"] for old in registry["history"]):
        raise ValueError("History event already exists")
    result = copy.deepcopy(registry)
    row = result["records"][wid]
    if kind == "NAME_CHANGED":
        old, new = row.get("current_name", ""), str(clean.get("new_name", "")).strip()
        if not new or new == old:
            raise ValueError("A different non-empty station name is required")
        if old and old not in row["historical_names"]:
            row["historical_names"].append(old)
        row["current_name"] = new
    elif kind == "PROVIDER_CHANGED":
        values = clean.get("operator_links")
        if not _unique_strings(values):
            raise ValueError("Explicit operator link collection is required")
        row["operator_links"] = sorted(values)
    elif kind == "SATELLITE_CHANGED":
        values = clean.get("satellite_positions")
        if not _unique_strings(values):
            raise ValueError("Explicit satellite position collection is required")
        row["satellite_positions"] = sorted(values)
    elif kind == "SERVICE_REFERENCE_CHANGED":
        old_refs, new_refs = clean.get("previous_service_references"), clean.get("service_references")
        if not _unique_strings(old_refs) or not _unique_strings(new_refs):
            raise ValueError("Previous and current service references are required")
        if not set(old_refs).issubset(set(row["service_references"])):
            raise ValueError("Previous service references do not match current registry state")
        row["historical_service_references"] = sorted(set(row["historical_service_references"]) | (set(old_refs) - set(new_refs)))
        row["service_references"] = sorted(set(new_refs))
    elif kind == "SERVICE_REMOVED":
        ref = clean.get("service_reference")
        if ref not in row["service_references"]:
            raise ValueError("Removed service reference is not currently linked")
        row["service_references"].remove(ref)
        if ref not in row["historical_service_references"]:
            row["historical_service_references"].append(ref)
    elif kind == "SOURCE_OBSERVED":
        source_ref = clean.get("source_ref")
        if not source_ref or source_ref.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:[\\/]", source_ref):
            raise ValueError("Source provenance must be a safe source-relative reference")
        if source_ref not in row["source_provenance"]:
            row["source_provenance"].append(source_ref)
    elif kind == "IDENTITY_RETIRED":
        row["status"] = "retired"
    elif kind in ("IDENTITY_APPROVED", "APPROVAL_REVOKED"):
        approval_ref = clean.get("approval_ledger_event_id")
        if not isinstance(approval_ref, str) or not approval_ref.startswith("AP-"):
            raise ValueError("Git approval ledger event reference is required")
        if approval_ref in row["approval_history_refs"]:
            raise ValueError("Approval ledger event is already linked")
        row["approval_history_refs"].append(approval_ref)
    elif kind in ("ARTWORK_APPROVED", "ARTWORK_REBRANDED"):
        if clean.get("qa_approved") is not True or clean.get("human_approved") is not True:
            raise PermissionError("Artwork change requires QA and explicit human approval")
        if kind == "ARTWORK_REBRANDED" and clean.get("official_rebrand_confirmed") is not True:
            raise PermissionError("Rebrand requires official rebrand evidence")
        before = clean.get("previous_variants", {})
        after = clean.get("variants") if kind == "ARTWORK_APPROVED" else clean.get("new_variants")
        if kind == "ARTWORK_APPROVED" and row.get("artwork_current"):
            raise ValueError("Existing artwork must use the explicit rebrand flow")
        if kind == "ARTWORK_REBRANDED" and (not isinstance(before, dict) or
                any(row.get("artwork_current", {}).get(style) != before.get(style) for style in STYLES)):
            raise ValueError("Previous artwork hashes do not match the current Warder Master state")
        if not isinstance(after, dict) or set(after) != set(STYLES) or any(not _valid_sha(after.get(style)) for style in STYLES):
            raise ValueError("All three new variant hashes are required")
        paths = clean.get("asset_paths")
        if not isinstance(paths, dict) or set(paths) != set(STYLES) or any(not _valid_asset_path(wid, paths.get(style)) for style in STYLES):
            raise ValueError("All three immutable Git artwork asset paths are required")
        approval_ref = clean.get("approval_ledger_event_id")
        if not isinstance(approval_ref, str) or not approval_ref.startswith("AP-"):
            raise ValueError("Git approval ledger event reference is required")
        if kind == "ARTWORK_REBRANDED":
            if all(before[style].lower() == after[style].lower() for style in STYLES):
                raise ValueError("Artwork history event contains no content change")
            row["artwork_history"].append({"event_id": clean["event_id"],
                "previous_variants": {s: before[s].lower() for s in STYLES},
                "previous_asset_paths": copy.deepcopy(row.get("artwork_asset_paths", {})),
                "new_variants": {s: after[s].lower() for s in STYLES},
                "new_asset_paths": dict(paths)})
        row["artwork_current"] = {s: after[s].lower() for s in STYLES}
        row["artwork_asset_paths"] = dict(paths)
        if approval_ref not in row["approval_history_refs"]:
            row["approval_history_refs"].append(approval_ref)
    result["history"].append(clean)
    row["history_refs"].append(clean["event_id"])
    if validate_registry(result)["status"] != "VALID":
        raise ValueError("Event would violate Warder ID registry invariants")
    return result


def normalize_change_watch_event(event):
    """Validate the future Change Watch hook without applying it to Master."""
    if not isinstance(event, dict) or event.get("event_type") not in WATCH_EVENTS:
        raise ValueError("Unsupported Warder Change Watch event")
    required = ("event_id", "observed_at", "source_ref")
    if any(not isinstance(event.get(key), str) or not event[key].strip() for key in required):
        raise ValueError("Change Watch event needs stable event_id, observed_at and source_ref")
    if not _valid_sha(event.get("evidence_sha256")):
        raise ValueError("Change Watch evidence SHA-256 is required")
    return {"schema": SCHEMA, "event_id": event["event_id"].strip(),
            "event_type": event["event_type"], "observed_at": event["observed_at"].strip(),
            "source_ref": event["source_ref"].strip(),
            "evidence_sha256": event["evidence_sha256"].lower(),
            "service_reference": event.get("service_reference"),
            "warder_id": event.get("warder_id"), "details": copy.deepcopy(event.get("details", {})),
            "applied_to_registry": False}


def registry_rows(registry, approval_ledger=None):
    """Create safe read-only rows using only the Git approval ledger."""
    events = approval_ledger.get("events", []) if isinstance(approval_ledger, dict) else []
    approvals = defaultdict(list)
    for event in events:
        if isinstance(event, dict) and isinstance(event.get("warder_id"), str):
            approvals[event["warder_id"]].append(event)
    rows = []
    for wid, row in sorted(registry.get("records", {}).items()):
        refs = row.get("service_references", []) + row.get("historical_service_references", [])
        relevant = approvals.get(wid, [])
        latest = relevant[-1] if relevant else None
        if latest and latest.get("decision") == "APPROVAL_REVOKED":
            approval = "REVOKED"
        elif latest and latest.get("decision") in {"ARTWORK_APPROVED", "IDENTITY_AND_ARTWORK_APPROVED"}:
            variants = latest.get("variants", {})
            approval = "APPROVED" if all(variants.get(style) == row.get("artwork_current", {}).get(style)
                                          and _valid_sha(variants.get(style)) for style in STYLES) else "STALE_EVIDENCE"
        elif latest and latest.get("decision") == "IDENTITY_APPROVED":
            approval = "IDENTITY_APPROVED"
        else:
            approval = "NO_GIT_APPROVAL"
        rows.append({"warder_id": wid, "name": row.get("current_name", ""),
                     "service_references": refs, "operators": row.get("operator_links", []),
                     "satellites": row.get("satellite_positions", []), "status": row.get("status", "pending"),
                     "approval": approval, "artwork_current": row.get("artwork_current", {}),
                     "artwork_history": row.get("artwork_history", []),
                     "history_refs": row.get("history_refs", [])})
    return rows


def empty_approval_ledger():
    return {"schema": 1, "authority": "WARDER_MASTER_APPROVAL_LEDGER", "events": []}


def validate_approval_ledger_transition(previous, current):
    """Approval events are append-only; revocation is a new event, never deletion."""
    issues = []
    old = previous.get("events", []) if isinstance(previous, dict) else None
    new = current.get("events", []) if isinstance(current, dict) else None
    if not isinstance(old, list) or not isinstance(new, list) or new[:len(old)] != old:
        issues.append({"code": "APPROVAL_LEDGER_REWRITTEN_OR_REORDERED"})
    return {"status": "INVALID" if issues else "VALID", "issues": issues,
            "appended": max(0, len(new) - len(old)) if isinstance(old, list) and isinstance(new, list) else 0}


def validate_approval_ledger(ledger, registry):
    """Validate the append-only Git approval ledger separately from identity."""
    issues = []
    if not isinstance(ledger, dict) or ledger.get("schema") != 1 or ledger.get("authority") != "WARDER_MASTER_APPROVAL_LEDGER":
        return {"status": "INVALID", "event_count": 0,
                "issues": [{"code": "APPROVAL_LEDGER_SCHEMA_INVALID"}]}
    events = ledger.get("events")
    if not isinstance(events, list):
        return {"status": "INVALID", "event_count": 0,
                "issues": [{"code": "APPROVAL_LEDGER_EVENTS_INVALID"}]}
    issues.extend(_privacy_issues(ledger))
    seen = set()
    seen_approval_ids = set()
    refs = defaultdict(set)
    by_event_id = {}
    revoked_events = set()
    records = registry.get("records", {}) if isinstance(registry, dict) else {}
    for event in events:
        if not isinstance(event, dict):
            issues.append({"code": "APPROVAL_EVENT_INVALID"}); continue
        event_id = event.get("event_id")
        body = {key: value for key, value in event.items() if key != "event_id"}
        if not isinstance(event_id, str) or event_id != "AP-" + sha256_json(body)[:24] or event_id in seen:
            issues.append({"code": "APPROVAL_EVENT_ID_INVALID_OR_DUPLICATE", "event_id": event_id})
        seen.add(event_id)
        by_event_id[event_id] = event
        wid = event.get("warder_id")
        if wid not in records:
            issues.append({"code": "APPROVAL_UNKNOWN_WARDER_ID", "warder_id": wid})
        else:
            refs[wid].add(event_id)
        if event.get("event_type") != "MASTER_APPROVAL":
            issues.append({"code": "UNKNOWN_APPROVAL_EVENT_TYPE", "event_id": event_id})
        approval_id = event.get("approval_id")
        if not isinstance(approval_id, str) or not approval_id.strip() or approval_id in seen_approval_ids:
            issues.append({"code": "APPROVAL_ID_MISSING_OR_REUSED", "event_id": event_id})
        if isinstance(approval_id, str):
            seen_approval_ids.add(approval_id)
        if event.get("decision") not in {"IDENTITY_APPROVED", "ARTWORK_APPROVED", "IDENTITY_AND_ARTWORK_APPROVED", "APPROVAL_REVOKED"}:
            issues.append({"code": "INVALID_APPROVAL_DECISION", "event_id": event_id})
        for field in ("approval_id", "approved_at", "evidence_ref", "review_evidence_sha256"):
            if not isinstance(event.get(field), str) or not event[field].strip():
                issues.append({"code": "APPROVAL_EVIDENCE_FIELD_MISSING", "event_id": event_id,
                               "field": field})
        if not _valid_sha(event.get("evidence_sha256")) or not _valid_sha(event.get("review_evidence_sha256")):
            issues.append({"code": "APPROVAL_EVIDENCE_HASH_INVALID", "event_id": event_id})
        if event.get("human_approved") is not True:
            issues.append({"code": "APPROVAL_NOT_HUMAN_CONFIRMED", "event_id": event_id})
        if event.get("decision") == "APPROVAL_REVOKED":
            target = by_event_id.get(event.get("revokes_event_id"))
            if (not target or target.get("warder_id") != wid or
                    target.get("decision") == "APPROVAL_REVOKED" or event.get("revokes_event_id") in revoked_events or
                    target.get("event_id") == event_id):
                issues.append({"code": "APPROVAL_REVOCATION_TARGET_INVALID", "event_id": event_id})
            else:
                revoked_events.add(event.get("revokes_event_id"))
        if event.get("decision") in {"ARTWORK_APPROVED", "IDENTITY_AND_ARTWORK_APPROVED"}:
            if (not isinstance(event.get("qa_evidence_ref"), str) or not event["qa_evidence_ref"].strip()
                    or not _valid_sha(event.get("qa_evidence_sha256"))):
                issues.append({"code": "ARTWORK_APPROVAL_QA_EVIDENCE_MISSING", "event_id": event_id})
            record = records.get(wid, {})
            variants, paths = event.get("variants"), event.get("asset_paths")
            if not isinstance(variants, dict) or not isinstance(paths, dict) or set(variants) != set(STYLES) or set(paths) != set(STYLES):
                issues.append({"code": "APPROVED_ARTWORK_TRIPLET_MISSING", "event_id": event_id})
            else:
                known_versions = [(record.get("artwork_current", {}), record.get("artwork_asset_paths", {}))]
                for version in record.get("artwork_history", []):
                    known_versions.extend(((version.get("previous_variants", {}), version.get("previous_asset_paths", {})),
                                           (version.get("new_variants", {}), version.get("new_asset_paths", {}))))
                version_match = any(variants == hashes and paths == asset_paths
                                    for hashes, asset_paths in known_versions)
                if not version_match:
                    issues.append({"code": "APPROVED_ARTWORK_VERSION_NOT_IN_IDENTITY_HISTORY", "event_id": event_id})
                for style in STYLES:
                    if not _valid_sha(variants.get(style)):
                        issues.append({"code": "APPROVED_ARTWORK_HASH_DOES_NOT_MATCH_REGISTRY", "event_id": event_id,
                                       "style": style})
                    if not _valid_asset_path(wid, paths.get(style)):
                        issues.append({"code": "APPROVED_ARTWORK_PATH_DOES_NOT_MATCH_REGISTRY", "event_id": event_id,
                                       "style": style})
    return {"status": "VALID" if not issues else "INVALID", "event_count": len(events),
            "unique_approved_ids": len({event.get("warder_id") for event in events
                                         if isinstance(event, dict) and event.get("decision") != "APPROVAL_REVOKED"}),
            "issues": issues, "identity_and_approval_are_separate": True}


def validate_master_store(registry, ledger, read_asset=None):
    """Cross-check registry, ledger, immutable artwork files, and all links."""
    identity = validate_registry(registry)
    approvals = validate_approval_ledger(ledger, registry)
    issues = [{"scope": "identity", **item} for item in identity["issues"]]
    issues.extend({"scope": "approval", **item} for item in approvals["issues"])
    events = ledger.get("events", []) if isinstance(ledger, dict) else []
    expected_refs = defaultdict(set)
    for event in events:
        if isinstance(event, dict) and isinstance(event.get("warder_id"), str):
            expected_refs[event["warder_id"]].add(event.get("event_id"))
    for wid, row in registry.get("records", {}).items() if isinstance(registry, dict) else ():
        if set(row.get("approval_history_refs", [])) != expected_refs.get(wid, set()):
            issues.append({"scope": "cross_reference", "code": "APPROVAL_HISTORY_LINK_MISMATCH",
                           "warder_id": wid})
        assets = []
        current = row.get("artwork_current", {})
        paths = row.get("artwork_asset_paths", {})
        if current:
            assets.append((current, paths, "current"))
        for index, history in enumerate(row.get("artwork_history", [])):
            assets.extend(((history.get("previous_variants", {}), history.get("previous_asset_paths", {}), f"history[{index}].previous"),
                           (history.get("new_variants", {}), history.get("new_asset_paths", {}), f"history[{index}].new")))
        for hashes, asset_paths, label in assets:
            for style in STYLES:
                path = asset_paths.get(style) if isinstance(asset_paths, dict) else None
                digest = hashes.get(style) if isinstance(hashes, dict) else None
                if not _valid_asset_path(wid, path) or not _valid_sha(digest):
                    issues.append({"scope": "asset", "code": "ARTWORK_REFERENCE_INVALID",
                                   "warder_id": wid, "location": label, "style": style})
                elif read_asset is not None:
                    try:
                        content = read_asset(path)
                        if hashlib.sha256(content).hexdigest() != digest:
                            issues.append({"scope": "asset", "code": "ARTWORK_ASSET_SHA256_MISMATCH",
                                           "warder_id": wid, "path": path, "style": style})
                    except (OSError, KeyError, ValueError):
                        issues.append({"scope": "asset", "code": "ARTWORK_ASSET_MISSING",
                                       "warder_id": wid, "path": path, "style": style})
    return {"status": "VALID" if not issues else "INVALID", "identity": identity,
            "approval_ledger": approvals, "issues": issues,
            "production_branch_written": False}


def make_approval_event(*, warder_id, decision, approval_id, approved_at,
                        evidence_ref, evidence_sha256, review_evidence_sha256,
                        variants=None, asset_paths=None, human_approved=False,
                        qa_evidence_ref=None, qa_evidence_sha256=None):
    """Create a content-addressed ledger event from an explicit human action."""
    if human_approved is not True:
        raise PermissionError("Only an explicit human approval can create a Master ledger event")
    if decision in {"ARTWORK_APPROVED", "IDENTITY_AND_ARTWORK_APPROVED"} and (
            not isinstance(qa_evidence_ref, str) or not qa_evidence_ref.strip() or
            not _valid_sha(qa_evidence_sha256)):
        raise ValueError("Artwork approval requires a hashed QA evidence reference")
    body = {"event_type": "MASTER_APPROVAL", "warder_id": warder_id,
            "decision": decision, "approval_id": approval_id,
            "approved_at": approved_at, "evidence_ref": evidence_ref,
            "evidence_sha256": str(evidence_sha256).lower(),
            "review_evidence_sha256": str(review_evidence_sha256).lower(),
            "human_approved": True}
    if variants is not None:
        body["variants"] = {key: str(value).lower() for key, value in variants.items()}
    if asset_paths is not None:
        body["asset_paths"] = dict(asset_paths)
    if qa_evidence_ref is not None:
        body["qa_evidence_ref"] = qa_evidence_ref
    if qa_evidence_sha256 is not None:
        body["qa_evidence_sha256"] = str(qa_evidence_sha256).lower()
    body["event_id"] = "AP-" + sha256_json(body)[:24]
    return body
