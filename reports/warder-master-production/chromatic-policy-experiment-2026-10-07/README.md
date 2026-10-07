# Auxiliary isolated-chromatic policy experiment

Input: accepted diagnostic checkpoint `17dfbd0a23d4a6073aed9ab5846a3fd45e3d35c4`.
Scope: the saved 903 engine-review families only. The 320 source-unresolved families are excluded.

This is an evidence-only experiment. It does not change the production renderer, its thresholds, templates, outputs, or prior PASS/REVIEW decisions. No new experimental PNG was generated because none of the saved component records provides pixel-mask/contour evidence sufficient to prove that an isolated chromatic component is a simple glyph-like wordmark rather than a brand symbol. Bbox and mask hashes establish location and identity, not shape semantics. No OCR, filename inference, or internet matching was used.

The mandatory HARMONIC sentinel remains AMBIGUOUS CHROMATIC. See `harmonic-decision.json` and `reduced-review-sheet.png`. The current black and white review panels were reconstructed from the exact source and unchanged engine, then PNG SHA256 checked against the accepted checkpoint's saved candidate hashes.

Files:
- `component-eligibility.jsonl.gz`: empty strong-candidate set.
- `component-rejections.jsonl.gz`: every low-contrast chromatic/two-tone component and its exact exclusion reason.
- `family-experiment-summary.jsonl.gz`: one record for each of the 903 families.
- `summary.json`: totals and scope.
- `harmonic-decision.json`: sentinel evidence and decision.
- `review-sheet-manifest.json`, `reduced-review-sheet.png`: one-family representative sheet; experimental panels say NOT GENERATED because no strong candidate passed.

No production policy was promoted. No assets were published. TEST202 was not built.
