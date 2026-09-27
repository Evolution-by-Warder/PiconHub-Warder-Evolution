# Phase 4 — Achromatic Tonal-field / Stroke Continuity Diagnostic

**Date:** 2026-09-27  
**Scope:** classification/reconstruction diagnostic only; no recolor, candidate PNG, source, master, or production picon was written.

## Method and frozen classes

The V9 solid achromatic core remains alpha ≥32 and RGB channel spread ≤18. The chromatic core, confirmed chromatic AA, and ambiguous chromatic boundary are reused unchanged from the completed AA-boundary experiment. A solid visible pixel with spread >18 is already in the frozen chromatic core; tonal continuity cannot promote it. Comparative local luminance/RGB evidence is inspected only for visible subthreshold pixels outside every frozen protected class, and is never an edit mask. Proposed grouping reuses the previous 8% material-fraction anchor and median-anchor-height gap rule. Two-tone and exterior guards remain enabled.

## Results

| Case | Core components 4/8 | Median W×H (8) | 1×1 (4/8) | Outside-core visible / frozen chroma+AA+ambiguous | Tonal candidates | Reconstructed 8-connectivity | Groups | Editable / changed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| #14607 | 58/52 | 1.0×1.0 | 37/29 | 3873 / 3322 | 0 | 52→52 | 39 | 0 / 0 |
| #14700 | 19/18 | 4.5×8.5 | 9/9 | 2192 / 1136 | 154 | 18→14 | 1 | 0 / 0 |
| #14593 | 14/14 | 11.5×14.0 | 4/4 | 4310 / 2699 | 51 | 14→14 | 1 | 0 / 0 |
| #14597 | 224/214 | 1.0×1.0 | 186/169 | 5831 / 4986 | 0 | 214→214 | 138 | 0 / 0 |
| PASS-control | 0/0 | 0.0×0.0 | 0/0 | 7757 / 7757 | 0 | 0→0 | 0 | 0 / 0 |

## #14607 / #14611: gap-pixel answer

The byte-identical #14607/#14611 source pair was calculated once; #14611 was checked against the same source and CURRENT WHITE SHA256 values. #14607 has 29 one-pixel 8-connected achromatic core fragments. Across all visible outside-core pixels, the exclusive partition is `{"protected_chromatic_core": 2595, "confirmed_true_chromatic_AA": 4, "ambiguous_chromatic_boundary": 723, "alpha_below_32": 551, "channel_spread_over_18": 0, "safe_tonal_candidate": 0, "other_unclassified": 0}`. In the immediate 8-neighborhood around singleton fragments (197 pixels), the exclusive partition is `{"protected_chromatic_core": 163, "confirmed_true_chromatic_AA": 0, "ambiguous_chromatic_boundary": 28, "alpha_below_32": 6, "channel_spread_over_18": 0, "safe_tonal_candidate": 0, "other_unclassified": 0}`. Separately, spread >18 occurs in 172 of those nearby pixels; every one is already frozen as chromatic core. The pixel-level CSV records RGBA, spread, linear luminance, alpha, nearest RGB distances/coordinates to achromatic and chromatic cores, frozen class, reason, and visible 8-neighbor context.

This answers the main question: the immediate gaps are predominantly frozen chromatic-core or ambiguous-boundary pixels (163 + 28), not safely identifiable achromatic tonal stroke. The remaining six visible near-fragment pixels are alpha-subthreshold and fail local stroke support; none was accepted. Solid pixels with spread >18 cannot be relabeled as tonal under the frozen V9 partition. Reconstruction therefore did not add a pixel, reduce 52 8-connected components, or improve the 39 proposed groups; median geometry remains 1×1. This does not establish that every excluded pixel is perceptually chromatic; it establishes that promotion is unsafe under the frozen classes and measured local evidence.

## Controls and safety

#14700 remains one wordmark group after 154 locally supported subthreshold tonal candidates attach; group-level two-tone remains true and recolor stays blocked. #14593 remains one incomplete group with two-tone and chroma/true-AA/ambiguous contacts; its 51 diagnostic attachments do not reduce the 8-connected component count. #14597 produced no tonal candidates and remains a cautious probe. Digi Slovakia PASS has zero tonal candidates, zero editable pixels, and zero candidate/current changes. Every case preserves alpha and all frozen classes; new tonal pixels have zero intersection with protected masks. No recolor candidate was generated.

## Visual outputs

The seven-panel diagnostic sheets and the #14607 automatically sampled singleton-fragment zoom pages are supplied with this result. The detailed #14607 gap-pixel inventory is `14607-GAP-PIXELS.csv`.

## Conclusion

**TONAL-STROKE RECONSTRUCTION NOT PROVEN FOR #14607 / RECOLOR NOT TESTED.** Near-fragment pixels are predominantly chromatic-core or ambiguous; the small alpha-subthreshold remainder has no demonstrated stroke continuity. The #14607 fragmentation remains unexplained by this tonal-field path. #14700 shows local tonal attachment can improve the diagnostic glyph representation, but its two-tone guard still blocks recolor. No production changes were made.
