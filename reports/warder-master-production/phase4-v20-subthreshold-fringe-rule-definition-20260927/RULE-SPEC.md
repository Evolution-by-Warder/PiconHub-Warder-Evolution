# Proposed structural subthreshold-fringe rule — diagnostic only

**Disposition: NOT ADOPTED.** The tested strict profile rule is conservative but the current evidence does not establish a reliable general gate. No production algorithm or threshold is defined.

## Proposed predicate tested (derived without #14700)

For each pixel in the untouched `0 < alpha < 32` perimeter, find direct confirmed core support, trace the outward 8-neighbor normal through source-visible pixels to the first `alpha = 0` location, and measure the exact straight-alpha composite on the actual WHITE MASTER. Require every linear Rec.709 luminance sample to be nondecreasing from the recolored core to the MASTER. Any reversal or untraceable ray returns REVIEW. The proposed profile test contains no numeric cutoff and does not assign ownership to any untouched pixel.

The predicate was frozen using the exact Class P controls before evaluating #14700. `Was #14700 used to derive this condition? NO.` The rule does not use M1 or the 40 one-hop pixels.

## Why not adopted

All five Class P controls fail this strict predicate: each has at least 198 reversal profiles; MEGA and CNBC also have many untraceable rays. Thus exact monotonicity rejects ordinary safe-control AA and supplies no useful acceptance region. Synthetic A/B/C all return REVIEW, but B's isolated perturbation does not change its profile reversal count from the unmodified baseline (546); the gate is responding to the control's background profile behavior rather than detecting that isolated defect. The test is therefore conservative but non-discriminating.

Master texture and one-pixel raster changes can create local reversals, while a smooth bright ring can remain monotonic when its endpoint is the MASTER. Relaxing the zero-reversal rule to ignore isolated pixels or permit a connected arc requires a threshold. Reusing `MATERIAL_FRACTION = 0.08` as a perimeter allowance is not supported by the source rule's original meaning (fraction of contrast-relevant material), so it is not repurposed here. The evidence does not support a defensible general structural fringe gate.

## Pipeline ordering

1. Complete contrast-relevant wordmark/group confirmed.
2. Exterior MASTER context confirmed.
3. No protected chromatic-core intersection.
4. No protected true chromatic-AA intersection.
5. No ambiguous protected-boundary intersection.
6. No blocked grouping links.
7. Topology-aware two-tone is false with sufficient interior evidence.
8. Independently confirmed edit mask is safe and complete for contrast-relevant material.
9. Identify the remaining visible `alpha < 32` perimeter; keep it out of the edit mask.
10. Evaluate structural fringe/completeness.
11. Only after all prior gates pass may an experimental AUTO-FIX candidate be considered. Any earlier failure stops the pipeline; fringe cannot override it.

## #14700 protected/other pixel

The prior ownership audit labels one pixel `PROTECTED / OTHER` because its channel spread exceeds the frozen achromatic limit; it is not proven to belong to the wordmark. That audit also explicitly reports zero low-alpha perimeter pixels adjacent to frozen protected masks. Thus this pixel is unowned/unresolved, not a confirmed protected chroma/AA/boundary-mask intersection. It remains untouched; the rule does not promote it to ownership. This distinction does not itself prove visual completeness.

## Counterexamples

A is an algorithmically generated bright perimeter band over AB1's real fitted mask; B is one deterministic singleton perimeter perturbation; C is a largest proper 8-connected partial perimeter segment. The synthetic output uses RGB 224 on the selected edge pixels, preserves output alpha and geometry, and never changes a production picon.

## Frozen parameters

`OPAQUE_ALPHA=32`, `ACHROMATIC_DELTA=18`, ownership raw RGB distance 18, `ACHROMATIC_REQUIRED=0.985`, contrast ratio 2.50, `MATERIAL_FRACTION=0.08`, `TWO_TONE_FRACTION=0.03`, WHITE target `(16,16,16)`, topology-aware two-tone definition and all protection/grouping rules remain unchanged.
