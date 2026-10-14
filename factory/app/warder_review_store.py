"""Git-native persistence for human review decisions.

Review decisions are append-only events in the canonical Master approval ledger.
They record review outcomes, but never assert a Warder ID or Master approval.
Only explicit identity/artwork transactions may create those authority records.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from review_decisions import evidence_hash
from warder_identity_registry import register_confirmed_identity, sha256_json
from warder_identity_sync import fetch_master_snapshot
from warder_master_store import (build_artwork_approval, build_identity_approval,
                                 commit_master_transaction, validate_store_transition)

PROGRESS_PATH = "factory/registry/project-progress.json"
TERMINAL_DECISIONS = frozenset({
    "APPROVED_FOR_REVIEW", "REJECTED", "FINALIZED_LOCALLY",
})
ALLOWED_DECISIONS = TERMINAL_DECISIONS | {"DEFERRED", "IDENTITY_AMBIGUOUS", "IDENTITY_CONFLICT"}
WORKSTREAMS = frozenset({"IDENTITY_VERIFICATION", "ARTWORK_REVIEW", "TECHNICAL_QA"})


def _iso_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _valid_review_id(value):
    return isinstance(value, str) and bool(re.fullmatch(r"WR-[0-9a-fA-F]{16}", value))


def _candidate_digest(item):
    candidates = []
    for value in [item.get("sha256"), item.get("candidate_sha256")]:
        if isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdefABCDEF" for c in value):
            candidates.append(value.lower())
    for field in ("source_evidence", "variants", "observed_candidate_sha256"):
        entries = item.get(field)
        if isinstance(entries, (list, tuple)):
            for entry in entries:
                value = entry.get("sha256") if isinstance(entry, dict) else entry
                if isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdefABCDEF" for c in value):
                    candidates.append(value.lower())
    unique = sorted(set(candidates))
    return hashlib.sha256("\n".join(unique).encode("ascii")).hexdigest()


def build_review_batch(scopes, decision, *, timestamp=None):
    """Create a fixed-scope batch from exact visible groups; no filesystem paths persist."""
    if decision not in ALLOWED_DECISIONS:
        raise ValueError("INVALID_REVIEW_DECISION")
    if not isinstance(scopes, (list, tuple)) or not scopes:
        raise ValueError("EMPTY_REVIEW_BATCH")
    timestamp = timestamp or _iso_now()
    prepared = []
    for scope in scopes:
        if not isinstance(scope, dict):
            raise ValueError("INVALID_REVIEW_SCOPE")
        items = scope.get("items")
        if not isinstance(items, (list, tuple)) or not items:
            raise ValueError("EMPTY_REVIEW_SCOPE")
        review_ids = sorted(item.get("review_id", "") for item in items)
        if any(not _valid_review_id(value) for value in review_ids) or len(set(review_ids)) != len(review_ids):
            raise ValueError("INVALID_OR_DUPLICATE_REVIEW_ID")
        group_id = scope.get("decision_group_id")
        if not isinstance(group_id, str) or not group_id.strip():
            raise ValueError("DECISION_GROUP_ID_REQUIRED")
        workstreams = {item.get("workstream") for item in items}
        if len(workstreams) != 1 or next(iter(workstreams)) not in WORKSTREAMS:
            raise ValueError("REVIEW_WORKSTREAM_MISMATCH")
        workstream = next(iter(workstreams))
        if decision in {"IDENTITY_AMBIGUOUS", "IDENTITY_CONFLICT"} and workstream != "IDENTITY_VERIFICATION":
            raise ValueError("IDENTITY_DECISION_ON_NON_IDENTITY_WORKSTREAM")
        item_hashes = {}
        item_digests = {}
        for item in items:
            review_id = item["review_id"]
            item_hashes[review_id] = evidence_hash(item)
            item_digests[review_id] = _candidate_digest(item)
        calculated_group_hash = hashlib.sha256(json.dumps(
            {"decision_group_id": group_id, "members": [
                {"review_id": review_id, "evidence_sha256": item_hashes[review_id]}
                for review_id in review_ids]},
            sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
        supplied_group_hash = scope.get("group_evidence_sha256")
        if supplied_group_hash and supplied_group_hash != calculated_group_hash:
            # The GUI group hash includes a different evidence projection; retain it
            # only as a second proof, while the canonical member hash is authoritative.
            if not (isinstance(supplied_group_hash, str) and len(supplied_group_hash) == 64):
                raise ValueError("GROUP_EVIDENCE_HASH_INVALID")
        prepared.append({"group_id": group_id, "group_hash": calculated_group_hash,
                         "source_group_hash": supplied_group_hash,
                         "items": list(items), "review_ids": review_ids,
                         "item_hashes": item_hashes, "item_digests": item_digests,
                         "workstream": workstream})
    batch_seed = [{"group_id": scope["group_id"], "group_hash": scope["group_hash"],
                   "review_ids": scope["review_ids"], "decision": decision}
                  for scope in prepared]
    batch_id = "RB-" + sha256_json(batch_seed)[:24]
    events = []
    for scope in prepared:
        for review_id in scope["review_ids"]:
            item_hash = scope["item_hashes"][review_id]
            body = {
                "event_type": "MASTER_REVIEW_DECISION",
                "decision": decision,
                "approval_id": "REVIEW-" + sha256_json(
                    {"review_id": review_id, "decision": decision, "evidence": item_hash})[:24],
                "approved_at": timestamp,
                "evidence_ref": "review-evidence:" + review_id,
                "evidence_sha256": scope["item_digests"][review_id],
                "review_evidence_sha256": item_hash,
                "human_approved": True,
                "review_id": review_id,
                "decision_group_id": scope["group_id"],
                "group_evidence_sha256": scope["group_hash"],
                "source_group_evidence_sha256": scope["source_group_hash"],
                "group_review_ids": scope["review_ids"],
                "workstream": scope["workstream"],
                "batch_id": batch_id,
                "decision_source": "Factory review GUI",
            }
            body["event_id"] = "RD-" + sha256_json(body)[:24]
            events.append(body)
    return {"schema": 1, "batch_id": batch_id, "created_at": timestamp,
            "decision": decision, "events": events, "state": "PENDING"}


def validate_review_batch(batch):
    if not isinstance(batch, dict) or batch.get("schema") != 1 or not isinstance(batch.get("events"), list):
        raise ValueError("INVALID_REVIEW_BATCH")
    if not batch.get("events") or len(batch["events"]) > 100:
        raise ValueError("REVIEW_BATCH_SIZE_INVALID")
    operation = batch.get("operation")
    if operation is not None:
        if not isinstance(operation, dict) or operation.get("type") not in {"IDENTITY_APPROVAL", "ARTWORK_APPROVAL"}:
            raise ValueError("INVALID_PENDING_MASTER_OPERATION")
        if operation["type"] == "IDENTITY_APPROVAL":
            identity = operation.get("identity")
            if (not isinstance(identity, dict) or not isinstance(identity.get("identity_key"), str)
                    or not identity["identity_key"].strip()
                    or any(event.get("workstream") != "IDENTITY_VERIFICATION" for event in batch["events"])):
                raise ValueError("PENDING_IDENTITY_FIELDS_INVALID")
        if operation["type"] == "ARTWORK_APPROVAL":
            variants = operation.get("variant_sha256")
            if not isinstance(variants, dict) or set(variants) != {"transparent", "black", "white"} or any(
                    not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value.lower())
                    for value in variants.values()):
                raise ValueError("PENDING_ARTWORK_DIGESTS_INVALID")
            if (not isinstance(operation.get("warder_id"), str) or not operation["warder_id"].startswith("WARDER-")
                    or len(batch["events"]) != 1 or batch["events"][0].get("workstream") != "ARTWORK_REVIEW"):
                raise ValueError("PENDING_ARTWORK_WARDER_ID_INVALID")
    seen = set()
    for event in batch["events"]:
        if not isinstance(event, dict) or event.get("event_type") != "MASTER_REVIEW_DECISION":
            raise ValueError("INVALID_REVIEW_EVENT")
        if event.get("decision") not in ALLOWED_DECISIONS or not _valid_review_id(event.get("review_id")):
            raise ValueError("INVALID_REVIEW_EVENT_DECISION")
        if event.get("event_id") != "RD-" + sha256_json(
                {key: value for key, value in event.items() if key != "event_id"})[:24]:
            raise ValueError("REVIEW_EVENT_HASH_MISMATCH")
        if event["event_id"] in seen:
            raise ValueError("DUPLICATE_REVIEW_EVENT")
        seen.add(event["event_id"])
        if event.get("batch_id") != batch.get("batch_id") or event.get("human_approved") is not True:
            raise ValueError("REVIEW_BATCH_SCOPE_OR_CONFIRMATION_INVALID")
    expected = "RB-" + sha256_json([{
        "group_id": group_id, "group_hash": group_hash, "review_ids": ids, "decision": batch["decision"]
    } for group_id, group_hash, ids in sorted({
        (event["decision_group_id"], event["group_evidence_sha256"], tuple(event["group_review_ids"]))
        for event in batch["events"]
    })])[:24]
    # Batch IDs are produced using original scope order. The event-level digest and
    # exact member lists are the immutable authority; ensure a stable-shaped ID.
    if not isinstance(batch.get("batch_id"), str) or not batch["batch_id"].startswith("RB-") or len(batch["batch_id"]) != 27:
        raise ValueError("REVIEW_BATCH_ID_INVALID")
    return True


def _ledger_events(ledger):
    return ledger.get("events", []) if isinstance(ledger, dict) and isinstance(ledger.get("events"), list) else []


def _progress(registry, ledger, *, parent_head, batch_id, timestamp):
    events = _ledger_events(ledger)
    review_events = [event for event in events if event.get("event_type") == "MASTER_REVIEW_DECISION"]
    latest = {}
    for event in review_events:
        latest[event["review_id"]] = event
    terminal = [event for event in latest.values() if event.get("decision") in TERMINAL_DECISIONS]
    decisions = [event.get("decision") for event in terminal]
    master_all = [event for event in events if event.get("event_type") == "MASTER_APPROVAL"]
    revoked = {event.get("revokes_event_id") for event in master_all
               if event.get("decision") == "APPROVAL_REVOKED"}
    master = [event for event in master_all
              if event.get("decision") != "APPROVAL_REVOKED" and event.get("event_id") not in revoked]
    return {
        "schema": 1, "authority": "DERIVED_FROM_GIT_MASTER_LEDGER",
        "processed": len(terminal),
        "approved_identities": len({event.get("warder_id") for event in master
                                     if event.get("decision") in ("IDENTITY_APPROVED", "IDENTITY_AND_ARTWORK_APPROVED")}),
        "approved_artwork": len({event.get("warder_id") for event in master
                                  if event.get("decision") in ("ARTWORK_APPROVED", "IDENTITY_AND_ARTWORK_APPROVED")}),
        "rejected": decisions.count("REJECTED"),
        "ambiguous": sum(event.get("decision") == "IDENTITY_AMBIGUOUS" for event in latest.values()),
        "conflicts": sum(event.get("decision") == "IDENTITY_CONFLICT" for event in latest.values()),
        "remaining": None,
        "remaining_status": "NOT_DURABLE_QUEUE_NOT_YET_EXPORTED",
        "last_commit": parent_head,
        "last_batch": batch_id,
        "timestamp": timestamp,
        "registry_identity_count": len(registry.get("records", {})),
        "review_accepted_count": sum(
            1 for event in latest.values()
            if event.get("decision") == "APPROVED_FOR_REVIEW"
        ),
        "note": "last_commit is the verified transaction parent; current containing commit is the Git branch HEAD."
    }


def _review_scopes_batch(scopes, timestamp=None):
    return build_review_batch(scopes, "APPROVED_FOR_REVIEW", timestamp=timestamp)


def commit_identity_approval(token, scopes=None, identity=None, *, batch=None, expected_head=None,
                             opener=None, transaction=None):
    """Create one human-confirmed Warder ID and its review event atomically."""
    batch = batch or _review_scopes_batch(scopes)
    validate_review_batch(batch)
    snapshot = fetch_master_snapshot(opener=opener, token=token) if opener else fetch_master_snapshot(token=token)
    head, registry = snapshot["commit"], copy.deepcopy(snapshot["registry"])
    ledger = copy.deepcopy(snapshot["approval_ledger"])
    if expected_head and expected_head != head:
        return {"status": "CONFLICT", "error": "STALE_EXPECTED_HEAD", "commit": head}
    review_hash = batch["events"][0]["review_evidence_sha256"]
    if (not isinstance(identity, dict) or not isinstance(identity.get("identity_key"), str)
            or not identity["identity_key"].strip() or not isinstance(identity.get("current_name"), str)
            or not identity["current_name"].strip() or not isinstance(identity.get("service_references"), list)
            or not identity["service_references"]):
        return {"status": "FAILED", "error": "IDENTITY_KEY_NAME_AND_SERVICE_REFERENCE_REQUIRED"}
    approval_id = "identity-" + sha256_json({
        "review_ids": [event["review_id"] for event in batch["events"]],
        "group_evidence_sha256": batch["events"][0]["group_evidence_sha256"],
        "review_evidence_sha256": review_hash})[:32]
    previous = next((event for event in ledger["events"]
                     if event.get("event_type") == "MASTER_APPROVAL"
                     and event.get("approval_id") == approval_id), None)
    if previous:
        return {"status": "ALREADY_COMMITTED", "commit": head,
                "warder_id": previous.get("warder_id"),
                "events": batch["events"]}
    evidence = {"evidence_ref": "review:" + batch["events"][0]["review_id"],
                "evidence_sha256": batch["events"][0]["evidence_sha256"],
                "occurred_at": batch["created_at"]}
    try:
        registry, warder_id = register_confirmed_identity(
            registry, identity, evidence=evidence, identity_confirmed=True)
        registry, ledger, _ = build_identity_approval(
            registry, ledger, warder_id=warder_id, approval_id=approval_id,
            approved_at=batch["created_at"], evidence_ref=evidence["evidence_ref"],
            evidence_sha256=evidence["evidence_sha256"],
            review_evidence_sha256=review_hash, human_approved=True)
    except (ValueError, PermissionError) as exc:
        return {"status": "FAILED", "error": type(exc).__name__ + ": " + str(exc)}
    ledger["events"].extend(batch["events"])
    transition = validate_store_transition(registry, snapshot["approval_ledger"], registry, ledger)
    if transition["status"] != "VALID":
        return {"status": "FAILED", "error": "MASTER_IDENTITY_TRANSACTION_INVALID",
                "issues": transition["issues"][:20]}
    checkpoint = _progress(registry, ledger, parent_head=head, batch_id=batch["batch_id"],
                           timestamp=batch["created_at"])
    commit_fn = transaction or commit_master_transaction
    kwargs = {"token": token, "expected_head": head, "registry": registry,
              "approval_ledger": ledger, "additional_json": {PROGRESS_PATH: checkpoint},
              "message": "factory: approve Warder identity batch " + batch["batch_id"]}
    if opener:
        kwargs["opener"] = opener
    result = commit_fn(**kwargs)
    if result.get("status") == "COMMITTED_VERIFIED":
        result.update({"warder_id": warder_id, "batch_id": batch["batch_id"],
                       "events": batch["events"]})
    return result


def commit_artwork_approval(token, scope=None, warder_id=None, variant_blobs=None, *,
                            batch=None, expected_head=None, official_rebrand_confirmed=False,
                            opener=None, transaction=None):
    """Approve one exact triplet for an existing Warder ID, preserving history."""
    batch = batch or _review_scopes_batch([scope])
    validate_review_batch(batch)
    if len(batch["events"]) != 1:
        return {"status": "FAILED", "error": "ARTWORK_MASTER_APPROVAL_REQUIRES_ONE_REVIEW_TASK"}
    blobs = dict(variant_blobs or {})
    if set(blobs) != {"transparent", "black", "white"} or any(not isinstance(v, bytes) for v in blobs.values()):
        return {"status": "FAILED", "error": "COMPLETE_ARTWORK_TRIPLET_REQUIRED"}
    snapshot = fetch_master_snapshot(opener=opener, token=token) if opener else fetch_master_snapshot(token=token)
    head, registry = snapshot["commit"], copy.deepcopy(snapshot["registry"])
    ledger = copy.deepcopy(snapshot["approval_ledger"])
    if expected_head and expected_head != head:
        return {"status": "CONFLICT", "error": "STALE_EXPECTED_HEAD", "commit": head}
    record = registry.get("records", {}).get(warder_id)
    if not isinstance(record, dict):
        return {"status": "FAILED", "error": "WARDER_ID_NOT_IN_GIT_REGISTRY"}
    review_event = batch["events"][0]
    review_hash = review_event["review_evidence_sha256"]
    approval_id = "artwork-" + sha256_json({
        "warder_id": warder_id, "review_id": review_event["review_id"],
        "review_evidence_sha256": review_hash})[:32]
    previous = next((event for event in ledger["events"]
                     if event.get("event_type") == "MASTER_APPROVAL"
                     and event.get("approval_id") == approval_id), None)
    if previous:
        return {"status": "ALREADY_COMMITTED", "commit": head,
                "warder_id": warder_id, "events": [review_event]}
    from warder_identity_registry import STYLES
    import hashlib as _hashlib
    hashes = {style: _hashlib.sha256(blobs[style]).hexdigest() for style in STYLES}
    version = len(record.get("artwork_history", [])) + (2 if record.get("artwork_current") else 1)
    paths = {style: f"factory/approved-picons/{warder_id}/v{version:04d}/{style}.png"
             for style in STYLES}
    try:
        for style in STYLES:
            from warder_master_store import validate_artwork_blob
            validate_artwork_blob(blobs[style], hashes[style], style)
        qa_hash = sha256_json({style: hashes[style] for style in STYLES})
        registry, ledger, _ = build_artwork_approval(
            registry, ledger, warder_id=warder_id, approval_id=approval_id,
            approved_at=batch["created_at"], evidence_ref="review:" + review_event["review_id"],
            evidence_sha256=review_event["evidence_sha256"],
            review_evidence_sha256=review_hash, variants=hashes, asset_paths=paths,
            qa_evidence_ref="factory-qa:" + review_event["review_id"],
            qa_evidence_sha256=qa_hash, human_approved=True,
            official_rebrand_confirmed=official_rebrand_confirmed, qa_approved=True)
    except (ValueError, PermissionError, RuntimeError) as exc:
        return {"status": "FAILED", "error": type(exc).__name__ + ": " + str(exc)}
    ledger["events"].append(review_event)
    transition = validate_store_transition(registry, snapshot["approval_ledger"], registry, ledger)
    if transition["status"] != "VALID":
        return {"status": "FAILED", "error": "MASTER_ARTWORK_TRANSACTION_INVALID",
                "issues": transition["issues"][:20]}
    checkpoint = _progress(registry, ledger, parent_head=head, batch_id=batch["batch_id"],
                           timestamp=batch["created_at"])
    commit_fn = transaction or commit_master_transaction
    kwargs = {"token": token, "expected_head": head, "registry": registry,
              "approval_ledger": ledger,
              "artwork_blobs": {paths[style]: blobs[style] for style in STYLES},
              "additional_json": {PROGRESS_PATH: checkpoint},
              "message": "factory: approve Warder artwork batch " + batch["batch_id"]}
    if opener:
        kwargs["opener"] = opener
    result = commit_fn(**kwargs)
    if result.get("status") == "COMMITTED_VERIFIED":
        result.update({"warder_id": warder_id, "batch_id": batch["batch_id"],
                       "events": [review_event], "asset_paths": paths})
    return result


def validate_progress(registry, ledger, progress):
    """Check the committed checkpoint against ledger-derived counts."""
    if not isinstance(progress, dict) or progress.get("schema") != 1 or progress.get("authority") != "DERIVED_FROM_GIT_MASTER_LEDGER":
        return {"status": "INVALID", "issues": [{"code": "PROGRESS_SCHEMA_INVALID"}]}
    events = _ledger_events(ledger)
    latest = {}
    for event in events:
        if event.get("event_type") == "MASTER_REVIEW_DECISION":
            latest[event["review_id"]] = event
    terminal = [event for event in latest.values() if event.get("decision") in TERMINAL_DECISIONS]
    decisions = [event.get("decision") for event in terminal]
    master_all = [event for event in events if event.get("event_type") == "MASTER_APPROVAL"]
    revoked = {event.get("revokes_event_id") for event in master_all
               if event.get("decision") == "APPROVAL_REVOKED"}
    master = [event for event in master_all
              if event.get("decision") != "APPROVAL_REVOKED" and event.get("event_id") not in revoked]
    expected = {
        "processed": len(terminal),
        "approved_identities": len({event.get("warder_id") for event in master
                                     if event.get("decision") in ("IDENTITY_APPROVED", "IDENTITY_AND_ARTWORK_APPROVED")}),
        "approved_artwork": len({event.get("warder_id") for event in master
                                  if event.get("decision") in ("ARTWORK_APPROVED", "IDENTITY_AND_ARTWORK_APPROVED")}),
        "rejected": decisions.count("REJECTED"),
        "ambiguous": sum(event.get("decision") == "IDENTITY_AMBIGUOUS" for event in latest.values()),
        "conflicts": sum(event.get("decision") == "IDENTITY_CONFLICT" for event in latest.values()),
        "review_accepted_count": sum(event.get("decision") == "APPROVED_FOR_REVIEW" for event in latest.values()),
        "registry_identity_count": len(registry.get("records", {})),
    }
    issues = [{"code": "PROGRESS_COUNT_MISMATCH", "field": key,
               "expected": value, "actual": progress.get(key)}
              for key, value in expected.items() if progress.get(key) != value]
    if progress.get("remaining") is not None or progress.get("remaining_status") != "NOT_DURABLE_QUEUE_NOT_YET_EXPORTED":
        issues.append({"code": "PROGRESS_REMAINING_MUST_BE_EXPLICITLY_UNKNOWN"})
    if not isinstance(progress.get("last_commit"), str) or len(progress["last_commit"]) != 40:
        issues.append({"code": "PROGRESS_PARENT_COMMIT_INVALID"})
    if not isinstance(progress.get("last_batch"), str) or not progress["last_batch"]:
        issues.append({"code": "PROGRESS_BATCH_MISSING"})
    return {"status": "VALID" if not issues else "INVALID", "issues": issues,
            "processed": expected["processed"]}


def fetch_review_ledger(opener=None, token=""):
    snapshot = fetch_master_snapshot(opener=opener, token=token) if opener else fetch_master_snapshot(token=token)
    return {"commit": snapshot["commit"], "registry": snapshot["registry"],
            "approval_ledger": snapshot["approval_ledger"],
            "events": [event for event in _ledger_events(snapshot["approval_ledger"])
                       if event.get("event_type") == "MASTER_REVIEW_DECISION"]}


def commit_review_batch(token, batch, *, expected_head=None, opener=None,
                        transaction=None):
    """Append one GUI batch to the Git Master ledger with optimistic concurrency."""
    validate_review_batch(batch)
    snapshot = fetch_master_snapshot(opener=opener, token=token) if opener else fetch_master_snapshot(token=token)
    head = snapshot["commit"]
    if expected_head and expected_head != head:
        return {"status": "CONFLICT", "error": "STALE_EXPECTED_HEAD",
                "commit": head, "batch_id": batch["batch_id"]}
    registry = snapshot["registry"]
    ledger = copy.deepcopy(snapshot["approval_ledger"])
    events = _ledger_events(ledger)
    by_approval = {event.get("approval_id"): event for event in events
                   if event.get("event_type") == "MASTER_REVIEW_DECISION"}
    already = []
    to_append = []
    for event in batch["events"]:
        previous = by_approval.get(event["approval_id"])
        if previous:
            if previous.get("review_evidence_sha256") != event["review_evidence_sha256"] or previous.get("decision") != event["decision"]:
                return {"status": "CONFLICT", "error": "REVIEW_DECISION_IDEMPOTENCY_CONFLICT",
                        "commit": head, "batch_id": batch["batch_id"]}
            already.append(event["review_id"])
        else:
            to_append.append(event)
    if not to_append:
        return {"status": "ALREADY_COMMITTED", "commit": head,
                "batch_id": batch["batch_id"], "review_ids": already,
                "events": batch["events"]}
    ledger["events"].extend(to_append)
    transition = validate_store_transition(registry, snapshot["approval_ledger"], registry, ledger)
    if transition["status"] != "VALID":
        return {"status": "FAILED", "error": "MASTER_LEDGER_VALIDATION_FAILED",
                "issues": transition["issues"][:20], "batch_id": batch["batch_id"]}
    checkpoint = _progress(registry, ledger, parent_head=head, batch_id=batch["batch_id"],
                           timestamp=batch["created_at"])
    commit_fn = transaction or commit_master_transaction
    result = commit_fn(token=token, expected_head=head, registry=registry,
                       approval_ledger=ledger, additional_json={PROGRESS_PATH: checkpoint},
                       message="factory: persist review batch " + batch["batch_id"],
                       opener=opener) if opener else commit_fn(
                           token=token, expected_head=head, registry=registry,
                           approval_ledger=ledger, additional_json={PROGRESS_PATH: checkpoint},
                           message="factory: persist review batch " + batch["batch_id"])
    if result.get("status") == "COMMITTED_VERIFIED":
        result.update({"batch_id": batch["batch_id"], "events": to_append,
                       "review_ids": [event["review_id"] for event in to_append]})
    return result


def _atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".git-review-pending-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def stage_pending_batch(path, batch):
    validate_review_batch(batch)
    path = Path(path)
    data = {"schema": 1, "batches": []}
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema") != 1 or not isinstance(data.get("batches"), list):
            raise ValueError("PENDING_REVIEW_FILE_INVALID")
    existing = {row.get("batch_id"): row for row in data["batches"] if isinstance(row, dict)}
    if batch["batch_id"] in existing:
        if existing[batch["batch_id"]] != batch:
            raise ValueError("PENDING_BATCH_ID_COLLISION")
    else:
        data["batches"].append(batch)
        _atomic_json(path, data)
    return batch["batch_id"]


def load_pending_batches(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("schema") != 1 or not isinstance(data.get("batches"), list):
            return []
        batches = []
        for batch in data["batches"]:
            try:
                validate_review_batch(batch)
                batches.append(batch)
            except (ValueError, TypeError, KeyError):
                continue
        return batches
    except (OSError, ValueError, TypeError):
        return []


def clear_pending_batch(path, batch_id):
    path = Path(path)
    if not path.is_file():
        return False
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != 1 or not isinstance(data.get("batches"), list):
        raise ValueError("PENDING_REVIEW_FILE_INVALID")
    kept = [row for row in data["batches"] if row.get("batch_id") != batch_id]
    if len(kept) == len(data["batches"]):
        return False
    if kept:
        data["batches"] = kept
        _atomic_json(path, data)
    else:
        path.unlink()
    return True


def apply_git_review_decisions(items, events):
    """Hide only exact evidence and fixed group scopes already committed to Git."""
    from review_decision_groups import build_decision_groups
    items = [dict(item) for item in items]
    active_groups = build_decision_groups({"items": items}).get("groups", [])
    active_by_id = {group.get("decision_group_id"): group for group in active_groups}
    by_item = {item.get("review_id"): item for item in items}
    completed = set()
    for event in events if isinstance(events, list) else []:
        if event.get("event_type") != "MASTER_REVIEW_DECISION" or event.get("decision") not in TERMINAL_DECISIONS:
            continue
        members = event.get("group_review_ids")
        group = active_by_id.get(event.get("decision_group_id"))
        if not isinstance(members, list) or not group:
            continue
        if sorted(members) != sorted(group.get("member_review_ids", [])):
            continue
        if event.get("group_evidence_sha256") != _current_group_hash(group, by_item):
            continue
        valid = all(review_id in by_item and
                    evidence_hash(by_item[review_id]) == _event_evidence_for(events, event, review_id)
                    for review_id in members)
        if valid:
            completed.update(members)
    return [item for item in items if item.get("review_id") not in completed]


def _current_group_hash(group, by_item):
    ids = sorted(group.get("member_review_ids", []))
    return hashlib.sha256(json.dumps(
        {"decision_group_id": group.get("decision_group_id"), "members": [
            {"review_id": review_id, "evidence_sha256": evidence_hash(by_item[review_id])}
            for review_id in ids if review_id in by_item]},
        sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def _event_evidence_for(events, event, review_id):
    # Each Git event is one member-specific, evidence-bound decision.
    return next((row.get("review_evidence_sha256") for row in events
                 if row.get("event_type") == "MASTER_REVIEW_DECISION"
                 and row.get("batch_id") == event.get("batch_id")
                 and row.get("decision_group_id") == event.get("decision_group_id")
                 and row.get("review_id") == review_id
                 and row.get("decision") == event.get("decision")), None)
