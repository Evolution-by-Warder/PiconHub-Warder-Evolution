"""Evidence-bounded review decision groups.

Groups reduce repeated human artwork choices only when every member has the
same exact candidate RGBA set, exact Master RGBA set, reason and source-family
context. Artwork groups never combine or approve service identities.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

from review_decisions import DECISIONS, evidence_hash
from source_registry import atomic_json


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _hash(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _valid_sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value.lower())


def _source_context(item):
    origins = item.get("source_origins") or [item.get("source_origin") or "unknown"]
    origins = sorted({str(value).casefold()[:40] for value in origins if isinstance(value, str)})
    provenance = item.get("verified_provenance") or item.get("provenance") or []
    if isinstance(provenance, dict):
        provenance = [provenance]
    normalized = []
    for row in provenance:
        if isinstance(row, dict):
            normalized.append({
                "format": str(row.get("format") or row.get("package_format") or "unknown").casefold()[:40],
                "style": str(row.get("style") or row.get("package_style") or "unknown").casefold()[:40],
                "verified": bool(row.get("verified") or row.get("package_hash_verified")),
            })
    return {"origins": origins or ["unknown"], "provenance": sorted(
        normalized, key=lambda row: (row["format"], row["style"], row["verified"]))}


def _artwork_key(item):
    units = item.get("artwork_review_units") or []
    if not units or not all(isinstance(unit, dict) for unit in units):
        return None
    candidate_pixels = []
    master_pixels = []
    statuses = []
    for unit in units:
        candidate = unit.get("pixel_sha256")
        master = unit.get("master_pixel_sha256") or []
        if not _valid_sha(candidate) or not master or not all(_valid_sha(value) for value in master):
            return None
        candidate_pixels.append(candidate.lower())
        master_pixels.extend(value.lower() for value in master)
        status = unit.get("master_pixel_comparison")
        if status not in ("NO_PIXEL_EXACT_SAME_SERVICE_MASTER",
                          "PIXEL_EXACT_SAME_SERVICE_MASTER"):
            return None
        statuses.append(status)
    # A group card may only summarize one exact candidate artwork and one
    # exact Master artwork. Multi-artwork cases stay as individual tasks so
    # the GUI cannot hide a visual alternative behind a group approval.
    if len(set(candidate_pixels)) != 1 or len(set(master_pixels)) != 1:
        return None
    # Canonical multisets preserve multiplicity for exact same-artwork tasks.
    identity_context = item.get("verified_identity_context")
    if not isinstance(identity_context, str) or not identity_context:
        identity_context = item.get("candidate_identity")
    if not isinstance(identity_context, str) or not identity_context:
        return None
    return {
        "identity_context": identity_context,
        "reason": sorted(set(str(value) for value in item.get("reasons", []))),
        "candidate_pixel_multiset": sorted(candidate_pixels),
        "master_pixel_multiset": sorted(master_pixels),
        "master_comparison_statuses": sorted(statuses),
        "source_context": _source_context(item),
    }


def _identity_key(item):
    ref = item.get("candidate_identity")
    if not isinstance(ref, str) or not ref:
        return None
    variants = item.get("variants") or []
    hashes = []
    for variant in variants:
        if not isinstance(variant, dict) or not _valid_sha(variant.get("sha256")):
            return None
        hashes.append(variant["sha256"].lower())
    if not hashes:
        hashes = [value.lower() for value in item.get("observed_candidate_sha256", [])
                  if _valid_sha(value)]
    if not hashes or len(set(hashes)) != 1:
        return None
    return {
        "service_reference": ref,
        "conflict_type": str(item.get("category") or "IDENTITY_COLLISION"),
        "reason": sorted(set(str(value) for value in item.get("reasons", []))),
        "candidate_sha_multiset": sorted(hashes),
        "source_context": _source_context(item),
    }


def _build_group(scope, key, members):
    ordered = sorted(members, key=lambda item: str(item.get("review_id", "")))
    member_ids = [item["review_id"] for item in ordered]
    member_hashes = {item["review_id"]: evidence_hash(item) for item in ordered}
    evidence_payload = {
        "scope": scope,
        "group_key": key,
        "member_review_ids": member_ids,
        "member_evidence_hashes": member_hashes,
    }
    group_evidence_hash = _hash(evidence_payload)
    decision_group_id = "WDG-" + _hash({
        "scope": scope, "group_evidence_hash": group_evidence_hash
    })[:20].upper()
    refs = sorted({item.get("candidate_identity") for item in ordered
                   if isinstance(item.get("candidate_identity"), str)})
    pixel_sets = sorted({pixel for item in ordered
                         for unit in item.get("artwork_review_units", [])
                         if isinstance(unit, dict)
                         for pixel in [unit.get("pixel_sha256")] if _valid_sha(pixel)})
    master_sets = sorted({pixel for item in ordered
                          for unit in item.get("artwork_review_units", [])
                          if isinstance(unit, dict)
                          for pixel in (unit.get("master_pixel_sha256") or [])
                          if _valid_sha(pixel)})
    candidate_shas = sorted({sha.lower() for item in ordered
                             for unit in item.get("artwork_review_units", [])
                             if isinstance(unit, dict)
                             for sha in ([unit.get("representative_sha256")] +
                                         list(unit.get("duplicate_sha256") or []))
                             if _valid_sha(sha)})
    if scope == "ARTWORK_ONLY":
        reason = ("Identické dekódované kandidátne pixely, identické Master pixely, "
                  "rovnaký typ konfliktu a zdrojový kontext. Rozhodnutie sa týka iba artworku; "
                  "identity služieb zostávajú samostatné.")
    elif scope == "IDENTITY_SAME_SERVICE":
        reason = "Presná duplicita identitného konfliktu pre tú istú service reference a rovnaké dôkazy."
    else:
        reason = "Bezpečné podmienky na zlúčenie s inou úlohou neboli preukázané."
    return {
        "decision_group_id": decision_group_id,
        "group_evidence_hash": group_evidence_hash,
        "group_key": key,
        "scope": scope,
        "member_review_ids": member_ids,
        "member_evidence_hashes": member_hashes,
        "review_tasks": len(ordered),
        "affected_service_references": refs,
        "service_count": len(refs),
        "candidate_sha256s": candidate_shas,
        "common_candidate_pixel_sha256": pixel_sets if scope == "ARTWORK_ONLY" else [],
        "common_master_pixel_sha256": master_sets if scope == "ARTWORK_ONLY" else [],
        "unique_artworks": len(set(pixel_sets)),
        "grouping_reason": reason,
        "decision": "PENDING",
    }


def build_decision_groups(queue):
    """Return stable groups and counts; never changes queue decisions."""
    buckets = {}
    pending = [item for item in queue.get("items", [])
               if isinstance(item, dict) and item.get("decision", "PENDING") == "PENDING"]
    for item in pending:
        lane = item.get("workstream")
        key_data = _artwork_key(item) if lane == "ARTWORK_REVIEW" else None
        if key_data is not None:
            scope = "ARTWORK_ONLY"
            bucket_key = (scope, _canonical(key_data))
        elif lane == "IDENTITY_VERIFICATION":
            key_data = _identity_key(item)
            if key_data is not None:
                scope = "IDENTITY_SAME_SERVICE"
                bucket_key = (scope, _canonical(key_data))
            else:
                scope = "SINGLE_TASK"
                bucket_key = (scope, item.get("review_id"))
        else:
            scope = "SINGLE_TASK"
            bucket_key = (scope, item.get("review_id"))
        buckets.setdefault(bucket_key, (scope, key_data, []))[2].append(item)

    groups = [_build_group(scope, key, members)
              for scope, key, members in buckets.values()]
    groups.sort(key=lambda group: (group["scope"], group["decision_group_id"]))
    task_count = sum(group["review_tasks"] for group in groups)
    return {
        "schema": 1,
        "policy": "EXACT_EVIDENCE_GROUPING_ONLY; ARTWORK_NEVER_APPROVES_IDENTITY",
        "groups": groups,
        "summary": {
            "active_technical_items": len(pending),
            "user_decision_groups": len(groups),
            "potential_decisions_saved": max(0, len(pending) - len(groups)),
            "grouped_tasks": sum(group["review_tasks"] for group in groups
                                 if group["review_tasks"] > 1),
            "single_task_groups": sum(group["review_tasks"] == 1 for group in groups),
            "multi_task_groups": sum(group["review_tasks"] > 1 for group in groups),
        },
    }


def _validate_group(group):
    if not isinstance(group, dict):
        raise ValueError("Invalid decision group")
    ids = group.get("member_review_ids")
    hashes = group.get("member_evidence_hashes")
    scope = group.get("scope")
    if scope not in ("ARTWORK_ONLY", "IDENTITY_SAME_SERVICE", "SINGLE_TASK"):
        raise ValueError("Invalid group scope")
    if not isinstance(ids, list) or not ids or ids != sorted(set(ids)):
        raise ValueError("Invalid group members")
    if not isinstance(hashes, dict) or set(hashes) != set(ids):
        raise ValueError("Invalid group evidence hashes")
    expected_evidence = _hash({
        "scope": scope,
        "group_key": group.get("group_key"),
        "member_review_ids": ids,
        "member_evidence_hashes": hashes,
    })
    # Persisted groups do not expose internal keys; their declared hash is
    # checked against the explicit group evidence payload supplied at creation.
    if group.get("group_evidence_hash") != expected_evidence:
        raise ValueError("Decision group evidence changed")
    expected_id = "WDG-" + _hash({
        "scope": scope, "group_evidence_hash": expected_evidence
    })[:20].upper()
    if group.get("decision_group_id") != expected_id:
        raise ValueError("Decision group identity mismatch")


def record_group_decision(ledger_path, group, decision, note, operator_confirmation):
    """Record one explicit, fixed-membership decision in the local audit ledger."""
    if not operator_confirmation:
        raise PermissionError("Explicit operator confirmation required")
    if decision not in DECISIONS:
        raise ValueError("Unknown decision")
    if not isinstance(note, str) or len(note) > 2000:
        raise ValueError("Invalid note")
    _validate_group(group)
    entry = {
        "decision_group_id": group["decision_group_id"],
        "group_evidence_hash": group["group_evidence_hash"],
        "scope": group["scope"],
        "member_review_ids": list(group["member_review_ids"]),
        "member_evidence_hashes": dict(group["member_evidence_hashes"]),
        "decision": decision,
        "note": note,
        "status": "ACTIVE",
        "decided_at": datetime.now(timezone.utc).isoformat(),
    }
    path = Path(ledger_path)
    ledger = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {
        "schema": 1, "decisions": {}, "group_decisions": {}}
    if ledger.get("schema") != 1 or not isinstance(ledger.get("decisions", {}), dict):
        raise ValueError("Invalid decision ledger")
    groups = ledger.setdefault("group_decisions", {})
    if not isinstance(groups, dict):
        raise ValueError("Invalid group decision ledger")
    previous = groups.get(entry["decision_group_id"])
    if previous:
        history = list(previous.get("history") or [])
        history.append({key: value for key, value in previous.items() if key != "history"})
        entry["history"] = history
    groups[entry["decision_group_id"]] = entry
    atomic_json(path, ledger)
    return entry


def apply_group_decisions(queue, ledger_path):
    """Apply only an exact, still-current group decision to its fixed members."""
    path = Path(ledger_path)
    try:
        ledger = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, ValueError):
        return queue
    decisions = ledger.get("group_decisions", {})
    if not isinstance(decisions, dict):
        return queue
    result = {**queue, "items": [dict(item) for item in queue.get("items", [])]}
    by_id = {item.get("review_id"): item for item in result["items"]}
    for group in build_decision_groups(result)["groups"]:
        prior = decisions.get(group["decision_group_id"])
        if not isinstance(prior, dict) or prior.get("status") != "ACTIVE":
            continue
        if (prior.get("group_evidence_hash") != group["group_evidence_hash"] or
                prior.get("member_review_ids") != group["member_review_ids"] or
                prior.get("member_evidence_hashes") != group["member_evidence_hashes"] or
                prior.get("decision") not in DECISIONS):
            continue
        for review_id in group["member_review_ids"]:
            item = by_id.get(review_id)
            if item is not None and item.get("decision", "PENDING") == "PENDING":
                item["decision"] = prior["decision"]
                item["decision_note"] = prior.get("note", "")
                item["decision_group_id"] = group["decision_group_id"]
    return result


def revoke_group_decision(ledger_path, decision_group_id, *, operator_confirmation=False):
    """Revoke a prior group decision while retaining its complete audit record."""
    if not operator_confirmation:
        raise PermissionError("Explicit operator confirmation required")
    path = Path(ledger_path)
    ledger = json.loads(path.read_text(encoding="utf-8"))
    groups = ledger.get("group_decisions")
    if not isinstance(groups, dict) or decision_group_id not in groups:
        raise KeyError("Decision group not found")
    previous = groups[decision_group_id]
    history = list(previous.get("history") or [])
    history.append({key: value for key, value in previous.items() if key != "history"})
    groups[decision_group_id] = {
        "decision_group_id": decision_group_id,
        "status": "REVOKED",
        "decision": "REVOKED",
        "revoked_at": datetime.now(timezone.utc).isoformat(),
        "history": history,
    }
    atomic_json(path, ledger)
    return groups[decision_group_id]
