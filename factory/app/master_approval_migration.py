"""Fail-closed migration of recorded human Master approvals.

Default operation is a read-only report. Manifest writing is opt-in, never
targets the repository/diagnostic upload, and refuses to replace an existing
file. PNG presence, review clicks and local finalization alone are not proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from master_coverage import REQUIRED_STYLES


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def _sha(value):
    return isinstance(value, str) and len(value) == 64 and all(
        char in "0123456789abcdefABCDEF" for char in value)


def _load_records(inputs):
    records = []
    for source in inputs:
        if isinstance(source, list):
            records.extend(row for row in source if isinstance(row, dict))
        elif isinstance(source, dict):
            if ("event_type" in source or "master_approved" in source or
                    "service_reference" in source):
                records.append(source)
            for key in ("records", "approvals", "events"):
                value = source.get(key)
                if isinstance(value, list):
                    records.extend(row for row in value if isinstance(row, dict))
            # Preserve legacy review ledgers for audit, but never interpret a
            # review-stage decision as Master artwork approval.
            decisions = source.get("decisions")
            if isinstance(decisions, dict):
                for review_id, decision in decisions.items():
                    if isinstance(decision, dict):
                        records.append({"event_type": "LEGACY_REVIEW_DECISION",
                                        "record_id": review_id, **decision})
    return records


def _explicit_approval(record):
    return (record.get("master_approved") is True or
            record.get("event_type") in ("MASTER_APPROVAL", "MASTER_ARTWORK_APPROVED",
                                          "MASTER_VARIANT_APPROVAL"))


def migrate_approval_evidence(master_index, evidence_sources, *, master_commit):
    """Create a read-only migration result; does not write any file.

    Input approval record must explicitly affirm identity/artwork approval,
    name a source approval record and bind to this exact Master commit. Its
    optional evidence_sha256, when supplied, must hash the canonical record
    excluding that digest field.
    """
    if not isinstance(master_index, dict) or not isinstance(master_index.get("services"), dict):
        raise ValueError("Master index must contain a services object")
    if not isinstance(master_commit, str) or len(master_commit) != 40:
        raise ValueError("Exact 40-character Master commit is required")
    if any(char not in "0123456789abcdefABCDEF" for char in master_commit):
        raise ValueError("Master commit must be hexadecimal")
    master_services = master_index["services"]
    master_hashes = {}
    conflicts = set()
    for ref, entries in master_services.items():
        per_style = {}
        for row in entries if isinstance(entries, list) else []:
            if not isinstance(row, dict) or row.get("style") not in REQUIRED_STYLES:
                continue
            sha = row.get("sha256")
            if _sha(sha):
                per_style.setdefault(row["style"], set()).add(sha.lower())
        master_hashes[ref] = per_style
        if any(len(values) > 1 for values in per_style.values()):
            conflicts.add(ref)
    records = _load_records(evidence_sources)
    decisions = {}
    rejected = []
    for index, record in enumerate(records):
        ref = record.get("service_reference")
        if not isinstance(ref, str) or not ref.strip():
            rejected.append({"record_index": index, "reason": "SERVICE_REFERENCE_MISSING"})
            continue
        ref = ref.strip()
        if ref not in master_services:
            decisions.setdefault(ref, []).append({"status": "NEW", "reason": "SERVICE_NOT_IN_MASTER"})
            continue
        if not _explicit_approval(record):
            decisions.setdefault(ref, []).append({"status": "NO_EVIDENCE",
                                                   "reason": "NOT_AN_EXPLICIT_MASTER_APPROVAL"})
            continue
        if record.get("identity_verified") is not True or record.get("artwork_approved") is not True:
            decisions.setdefault(ref, []).append({"status": "NO_EVIDENCE",
                                                   "reason": "IDENTITY_OR_ARTWORK_APPROVAL_FLAG_MISSING"})
            continue
        approval_ref = record.get("approval_ref") or record.get("record_id")
        if not isinstance(approval_ref, str) or not approval_ref.strip():
            decisions.setdefault(ref, []).append({"status": "NO_EVIDENCE", "reason": "APPROVAL_REFERENCE_MISSING"})
            continue
        if record.get("master_commit") != master_commit:
            decisions.setdefault(ref, []).append({"status": "CONFLICT", "reason": "MASTER_COMMIT_MISMATCH"})
            continue
        digest_material = {key: value for key, value in record.items() if key != "evidence_sha256"}
        computed_digest = hashlib.sha256(_canonical(digest_material)).hexdigest()
        declared_digest = record.get("evidence_sha256")
        if declared_digest is not None and (not _sha(declared_digest) or declared_digest.lower() != computed_digest):
            decisions.setdefault(ref, []).append({"status": "CONFLICT", "reason": "SOURCE_EVIDENCE_HASH_MISMATCH"})
            continue
        variants = record.get("variants")
        if not isinstance(variants, dict) or not variants:
            decisions.setdefault(ref, []).append({"status": "NO_EVIDENCE", "reason": "VARIANT_HASHES_MISSING"})
            continue
        current = master_hashes.get(ref, {})
        bad = [style for style, sha in variants.items()
               if style not in REQUIRED_STYLES or not _sha(sha) or
               sha.lower() not in current.get(style, set())]
        if bad:
            decisions.setdefault(ref, []).append({"status": "CONFLICT",
                                                   "reason": "APPROVED_VARIANT_DOES_NOT_MATCH_MASTER",
                                                   "styles": sorted(map(str, bad))})
            continue
        if ref in conflicts:
            decisions.setdefault(ref, []).append({"status": "CONFLICT", "reason": "MASTER_STYLE_CONFLICT"})
            continue
        entry = {"identity_verified": True, "artwork_approved": True,
                 "approval_ref": approval_ref.strip()[:200],
                 "evidence_sha256": computed_digest,
                 "variants": {style: variants[style].lower() for style in REQUIRED_STYLES if style in variants}}
        status = "VERIFIED" if all(style in entry["variants"] for style in REQUIRED_STYLES) else "PARTIAL"
        decisions.setdefault(ref, []).append({"status": status, "manifest_entry": entry})

    result_services = {}
    for ref in sorted(master_services):
        rows = decisions.get(ref, [])
        approvals = [row for row in rows if row["status"] in ("VERIFIED", "PARTIAL")]
        signatures = {hashlib.sha256(_canonical(row["manifest_entry"])).hexdigest() for row in approvals}
        if ref in conflicts or any(row["status"] == "CONFLICT" for row in rows) or len(signatures) > 1:
            status, reason = "CONFLICT", "CONFLICTING_OR_STALE_APPROVAL_EVIDENCE"
        elif approvals:
            status = approvals[0]["status"]
            reason = "EXPLICIT_HUMAN_MASTER_APPROVAL_AND_CURRENT_HASHES"
            result_services[ref] = approvals[0]["manifest_entry"]
        else:
            status = "NO_EVIDENCE"
            reason = (rows[0].get("reason") if rows else "NO_RECORDED_APPROVAL_EVIDENCE")
        decisions[ref] = [{"status": status, "reason": reason}]
    for ref, rows in list(decisions.items()):
        if ref not in master_services and rows and all(row.get("status") == "NEW" for row in rows):
            decisions[ref] = [{"status": "NEW", "reason": "SERVICE_NOT_IN_MASTER"}]
    counts = {status: sum(1 for rows in decisions.values() if rows and rows[0].get("status") == status)
              for status in ("VERIFIED", "PARTIAL", "NO_EVIDENCE", "CONFLICT", "NEW")}
    return {"schema": 1, "read_only": True, "automatic_approval": False,
            "master_commit": master_commit, "counts": counts,
            "services": decisions, "rejected_records": rejected,
            "manifest": {"schema": 1, "master_commit": master_commit,
                         "services": result_services},
            "manifest_policy": "LOCAL_ONLY_EXPLICIT_WRITE_REQUIRED_NEVER_AUTO_UPLOADED"}


def write_manifest_new(path, manifest):
    """Create a local manifest atomically without replacing existing evidence."""
    path = Path(path)
    if _inside_git_checkout(path):
        raise ValueError("Approval manifest must stay outside a Git checkout")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".approval-migration-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(manifest, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        # Hard-link is atomic and fails if the destination already exists.
        os.link(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
    return path


def _inside_git_checkout(path):
    resolved = Path(path).absolute()
    return any((parent / ".git").exists() for parent in (resolved, *resolved.parents))


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--master-index", required=True)
    parser.add_argument("--master-commit", required=True)
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--report", required=True, help="Local migration audit report path")
    parser.add_argument("--write-manifest", help="Optional local manifest path; must not exist")
    args = parser.parse_args(argv)
    result = migrate_approval_evidence(_read_json(args.master_index),
                                      [_read_json(path) for path in args.evidence],
                                      master_commit=args.master_commit)
    # Report can be refreshed, but manifest is separate and no-overwrite.
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.write_manifest:
        write_manifest_new(args.write_manifest, result["manifest"])
    print(json.dumps({"counts": result["counts"], "report": str(args.report),
                      "manifest_written": bool(args.write_manifest)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
