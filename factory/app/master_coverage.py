"""Fail-closed MASTER-FIRST coverage classification.

Master file presence is not an approval signal. A service is considered covered
only when a local, explicit approval-evidence manifest is bound to the exact
Master commit and exact current variant SHA-256 values.
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


def build_master_coverage(master_registry, approval_evidence=None, *, master_commit=None, candidate_refs=()):
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
    manifest = approval_evidence if isinstance(approval_evidence, dict) else None
    manifest_services = manifest.get("services", {}) if manifest else {}
    commit_matches = bool(manifest and master_commit and manifest.get("master_commit") == master_commit)
    result = {}
    refs = {str(ref) for ref in candidate_refs if isinstance(ref, str) and ref}
    for ref in sorted(set(services) | set(manifest_services) | refs):
        entries = services.get(ref, [])
        if not entries:
            result[ref] = {"status": "NEW", "reason": "SERVICE_NOT_IN_MASTER",
                           "covered_styles": [], "missing_styles": list(REQUIRED_STYLES),
                           "approval_ref": None, "evidence_hash": _hash({"ref": ref, "status": "NEW"})}
            continue
        if ref in conflicts:
            result[ref] = {"status": "AMBIGUOUS", "reason": "MASTER_HAS_STYLE_CONFLICT",
                           "covered_styles": [], "missing_styles": list(REQUIRED_STYLES),
                           "approval_ref": None, "evidence_hash": _hash({"ref": ref, "status": "AMBIGUOUS", "entries": entries})}
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


def coverage_diagnostic(coverage_index, approval_manifest_status):
    """Compact, local diagnostic and migration instructions; never writes Registry."""
    return {"schema": 1, "master_commit": coverage_index.get("master_commit"),
            "approval_manifest": approval_manifest_status,
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
