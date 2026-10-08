#!/usr/bin/env python3
"""Clean-checkout end-to-end regression for the auxiliary-only ingress CLI."""
from __future__ import annotations
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="warder-aux-ingress-") as tmp:
    report_path = Path(tmp) / "ingress.json"
    run = subprocess.run([sys.executable, str(ROOT / "tools/auxiliary_ingress.py"),
                          "--report", str(report_path)], cwd=ROOT, text=True,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if run.returncode != 0:
        raise SystemExit(f"auxiliary ingress CLI failed ({run.returncode}):\n{run.stdout}\n{run.stderr}")
    report = json.loads(report_path.read_text())
    assert (report["identities"], report["provider"], report["satellite"], report["candidate_pngs"]) == (173, 172, 1, 346)
    assert (report["pass"], report["review"], report["fail"]) == (173, 0, 0)
    assert report["transparent_sources_unchanged"] is True
    assert report["legacy_fallback_touched"] is False
    assert report["digest_bound_approval_records"] == 18
    assert report["raw_review_variants"] == 16
    assert report["review_variants_approved"] == 16
    variants = [v for row in report["results"] for v in row["variants"].values()]
    assert len(variants) == 346
    assert all(v["pixel_equivalent"] for v in variants)
    assert all(v["visual_approval_applied_to_review"] for row in report["results"]
               for v in row["variants"].values() if v["engine_status"] == "REVIEW")
    odesa = next(row for row in report["results"] if row["identity"] == "provider-logo::ODESA LAYV.png")["variants"]["white"]
    assert odesa["pixel_equivalent"] and not odesa["pixel_exact"]
    assert odesa["visual_approval_applied_to_review"]
    assert sum(v["pixel_exact"] for v in variants) == 332
    assert sum(v["pixel_equivalent"] and not v["pixel_exact"] for v in variants) == 14
print(json.dumps({"actual_auxiliary_ingress_cli": "PASS", "identities": 173,
                  "provider": 172, "satellite": 1, "candidate_pngs": 346,
                  "pass": 173, "review": 0, "fail": 0,
                  "digest_bound_approvals": "16 active REVIEW variants approved; 2 records not needed by PASS variants",
                  "pixel_exact": 332,
                  "bounded_aa_equivalent": 14}, sort_keys=True))
