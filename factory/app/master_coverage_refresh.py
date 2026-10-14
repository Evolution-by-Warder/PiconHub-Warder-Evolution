"""Reclassify a persisted review queue against a fresh Git Master without rescanning PNGs."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

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


def recalculate_master_first(queue, snapshot):
    """Return fresh queue and coverage from already persisted review evidence.

    This function reads no PNGs and performs no render/QA. Approval stays fail-closed:
    only Git ledger events tied to the current registry hashes can cover artwork.
    """
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

    items = _restore_covered_items(queue)
    items = apply_git_review_decisions(items, review_events)
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
    updated["master_first_refresh"] = {
        "source_queue_count": len(original_items),
        "recalculated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "master_commit": commit,
        "rendering_performed": False,
        "pngs_read": 0,
        "automatic_identity_approvals": 0,
        "active_items": updated["count"],
        "covered_items": len(updated.get("covered_items", [])),
    }
    diagnostic = coverage_diagnostic(coverage, approval_status)
    diagnostic["refresh"] = dict(updated["master_first_refresh"])
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
    return {"queue_path": str(queue_path), "diagnostic_path": str(diagnostic_path),
            "master_commit": result["master_commit"], "active_items": queue["count"],
            "covered_items": len(queue.get("covered_items", [])),
            "decision_groups": queue.get("decision_group_summary", {}).get("user_decision_groups", 0)}
