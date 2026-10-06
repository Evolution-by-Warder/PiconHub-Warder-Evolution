# Auxiliary Warder ingress review run — 2026-10-06

Status: review checkpoint only; not production approval.

The run uses stable auxiliary keys `provider-logo::<filename>` and `satellite-logo::<filename>`. It does not create channel service references or change channel identity paths. Native 220×132 auxiliary canvases preserve their full source bytes and placement; `fit_logo` is not applied to those. Source QC checks reuse `source_qc_recovery.rectangular_background_signals`; rendering calls unchanged `rebuild_master_catalog.classify_and_render` with the immutable templates.

To reproduce, provide the six source ZIPs named in `input-provenance.json`, then run:

```sh
python3 tools/auxiliary_ingress.py \
  --input-dir /path/to/six-auxiliary-zips \
  --engine-dir . \
  --output-dir /path/to/output
```

The complete per-identity/per-variant report is split into `machine-report-*.jsonl` parts; concatenate them in lexical order to reconstruct `machine-report.jsonl`; `summary.json` gives counts; `review-manifest.json` lists only REVIEW/HOLD/FAIL/source-unresolved items. Candidate PNGs are committed byte-for-byte inside `candidate-output.zip`; segmented archive parts and SHA256 are listed in `remote-artifact-manifest.json`. Review sheets are PNGs in `review-sheets.zip`, also segmented and hashed there.

The 390 identities without transparent source remain SOURCE-UNRESOLVED. No legacy Black/White file was used to infer alpha. HARMONIC Black is REVIEW under the native renderer. HELLASAT 300W transparent output is byte-identical to its native source canvas, so geometry remains unchanged.
