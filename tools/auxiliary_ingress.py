#!/usr/bin/env python3
"""Explicit, non-destructive ingress for Warder auxiliary logo identities.

Channel service-reference validation and channel paths are deliberately not
called here. Input/output identity is namespaced as provider-logo:: or
satellite-logo:: and candidate outputs are compared read-only.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath

import numpy as np
from PIL import Image

import auxiliary_renderer as renderer
from warder_visual_qc import (
    CENTER_TOLERANCE, SAFE_BBOX, center_rgba_layer,
    compare_approved_pixels, digest_bound_approval_matches,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = Path("reports/warder-master-production")
SOURCE_DIR = BASE / "auxiliary-proof-engine-candidates-2026-10-07"
CENTER_DIR = BASE / "auxiliary-centering-2026-10-08"
INPUTS = {
    "transparent_sources": {"path": SOURCE_DIR / "transparent-sources.zip", "size": 1117501,
                             "sha256": "ed73471b2e9bdc63e811a73000072bbee0be2623fc5620e7df6a34562044eb9a",
                             "git_blob_sha": "204d2f97336327fba8a93d62549dbd3ea830421a"},
    "provider_black": {"path": CENTER_DIR / "provider-black-centered.zip", "size": 5949641,
                       "sha256": "08290327a5a94733fbfcb52fb2cc956f4dadee9d9a20c198af77b89799d35035",
                       "git_blob_sha": "a7683738b5438871195b2e9f0f268b6606fa5d68"},
    "provider_white": {"path": CENTER_DIR / "provider-white-centered.zip", "size": 5914324,
                       "sha256": "cdb9d00e0db9d23e04bc5deefba3523296777f1908ce2eeb6d1d75460b89bf9b",
                       "git_blob_sha": "38eb314d37f6b13e8ca3b67504c91fda6938c308"},
    "satellite_black_white": {"path": CENTER_DIR / "satellite-black-white-centered.zip", "size": 77182,
                              "sha256": "736d82cadaffecea26ec12572394870e648363e2b00b1f1129c16aeef9c5d2d7",
                              "git_blob_sha": "297f1891eae13a5c297350bdf523a3d95655e4ae"},
}
SOURCE_COMMIT = "db5eec9f1cdb7a4d587cb1bcdeebc6b3f0d51819"
CANDIDATE_CHECKPOINT = "8bf726a3d7ba046f5bc531c8236b573963b7557a"
QC_CHECKPOINT = "13dd00b5624c4b6659574cdddedd503edc18947c"
PROVENANCE = {
    "source_commit": SOURCE_COMMIT,
    "renderer_sha256": "a66c7d8691c43648cb8650c194ad247c2159664262c590d7f2bdcd4c167e307a",
    "centering_checkpoint_path": str(CENTER_DIR) + "/",
}
TEMPLATE_SHA256 = {
    "black": "61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe",
    "white": "c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha(path: Path) -> str:
    return subprocess.check_output(["git", "hash-object", str(path)], cwd=ROOT, text=True).strip()


def read_png_zip(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"bad ZIP member CRC: {path}: {bad}")
        out = {}
        for member in archive.infolist():
            pure = PurePosixPath(member.filename)
            if pure.is_absolute() or ".." in pure.parts:
                raise ValueError(f"unsafe ZIP member path in {path}: {member.filename}")
            if member.is_dir() or pure.suffix.lower() != ".png":
                continue
            key = pure.as_posix()
            if key in out:
                raise ValueError(f"duplicate basename in {path}: {key}")
            out[key] = archive.read(member)
        return out


def read_sources(path: Path) -> tuple[dict[str, bytes], dict[str, str]]:
    result: dict[str, bytes] = {}
    domains: dict[str, str] = {}
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"bad source ZIP CRC: {bad}")
        for member in archive.infolist():
            pure = PurePosixPath(member.filename)
            if pure.is_absolute() or ".." in pure.parts:
                raise ValueError(f"unsafe source ZIP path: {member.filename}")
            if pure.suffix.lower() != ".png":
                continue
            if len(pure.parts) != 3 or pure.parts[0] != "source-transparent" or pure.parts[1] not in {"provider", "satellite"}:
                raise ValueError(f"invalid auxiliary source path: {member.filename}")
            name = pure.name
            key = name.casefold()
            if key in {n.casefold() for n in result}:
                raise ValueError(f"case-insensitive duplicate auxiliary filename: {name}")
            result[name] = archive.read(member)
            domains[name] = pure.parts[1]
    return result, domains


def verify_pins() -> dict:
    evidence = {}
    for label, spec in INPUTS.items():
        path = ROOT / spec["path"]
        data = path.read_bytes()
        actual_sha = sha(data)
        actual_blob = git_blob_sha(path)
        if len(data) != spec["size"] or actual_sha != spec["sha256"] or actual_blob != spec["git_blob_sha"]:
            raise ValueError(f"pinned input mismatch for {label}: size={len(data)} sha={actual_sha} blob={actual_blob}")
        evidence[label] = {"path": str(spec["path"]), "size": len(data), "sha256": actual_sha,
                           "git_blob_sha": actual_blob, "zip_integrity": "PASS"}
    for style in ("black", "white"):
        path = ROOT / f"templates/picons/{style}-sablona.png"
        if sha(path.read_bytes()) != TEMPLATE_SHA256[style]:
            raise ValueError(f"immutable {style} master template hash mismatch")
    return evidence


def run() -> dict:
    pins = verify_pins()
    source_spec = ROOT / INPUTS["transparent_sources"]["path"]
    sources, domains = read_sources(source_spec)
    if (len(sources), Counter(domains.values())) != (173, Counter({"provider": 172, "satellite": 1})):
        raise ValueError("auxiliary source scope is not exactly 172 Provider + 1 Satellite")
    provider_black = read_png_zip(ROOT / INPUTS["provider_black"]["path"])
    provider_white = read_png_zip(ROOT / INPUTS["provider_white"]["path"])
    satellite = read_png_zip(ROOT / INPUTS["satellite_black_white"]["path"])
    if set(provider_black) != {f"black/provider/{n}" for n in sources if domains[n] == "provider"} or set(provider_white) != {f"white/provider/{n}" for n in sources if domains[n] == "provider"}:
        raise ValueError("Provider candidate ZIP identity set mismatch")
    if set(satellite) != {f"{style}/satellite/{name}" for style in ("black", "white") for name in sources if domains[name] == "satellite"}:
        raise ValueError("Satellite candidate ZIP member set mismatch")

    centering_audit = {r["filename"]: r for r in (json.loads(line) for line in (ROOT / CENTER_DIR / "centering-audit.jsonl").read_text().splitlines())}
    sha_manifest = [json.loads(line) for line in (ROOT / CENTER_DIR / "sha256-manifest.jsonl").read_text().splitlines()]
    sha_index = {(r["identity"], r["type"]): r for r in sha_manifest}
    if len(sha_manifest) != 519 or len(sha_index) != 519:
        raise ValueError("per-PNG SHA manifest must contain exactly 519 unique source/variant rows")
    if set(centering_audit) != set(sources):
        raise ValueError("pinned audit identity coverage mismatch")
    approval_doc = json.loads((ROOT / "tests/fixtures/auxiliary-visual-approvals.json").read_text())
    approvals = {(r["identity"], r["variant"]): r for r in approval_doc["approved_review_variants"]}
    masters = {s: Image.open(ROOT / f"templates/picons/{s}-sablona.png").convert("RGBA") for s in ("black", "white")}
    rows = []
    for name in sorted(sources, key=str.casefold):
        data = sources[name]
        if sha(data) != centering_audit[name]["source_sha256"]:
            raise ValueError(f"source SHA mismatch for {name}")
        source_identity = f"{domains[name]}-logo::{name}"
        source_row = sha_index.get((source_identity, "transparent-master"))
        if not source_row or source_row["sha256"] != sha(data) or source_row.get("unchanged") is not True:
            raise ValueError(f"individual source hash manifest mismatch: {source_identity}")
        try:
            source = Image.open(io.BytesIO(data)).convert("RGBA")
            source.load()
        except Exception as exc:
            raise ValueError(f"invalid transparent PNG {name}: {exc}") from exc
        if source.size != (220, 132):
            raise ValueError(f"source dimensions mismatch {name}: {source.size}")
        fitted, scale, bbox = renderer.fit_logo(source)
        geometry = renderer.fit_geometry_mask(source, bbox, scale)
        identity = f"{domains[name]}-logo::{name}"
        variants = {}
        for style in ("black", "white"):
            result = renderer.classify_and_render(fitted, masters[style], style, centering_mask=geometry)
            expected_bytes = (provider_black[f"black/provider/{name}"] if style == "black" else provider_white[f"white/provider/{name}"]) if domains[name] == "provider" else satellite[f"{style}/satellite/{name}"]
            expected_sha = sha(expected_bytes)
            cp_sha = centering_audit[name]["variants"][style]["new_sha256"]
            manifest_row = sha_index.get((identity, style))
            if (expected_sha != cp_sha or not manifest_row
                    or manifest_row.get("new_sha256") != expected_sha):
                raise ValueError(f"approved output SHA differs from centering audit: {identity} {style}")
            expected = Image.open(io.BytesIO(expected_bytes)).convert("RGBA")
            actual_rgba = np.asarray(result.image.convert("RGBA"))
            expected_rgba = np.asarray(expected)
            comparison = compare_approved_pixels(actual_rgba, expected_rgba)
            actual_png = io.BytesIO(); result.image.save(actual_png, format="PNG", optimize=True)
            actual_png_bytes = actual_png.getvalue()
            actual_sha = sha(actual_png_bytes)
            approval = approvals.get((identity, style))
            approval_matches_output = bool(approval and digest_bound_approval_matches(
                approval, identity=identity, source_sha256=sha(data), variant=style,
                output_sha256=actual_sha, checkpoint_output_sha256=expected_sha,
                review_reason=result.reason, approved_checkpoint=CANDIDATE_CHECKPOINT,
                template_sha256=TEMPLATE_SHA256[style], candidate_renderer_provenance=PROVENANCE,
                alpha_geometry_sha256=result.alpha_geometry_sha256,
                current_output_png=actual_png_bytes, checkpoint_output_png=expected_bytes))
            approved = bool(result.status == "REVIEW" and approval_matches_output)
            # Visual approvals are the only allowed status exception; pixels still must match exactly or bounded AA.
            if not comparison.equivalent:
                approved = False
            # The saved proof audit records final candidate QC, while this
            # engine call reports its raw PASS/AUTO-FIXED/REVIEW decision.
            # PASS and AUTO-FIXED are acceptable after output comparison; a
            # raw REVIEW requires the exact digest-bound visual approval.
            expected_status = "PASS"  # approved QC checkpoint final state for all 173 identities
            status_matches = result.status in {"PASS", "AUTO-FIXED"} or approved
            variant_status = "PASS" if comparison.equivalent and status_matches else "REVIEW"
            variants[style] = {"status": variant_status, "engine_status": result.status,
                               "approved_final_status": expected_status, "engine_status_accepted": status_matches,
                               "pixel_exact": comparison.exact, "pixel_equivalent": comparison.equivalent,
                               "pixel_reason": comparison.reason, "source_sha256": sha(data),
                               "candidate_sha256": expected_sha, "rendered_sha256": actual_sha,
                               "visual_approval_record_matches": approval_matches_output,
                               "visual_approval_applied_to_review": approved,
                               "renderer_reason": result.reason}
        if variants["black"]["status"] != "PASS" or variants["white"]["status"] != "PASS":
            family_status = "REVIEW"
        else:
            family_status = "PASS"
        rows.append({"identity": identity, "domain": domains[name], "filename": name,
                     "source_sha256": sha(data), "black_sha256": variants["black"]["candidate_sha256"],
                     "white_sha256": variants["white"]["candidate_sha256"],
                     "status": family_status, "variants": variants})
    if sum(1 for r in rows if r["domain"] == "provider") != 172 or sum(1 for r in rows if r["domain"] == "satellite") != 1:
        raise ValueError("identity mapping count mismatch")
    return {"input_pins": pins, "approved_source_commit": SOURCE_COMMIT,
            "approved_candidate_checkpoint": CANDIDATE_CHECKPOINT, "approved_qc_checkpoint": QC_CHECKPOINT,
            "identities": 173, "provider": 172, "satellite": 1, "candidate_pngs": 346,
            "pass": sum(r["status"] == "PASS" for r in rows),
            "review": sum(r["status"] == "REVIEW" for r in rows), "fail": 0,
            "digest_bound_approval_records": len(approvals),
            "digest_bound_approvals_matched": sum(v["visual_approval_record_matches"] for r in rows for v in r["variants"].values()),
            "raw_review_variants": sum(v["engine_status"] == "REVIEW" for r in rows for v in r["variants"].values()),
            "review_variants_approved": sum(v["visual_approval_applied_to_review"] for r in rows for v in r["variants"].values()),
            "transparent_sources_unchanged": True, "legacy_fallback_touched": False,
            "results": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=ROOT / "reports/warder-master-production/auxiliary-integration-2026-10-08/ingress-run.json")
    args = parser.parse_args()
    report = run()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("identities", "provider", "satellite", "candidate_pngs", "pass", "review", "fail", "transparent_sources_unchanged", "legacy_fallback_touched")}))
    return 0 if report["review"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
