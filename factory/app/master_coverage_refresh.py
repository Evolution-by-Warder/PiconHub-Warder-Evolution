"""Reclassify a persisted review queue against a fresh Git Master without rescanning PNGs."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import time

from master_coverage import (
    approval_evidence_from_git_master,
    apply_master_first_coverage,
    build_master_coverage,
    coverage_diagnostic,
    git_master_coverage_index,
)
from review_decision_groups import build_decision_groups
from review_queue import save_review_queue
from source_registry import atomic_json
from warder_identity_registry import validate_master_store
from warder_review_store import apply_git_review_decisions


def _restore_covered_items(queue):
    """Re-evaluate old coverage records instead of treating them as permanent approval."""
    items = [dict(item) for item in queue.get("items", [])]
    seen = {item.get("review_id") for item in items}
    for covered in queue.get("covered_items", []):
        if not isinstance(covered, dict):
            continue
        item = dict(covered)
        review_id = item.get("review_id")
        if not review_id or review_id in seen:
            continue
        if item.get("coverage_status") != "COVERED_BY_APPROVED_MASTER":
            continue
        item["decision"] = "PENDING"
        for key in ("coverage_status", "coverage_reason", "coverage_evidence_hash",
                    "master_coverage_evidence_hash"):
            item.pop(key, None)
        items.append(item)
        seen.add(review_id)
    return items


def _review_status(item):
    """Conservative workflow label; this never approves an identity or artwork."""
    lane = item.get("workstream") or item.get("category")
    reasons = item.get("reasons", [])
    if not isinstance(reasons, (list, tuple)):
        reasons = [reasons]
    tokens = " ".join(str(value) for value in (
        list(reasons) + [item.get("reason", ""), item.get("conflict_type", "")])).upper()
    if lane == "TECHNICAL_QA":
        return "TECHNICAL_QA", "TECHNICAL_FINDING_REQUIRES_QA"
    if any(value in tokens for value in ("AMBIGUOUS", "IDENTITY_UNVERIFIED")):
        return "AMBIGUOUS", "IDENTITY_EVIDENCE_IS_AMBIGUOUS"
    if any(value in tokens for value in ("CONFLICT", "COLLISION")):
        return "CONFLICT", "EXPLICIT_CONFLICT_EVIDENCE"
    service_ref = (item.get("service_reference") or item.get("candidate_service_ref")
                   or item.get("candidate_identity"))
    candidate_sha = item.get("candidate_sha256") or item.get("sha256")
    if not isinstance(service_ref, str) or not service_ref.strip():
        return "BLOCKED_MISSING_EVIDENCE", "SERVICE_REFERENCE_MISSING"
    if (not isinstance(candidate_sha, str) or len(candidate_sha) != 64 or
            any(char not in "0123456789abcdefABCDEF" for char in candidate_sha)):
        return "BLOCKED_MISSING_EVIDENCE", "CANDIDATE_SHA256_MISSING_OR_INVALID"
    if lane not in {"IDENTITY_VERIFICATION", "ARTWORK_REVIEW"}:
        return "BLOCKED_MISSING_EVIDENCE", "UNKNOWN_REVIEW_WORKSTREAM"
    if lane == "IDENTITY_VERIFICATION" and not any(
            item.get(key) for key in ("source_provenance", "source_family", "source_evidence", "source")):
        return "BLOCKED_MISSING_EVIDENCE", "IDENTITY_SOURCE_PROVENANCE_MISSING"
    return "READY_FOR_HUMAN_APPROVAL", "REQUIRED_EVIDENCE_PRESENT_HUMAN_DECISION_REQUIRED"


def _workflow_summary(source_items, active_items, covered_items, completed_ids, groups):
    """Persist a per-review-ID status map without mutating evidence-hashed items."""
    statuses = {}
    for item in source_items:
        review_id = item.get("review_id")
        if not isinstance(review_id, str):
            continue
        statuses[review_id] = {"status": "PENDING", "reason": "NOT_CLASSIFIED"}
    for item in covered_items:
        review_id = item.get("review_id")
        if isinstance(review_id, str):
            statuses[review_id] = {"status": "AUTO_RESOLVED_VERIFIED",
                                   "reason": item.get("coverage_reason") or "EXPLICIT_GIT_APPROVAL_MATCH",
                                   "evidence_sha256": item.get("coverage_evidence_hash")}
    for review_id in completed_ids:
        statuses[review_id] = {"status": "COMPLETED_GIT_CONFIRMED",
                               "reason": "EXACT_REVIEW_EVIDENCE_AND_GROUP_SCOPE_MATCH"}
    counts = {key: 0 for key in (
        "AUTO_RESOLVED_VERIFIED", "READY_FOR_HUMAN_APPROVAL", "AMBIGUOUS",
        "CONFLICT", "TECHNICAL_QA", "BLOCKED_MISSING_EVIDENCE",
        "COMPLETED_GIT_CONFIRMED")}
    for item in active_items:
        review_id = item.get("review_id")
        if not isinstance(review_id, str):
            continue
        status, reason = _review_status(item)
        statuses[review_id] = {"status": status, "reason": reason}
        counts[status] += 1
    counts["AUTO_RESOLVED_VERIFIED"] = sum(
        value["status"] == "AUTO_RESOLVED_VERIFIED" for value in statuses.values())
    counts["COMPLETED_GIT_CONFIRMED"] = len(completed_ids)
    return {"schema": 1, "task_statuses": statuses, "counts": counts,
            "raw_source_tasks": len(statuses), "active_technical_tasks": len(active_items),
            "unique_decision_groups": len(groups.get("groups", [])),
            "automatic_identity_approvals": 0}


def recalculate_master_first(queue, snapshot):
    """Return fresh queue and coverage from already persisted review evidence.

    This function reads no PNGs and performs no render/QA. Approval stays fail-closed:
    only Git ledger events tied to the current registry hashes can cover artwork.
    """
    started = time.perf_counter()
    if not isinstance(queue, dict) or queue.get("schema") != 1:
        raise ValueError("Saved review queue schema is invalid")
    original_items = queue.get("items")
    if not isinstance(original_items, list) or queue.get("count") != len(original_items):
        raise ValueError("Saved review queue item count is inconsistent")
    if not isinstance(snapshot, dict):
        raise ValueError("Git Master snapshot is unavailable")
    registry = snapshot.get("registry")
    ledger = snapshot.get("approval_ledger")
    commit = snapshot.get("commit")
    if not isinstance(commit, str) or len(commit) != 40:
        raise ValueError("Git Master snapshot has no valid pinned commit")
    checked = validate_master_store(registry, ledger)
    if checked.get("status") != "VALID":
        raise ValueError("Git Master failed validation: " + str(checked.get("issues", [])[:10]))
    review_events = snapshot.get("events")
    if not isinstance(review_events, list):
        review_events = [event for event in ledger.get("events", [])
                         if isinstance(event, dict) and event.get("event_type") == "MASTER_REVIEW_DECISION"]

    restored_items = _restore_covered_items(queue)
    filtered_items = apply_git_review_decisions(restored_items, review_events)
    filtered_ids = {item.get("review_id") for item in filtered_items}
    completed_ids = {item.get("review_id") for item in restored_items
                     if item.get("review_id") and item.get("review_id") not in filtered_ids}
    items = filtered_items
    base = dict(queue)
    base["items"] = items
    base["count"] = len(items)
    base["covered_items"] = []
    base.pop("master_coverage_summary", None)

    approval, approval_status = approval_evidence_from_git_master(
        registry, ledger, master_commit=commit)
    projected, known_refs, retired_refs = git_master_coverage_index(registry)
    candidate_refs = set(retired_refs)
    for item in items:
        for key in ("candidate_identity", "service_reference", "candidate_service_ref"):
            value = item.get(key)
            if isinstance(value, str) and value:
                candidate_refs.add(value)
    coverage = build_master_coverage(
        projected, approval, master_commit=commit, candidate_refs=candidate_refs,
        known_refs=known_refs, unavailable=False)
    updated = apply_master_first_coverage(base, coverage)
    groups = build_decision_groups(updated)
    updated["decision_groups"] = groups["groups"]
    updated["decision_group_summary"] = groups["summary"]
    refresh = {
        "source_queue_count": len(original_items),
        "recalculated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "master_commit": commit,
        "rendering_performed": False,
        "pngs_read": 0,
        "automatic_identity_approvals": 0,
        "active_items": updated["count"],
        "covered_items": len(updated.get("covered_items", [])),
        "covered_this_refresh": updated.get("master_coverage_summary", {}).get(
            "covered_artwork_tasks_this_run", 0),
        "completed_git_confirmed": len(completed_ids),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    updated["master_first_refresh"] = refresh
    all_source_items = restored_items
    workflow = _workflow_summary(all_source_items, updated["items"],
                                 updated.get("covered_items", []), completed_ids, groups)
    updated["processing_workflow"] = workflow
    diagnostic = coverage_diagnostic(coverage, approval_status)
    diagnostic["refresh"] = dict(refresh)
    diagnostic["processing_workflow"] = workflow
    return {"queue": updated, "coverage_diagnostic": diagnostic,
            "master_commit": commit, "approval_status": approval_status}


def persist_master_first_refresh(report_dir, source_queue_path, result, *, run_id=None):
    """Atomically save a new queue and diagnostic; leave old reports untouched."""
    directory = Path(report_dir)
    directory.mkdir(parents=True, exist_ok=True)
    if run_id is None:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    if not isinstance(run_id, str) or not run_id.replace("-", "").isalnum():
        raise ValueError("Unsafe refresh run id")
    queue_path = directory / ("review-queue-master-refresh-" + run_id + ".json")
    diagnostic_path = directory / ("master-coverage-refresh-" + run_id + ".json")
    queue = result["queue"]
    if queue.get("count") != len(queue.get("items", [])):
        raise ValueError("Refreshed queue count is inconsistent")
    save_review_queue(queue_path, queue)
    diagnostic = dict(result["coverage_diagnostic"])
    diagnostic["refresh"]["source_review_queue"] = Path(source_queue_path).name
    diagnostic["refresh"]["review_queue"] = queue_path.name
    atomic_json(diagnostic_path, diagnostic)
    refresh = dict(queue.get("master_first_refresh", {}))
    covered_total = len(queue.get("covered_items", []))
    covered_this_run = refresh.get("covered_this_refresh", 0)
    approval_status = result.get("approval_status", {})
    unchanged_reason = None
    if refresh.get("source_queue_count") == queue["count"]:
        if approval_status.get("service_records", 0) == 0:
            unchanged_reason = ("Git Master snapshot is valid, but its registry/approval ledger has no "
                                "verified approved service records matching this queue.")
        elif covered_this_run == 0:
            unchanged_reason = ("No exact service-reference and approved artwork SHA match covered an "
                                "active task; unresolved evidence remains visible.")
    return {"queue_path": str(queue_path), "diagnostic_path": str(diagnostic_path),
            "master_commit": result["master_commit"],
            "source_active_items": refresh.get("source_queue_count", 0),
            "active_items": queue["count"],
            "covered_items": covered_total, "covered_this_refresh": covered_this_run,
            "completed_git_confirmed": refresh.get("completed_git_confirmed", 0),
            "decision_groups": queue.get("decision_group_summary", {}).get("user_decision_groups", 0),
            "elapsed_seconds": refresh.get("elapsed_seconds", 0),
            "approval_status": approval_status,
            "unchanged_reason": unchanged_reason,
            "processing_workflow": queue.get("processing_workflow", {})}



def format_master_refresh_result(result):
    """Human-readable truthful confirmation for the GUI."""
    before = result.get("source_active_items", "?")
    after = result.get("active_items", "?")
    covered = result.get("covered_this_refresh", 0)
    commit = str(result.get("master_commit", "unknown"))[:12]
    elapsed = result.get("elapsed_seconds", 0)
    workflow = result.get("processing_workflow", {})
    counts = workflow.get("counts", {})
    human = sum(counts.get(key, 0) for key in (
        "READY_FOR_HUMAN_APPROVAL", "AMBIGUOUS", "CONFLICT", "TECHNICAL_QA",
        "BLOCKED_MISSING_EVIDENCE"))
    groups = result.get("decision_groups", workflow.get("unique_decision_groups", "?"))
    text = (f"{before} → {after} aktívnych | skupiny {groups} | človek {human} | "
            f"pokryté {covered} | Git {commit} | {elapsed} s | BEZ RENDERU")
    reason = result.get("unchanged_reason")
    if reason:
        text += " · " + reason
    return text
