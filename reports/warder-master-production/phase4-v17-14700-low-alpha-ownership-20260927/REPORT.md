# Phase 4 — #14700 low-alpha perimeter ownership / AA attribution

**Result: `PARTIAL SAFE OWNERSHIP / COMPLETE MASK = REVIEW`.** The one-hop test proves ownership for only part of the subthreshold perimeter. The complete edit mask remains unresolved; no candidate or edit mask was generated.

## Scope and method

The prior final-gate source and CURRENT WHITE hashes were revalidated. The fixed confirmed wordmark contains 1224 pixels and uses existing glyph component IDs `[6, 7, 8, 9, 10]`. The perimeter is the 300 visible pixels with `0 < alpha < 32` in the eight-neighbor exterior ring of that unchanged wordmark.

The earlier frozen core-only tonal classifier remains unchanged and is recorded separately: 95 perimeter pixels had no local solid-core stroke support, 205 were classified tonal-discontinuous, and none were accepted. This diagnostic then tested one non-propagating local attribution step using only already-confirmed group pixels. To pass, a pixel had to touch exactly one pre-confirmed glyph; have support from an already-confirmed safe tonal attachment; satisfy frozen V9 channel spread ≤18 and RGB max-channel distance ≤18; show alpha attenuation versus directly adjacent confirmed material; continue luminance within the median existing core-edge step; and have no protected pixel or protected 8-neighbor. Newly classified pixels were never used as support for another pixel. No output/edit mask was created.

The existing local luminance step was measured between the directly adjacent pre-confirmed tonal attachment and its neighboring frozen solid core. It is not a newly selected threshold. No geometry, dilation/closing, coordinate rule, per-logo setting, or protection class changed.

## Ownership results

- Perimeter: **300 px**.
- Safe one-hop ownership: **40 px**.
- Ambiguous: **259 px**.
- Protected/other: **1 px**.
- Complete ownership: **NO**.

Exclusive reasons:

- local RGB continuity to preconfirmed wordmark fails frozen max-channel distance 18: **252 px**
- one-hop attachment to already-confirmed safe wordmark AA; frozen RGB/luma/alpha evidence passes; no chaining: **40 px**
- alpha does not attenuate away from direct confirmed support: **6 px**
- multiple directly adjacent confirmed glyph owners: **1 px**
- channel spread exceeds frozen V9 achromatic limit at subthreshold alpha; chromatic ownership is not proven, so REVIEW: **1 px**

All 40 safe pixels are directly adjacent to a previously accepted safe tonal attachment, pass frozen RGB continuity and local luminance/alpha checks, and have a unique directly adjacent glyph owner. Safe pixels by glyph ID are 6: 11, 8: 3, 9: 6, 10: 20, 7: 0. There is no propagation through newly accepted pixels. The remaining 252 RGB-discontinuous pixels fail the frozen local max-channel limit; 6 do not attenuate in alpha away from confirmed material; one has multiple directly adjacent glyph owners; and one has channel spread above V9's achromatic limit. No perimeter pixel is adjacent to the frozen protected masks.

### Per-glyph perimeter adjacency

Counts are by direct adjacency to the fixed confirmed glyph group, not ownership assignments. A pixel touching multiple glyphs is counted against each adjacent glyph.

| Glyph component ID | Ambiguous | Protected/other | Safe |
|---:|---:|---:|---:|
| 6 | 31 | 0 | 11 |
| 7 | 48 | 0 | 0 |
| 8 | 48 | 1 | 3 |
| 9 | 39 | 0 | 6 |
| 10 | 94 | 0 | 20 |

## Negative and stability controls

#14607 remains the frozen negative control: the one-step singleton-fragment scope contains 6 visible alpha<32 pixels and safe ownership remains **0**. All six are next to frozen protected chromatic/AA/ambiguous material and remain rejected. #14611 source and CURRENT WHITE bytes are identical to #14607; the duplicate regression reuses that result.

#14593 remains REVIEW (incomplete group, protected contacts, 14 blocked links); #14597 remains cautious REVIEW with no target; Digi Slovakia remains PASS with **0 changed pixels**. Both genuine two-tone positive controls remain topology-aware `two-tone=true` and have no candidate.

## Gate and outcome

The partial one-hop evidence does not establish ownership of the complete 300-pixel perimeter. Therefore the completeness gate fails and the requested second final safety gate was not run. Candidate = none; editable pixels = 0; changed pixels = 0. Source, CURRENT WHITE, MASTER, protected masks, and production picons are unchanged. No frozen ownership, alpha, chromatic protection, or two-tone rule was weakened.

## Visual diagnostics

`diagnostics/14700-low-alpha-ownership.jpg` shows the full source-derived logo, fixed confirmed wordmark, perimeter, safe subset, ambiguous pixels, and the one outlier. `diagnostics/14700-low-alpha-ownership-zoom.jpg` enlarges the same attribution classes across the wordmark. `14700-LOW-ALPHA-PIXELS.csv` contains 300 source-coordinate mapped pixel records; `14607-LOW-ALPHA-NEGATIVE-CONTROL.csv` contains the negative-control records.
