#!/usr/bin/env python3
"""Build and verify non-production hybrid auxiliary ZIP candidates.

This consumes the already-approved strict safe tree and the pinned legacy
runtime ZIPs. It does not render, normalize, or alter any PNG artwork.
"""
from __future__ import annotations

import hashlib
import json
import stat
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "reports/warder-master-production/auxiliary-ingress-run-2026-10-06"
GATE = ROOT / "reports/warder-master-production/auxiliary-publishability-gate-2026-10-07"
COVERAGE = ROOT / "reports/warder-master-production/auxiliary-coverage-impact-2026-10-07"
OUT = ROOT / "reports/warder-master-production/auxiliary-hybrid-runtime-candidate-2026-10-07"
ARCHIVE_DIR = OUT / "archives"
SAFE = GATE / "safe-candidate-tree"

LEGACY = {
    ("provider", "transparent"): Path("/tmp/piconhub-provider-transparent.zip"),
    ("provider", "black"): Path("/tmp/aux-source-recovery-provider-black.zip"),
    ("provider", "white"): Path("/tmp/aux-source-recovery-provider-white.zip"),
    ("satellite", "transparent"): Path("/tmp/piconhub-satellite-transparent.zip"),
    ("satellite", "black"): Path("/tmp/aux-source-recovery-satellite-black.zip"),
    ("satellite", "white"): Path("/tmp/aux-source-recovery-satellite-white.zip"),
}
PINS = {
    ("provider", "transparent"): (11481399, "93ef555cf09d49a72188c477949d948feaf6416a0fcff047600d36b3a96e4b8f", 1145),
    ("provider", "black"): (11990269, "f693c2d70866a1b7161046a0e3fd74610b4785673e9ad11f2fa5cefbd6d1e13f", 1297),
    ("provider", "white"): (13974289, "ebff6f537720da39410741cb13abcce0be6a1f822264f516a291a2e70c889cff", 1256),
    ("satellite", "transparent"): (780076, "4e8c7d8095aa2c79a30eb1b9af05f4107758a515a31246565da13a6f05da1d5d", 69),
    ("satellite", "black"): (2244970, "6458bdf32db1dddd21ecf8894864e130d5c5535fcfe7fe2681509ad7b0958d8a", 269),
    ("satellite", "white"): (2421870, "539cda4f3f599f5e3f2b6e6690a4625fc5c678bdfb46cb9b1b68622d28b08b2b", 269),
}
DIRS = {
    "provider": ("piconProv", "piconProv_220x132"),
    "satellite": ("piconSat", "piconSat_220x132"),
}
SAFE_IDS = {
    ("provider", "transparent"): "piconProv-warder-safe-t",
    ("provider", "black"): "piconProv-warder-safe-b",
    ("provider", "white"): "piconProv-warder-safe-w",
    ("satellite", "transparent"): "piconSat-warder-safe-t",
    ("satellite", "black"): "piconSat-warder-safe-b",
    ("satellite", "white"): "piconSat-warder-safe-w",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def png_names(zf: zipfile.ZipFile) -> list[str]:
    names = []
    for item in zf.infolist():
        path = PurePosixPath(item.filename)
        if item.is_dir() or path.suffix.lower() != ".png":
            continue
        if item.external_attr >> 28 == 0xA:
            raise AssertionError(f"symlink ZIP member: {item.filename}")
        names.append(item.filename)
    return names


def check_png(data: bytes, *, expected_size=(220, 132), expected_mode="RGBA"):
    from io import BytesIO
    with Image.open(BytesIO(data)) as image:
        image.load()
        if (image.format != "PNG"
                or (expected_size is not None and image.size != expected_size)
                or (expected_mode is not None and image.mode != expected_mode)):
            raise AssertionError(f"invalid output PNG: {image.format} {image.size} {image.mode}")


def write_deterministic_member(zf: zipfile.ZipFile, name: str, data: bytes):
    info = zipfile.ZipInfo(name, date_time=(2026, 10, 7, 0, 0, 0))
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def main():
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    qc = json.loads((GATE / "qc-summary.json").read_text(encoding="utf-8"))
    if qc.get("status") != "PASS" or qc.get("total_complete_triads") != 173:
        raise SystemExit("accepted strict-safe-tree QC baseline is missing")

    safe_rows = read_jsonl(GATE / "publishability-manifest.jsonl")
    excluded_rows = read_jsonl(GATE / "exclusion-manifest.jsonl")
    safe_by_domain = {domain: set() for domain in DIRS}
    for row in safe_rows:
        domain = "provider" if row["domain"] == "provider-logo" else "satellite"
        if row.get("qc_status", {}).get("output_qc") != "PASS":
            raise SystemExit(f"non-passing safe candidate: {row['identity']}")
        safe_by_domain[domain].add(row["identity_filename"])
    excluded = {(
        "provider" if row["domain"] == "provider-logo" else "satellite",
        row["filename"],
    ) for row in excluded_rows}
    if set().union(*safe_by_domain.values()) & {name for _, name in excluded}:
        raise SystemExit("safe/review identity leakage in source manifests")
    if {d: len(v) for d, v in safe_by_domain.items()} != {"provider": 172, "satellite": 1}:
        raise SystemExit("safe triad identity count mismatch")

    current_names = {domain: {variant: set() for variant in ("transparent", "black", "white")} for domain in DIRS}
    archive_rows = []
    fallback_transparent = {}

    # Validate and preserve the six pinned upstream archives. Only the two
    # transparent archives are repacked, byte-for-byte at the PNG level, to
    # place legacy fallback copies in the existing base directory.
    for (domain, variant), source in LEGACY.items():
        expected_size, expected_sha, expected_count = PINS[(domain, variant)]
        raw = source.read_bytes()
        if len(raw) != expected_size or sha(raw) != expected_sha:
            raise SystemExit(f"pinned legacy archive mismatch: {domain}/{variant}")
        with zipfile.ZipFile(source) as zf:
            if zf.testzip() is not None:
                raise SystemExit(f"legacy ZIP CRC failure: {domain}/{variant}")
            members = png_names(zf)
            basenames = [PurePosixPath(name).name for name in members]
            if len(members) != expected_count or len(set(basenames)) != len(basenames):
                raise SystemExit(f"legacy member count/name collision: {domain}/{variant}")
            for name in members:
                data = zf.read(name)
                check_png(data, expected_size=(220, 132) if variant == "transparent" else None,
                          expected_mode="RGBA" if variant == "transparent" else None)
                current_names[domain][variant].add(PurePosixPath(name).name)
            if variant == "transparent":
                base_dir, _priority_dir = DIRS[domain]
                output = ARCHIVE_DIR / f"{domain}-transparent-legacy-fallback.zip"
                with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as out:
                    for name in sorted(members, key=lambda n: PurePosixPath(n).name.casefold()):
                        write_deterministic_member(out, f"{base_dir}/{PurePosixPath(name).name}", zf.read(name))
                fallback_transparent[(domain, variant)] = output

    # Build six safe, variant-specific overlay ZIPs from already approved PNGs.
    safe_archives = {}
    for domain, variant in ((d, v) for d in DIRS for v in ("transparent", "black", "white")):
        source_folder = SAFE / domain / variant
        expected_names = safe_by_domain[domain]
        actual_names = {p.name for p in source_folder.glob("*.png")}
        if actual_names != expected_names:
            raise SystemExit(f"safe tree names differ from publishability manifest: {domain}/{variant}")
        _base_dir, priority_dir = DIRS[domain]
        output = ARCHIVE_DIR / f"{domain}-{variant}-warder-safe-220x132.zip"
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as out:
            for path in sorted(source_folder.glob("*.png"), key=lambda p: p.name.casefold()):
                data = path.read_bytes()
                check_png(data)
                write_deterministic_member(out, f"{priority_dir}/{path.name}", data)
        safe_archives[(domain, variant)] = output

    # Re-open every candidate ZIP. Check CRC, member paths, identity set, PNG
    # geometry and per-file hashes against the immutable safe tree manifest.
    safe_path_names = {(r["identity"], v): r["output_paths"][v] for r in safe_rows for v in ("transparent", "black", "white")}
    safe_hashes = {(r["identity"], "transparent"): r["transparent_sha256"] for r in safe_rows}
    safe_hashes.update({(r["identity"], "black"): r["black_sha256"] for r in safe_rows})
    safe_hashes.update({(r["identity"], "white"): r["white_sha256"] for r in safe_rows})
    archive_manifest = {"schema": 1, "status": "PREPARED_NOT_PUBLISHED", "safe_source_checkpoint": "a97acf919b93e4efaa1fc31766c55a634b487208", "archives": {}}
    candidate_archives = {
        **{("legacy-fallback", domain, variant): path for (domain, variant), path in fallback_transparent.items()},
        **{("warder-safe", domain, variant): path for (domain, variant), path in safe_archives.items()},
    }
    for (layer, domain, variant), path in candidate_archives.items():
        raw = path.read_bytes()
        with zipfile.ZipFile(path) as zf:
            if zf.testzip() is not None:
                raise SystemExit(f"candidate ZIP CRC failure: {path.name}")
            members = png_names(zf)
            names = [PurePosixPath(m).name for m in members]
            if len(names) != len(set(names)):
                raise SystemExit(f"duplicate basename in candidate ZIP: {path.name}")
            if layer == "warder-safe":
                expected = safe_by_domain[domain]
                priority = DIRS[domain][1]
                if set(names) != expected or any(not m.startswith(priority + "/") for m in members):
                    raise SystemExit(f"safe archive membership/destination mismatch: {path.name}")
                for member in members:
                    data = zf.read(member)
                    check_png(data)
                    ident = ("provider-logo::" if domain == "provider" else "satellite-logo::") + PurePosixPath(member).name
                    if sha(data) != safe_hashes[(ident, variant)]:
                        raise SystemExit(f"safe archive source/output hash mismatch: {member}")
            else:
                base = DIRS[domain][0]
                if len(names) != PINS[(domain, variant)][2] or any(not m.startswith(base + "/") for m in members):
                    raise SystemExit(f"legacy fallback members/destination mismatch: {path.name}")
        archive_manifest["archives"][path.name] = {
            "sha256": sha(raw),
            "size_bytes": len(raw),
            "png_count": len(png_names(zipfile.ZipFile(path))),
            "destination": DIRS[domain][1] if layer == "warder-safe" else DIRS[domain][0],
            "layer": "WARDER_SAFE_PRIORITY" if layer == "warder-safe" else "LEGACY_FALLBACK",
            "variant": variant,
            "domain": domain,
            "zip_crc": "PASS",
        }

    # Verify the resulting lookup set is a superset of each pinned current
    # variant set. Counts here are filename identities visible to the existing
    # priority-then-base lookup, not claims of Warder approval.
    coverage = {}
    for domain in DIRS:
        coverage[domain] = {}
        for variant in ("transparent", "black", "white"):
            merged = current_names[domain][variant] | safe_by_domain[domain]
            coverage[domain][variant] = {
                "legacy_current_count": len(current_names[domain][variant]),
                "safe_priority_count": len(safe_by_domain[domain]),
                "resulting_lookup_identity_count": len(merged),
                "legacy_current_identities_preserved": len(current_names[domain][variant] - merged) == 0,
                "safe_ids_additive": len(merged - current_names[domain][variant]),
            }
            if not coverage[domain][variant]["legacy_current_identities_preserved"]:
                raise SystemExit(f"legacy coverage loss: {domain}/{variant}")

    fallback_entries = {
        "provider": {
            "transparent": {"asset_id": "piconProv-legacy-t", "filename": fallback_transparent[("provider", "transparent")].name},
            "black": {"asset_id": "piconProv-b", "filename": "piconProv-black.zip", "pinned_sha256": PINS[("provider", "black")][1], "pinned_size_bytes": PINS[("provider", "black")][0]},
            "white": {"asset_id": "piconProv-w", "filename": "piconProv-white.zip", "pinned_sha256": PINS[("provider", "white")][1], "pinned_size_bytes": PINS[("provider", "white")][0]},
        },
        "satellite": {
            "transparent": {"asset_id": "piconSat-legacy-t", "filename": fallback_transparent[("satellite", "transparent")].name},
            "black": {"asset_id": "piconSat-b", "filename": "piconSat-black.zip", "pinned_sha256": PINS[("satellite", "black")][1], "pinned_size_bytes": PINS[("satellite", "black")][0]},
            "white": {"asset_id": "piconSat-w", "filename": "piconSat-white.zip", "pinned_sha256": PINS[("satellite", "white")][1], "pinned_size_bytes": PINS[("satellite", "white")][0]},
        },
    }
    candidate_mapping = {
        "proposal_schema": "warder-auxiliary-hybrid-v1",
        "status": "CANDIDATE_ONLY_NOT_RUNTIME_CONSUMABLE_UNTIL_COMPOSITE_EXECUTOR_IS_IMPLEMENTED",
        "selection_labels": {"transparent": "Transparentné", "black": "Čierne", "white": "Biele"},
        "size_selector": False,
        "runtime_contract": "One GUI selection executes legacy_fallback first, then warder_safe_priority. Both operations are SHA/size pinned and independently validated. The existing consumer lookup remains *_220x132 first, then base directory.",
        "no_destructive_cleanup": True,
        "no_deletion": "No recursive delete of piconProv/ or piconSat/; each package adds/overwrites only its listed PNGs. Legacy files not included in safe archives remain untouched.",
        "domains": {},
        "assets": {},
    }
    for domain in DIRS:
        fallback_dir, priority_dir = DIRS[domain]
        candidate_mapping["domains"][domain] = {
            "base_fallback_directory": fallback_dir,
            "priority_directory": priority_dir,
            "lookup_priority": [priority_dir, fallback_dir],
            "variants": {},
        }
        for variant in ("transparent", "black", "white"):
            safe_archive = safe_archives[(domain, variant)]
            fallback = dict(fallback_entries[domain][variant])
            if variant == "transparent":
                legacy_archive = fallback_transparent[(domain, variant)]
                fallback.update({
                    "destination": fallback_dir,
                    "sha256": sha(legacy_archive.read_bytes()),
                    "size_bytes": legacy_archive.stat().st_size,
                    "png_count": PINS[(domain, variant)][2],
                    "url": "https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/<candidate-commit>/" + str(legacy_archive.relative_to(ROOT)).replace("\\", "/"),
                })
            else:
                fallback.update({"destination": fallback_dir, "png_count": PINS[(domain, variant)][2]})
            candidate_mapping["domains"][domain]["variants"][variant] = {
                "fallback": fallback,
                "safe_priority": {
                    "asset_id": SAFE_IDS[(domain, variant)],
                    "archive": safe_archive.name,
                    "destination": priority_dir,
                    "png_count": len(safe_by_domain[domain]),
                    "sha256": sha(safe_archive.read_bytes()),
                    "size_bytes": safe_archive.stat().st_size,
                    "url": "https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/<candidate-commit>/" + str(safe_archive.relative_to(ROOT)).replace("\\", "/"),
                    "approved_identities": sorted(safe_by_domain[domain]),
                },
                "install_order": ["legacy_fallback", "warder_safe_priority"],
            }
            if variant == "transparent":
                candidate_mapping["assets"][fallback["asset_id"]] = {
                    "filename": fallback["filename"], "size": fallback["size_bytes"],
                    "sha256": fallback["sha256"], "root": fallback_dir,
                    "url": fallback["url"], "classification": "LEGACY_FALLBACK_ONLY",
                }
            candidate_mapping["assets"][SAFE_IDS[(domain, variant)]] = {
                "filename": safe_archive.name, "size": safe_archive.stat().st_size,
                "sha256": sha(safe_archive.read_bytes()), "root": priority_dir,
                "url": "https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/<candidate-commit>/" + str(safe_archive.relative_to(ROOT)).replace("\\", "/"),
                "classification": "WARDER_SAFE_APPROVED",
            }

    # Record no deletion, no GUI size selector, and exact candidate data.
    (OUT / "archive-manifest.json").write_text(json.dumps(archive_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "candidate-downloads.json").write_text(json.dumps(candidate_mapping, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    (OUT / "lookup-coverage.json").write_text(json.dumps(coverage, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # A publication-shaped manifest of every current legacy identity plus
    # safe-source provenance, explicitly keeping approval classes separate.
    safe_names_set = {(d, n) for d, names in safe_by_domain.items() for n in names}
    current_all = {(d, n) for d, variants in current_names.items() for names in variants.values() for n in names}
    rows = []
    for domain, name in sorted(current_all | safe_names_set):
        is_safe = (domain, name) in safe_names_set
        variants = [v for v in ("transparent", "black", "white") if name in current_names[domain][v]]
        rows.append({
            "identity": ("provider-logo::" if domain == "provider" else "satellite-logo::") + name,
            "domain": domain,
            "current_legacy_variants": variants,
            "warder_safe_triads": is_safe,
            "legacy_fallback_only": not is_safe,
            "safe_priority_path": {v: f"{DIRS[domain][1]}/{name}" for v in ("transparent", "black", "white")} if is_safe else None,
        })
    (OUT / "migration-manifest.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")

    summary = {
        "status": "PASS_CANDIDATE_PREPARATION_ONLY",
        "publication": "NOT PUBLISHED",
        "test202": "NOT BUILT",
        "provider_current_identities": 1335,
        "provider_safe_identities": 172,
        "satellite_current_identities": 269,
        "satellite_safe_identities": 1,
        "legacy_runtime_coverage_preserved": True,
        "review_or_unresolved_in_safe_archives": 0,
        "safe_archive_png_counts": {"provider": 172, "satellite": 1},
        "variant_safe_archive_counts": {d: {v: len(safe_by_domain[d]) for v in ("transparent", "black", "white")} for d in DIRS},
        "legacy_fallback_counts": {d: {v: len(current_names[d][v]) for v in ("transparent", "black", "white")} for d in DIRS},
        "coverage_by_variant": coverage,
        "safe_tree_qc": qc,
        "no_destructive_fallback": True,
        "no_consumer_lookup_change": True,
        "candidate_mapping_is_runtime_consumable": False,
        "runtime_gap": "Current auxiliary downloader resolves one catalog asset ID per GUI selection; TEST202 must add an explicit two-stage fallback-then-safe composite executor before using this candidate mapping.",
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
