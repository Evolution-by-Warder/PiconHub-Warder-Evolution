"""Fail-closed MASTER-FIRST coverage classification.

Master file presence is not an approval signal. Production coverage is derived
from the Git approval ledger plus exact current variant hashes. The local
approval evidence file is only a migration input and is not consumed here.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

REQUIRED_STYLES = ("transparent", "black", "white")
STATUSES = ("APPROVED_COMPLETE", "APPROVED_INCOMPLETE", "KNOWN_UNAPPROVED", "NEW", "AMBIGUOUS")
APPROVAL_FILE = "master-approval-evidence.json"


def _sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value.lower())


def _hash(value):
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_approval_evidence(path):
    """Read an optional local approval manifest without creating or changing it."""
    path = Path(path)
    if not path.is_file():
        return None, {"status": "MISSING", "path": str(path)}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        return None, {"status": "INVALID", "error": f"{type(exc).__name__}: {exc}"}
    if not isinstance(value, dict) or value.get("schema") != 1 or not isinstance(value.get("services"), dict):
        return None, {"status": "INVALID", "error": "Expected schema 1 and a services object"}
    return value, {"status": "AVAILABLE", "service_records": len(value["services"])}


def approval_evidence_from_git_master(identity_registry, approval_ledger, *, master_commit):
    """Adapt explicit Git approvals to the read-only coverage classifier.

    The local migration file is deliberately not consulted. A service needs an
    explicit identity approval and artwork approval (or one combined event),
    both attached to one unambiguous Warder ID and matching current hashes.
    """
    from warder_identity_registry import validate_master_store
    checked = validate_master_store(identity_registry, approval_ledger)
    if checked["status"] != "VALID" or not isinstance(master_commit, str) or len(master_commit) != 40:
        return None, {"status": "GIT_MASTER_INVALID_OR_UNAVAILABLE",
                      "issues": checked.get("issues", [])[:10]}
    events_by_id = {}
    for event in approval_ledger.get("events", []):
        events_by_id.setdefault(event.get("warder_id"), []).append(event)
    services = {}
    ambiguous = set()
    for wid, record in identity_registry.get("records", {}).items():
        if record.get("status") != "active":
            continue
        events = events_by_id.get(wid, [])
        revoked = {event.get("revokes_event_id") for event in events
                   if event.get("decision") == "APPROVAL_REVOKED"}
        effective = [event for event in events if event.get("event_id") not in revoked and
                     event.get("decision") != "APPROVAL_REVOKED"]
        combined = [event for event in effective if event.get("decision") == "IDENTITY_AND_ARTWORK_APPROVED"]
        identity_approved = any(event.get("decision") in {"IDENTITY_APPROVED", "IDENTITY_AND_ARTWORK_APPROVED"}
                                for event in effective)
        artwork_events = [event for event in effective if event.get("decision") in
                          {"ARTWORK_APPROVED", "IDENTITY_AND_ARTWORK_APPROVED"}]
        artwork = artwork_events[-1] if artwork_events else None
        if combined:
            identity_approved = True
        if not identity_approved or not artwork:
            continue
        variants = artwork.get("variants", {})
        current = record.get("artwork_current", {})
        if any(variants.get(style) != current.get(style) for style in REQUIRED_STYLES):
            continue
        for ref in record.get("service_references", []):
            if ref in services:
                ambiguous.add(ref)
            else:
                services[ref] = {"identity_verified": True, "artwork_approved": True,
                    "approval_ref": artwork.get("approval_id"),
                    "evidence_sha256": artwork.get("evidence_sha256"),
                    "variants": variants}
    for ref in ambiguous:
        services.pop(ref, None)
    return {"schema": 1, "master_commit": master_commit, "services": services}, {
        "status": "GIT_LEDGER", "service_records": len(services),
        "identity_approval_required": True, "artwork_sha_must_match_current_registry": True}


def build_master_coverage(master_registry, approval_evidence=None, *, master_commit=None, candidate_refs=(), known_refs=(), unavailable=False):
    """Classify every Master service; no PNG/reference alone can confer approval.

    Manifest format::

        {"schema": 1, "master_commit": "<exact commit>",
         "services": {"<service-ref>": {
           "identity_verified": true, "artwork_approved": true,
           "approval_ref": "<human audit reference>",
           "evidence_sha256": "<hash of the immutable approval record>",
           "variants": {"transparent": "<current master SHA-256>", ...}}}}

    Partial variant maps are allowed only for explicitly approved identities and
    artwork; missing styles then classify as APPROVED_INCOMPLETE.
    """
    registry = master_registry if isinstance(master_registry, dict) else {}
    services = registry.get("services") if isinstance(registry.get("services"), dict) else {}
    conflicts = {row.get("service_reference") for row in registry.get("conflicts", [])
                 if isinstance(row, dict) and row.get("service_reference")}
    known = {str(ref) for ref in known_refs if isinstance(ref, str) and ref}
    manifest = approval_evidence if isinstance(approval_evidence, dict) else None
    manifest_services = manifest.get("services", {}) if manifest else {}
    commit_matches = bool(manifest and master_commit and manifest.get("master_commit") == master_commit)
    result = {}
    refs = {str(ref) for ref in candidate_refs if isinstance(ref, str) and ref}
    for ref in sorted(set(services) | set(manifest_services) | refs | known):
        entries = services.get(ref, [])
        if unavailable:
            status, reason, covered, approval_ref = "AMBIGUOUS", "GIT_MASTER_UNAVAILABLE", [], None
        elif ref in conflicts:
            status, reason, covered, approval_ref = "AMBIGUOUS", "MASTER_IDENTITY_OR_STYLE_CONFLICT", [], None
        elif not entries:
            status, reason, covered, approval_ref = (
                ("KNOWN_UNAPPROVED", "KNOWN_IDENTITY_WITHOUT_CURRENT_ARTWORK", [], None)
                if ref in known else
                ("NEW", "SERVICE_NOT_IN_MASTER", [], None))
        else:
            status = reason = None
            covered = []
            approval_ref = None
        if status is not None:
            result[ref] = {"status": status, "reason": reason,
                           "covered_styles": covered, "missing_styles": list(REQUIRED_STYLES),
                           "approval_ref": approval_ref,
                           "evidence_hash": _hash({"ref": ref, "status": status, "reason": reason,
                                                  "entries": entries})}
            continue
        by_style = {}
        for entry in entries:
            if isinstance(entry, dict) and entry.get("style") in REQUIRED_STYLES and _sha(entry.get("sha256")):
                by_style.setdefault(entry["style"], set()).add(entry["sha256"].lower())
        if any(len(hashes) > 1 for hashes in by_style.values()):
            status, reason, covered = "AMBIGUOUS", "MULTIPLE_MASTER_HASHES_FOR_STYLE", []
            approval_ref = None
        else:
            evidence = manifest_services.get(ref) if isinstance(manifest_services, dict) else None
            if not manifest or not commit_matches:
                status, reason, covered, approval_ref = "KNOWN_UNAPPROVED", (
                    "APPROVAL_EVIDENCE_MISSING" if not manifest else "MASTER_COMMIT_MISMATCH"), [], None
            elif not isinstance(evidence, dict):
                status, reason, covered, approval_ref = "KNOWN_UNAPPROVED", "SERVICE_APPROVAL_MISSING", [], None
            elif evidence.get("identity_verified") is not True or evidence.get("artwork_approved") is not True:
                status, reason, covered, approval_ref = "KNOWN_UNAPPROVED", "EXPLICIT_IDENTITY_OR_ART_APPROVAL_MISSING", [], None
            elif (not isinstance(evidence.get("approval_ref"), str) or
                  not evidence.get("approval_ref", "").strip() or
                  not _sha(evidence.get("evidence_sha256"))):
                status, reason, covered, approval_ref = "KNOWN_UNAPPROVED", "APPROVAL_AUDIT_REFERENCE_OR_HASH_MISSING", [], None
            elif not isinstance(evidence.get("variants"), dict):
                status, reason, covered, approval_ref = "KNOWN_UNAPPROVED", "APPROVED_VARIANT_HASHES_MISSING", [], None
            else:
                declared = evidence["variants"]
                stale = any(style not in by_style or not _sha(declared.get(style)) or
                            declared.get(style).lower() not in by_style[style]
                            for style in declared if style in REQUIRED_STYLES)
                invalid_style = any(style not in REQUIRED_STYLES for style in declared)
                if stale or invalid_style or not declared:
                    status, reason, covered, approval_ref = "KNOWN_UNAPPROVED", "APPROVAL_EVIDENCE_STALE_OR_INVALID", [], None
                else:
                    covered = sorted(style for style, sha in declared.items()
                                     if style in by_style and _sha(sha) and sha.lower() in by_style[style])
                    missing = [style for style in REQUIRED_STYLES if style not in covered]
                    status = "APPROVED_INCOMPLETE" if missing else "APPROVED_COMPLETE"
                    reason = "REQUIRED_MASTER_VARIANTS_MISSING" if missing else "EXPLICIT_APPROVAL_AND_MASTER_HASHES_MATCH"
                    approval_ref = evidence["approval_ref"].strip()[:200]
        missing = [style for style in REQUIRED_STYLES if style not in covered]
        material = {"service_reference": ref, "status": status, "reason": reason,
                    "master_commit": master_commit, "approval_ref": approval_ref,
                    "approval_evidence_sha256": (manifest_services.get(ref, {}).get("evidence_sha256")
                                                  if isinstance(manifest_services.get(ref), dict) and status in ("APPROVED_COMPLETE", "APPROVED_INCOMPLETE") else None),
                    "covered_styles": covered,
                    "master_hashes": {style: sorted(values) for style, values in sorted(by_style.items())}}
        result[ref] = {"status": status, "reason": reason, "covered_styles": covered,
                       "missing_styles": missing, "approval_ref": approval_ref,
                       "approval_evidence_sha256": material["approval_evidence_sha256"],
                       "master_hashes": material["master_hashes"], "evidence_hash": _hash(material)}
    counts = {status: sum(item["status"] == status for item in result.values()) for status in STATUSES}
    return {"schema": 1, "policy": "EXPLICIT_APPROVAL_REQUIRED; MASTER_PNG_OR_REFERENCE_ALONE_IS_NOT_APPROVAL",
            "master_commit": master_commit, "approval_manifest_present": manifest is not None,
            "approval_manifest_commit_matches": commit_matches,
            "service_count": len(result), "counts": counts, "services": result}


def apply_master_first_coverage(queue, coverage_index):
    """Move only fully approved, exact-service artwork reviews to audit-only coverage."""
    queue = dict(queue)
    coverage = coverage_index.get("services", {}) if isinstance(coverage_index, dict) else {}
    active, covered_items = [], list(queue.get("covered_items", []))
    new_covered = []
    for raw in queue.get("items", []):
        item = dict(raw)
        ref = item.get("candidate_identity")
        match = coverage.get(ref) if isinstance(ref, str) else None
        if (item.get("decision", "PENDING") == "PENDING" and
                item.get("workstream") == "ARTWORK_REVIEW" and match and
                match.get("status") == "APPROVED_COMPLETE"):
            from review_decisions import evidence_hash
            audit = {**item, "coverage_status": "COVERED_BY_APPROVED_MASTER",
                     "coverage_reason": match.get("reason"),
                     "coverage_evidence_hash": _hash({
                         "review_evidence_hash": evidence_hash(item),
                         "master_coverage_evidence_hash": match.get("evidence_hash"),
                         "service_reference": ref,
                     }),
                     "master_coverage_evidence_hash": match.get("evidence_hash"),
                     "decision": "COVERED_BY_APPROVED_MASTER"}
            covered_items.append(audit)
            new_covered.append(audit)
        else:
            active.append(item)
    queue["items"] = active
    queue["count"] = len(active)
    queue["covered_items"] = covered_items
    if isinstance(queue.get("workstream_counts"), dict):
        for lane in queue["workstream_counts"]:
            queue["workstream_counts"][lane] = sum(
                item.get("workstream") == lane and item.get("decision", "PENDING") == "PENDING"
                for item in active)
    queue["master_coverage_summary"] = {
        "covered_artwork_tasks_this_run": len(new_covered),
        "covered_artwork_tasks_audit_total": len(covered_items),
        "statuses": {status: sum(1 for item in coverage.values() if item.get("status") == status)
                     for status in STATUSES},
        "automatic_identity_approvals": 0,
        "policy": "ONLY_EXPLICIT_APPROVED_COMPLETE; COVERED_ITEMS_RETAINED_IN_AUDIT",
    }
    return queue


def git_master_coverage_index(identity_registry):
    """Project the canonical Git Warder ID Registry into exact service/style evidence.

    Current refs are known even before artwork is approved. Historical refs are
    retained as conflicts so an old service alias cannot silently become a NEW
    identity. Reused refs across different Warder IDs always fail closed.
    """
    services = {}
    known_refs = set()
    retired_refs = set()
    owners = {}
    conflicts = []
    records = identity_registry.get("records", {}) if isinstance(identity_registry, dict) else {}
    for wid, record in sorted(records.items()):
        if not isinstance(record, dict):
            continue
        current = set(ref for ref in record.get("service_references", []) if isinstance(ref, str) and ref)
        historical = set(ref for ref in record.get("historical_service_references", []) if isinstance(ref, str) and ref)
        for ref in current | historical:
            owners.setdefault(ref, set()).add(wid)
            known_refs.add(ref)
            if ref in historical and ref not in current:
                retired_refs.add(ref)
        if record.get("status") != "active":
            retired_refs.update(current)
            continue
        artwork = record.get("artwork_current", {})
        if not isinstance(artwork, dict):
            artwork = {}
        for ref in current:
            rows = services.setdefault(ref, [])
            for style, sha in sorted(artwork.items()):
                if style in REQUIRED_STYLES and _sha(sha):
                    rows.append({"style": style, "sha256": sha.lower(),
                                 "warder_id": wid})
    for ref, ids in owners.items():
        if len(ids) > 1 or ref in retired_refs:
            conflicts.append({"service_reference": ref, "reason":
                              "SERVICE_REFERENCE_REUSED_OR_RETIRED",
                              "warder_ids": sorted(ids)})
    return services_wrapper(services, conflicts), known_refs, retired_refs


def services_wrapper(services, conflicts):
    return {"services": services, "conflicts": conflicts}


def coverage_diagnostic(coverage_index, approval_manifest_status):
    """Compact diagnostic; says which Git evidence was actually used."""
    return {"schema": 1, "master_commit": coverage_index.get("master_commit"),
            "approval_authority": approval_manifest_status,
            "local_approval_file_is_migration_input_only": True,
            "counts": coverage_index.get("counts", {}),
            "service_count": coverage_index.get("service_count", 0),
            "services": coverage_index.get("services", {}),
            "migration": {
                "manifest_filename": APPROVAL_FILE,
                "required_fields": ["master_commit", "services.<service_reference>.identity_verified",
                                    "services.<service_reference>.artwork_approved",
                                    "services.<service_reference>.approval_ref",
                                    "services.<service_reference>.evidence_sha256",
                                    "services.<service_reference>.variants.<style>.sha256"],
                "instruction": "Create this local manifest only from recorded human approval evidence. Match each variant SHA-256 to this exact Master commit. No entries are inferred from PNG presence, filenames, service references, or pixel similarity.",
                "registry_modified": False,
            }}
