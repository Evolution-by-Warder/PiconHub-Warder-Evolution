"""Compatibility policy for permanent Warder identities and artwork history.

This module does not allocate Warder IDs or define a competing registry. It
validates an existing authoritative ID source when one is supplied, and makes
logo changes an explicit, append-only proposal/approval lifecycle.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re

SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
REQUIRED_STYLES = ("transparent", "black", "white")
LIFECYCLE_STATES = frozenset({
    "ALREADY_APPROVED", "MISSING_IDENTITY", "MISSING_VARIANT",
    "CONFIRMED_REBRAND", "UNVERIFIED_ARTWORK_CHANGE",
    "IDENTITY_AMBIGUOUS", "RETIRED",
})


def _sha(value):
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def _digest(value):
    body = json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def audit_identity_rows(rows):
    """Audit normalized records from the existing canonical ID authority.

    The function deliberately accepts records rather than creating a schema or
    assigning identifiers. Expected normalized keys are warder_id,
    identity_key, service_references, operator_links, satellite_links,
    retired, and history (events with identity_key/warder_id).
    """
    rows = list(rows) if isinstance(rows, (list, tuple)) else []
    current_ids = {}
    identity_assignments = {}
    identity_to_ids = {}
    issues = []
    linked = {"service_references": 0, "operator_links": 0, "satellite_links": 0,
              "artwork_versions": 0, "history_events": 0, "retired": 0}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            issues.append({"code": "INVALID_RECORD", "record_index": index})
            continue
        wid = row.get("warder_id")
        identity = row.get("identity_key")
        if not isinstance(wid, str) or not wid.strip():
            issues.append({"code": "WARDER_ID_MISSING", "record_index": index})
            continue
        wid = wid.strip()
        if wid in current_ids:
            issues.append({"code": "WARDER_ID_NOT_UNIQUE", "warder_id": wid,
                           "record_indexes": [current_ids[wid], index]})
        else:
            current_ids[wid] = index
        if not isinstance(identity, str) or not identity.strip():
            issues.append({"code": "IDENTITY_KEY_MISSING", "warder_id": wid})
        else:
            prior = identity_assignments.get(wid)
            if prior is not None and prior != identity:
                issues.append({"code": "WARDER_ID_REASSIGNED", "warder_id": wid})
            identity_assignments[wid] = identity
            prior_id = identity_to_ids.get(identity)
            if prior_id is not None and prior_id != wid:
                issues.append({"code": "IDENTITY_HAS_MULTIPLE_WARDER_IDS",
                               "identity_key": identity,
                               "warder_ids": sorted((prior_id, wid))})
            identity_to_ids[identity] = wid
        for field in ("service_references", "operator_links", "satellite_links"):
            values = row.get(field, [])
            if not isinstance(values, list):
                issues.append({"code": "INVALID_LINK_COLLECTION", "warder_id": wid,
                               "field": field})
            else:
                linked[field] += len({str(value) for value in values if value})
        if row.get("retired") is True:
            linked["retired"] += 1
        history = row.get("history", [])
        if not isinstance(history, list):
            issues.append({"code": "INVALID_HISTORY", "warder_id": wid})
            continue
        linked["history_events"] += len(history)
        for event in history:
            if not isinstance(event, dict):
                issues.append({"code": "INVALID_HISTORY_EVENT", "warder_id": wid})
                continue
            if event.get("warder_id", wid) != wid:
                issues.append({"code": "HISTORY_ID_MISMATCH", "warder_id": wid})
            event_identity = event.get("identity_key", identity)
            if identity and event_identity and event_identity != identity:
                issues.append({"code": "HISTORICAL_ID_REUSE", "warder_id": wid})
            if event.get("event_type") in ("ARTWORK_APPROVED", "MASTER_ARTWORK_APPROVED"):
                linked["artwork_versions"] += 1
    return {"schema": 1, "audit_mode": "READ_ONLY_COMPATIBILITY_AUDIT",
            "status": "AUDITED" if rows else "WARDER_ID_SCHEMA_NOT_PRESENT",
            "record_count": len(rows), "unique_id_count": len(current_ids),
            "linked_counts": linked, "issues": issues,
            "id_generation": False, "id_reassignment": False,
            "master_mutated": False,
            "note": ("Records were checked against supplied canonical IDs; no IDs were generated."
                     if rows else "Current PiconHub index has service references, not a Warder ID registry.")}


def classify_master_observation(coverage_status, *, candidate_matches_master=False,
                                identity_ambiguous=False, retired=False,
                                rebrand_evidence=None):
    """Map existing MASTER-FIRST states to one non-conflicting work category."""
    if retired:
        state = "RETIRED"
    elif identity_ambiguous or coverage_status == "AMBIGUOUS":
        state = "IDENTITY_AMBIGUOUS"
    elif coverage_status == "NEW":
        state = "MISSING_IDENTITY"
    elif coverage_status == "APPROVED_INCOMPLETE":
        state = "MISSING_VARIANT"
    elif coverage_status == "APPROVED_COMPLETE":
        if candidate_matches_master:
            state = "ALREADY_APPROVED"
        elif (isinstance(rebrand_evidence, dict) and
              rebrand_evidence.get("identity_continuity_verified") is True and
              rebrand_evidence.get("official_rebrand_confirmed") is True and
              isinstance(rebrand_evidence.get("evidence_ref"), str) and
              rebrand_evidence.get("evidence_ref").strip()):
            state = "CONFIRMED_REBRAND"
        else:
            state = "UNVERIFIED_ARTWORK_CHANGE"
    else:
        state = "UNVERIFIED_ARTWORK_CHANGE"
    return {"state": state, "automatic_approval": False,
            "reason": ("EXPLICIT_REBRAND_EVIDENCE_REQUIRED" if state == "UNVERIFIED_ARTWORK_CHANGE"
                       else "MASTER_FIRST_CLASSIFICATION"),
            "evidence_ref": (rebrand_evidence.get("evidence_ref")
                             if state == "CONFIRMED_REBRAND" else None)}


def append_approved_artwork_history(history, event, *, canonical_warder_ids):
    """Return an append-only history copy for a human-approved rebrand.

    This records a change proposal's approval evidence only. It never writes
    the Master files or replaces their current artwork.
    """
    if not isinstance(history, list) or not isinstance(event, dict):
        raise ValueError("A history list and approval event are required")
    wid = event.get("warder_id")
    if not isinstance(wid, str) or wid not in set(canonical_warder_ids or ()):
        raise ValueError("Warder ID must already exist in the canonical authority")
    if event.get("event_type") not in ("ARTWORK_APPROVED", "MASTER_ARTWORK_APPROVED"):
        raise PermissionError("Only an explicit artwork approval event can enter history")
    if event.get("identity_continuity_verified") is not True or event.get("official_rebrand_confirmed") is not True:
        raise PermissionError("Confirmed identity continuity and rebrand evidence are required")
    if event.get("qa_approved") is not True or event.get("human_approved") is not True:
        raise PermissionError("Graphic QA and human approval are required")
    if not isinstance(event.get("evidence_ref"), str) or not event["evidence_ref"].strip():
        raise ValueError("Rebrand source evidence reference is required")
    before, after = event.get("previous_variants"), event.get("new_variants")
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise ValueError("Previous and new variant hashes are required")
    if any(not _sha(before.get(style)) or not _sha(after.get(style)) for style in REQUIRED_STYLES):
        raise ValueError("All three variant SHA-256 values are required")
    if all(before[style].lower() == after[style].lower() for style in REQUIRED_STYLES):
        raise ValueError("Artwork history event has no content change")
    history_copy = copy.deepcopy(history)
    normalized = {"event_type": "MASTER_ARTWORK_APPROVED", "warder_id": wid,
                  "previous_variants": {s: before[s].lower() for s in REQUIRED_STYLES},
                  "new_variants": {s: after[s].lower() for s in REQUIRED_STYLES},
                  "evidence_ref": event["evidence_ref"].strip(),
                  "evidence_sha256": event.get("evidence_sha256"),
                  "approved_at": event.get("approved_at"),
                  "identity_continuity_verified": True,
                  "official_rebrand_confirmed": True, "qa_approved": True,
                  "human_approved": True}
    if not _sha(normalized["evidence_sha256"]):
        raise ValueError("Immutable approval evidence SHA-256 is required")
    if normalized.get("approved_at") is None:
        raise ValueError("Approval timestamp is required")
    normalized["event_id"] = "WA-" + _digest(normalized)[:24]
    if any(isinstance(old, dict) and old.get("event_id") == normalized["event_id"]
           for old in history_copy):
        raise ValueError("Artwork approval event already exists")
    history_copy.append(normalized)
    return history_copy
