"""Anonymized item-level review evidence; PNG bytes and absolute paths are excluded."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath, PureWindowsPath

_HEX = re.compile(r"^[0-9a-fA-F]{64}$")
_ABSOLUTE = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\\\\\|/)")
_ALLOWED_LABEL = re.compile(r"^[\w .+()&'-]{1,100}$", re.UNICODE)


def _sha(value):
    return isinstance(value, str) and bool(_HEX.fullmatch(value))


def _opaque(value):
    return "sha256:" + hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def _source_id(source, family):
    """Stable source-relative identifier without retaining a user path/name."""
    raw = str(source or "").replace("\\", "/")
    lowered = raw.casefold()
    markers = ("/02-originals/", "/source-ingest/originals/", "/originals/",
               "02-originals/", "source-ingest/originals/", "originals/")
    relative = raw
    for marker in markers:
        pos = lowered.find(marker)
        if pos >= 0:
            relative = raw[pos + len(marker):]
            break
    relative = relative.strip("/")
    # Hash the normalized relative name so customer service names and directory
    # labels cannot leak through a public diagnostic while remaining stable.
    normalized = PurePosixPath(relative).as_posix().casefold()
    return str(family or "unknown") + ":relsha256:" + hashlib.sha256(
        normalized.encode("utf-8", errors="replace")).hexdigest()[:24]


def _safe_label(value):
    if not isinstance(value, str):
        return None
    candidate = PureWindowsPath(value).name
    candidate = PurePosixPath(candidate.replace("\\", "/")).name
    candidate = candidate.rsplit(".", 1)[0].strip()
    if not candidate or len(candidate) > 100 or not _ALLOWED_LABEL.fullmatch(candidate):
        return None
    return candidate


def _sources_for_item(item):
    sources = []
    for field in ("source_evidence", "variants"):
        entries = item.get(field)
        if isinstance(entries, (list, tuple)):
            for entry in entries:
                if isinstance(entry, dict):
                    sources.extend(entry.get("sources") or [])
                    sources.extend([entry.get("source"), entry.get("path")])
                elif isinstance(entry, str):
                    sources.append(entry)
    sources.extend([item.get("original"), item.get("candidate_source")])
    return sorted({value for value in sources if isinstance(value, str) and value})


def _observed_sha_sources(item):
    result = {}
    for field in ("source_evidence", "variants"):
        entries = item.get(field)
        if not isinstance(entries, (list, tuple)):
            continue
        for entry in entries:
            if not isinstance(entry, dict) or not _sha(entry.get("sha256")):
                continue
            sha = entry["sha256"].lower()
            sources = entry.get("sources") or [entry.get("source") or entry.get("path")]
            result.setdefault(sha, set()).update(source for source in sources
                                                  if isinstance(source, str) and source)
    for field in ("sha256", "candidate_sha256"):
        value = item.get(field)
        if _sha(value):
            result.setdefault(value.lower(), set()).add(item.get("original") or item.get("candidate_source") or "")
    for unit in item.get("artwork_review_units") or []:
        if isinstance(unit, dict):
            sha = unit.get("representative_sha256")
            if _sha(sha):
                result.setdefault(sha.lower(), set())
            for duplicate in unit.get("duplicate_sha256") or []:
                if _sha(duplicate):
                    result.setdefault(duplicate.lower(), set())
    return {sha: sorted(source for source in sources if source)
            for sha, sources in result.items()}


def _format_style(source, family, package_styles):
    if family == "openatv8":
        try:
            from registry_triage import _openatv_provenance
            fmt, style = _openatv_provenance(source, package_styles)
            return fmt, style, bool(fmt != "unknown" and style != "unknown")
        except (ImportError, OSError, TypeError, ValueError):
            pass
    return "unknown", "unknown", False


def _safe_master_entries(item):
    entries = []
    for entry in item.get("master_locations") or []:
        if not isinstance(entry, dict):
            continue
        style = entry.get("style")
        sha = entry.get("sha256")
        if style == "transparent" and _sha(sha):
            entries.append(sha.lower())
    return sorted(set(entries))


def build_review_evidence_export(queue, run_id, *, pixel_evidence=None, package_styles=None):
    """Produce exactly one anonymized record for every currently active task."""
    from registry_triage import origin_of
    pixel_evidence = pixel_evidence or {}
    package_styles = package_styles or {}
    active = [item for item in queue.get("items", [])
              if isinstance(item, dict) and item.get("decision", "PENDING") == "PENDING"]
    groups = queue.get("decision_groups") or []
    group_by_review = {}
    for group in groups:
        for review_id in group.get("member_review_ids", []):
            group_by_review[review_id] = group

    def _pixel_for(sha, units):
        evidence = pixel_evidence.get(sha, {})
        value = evidence if isinstance(evidence, str) else (
            evidence.get("pixel_sha256") if isinstance(evidence, dict) else None)
        if _sha(value):
            return value.lower()
        for unit in units:
            if (isinstance(unit, dict) and
                    str(unit.get("representative_sha256", "")).lower() == sha and
                    _sha(unit.get("pixel_sha256"))):
                return unit["pixel_sha256"].lower()
        return None

    pixel_counts = {}
    for item in active:
        units = item.get("artwork_review_units") or []
        pixels = {_pixel_for(sha, units) for sha in _observed_sha_sources(item)}
        for pixel in {value for value in pixels if value}:
            pixel_counts[pixel] = pixel_counts.get(pixel, 0) + 1

    records = []
    for item in sorted(active, key=lambda row: str(row.get("review_id", ""))):
        review_id = str(item.get("review_id") or "")
        group = group_by_review.get(review_id, {})
        raw_ref = item.get("candidate_identity") or item.get("service_reference") or ""
        units = [unit for unit in (item.get("artwork_review_units") or [])
                 if isinstance(unit, dict)]
        observed = _observed_sha_sources(item)
        all_sources = _sources_for_item(item)
        source_groups = []
        candidate_entries = []
        for sha, sources in sorted(observed.items()):
            source_ids = []
            families = set()
            formats = set()
            styles = set()
            verified = False
            for source in sources:
                family = origin_of(source)
                families.add(family)
                fmt, style, package_verified = _format_style(source, family, package_styles)
                formats.add(fmt)
                styles.add(style)
                verified = verified or package_verified
                source_ids.append(_source_id(source, family))
            fingerprint = pixel_evidence.get(sha, {})
            if isinstance(fingerprint, str):
                pixel_sha = fingerprint
                perceptual = None
            else:
                pixel_sha = fingerprint.get("pixel_sha256") if isinstance(fingerprint, dict) else None
                perceptual = fingerprint.get("dhash64") if isinstance(fingerprint, dict) else None
            if not _sha(pixel_sha):
                pixel_sha = next((unit.get("pixel_sha256") for unit in units
                                  if sha in {str(unit.get("representative_sha256", "")).lower(),
                                             *[str(value).lower() for value in unit.get("duplicate_sha256") or []]}), None)
            candidate_entries.append({
                "candidate_sha256": sha,
                "decoded_pixel_sha256": pixel_sha.lower() if _sha(pixel_sha) else None,
                "perceptual_dhash64": perceptual if isinstance(perceptual, str) else None,
                "source_relative_ids": sorted(set(source_ids)),
                "source_families": sorted(families),
                "formats": sorted(formats),
                "styles": sorted(styles),
                "verified_provenance": bool(verified),
            })
        candidate_pixels = sorted({entry["decoded_pixel_sha256"] for entry in candidate_entries
                                   if entry["decoded_pixel_sha256"]})
        master_pixels = sorted({value.lower() for unit in units
                                for value in (unit.get("master_pixel_sha256") or [])
                                if _sha(value)})
        master_shas = sorted({value.lower() for unit in units
                              for value in (unit.get("master_sha256") or [])
                              if _sha(value)} | set(_safe_master_entries(item)))
        origins = sorted({origin_of(source) for source in all_sources})
        source_family = origins[0] if len(origins) == 1 else ("multiple" if origins else "unknown")
        source_provenance = []
        for entry in candidate_entries:
            source_provenance.append({
                "candidate_sha256": entry["candidate_sha256"],
                "families": entry["source_families"],
                "formats": entry["formats"],
                "styles": entry["styles"],
                "verified": entry["verified_provenance"],
            })
        statuses = sorted({str(unit.get("master_pixel_comparison", "UNKNOWN")) for unit in units})
        if "PIXEL_EXACT_SAME_SERVICE_MASTER" in statuses:
            identical_master = all(status == "PIXEL_EXACT_SAME_SERVICE_MASTER" for status in statuses)
            different_master = False
        elif "NO_PIXEL_EXACT_SAME_SERVICE_MASTER" in statuses:
            identical_master = False
            different_master = True
        else:
            identical_master = None
            different_master = None
        group_tasks = int(group.get("review_tasks") or 1)
        labels = []
        for field in ("service_label", "master_service_name", "candidate_service_name"):
            value = _safe_label(item.get(field))
            if value:
                labels.append(value)
        artwork_ids = sorted({"WAG-" + value[:20].upper() for value in candidate_pixels})
        source_count = int(item.get("source_observations") or len(all_sources) or 0)
        records.append({
            "review_id": review_id,
            "workstream": item.get("workstream", "UNKNOWN"),
            "service_reference": _opaque(raw_ref) if raw_ref else None,
            "service_labels": sorted(set(labels)),
            "reason": sorted(set(str(value)[:120] for value in item.get("reasons", []))),
            "conflict_type": str(item.get("category") or item.get("reason") or "UNKNOWN")[:100],
            "candidate_sha256": item.get("sha256") if _sha(item.get("sha256")) else
                                (candidate_entries[0]["candidate_sha256"] if candidate_entries else None),
            "observed_candidate_sha256": sorted(observed),
            "candidate_artworks": candidate_entries,
            "master_sha256": master_shas,
            "master_decoded_pixel_sha256": master_pixels,
            "origin_source_family": source_family,
            "source_provenance": source_provenance,
            "verified_provenance_flags": {
                "any_package_format_style_verified": any(row["verified"] for row in source_provenance),
                "all_candidate_sha_values_verified": bool(candidate_entries) and
                    all(_sha(row["candidate_sha256"]) for row in candidate_entries),
            },
            "format": sorted({fmt for entry in candidate_entries for fmt in entry["formats"]}) or ["unknown"],
            "style": sorted({style for entry in candidate_entries for style in entry["styles"]}) or ["unknown"],
            "source_grouping": {
                "source_families": origins,
                "relative_source_ids": sorted({source_id for entry in candidate_entries
                                               for source_id in entry["source_relative_ids"]}),
                "observation_count": source_count,
                "duplicate_observations": max(0, source_count - len(observed)),
            },
            "artwork_group_id": artwork_ids,
            "identity_group_id": group["decision_group_id"] if group.get("scope") == "IDENTITY_SAME_SERVICE" else None,
            "decision_group_id": group.get("decision_group_id"),
            "decision_group_scope": group.get("scope"),
            "decision_group_task_count": group_tasks,
            "affected_service_count": int(group.get("service_count") or (1 if raw_ref else 0)),
            "pixel_identical_with_another_candidate": any(pixel_counts.get(pixel, 0) > 1
                                                           for pixel in candidate_pixels),
            "pixel_identical_with_master": identical_master,
            "different_from_master": different_master,
            "unique_artworks_in_review_group": int(group.get("unique_artworks") or len(candidate_pixels)),
            "master_pixel_status": statuses,
        })
    groups_export = []
    for group in groups:
        groups_export.append({
            key: group.get(key) for key in (
                "decision_group_id", "scope", "member_review_ids", "member_evidence_hashes",
                "group_evidence_hash", "review_tasks", "service_count",
                "common_candidate_pixel_sha256", "common_master_pixel_sha256",
                "unique_artworks", "grouping_reason")
        } | {"affected_service_references": sorted({
            record["service_reference"] for record in records
            if record["review_id"] in set(group.get("member_review_ids", []))
            and record["service_reference"]})
        })
    covered_observations = []
    for item in sorted((row for row in queue.get("covered_items", []) if isinstance(row, dict)),
                       key=lambda row: str(row.get("review_id", ""))):
        sources = _sources_for_item(item)
        shas = sorted(_observed_sha_sources(item))
        covered_observations.append({
            "review_id": str(item.get("review_id") or ""),
            "workstream": item.get("workstream", "ARTWORK_REVIEW"),
            "service_reference": _opaque(item.get("candidate_identity") or "")
                                 if item.get("candidate_identity") else None,
            "coverage_status": "COVERED_BY_APPROVED_MASTER",
            "coverage_reason": "EXPLICIT_APPROVAL_AND_MASTER_HASHES_MATCH",
            "coverage_evidence_hash": item.get("coverage_evidence_hash"),
            "master_coverage_evidence_hash": item.get("master_coverage_evidence_hash"),
            "candidate_sha256": shas[0] if len(shas) == 1 else None,
            "observed_candidate_sha256": shas,
            "master_sha256": sorted({sha.lower() for entry in item.get("master_locations", [])
                                      if isinstance(entry, dict) and entry.get("style") in ("transparent", "black", "white")
                                      for sha in [entry.get("sha256")] if _sha(sha)}),
            "source_families": sorted({origin_of(source) for source in sources}),
            "source_relative_ids": sorted({_source_id(source, origin_of(source)) for source in sources}),
        })
    return {
        "schema": 1,
        "run": str(run_id)[:64],
        "privacy": {
            "service_references": "sha256-pseudonym",
            "source_paths": "stable-relative-path-hash",
            "images_uploaded": False,
            "private_fields_omitted": True,
        },
        "active_review_tasks": len(records),
        "decision_group_count": len(groups),
        "covered_observation_count": len(covered_observations),
        "covered_observations": covered_observations,
        "decision_groups": groups_export,
        "records": records,
    }
