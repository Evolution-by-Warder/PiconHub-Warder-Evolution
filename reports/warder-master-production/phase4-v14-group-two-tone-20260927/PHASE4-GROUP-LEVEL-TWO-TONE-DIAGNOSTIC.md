# Phase 4 — Group-level Two-tone Diagnostic

**Scope:** frozen-guard audit; no recolor, threshold changes, candidates, or production writes.

## Frozen implementation

The source is `tools/phase4_achromatic_glyph_aa_diagnostic.py`, function `group_components`. It computes sRGB linear relative luminance and scales it to 0–255. Dark means ≤64; light means ≥192; both populations must each occupy at least 3% of the measured mask. Aggregation is once per complete group, not per glyph. The group connectivity mask contains reconstructed solid core plus tonal attachments, but the two-tone measure uses the original solid achromatic core mask from every group member. It samples raw source RGB without alpha compositing. Thus alpha≥32 achromatic edge/AA samples remain in the measurement, even at partial alpha; diagnostic tonal attachments below alpha 32 are excluded. MASTER/background pixels are not blended into this calculation. MASTER participates in contrast-ratio comparison separately. The code does not explicitly subtract protected pixels from that core measure; protected contacts are measured separately by the group boundary guard.

## #14700 result

**Diagnostic category: C. EDGE/AA-DRIVEN TWO-TONE.** Current frozen guard: two-tone `True`. Group comprises 5 reconstructed glyph components, 1224 total core+attachment pixels, of which 1070 original solid-core pixels enter the guard and 154 tonal attachments are excluded from the two-tone population. Dark=222 (20.75%); light=429 (40.09%). Core-only reproduces current result: `True`. High-alpha (alpha≥192) result: `False`; 8-neighbor interior-only: `False`; core-edge-only: `True`; attachments-only: `False`; core-edge plus attachments: `True`.

Per-glyph guard results: `{"6": {"pixels": 128, "median": 174.19406127929688, "p05": 26.891996383666992, "p95": 255.0, "dark_fraction": 0.265625, "light_fraction": 0.390625, "two_tone": true}, "7": {"pixels": 155, "median": 170.44117736816406, "p05": 8.083791732788086, "p95": 255.0, "dark_fraction": 0.23225806451612904, "light_fraction": 0.44516129032258067, "two_tone": true}, "8": {"pixels": 154, "median": 156.54295349121094, "p05": 18.199262619018555, "p95": 255.0, "dark_fraction": 0.23376623376623376, "light_fraction": 0.38961038961038963, "two_tone": true}, "9": {"pixels": 121, "median": 175.1047821044922, "p05": 20.456056594848633, "p95": 255.0, "dark_fraction": 0.23140495867768596, "light_fraction": 0.3884297520661157, "two_tone": true}, "10": {"pixels": 512, "median": 157.57077026367188, "p05": 19.064172744750977, "p95": 255.0, "dark_fraction": 0.171875, "light_fraction": 0.396484375, "two_tone": true}}`. All five glyph cores individually return two-tone, but each glyph's 8-neighbor interior-only result is false and its edge-only result is true. Thus this is not a cross-glyph median-luminance split: the dark and light populations coexist at each glyph's edge. The topological group is complete, exterior context is proven, and the group has no chroma, confirmed-AA, or ambiguous-boundary contact; the complete-wordmark guard remains REVIEW because two-tone and low-alpha perimeter guards remain active.

All 222 dark guard pixels are on the achromatic core edge (0 in the eroded interior), distributed across all five glyphs and 71 connected dark regions; none lies within one pixel of protected chroma/AA/boundary. Their alpha distribution is 77 pixels at alpha 32–63, 144 at 64–127, and 1 at 128–191. With the source alpha composited over the WHITE MASTER, dark pixels fall from 222 to 0 and the two-tone result becomes false; the CURRENT WHITE render gives the same 0 dark pixels. The 8-neighbor interior contains 307 pixels and all are in the light bucket. This points to raw RGB values in partially transparent edge samples, not a dark interior stroke. These alternative measurements are diagnostic only and do not replace the guard. Spatial, alpha-bucket, luminance, protected-distance, and per-pixel records are in `SUMMARY.json` and `14700-GROUP-PIXELS.csv`.

## Controls and safety

#14607/#14611 are frozen negative controls; no reconstruction or mask changes are made here. #14593 is read as an incomplete-group diagnostic reference only. #14597 remains a cautious no-target probe. Digi Slovakia retains 0 changes and no target. Source/current SHA values are preserved, `editable_pixels=0`, and `candidate_vs_current_changed_pixels=0`.

## Conclusion

The evidence supports **C. EDGE/AA-DRIVEN TWO-TONE**. The frozen guard remains unchanged, including its two-tone result. No repair or guard bypass was attempted.
