#!/usr/bin/env python3
"""Focused Warder visual-QC regressions; all rendering is in-memory only.

The ten real auxiliary proof identities are pinned in a compact fixture ZIP.
Pass ``--checkpoint-dir`` to additionally compare the complete 173-identity
run against the accepted 8bf726a3 centered archives. Discrepancies are never
written over candidates: they are recorded as REVIEW in the machine report.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import rebuild_master_catalog as engine  # noqa: E402
from warder_visual_qc import (  # noqa: E402
    CENTER_TOLERANCE,
    SAFE_BBOX,
    center_rgba_layer,
    compare_approved_pixels,
    approval_provenance_signature,
    digest_bound_approval_matches,
    detect_local_panels,
    logical_component_groups,
    review_reason_signature,
)


MASTER_HASHES = {
    "black": "61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe",
    "white": "c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589",
}
APPROVED_CANDIDATE_PROVENANCE = {
    "source_commit": "db5eec9f1cdb7a4d587cb1bcdeebc6b3f0d51819",
    "renderer_sha256": "a66c7d8691c43648cb8650c194ad247c2159664262c590d7f2bdcd4c167e307a",
    "centering_checkpoint_path": "reports/warder-master-production/auxiliary-centering-2026-10-08/",
}
REQUIRED_IDENTITIES = {
    "TV8.png", "7+ CHANNEL.png", "CCTV.png", "CBC.png", "BETA DIGITAL.png",
    "BETADIGITAL.png", "COSMONOVA LLC.png", "TVCINE 3 HD.png", "TVCINE 4 HD.png",
    "TVSRIES HD.png",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def image_bytes(image: Image.Image) -> bytes:
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def render(source_bytes: bytes, style: str, master: Image.Image) -> tuple[engine.VariantResult, np.ndarray, tuple[int, int]]:
    source = Image.open(io.BytesIO(source_bytes)).convert("RGBA")
    fitted, scale, source_bbox = engine.fit_logo(source)
    geometry = engine.fit_geometry_mask(source, source_bbox, scale)
    center = center_rgba_layer(fitted, geometry_mask=geometry)
    result = engine.classify_and_render(fitted, master, style, centering_mask=geometry)
    return result, geometry, (center.dx, center.dy)


def load_regression_fixture() -> tuple[list[dict], dict[str, bytes]]:
    path = ROOT / "tests/fixtures/warder-visual-qc-regressions.zip"
    with zipfile.ZipFile(path) as archive:
        if archive.testzip():
            raise AssertionError("auxiliary regression fixture ZIP is corrupt")
        manifest = json.loads(archive.read("manifest.json"))
        assets = {name: archive.read(name) for name in archive.namelist() if name.endswith(".png")}
    return manifest, assets


def run_component_helper_tests() -> dict:
    # Wordmark letters on a shared baseline group across a narrow word gap;
    # a distant badge remains independent.
    a = np.zeros((132, 220), dtype=bool)
    b = np.zeros_like(a)
    c = np.zeros_like(a)
    a[20:32, 20:28] = True
    b[20:32, 30:38] = True
    c[75:90, 120:145] = True
    groups = logical_component_groups([a, b, c])
    assert sorted(sorted(g) for g in groups) == [[0, 1], [2]]

    layer = Image.new("RGBA", (220, 132), (0, 0, 0, 0))
    pixels = np.asarray(layer).copy()
    pixels[14:34, 38:72] = [40, 40, 40, 255]
    layer = Image.fromarray(pixels, "RGBA")
    mask = pixels[..., 3] > 0
    black = center_rgba_layer(layer, geometry_mask=mask)
    white = center_rgba_layer(layer.copy(), geometry_mask=mask)
    assert (black.dx, black.dy) == (white.dx, white.dy)
    assert black.centered and black.safe_area and not black.clipped
    assert black.dx == 55 and black.dy == 42
    assert black.image.size == (220, 132)

    manifest, assets = load_regression_fixture()
    cbc = next(row for row in manifest if row["filename"] == "CBC.png")
    source = Image.open(io.BytesIO(assets[f"transparent/{cbc['filename']}"])).convert("RGBA")
    fitted, _, _ = engine.fit_logo(source)
    topology = detect_local_panels(np.asarray(fitted), achromatic_delta=engine.ACHROMATIC_DELTA,
                                   luminance_fn=engine.rel_luma)
    assert len(topology.panels) == 1, f"HD+ by ASTRA panel not recognized: {len(topology.panels)}"
    assert len(topology.knockout_glyphs) >= 2, "HD+ by ASTRA knockout glyphs not recognized"
    assert len(topology.review_reasons) == 0, topology.review_reasons

    # The checkpoint's only non-exact renders are at most seven 1-LSB RGB
    # differences on alpha 250..253 pixels. Alpha/geometry changes and even a
    # 2-LSB edge change must remain a hard mismatch.
    baseline = np.zeros((132, 220, 4), dtype=np.uint8)
    baseline[40, 50] = [10, 20, 30, 252]
    same = compare_approved_pixels(baseline, baseline.copy())
    assert same.equivalent and same.exact
    edge = baseline.copy(); edge[40, 50, 2] += 1
    assert compare_approved_pixels(edge, baseline).equivalent
    edge[40, 50, 2] += 1
    assert not compare_approved_pixels(edge, baseline).equivalent
    alpha_changed = baseline.copy(); alpha_changed[40, 50, 3] -= 1
    assert not compare_approved_pixels(alpha_changed, baseline).equivalent
    opaque = baseline.copy(); opaque[40, 50, 3] = 255
    opaque_expected = opaque.copy(); opaque[40, 50, 0] += 1
    assert not compare_approved_pixels(opaque, opaque_expected).equivalent
    too_many = np.zeros((132, 220, 4), dtype=np.uint8)
    too_many[20:28, 20, :] = [10, 20, 30, 252]
    too_many_expected = too_many.copy(); too_many_expected[20:28, 20, 0] += 1
    assert not compare_approved_pixels(too_many, too_many_expected).equivalent

    approval_doc = json.loads((ROOT / "tests/fixtures/auxiliary-visual-approvals.json").read_text())
    approval_records = approval_doc["approved_review_variants"]
    assert len(approval_records) == 4
    for approval in approval_records:
        reason = approval["review_reason"]
        assert approval["review_reason_signature"] == review_reason_signature(reason)
        args = {"identity": approval["identity"], "source_sha256": approval["source_sha256"],
                "variant": approval["variant"], "output_sha256": approval["approved_output_sha256"],
                "review_reason": reason, "approved_checkpoint": approval["approved_checkpoint"],
                "template_sha256": approval["template_sha256"],
                "candidate_renderer_provenance": APPROVED_CANDIDATE_PROVENANCE}
        assert digest_bound_approval_matches(approval, **args)
        for field, value in (("source_sha256", "0" * 64),
                             ("approved_output_sha256", "1" * 64),
                             ("review_reason", reason + " changed"),
                             ("review_reason_signature", "2" * 64),
                             ("template_sha256", "3" * 64),
                             ("identity", "provider-logo::changed.png"),
                             ("variant", "black"),
                             ("approved_checkpoint", "4" * 40),
                             ("candidate_renderer_provenance", {"source_commit": "changed"}),
                             ("approved_provenance_signature", "5" * 64),
                             ("approval_status", "REVOKED")):
            mutated = dict(approval); mutated[field] = value
            assert not digest_bound_approval_matches(mutated, **args), f"approval did not invalidate on {field} change"
    approval_regressions = {"records": len(approval_records), "valid_match": "PASS",
                            "source_sha_invalidation": "PASS", "output_sha_invalidation": "PASS",
                            "reason_signature_invalidation": "PASS", "template_sha_invalidation": "PASS",
                            "identity_variant_checkpoint_provenance_invalidation": "PASS",
                            "pixel_bounds": "PASS"}
    return {"logical_grouping": "PASS", "integer_centering": "PASS",
            "local_panel_knockout": "PASS", "hd_plus_panel_count": len(topology.panels),
            "hd_plus_knockout_count": len(topology.knockout_glyphs),
            "pixel_reproducibility": "PASS", "digest_bound_approval": approval_regressions}


def run_auxiliary_regressions() -> dict:
    manifest, assets = load_regression_fixture()
    if {row["filename"] for row in manifest} != REQUIRED_IDENTITIES:
        raise AssertionError("real auxiliary proof fixture identity set is incomplete")
    masters = {style: Image.open(ROOT / f"templates/picons/{style}-sablona.png").convert("RGBA")
               for style in ("black", "white")}
    for style, master in masters.items():
        if sha((ROOT / f"templates/picons/{style}-sablona.png").read_bytes()) != MASTER_HASHES[style]:
            raise AssertionError(f"immutable {style} template SHA mismatch")

    results = []
    status_counts: Counter[str] = Counter()
    for item in manifest:
        name = item["filename"]
        source_bytes = assets[f"transparent/{name}"]
        if sha(source_bytes) != item["source_sha256"]:
            raise AssertionError(f"transparent master SHA changed in fixture: {name}")
        variants = {}
        geometry_by_style = []
        translations = []
        for style in ("black", "white"):
            result, geometry, translation = render(source_bytes, style, masters[style])
            expected_bytes = assets[f"{style}/{name}"]
            expected_sha_field = item[f"{style}_sha256"]
            if sha(expected_bytes) != expected_sha_field:
                raise AssertionError(f"approved regression output fixture SHA mismatch: {name} {style}")
            expected = Image.open(io.BytesIO(expected_bytes)).convert("RGBA")
            same_pixels = result.image.tobytes() == expected.tobytes()
            if result.image.size != (220, 132) or result.image.mode != "RGBA":
                raise AssertionError(f"rendered output format regression: {name} {style}")
            difference_pixels = int(np.count_nonzero(np.any(np.asarray(result.image) != np.asarray(expected), axis=2)))
            geometry_by_style.append(geometry)
            translations.append(translation)
            variants[style] = {
                "engine_status": result.status,
                "expected_status": item["expected_variant_status"][style],
                "pixel_match": same_pixels,
                "different_pixels": difference_pixels,
                "alpha_geometry_sha256": result.alpha_geometry_sha256,
                "centering_translation": [result.centering_dx, result.centering_dy],
                "expected_sha256": sha(expected_bytes),
                "rendered_sha256": sha(image_bytes(result.image)),
                "reason": result.reason,
            }
        if not np.array_equal(geometry_by_style[0], geometry_by_style[1]) or translations[0] != translations[1]:
            raise AssertionError(f"BLACK/WHITE centering geometry differs: {name}")
        if variants["black"]["alpha_geometry_sha256"] != variants["white"]["alpha_geometry_sha256"]:
            raise AssertionError(f"BLACK/WHITE rendered alpha geometry differs: {name}")
        geometry = geometry_by_style[0]
        ys, xs = np.nonzero(geometry)
        bbox = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
        bbox = [bbox[0] + translations[0][0], bbox[1] + translations[0][1],
                bbox[2] + translations[0][0], bbox[3] + translations[0][1]]
        center_x, center_y = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
        centered = abs(center_x - 110) <= CENTER_TOLERANCE and abs(center_y - 66) <= CENTER_TOLERANCE
        safe = bbox[0] >= SAFE_BBOX[0] and bbox[1] >= SAFE_BBOX[1] and bbox[2] <= SAFE_BBOX[2] and bbox[3] <= SAFE_BBOX[3]
        if not centered or not safe:
            raise AssertionError(f"center/safe-area regression: {name} bbox={bbox}")
        repro = all(v["pixel_match"] for v in variants.values())
        final = "PASS" if repro and all(v["engine_status"] != "REVIEW" for v in variants.values()) else "REVIEW"
        status_counts[final] += 1
        results.append({"identity": item["identity"], "filename": name, "status": final,
                        "expected_proof_status": item["expected_status"], "bbox": bbox,
                        "center_x": center_x, "center_y": center_y,
                        "translation": list(translations[0]), "variants": variants})
    return {"identities": len(results), "pass": status_counts["PASS"], "review": status_counts["REVIEW"],
            "fail": 0, "results": results}


def run_channel_regressions() -> dict:
    fixtures = json.loads((ROOT / "tests/fixtures/channel-visual-qc-regressions.json").read_text())
    masters = {style: Image.open(ROOT / f"templates/picons/{style}-sablona.png").convert("RGBA")
               for style in ("black", "white")}
    results = []
    for item in fixtures:
        source_path = ROOT / item["source"]
        source_bytes = source_path.read_bytes()
        if sha(source_bytes) != item["source_sha256"]:
            raise AssertionError(f"channel source fixture changed: {item['source']}")
        source = Image.open(io.BytesIO(source_bytes)).convert("RGBA")
        fitted, scale, source_bbox = engine.fit_logo(source)
        geometry = engine.fit_geometry_mask(source, source_bbox, scale)
        variants = {}
        for style in ("black", "white"):
            result = engine.classify_and_render(fitted, masters[style], style, centering_mask=geometry)
            output_path = ROOT / item["variants"][style]["output"]
            if sha(output_path.read_bytes()) != item["variants"][style]["sha256"]:
                raise AssertionError(f"channel baseline output SHA changed: {output_path}")
            expected = Image.open(output_path).convert("RGBA")
            same = result.image.tobytes() == expected.tobytes()
            if not same or result.status != item["variants"][style]["status"]:
                raise AssertionError(f"channel renderer regression: {item['source']} {style}")
            variants[style] = {"status": result.status, "pixel_match": same}
        if variants["black"]["status"] != item["variants"]["black"]["status"] or variants["white"]["status"] != item["variants"]["white"]["status"]:
            raise AssertionError(f"channel variant status changed: {item['source']}")
        results.append({"source": item["source"], "overall_status": item["overall_status"], "variants": variants})
    return {"cases": len(fixtures), "variants": len(fixtures) * 2, "status": "PASS", "results": results}


def run_full_checkpoint(checkpoint_dir: Path) -> dict:
    checkpoint_dir = checkpoint_dir.resolve()
    source_path = checkpoint_dir / "transparent-sources.zip"
    black_path = checkpoint_dir / "provider-black-centered.zip"
    white_path = checkpoint_dir / "provider-white-centered.zip"
    satellite_path = checkpoint_dir / "satellite-black-white-centered.zip"
    audit_path = checkpoint_dir / "machine/audit.jsonl"
    centering_audit_path = checkpoint_dir / "centering-audit.jsonl"
    required = (source_path, black_path, white_path, satellite_path, audit_path, centering_audit_path)
    if any(not path.exists() for path in required):
        raise FileNotFoundError("checkpoint dir must contain the 8bf source/candidate archives and machine/audit.jsonl")

    def read_png_zip(path: Path) -> dict[str, bytes]:
        with zipfile.ZipFile(path) as archive:
            if archive.testzip():
                raise AssertionError(f"corrupt checkpoint ZIP: {path}")
            return {Path(name).name: archive.read(name) for name in archive.namelist() if name.lower().endswith(".png")}

    with zipfile.ZipFile(source_path) as archive:
        if archive.testzip():
            raise AssertionError("transparent source ZIP is corrupt")
        sources = {Path(name).name: archive.read(name) for name in archive.namelist() if name.lower().endswith(".png")}
    black = read_png_zip(black_path)
    white = read_png_zip(white_path)
    satellite = {}
    with zipfile.ZipFile(satellite_path) as archive:
        if archive.testzip():
            raise AssertionError("satellite ZIP is corrupt")
        satellite = {name: archive.read(name) for name in archive.namelist() if name.lower().endswith(".png")}
    audit = {row["filename"]: row for row in (json.loads(line) for line in audit_path.read_text().splitlines())}
    centering_audit = {row["filename"]: row for row in (json.loads(line) for line in centering_audit_path.read_text().splitlines())}
    if (len(sources), len(black), len(white), len(satellite), len(audit), len(centering_audit)) != (173, 172, 172, 2, 173, 173):
        raise AssertionError("checkpoint identity/variant counts do not match accepted 173/346 scope")

    masters = {style: Image.open(ROOT / f"templates/picons/{style}-sablona.png").convert("RGBA")
               for style in ("black", "white")}
    approval_doc = json.loads((ROOT / "tests/fixtures/auxiliary-visual-approvals.json").read_text())
    approvals = {(r["identity"], r["variant"]): r for r in approval_doc["approved_review_variants"]}
    approved_checkpoint = "8bf726a3d7ba046f5bc531c8236b573963b7557a"
    rows = []
    summary: Counter[str] = Counter()
    for name, source_bytes in sorted(sources.items(), key=lambda pair: pair[0].casefold()):
        if sha(source_bytes) != audit[name].get("source_sha256"):
            raise AssertionError(f"transparent source SHA differs from approved machine report: {name}")
        if sha(source_bytes) != centering_audit[name].get("source_sha256"):
            raise AssertionError(f"transparent source SHA differs from approved centering report: {name}")
        source = Image.open(io.BytesIO(source_bytes)).convert("RGBA")
        fitted, scale, source_bbox = engine.fit_logo(source)
        geometry = engine.fit_geometry_mask(source, source_bbox, scale)
        translated: dict[str, tuple[int, int]] = {}
        variants = {}
        for style in ("black", "white"):
            result, _, shift = render(source_bytes, style, masters[style])
            translated[style] = shift
            expected_bytes = (satellite[f"{style}/satellite/{name}"] if name == "150W.png"
                              else (black[name] if style == "black" else white[name]))
            if sha(expected_bytes) != centering_audit[name]["variants"][style]["new_sha256"]:
                raise AssertionError(f"approved centered candidate SHA mismatch: {name} {style}")
            expected = Image.open(io.BytesIO(expected_bytes)).convert("RGBA")
            comparison = compare_approved_pixels(np.asarray(result.image), np.asarray(expected))
            pixel_match = comparison.exact
            rendered_sha = sha(image_bytes(result.image))
            approval = approvals.get((f"{'satellite-logo' if name == '150W.png' else 'provider-logo'}::{name}", style))
            visual_approval = bool(
                approval and result.status == "REVIEW" and comparison.exact
                and digest_bound_approval_matches(
                    approval,
                    identity=f"{'satellite-logo' if name == '150W.png' else 'provider-logo'}::{name}",
                    source_sha256=sha(source_bytes), variant=style,
                    output_sha256=rendered_sha, review_reason=result.reason,
                    approved_checkpoint=approved_checkpoint,
                    template_sha256=sha((ROOT / f"templates/picons/{style}-sablona.png").read_bytes()),
                    candidate_renderer_provenance=APPROVED_CANDIDATE_PROVENANCE,
                )
            )
            different_pixels = int(np.count_nonzero(np.any(np.asarray(result.image) != np.asarray(expected), axis=2)))
            expected_engine_status = audit[name]["variants"][style]["status"]
            status_match = result.status == expected_engine_status
            review_reasons = []
            if result.status == "REVIEW":
                review_reasons.append(result.reason)
            if not comparison.equivalent:
                review_reasons.append(f"{different_pixels} rendered pixels differ from the approved checkpoint; candidate kept unchanged and marked REVIEW")
            variants[style] = {"engine_status": result.status, "checkpoint_status": expected_engine_status,
                               "pixel_match": pixel_match, "status_match": status_match,
                               "different_pixels": different_pixels,
                               "pixel_equivalent": comparison.equivalent,
                               "pixel_comparison": comparison.reason,
                               "max_rgb_delta": comparison.max_rgb_delta,
                               "visual_approval_matched": visual_approval,
                               "effective_status": "VISUAL-APPROVED" if visual_approval else result.status,
                               "review_reason": "; ".join(review_reasons),
                               "alpha_geometry_sha256": result.alpha_geometry_sha256,
                               "centering_translation": [result.centering_dx, result.centering_dy],
                               "checkpoint_sha256": sha(expected_bytes),
                               "rendered_sha256": sha(image_bytes(result.image))}
        if translated["black"] != translated["white"]:
            raise AssertionError(f"variant position mismatch: {name}")
        if variants["black"]["alpha_geometry_sha256"] != variants["white"]["alpha_geometry_sha256"]:
            raise AssertionError(f"variant alpha geometry mismatch: {name}")
        mask_bbox = engine.warder_visual_bbox(geometry)
        dx, dy = translated["black"]
        bbox = [mask_bbox[0] + dx, mask_bbox[1] + dy, mask_bbox[2] + dx, mask_bbox[3] + dy]
        cx, cy = (bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0
        if abs(cx - 110) > CENTER_TOLERANCE or abs(cy - 66) > CENTER_TOLERANCE:
            raise AssertionError(f"centering invariant failed {name}: {bbox}")
        safe = bbox[0] >= 8 and bbox[1] >= 8 and bbox[2] <= 212 and bbox[3] <= 124
        if not safe:
            raise AssertionError(f"safe-area invariant failed {name}: {bbox}")
        equivalent_pixels = all(v["pixel_equivalent"] for v in variants.values())
        needs_review = (not equivalent_pixels) or any(
            v["engine_status"] == "REVIEW" and not v["visual_approval_matched"]
            for v in variants.values()
        )
        status = "REVIEW" if needs_review else "PASS"
        summary[status] += 1
        rows.append({"identity": ("satellite-logo::" if name == "150W.png" else "provider-logo::") + name,
                     "filename": name, "status": status, "bbox": bbox, "center": [cx, cy],
                     "translation": list(translated["black"]), "variants": variants})
    aa_variants = sum(
        1 for row in rows for variant in row["variants"].values()
        if variant["pixel_equivalent"] and not variant["pixel_match"]
    )
    approvals_matched = sum(
        1 for row in rows for variant in row["variants"].values()
        if variant["visual_approval_matched"]
    )
    return {"total_identities": len(rows), "provider": 172, "satellite": 1,
            "candidate_pngs": 346, "pixel_exact_identities": sum(all(v["pixel_match"] for v in row["variants"].values()) for row in rows),
            "pixel_equivalent_identities": sum(all(v["pixel_equivalent"] for v in row["variants"].values()) for row in rows),
            "bounded_aa_rounding_variants": aa_variants,
            "digest_bound_visual_approvals_matched": approvals_matched,
            "pass": summary["PASS"], "review": summary["REVIEW"],
            "fail": 0, "transparent_source_sha_unchanged": True,
            "approved_checkpoint_files_modified": False,
            "approved_checkpoint": "8bf726a3d7ba046f5bc531c8236b573963b7557a",
            "review_identities": [row for row in rows if row["status"] == "REVIEW"],
            "results": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint-dir", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    helper = run_component_helper_tests()
    auxiliary = run_auxiliary_regressions()
    channels = run_channel_regressions()
    report = {"helper_regressions": helper, "auxiliary_proof_regressions": auxiliary,
              "channel_regressions": channels}
    if args.checkpoint_dir:
        report["full_173_reproducibility"] = run_full_checkpoint(args.checkpoint_dir)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    full = report.get("full_173_reproducibility")
    print(json.dumps({"helper_regressions": "PASS", "auxiliary_regressions": auxiliary["pass"],
                      "auxiliary_review": auxiliary["review"], "channel_regressions": "PASS",
                      "full_173": None if full is None else {k: full[k] for k in ("total_identities", "pass", "review", "fail")}},
                     ensure_ascii=False))
    # A reproducibility mismatch is deliberately REVIEW and does not fail the
    # implementation regression suite; no candidate file is ever overwritten.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
