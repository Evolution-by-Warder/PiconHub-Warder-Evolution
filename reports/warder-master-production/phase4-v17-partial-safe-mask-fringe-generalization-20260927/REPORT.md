# Partial safe mask + untouched subthreshold fringe — generalization study

**Result: B — GENERALIZATION PLAUSIBLE, RULE NOT YET DEFINED.** This is descriptive evidence only; #14700 remains diagnostic REVIEW. No gate/threshold/ownership rule or production candidate was created.

## Selection

Phase 3 audit contained 9041 rows; 223 unique source hashes met the frozen AUTO-FIXED/BLACK PASS/WHITE AUTO-FIXED criteria after excluding review-index assets, Digi Slovakia, and two-tone reasons. The pool was sorted by SHA256(`fringe-generalization|source_sha256`). The 160 ranked records were screened using the complete-wordmark grouping guard. For source fixtures absent from the small local fixture, the prior deterministic grouping-screen JSON was cross-checked by rank, exact source path and SHA256; selected fixtures were rerun with the helper. The first five distinct, visibly textual wordmarks with complete groups were chosen before any fringe measurements. Rank 4 was excluded after visual identity review because it is a standalone numeral rather than a textual wordmark. No selection used fringe outcomes.

| Class P wordmark | Rank | V9 selected components | confirmed alpha≥32 | subthreshold perimeter | group complete | confirmed-mask contacts | current WHITE=V9 full render |
|---|---:|---:|---:|---:|---|---|---|
| AB1 | 23 | 4 | 9779 | 715 | yes | no chroma/protected group blocker | yes |
| MEGA | 35 | 1 | 3624 | 620 | yes | no chroma/protected group blocker | yes |
| CNBC | 39 | 15 | 6031 | 976 | yes | no chroma/protected group blocker | yes |
| MTA3 | 72 | 2 | 6972 | 328 | yes | no chroma/protected group blocker | yes |
| Настоящее время | 139 | 4 | 4598 | 520 | yes | no chroma/protected group blocker | yes |

## Class P measurements

`FULL-AA` is the unchanged CURRENT WHITE output, verified pixel-identical to frozen V9 WHITE generation. `TRUNCATED-SAFE` starts from the same source/master and recolors only the same V9-selected alpha-connected components at alpha≥32; source RGB is retained for alpha 1–31. No candidate is written to production. Luminance deltas use inverse sRGB transfer followed by linear Rec.709 scaled 0–255. 8-connectivity is used only to describe clusters.

| Wordmark | Perimeter | changed pixels | ΔL∞ median / p95 / max | luminance mean / max | diff components / largest | structural pixels / fraction | structural largest / longest |
|---|---:|---:|---:|---:|---:|---:|---:|
| AB1 | 715 | 715 | 11.000 / 28.000 / 29.000 | 19.369 / 49.341 | 253 / 74 | 518 / 72.4% | 74 / 73 |
| MEGA | 620 | 587 | 2.000 / 17.050 / 26.000 | 5.691 / 41.987 | 43 / 115 | 114 / 18.4% | 15 / 15 |
| CNBC | 976 | 976 | 3.000 / 24.000 / 30.000 | 8.442 / 57.836 | 79 / 110 | 286 / 29.3% | 16 / 16 |
| MTA3 | 328 | 328 | 9.000 / 26.000 / 30.000 | 17.814 / 53.549 | 180 / 11 | 267 / 81.4% | 8 / 7 |
| Настоящее время | 520 | 520 | 12.000 / 26.000 / 30.000 | 20.477 / 57.571 | 210 / 19 | 453 / 87.1% | 19 / 19 |

Normalized largest structural component, structural fraction, and longest structural segment by perimeter pixel count are recorded in `AUDIT.csv` and `SUMMARY.json`. The denominator is explicitly a perimeter-pixel proxy, not a geometric contour length. Per-V9-component results are in `SUMMARY.json`; the component IDs are topology IDs, not OCR glyph labels.

## #14700 query comparison

#14700 frozen ownership remains 40 SAFE one-hop, 259 AMBIGUOUS, 1 PROTECTED/OTHER across the 300-pixel perimeter; these labels and masks were not changed. M0: 269/300 perimeter pixels differ from the prior full-AA reference; ΔL∞ median 1, p95 5, max 8; difference components 64, largest 27 px. Structural indicator: 48/300 pixels (16%), 36 components, largest/longest 3 px (1% of perimeter proxy). Across all seven compared features, #14700 is below the observed minimum of the five Class P controls. This is a lower-side outlier: ΔL∞ mean/median/p95/max are 1.86/1/5/8, versus positive-control minima 3.60/2/17.05/26; its structural indicator is 48/300 (16%), versus 18.4–87.1%, with largest/longest connected flagged segment 3 px, versus control longest segments 7–73 px. The indicator is a local luminance-extremum proxy, not a validated halo detector. These measurements describe smaller and more fragmented truncation differences in #14700, not a pass cutoff.

The contact sheets show no obvious continuous bright ring in the five Class P control truncations or in #14700 M0; the visible differences are mainly sparse edge pixels, while #14700's longest flagged segment is only 3 pixels. The controls nevertheless have larger raw metric values, so #14700 is not numerically representative. Taken together, the evidence makes generalization plausible only as a research direction: it does not establish a decision boundary or a production rule. No threshold was fitted.

## Controls

- **Class N:** #14607/#14611 remain blocked by protected chroma/AA/ambiguous boundaries and incomplete grouping; #14593 remains incomplete with 14 blocked links, protected contacts and frozen two-tone; #14597 remains cautious with no target; #10954 remains blocked at protected boundary; #5136 remains REVIEW after a protected-boundary rejection and no complete/new visible repair. No unsafe recolor or fringe simulation was run for these cases. Since the prerequisite safe complete mask is absent, a fringe score is undefined and cannot override any blocker.
- **Class T:** both genuine two-tone controls were reevaluated by the frozen topology-aware interior test. Each retains `two-tone=true`; neither receives a candidate.
- **Digi Slovakia:** PASS control regenerated identically to CURRENT WHITE; 0 changed pixels and no target.

## Leave-one-out sanity check

For each Class P item, the remaining four controls' observed min–max ranges and the held-out value are recorded in `SUMMARY.json`. This is descriptive range checking only. Leave-one-out results show whether any single control determines the span; they do not train or define a threshold.

## Invariants and decision

All selected source hashes match Phase 3 audit; each CURRENT WHITE image equals a fresh frozen V9 full-AA render; source-layer alpha is unchanged; truncated edits are restricted to selected components at alpha≥32; confirmed high-alpha masks have zero frozen-protection contact. Historical V9 full-AA references have zero chroma-core and true-AA contact; their low-alpha ambiguous overlap is separately reported because it is the subject of this simulation, not treated as new ownership evidence. No production picon, transparent source, MASTER, plugin, or skin was written. #14599 was not accessed. Conclusion: **GENERALIZATION PLAUSIBLE, RULE NOT YET DEFINED**. #14700 is a low-difference outlier relative to the five controls and remains DIAGNOSTIC REVIEW. Negative controls were not recolored or scored; their frozen independent blockers remain prior and cannot be superseded by a fringe metric.

## Contact sheets

- Class P zoom and 1:1 sheets: `diagnostics/P-*-FULL-TRUNCATED-DIFF-*.jpg`.
- #14700 current/M0/full-reference/difference sheets: `diagnostics/14700-CURRENT-M0-FULL-REFERENCE-DIFF-*.jpg`.
- Genuine two-tone controls: `diagnostics/T-*-TWO-TONE-CONTROL.jpg`.
