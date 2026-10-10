"""Read-only real PNG collision test and evidence pack for Warder Factory.

Run with the Python environment used by Factory:
python live_png_test.py "D:\\WARDER-PICON-FACTORY\\08-REPORTS\\identity-collisions-<run>.json"
Writes exactly one ZIP beside the input report; never edits PNG or registry.
"""
import argparse
import hashlib
import io
import json
import re
from collections import Counter
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image

HEX = re.compile(r"^[a-fA-F0-9]{64}$")


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _pixel_signature(data):
    with Image.open(io.BytesIO(data)) as image:
        image.load()
        rgba = image.convert("RGBA")
        return {
            "size": list(rgba.size),
            "rgba_sha256": _sha(rgba.tobytes()),
            "mode": image.mode,
        }


def _origin(path):
    parts = str(path).replace("\\", "/").casefold().split("/source-ingest/originals/")
    return parts[1].split("/", 1)[0] if len(parts) == 2 else "unknown"


def build_live_test(report_path, output_path=None, limit=10):
    report_path = Path(report_path).resolve()
    report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    if not isinstance(report.get("collisions"), list):
        raise ValueError("Not an identity-collisions report")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    output_path = Path(output_path) if output_path else report_path.parent / "warder-live-png-test.zip"
    output_path = output_path.resolve()
    if output_path == report_path:
        raise ValueError("Output must not overwrite input")
    selected = []
    for collision in report["collisions"]:
        variants = collision.get("variants") or []
        origins = {_origin(p) for v in variants for p in v.get("sources", [])}
        if "openatv8" in origins and "vhannibal" in origins:
            selected.append(collision)
            if len(selected) >= limit:
                break
    if not selected:
        raise ValueError("No mixed OpenATV/Vhannibal collisions")
    results = []
    with ZipFile(output_path, "w", ZIP_DEFLATED) as out:
        for index, collision in enumerate(selected, 1):
            item = {"service_reference": collision.get("candidate_service_ref"),
                    "variants": [], "pixel_result": "UNDETERMINED"}
            for variant_index, variant in enumerate(collision.get("variants", []), 1):
                expected = str(variant.get("sha256") or "").lower()
                entry = {"expected_sha256": expected, "sources": [], "status": "MISSING"}
                for source in variant.get("sources") or []:
                    path = Path(source)
                    record = {"origin": _origin(source), "path": str(path)}
                    if not path.is_file():
                        record["status"] = "MISSING"
                    elif not HEX.fullmatch(expected):
                        record["status"] = "INVALID_EXPECTED_SHA"
                    else:
                        try:
                            data = path.read_bytes()
                            actual = _sha(data)
                            record["actual_sha256"] = actual
                            if actual != expected:
                                record["status"] = "SHA_MISMATCH"
                            else:
                                pixel = _pixel_signature(data)
                                record.update(pixel)
                                record["status"] = "VERIFIED"
                                archive_name = f"cases/{index:02d}/variant-{variant_index:02d}-{actual[:16]}.png"
                                out.writestr(archive_name, data)
                                record["archive_path"] = archive_name
                        except (OSError, ValueError, SyntaxError) as exc:
                            record["status"] = "DECODE_OR_READ_ERROR"
                            record["error_type"] = type(exc).__name__
                    entry["sources"].append(record)
                if entry["sources"] and all(s["status"] == "VERIFIED" for s in entry["sources"]):
                    entry["status"] = "VERIFIED"
                else:
                    entry["status"] = "INCOMPLETE"
                item["variants"].append(entry)
            verified = [s for v in item["variants"] for s in v["sources"] if s["status"] == "VERIFIED"]
            if len(verified) >= 2 and all(v["status"] == "VERIFIED" for v in item["variants"]):
                signatures = {(tuple(s["size"]), s["rgba_sha256"]) for s in verified}
                item["pixel_result"] = "PIXEL_IDENTICAL" if len(signatures) == 1 else "PIXEL_DIFFERENT"
            results.append(item)
        summary = dict(Counter(item["pixel_result"] for item in results))
        out.writestr("live-test-results.json", json.dumps({
            "schema": 1, "source_report": report_path.name,
            "cases": results, "summary": summary,
            "policy": "READ_ONLY; PIXEL_MATCH_IS_NOT_IDENTITY_APPROVAL; NO_REGISTRY_WRITES",
        }, indent=2, ensure_ascii=False))
    return {"output": str(output_path), "cases": len(results), "summary": summary}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("identity_collisions_report")
    parser.add_argument("--output")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(build_live_test(args.identity_collisions_report, args.output, args.limit),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
