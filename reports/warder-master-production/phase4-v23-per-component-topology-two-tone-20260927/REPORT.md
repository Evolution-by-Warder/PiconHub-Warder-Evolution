# V23 — Per-component topology-aware two-tone replay

**Branch:** `phase4-v10-component-mask-test`  
**Starting HEAD:** `abf3d3fdc59705152dcfb017f200d4dfa7bec8c2`  
**Frozen V9 code:** Phase 3 checkpoint `e9b503d76eae3c3c7d7763df4909039a55d3edb8`  
**Topology-aware rule:** `5a42e95ac6978f66d1f52d834fe3b40c53e93992`  
**Result: A — ALL THREE ARE EDGE/AA FALSE POSITIVES**

## Finding

Frozen V9 components **4, 12, and 13** each remain unchanged as `alpha > 0`, eight-connected components. Their V9 material sample is exactly `component & (alpha >=32)`. All three are achromatic and frozen V9 marks each `two-tone=true` because the sample includes dark pixels at partial alpha along the component/material edge.

Applying the exact topology-aware interior function from the cited experiment to each same component’s solid material gives **sufficient evidence in all three**, with **zero dark and zero intermediate pixels** in every interior. Every interior pixel is in the light bucket. Therefore each result changes from frozen `two-tone=true` to topology-aware `not-two-tone`. The two genuine two-tone controls remain `two-tone=true` with sufficient interior evidence.

This isolates the historical V9 blocker as edge/AA-driven for all three components. It does **not** make #14700 a PASS or authorize recolor.

## Frozen identities and exact rule replay

V22’s exact Phase 3 fit and component assignment were loaded and independently asserted: source fitted by pinned `fit_logo`, `visible = alpha > 0`, eight-connected labels; all 1,224 M0 pixels remain in labels `[4,12,13]` with counts 488/155/581. V23 did not relabel, join, split, erode, dilate, or otherwise change component membership. Erosion is applied only to the same `alpha >=32` material sample as the diagnostic interior test; it does not define component identity or an edit mask.

The topology rule was read from the exact V15 script, not recreated from recollection. In that script, lines 65–77 define:

- `interior = material & binary_erosion(material, structure=EIGHT, border_value=0)`;
- luminance from the pinned glyph module’s linear-sRGB Rec.709 function, scaled to 0–255;
- dark `<=64`, light `>=192`, each at least `0.03` of the tested material;
- enough evidence only when interior is nonempty and contains at least `0.08` of the largest eight-connected component in the material mask; otherwise `INSUFFICIENT_INTERIOR_EVIDENCE`.

The frozen V9 parameters were asserted unchanged: `OPAQUE_ALPHA=32`, `ACHROMATIC_DELTA=18`, `ACHROMATIC_REQUIRED=0.985`, contrast ratio `2.50`, `MATERIAL_FRACTION=0.08`, and `TWO_TONE_FRACTION=0.03`. No ownership or fringe classifier was run.

## Per-component results

| Frozen V9 component | Visible / M0 / known perimeter px | Solid px | Frozen dark | Frozen light | Frozen intermediate | Frozen result | Interior px (fraction of solid) | Interior dark / light / intermediate | Evidence floor | Topology result |
|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---|
| 4 | 814 / 488 / 144 | 430 | 100 (23.26%) | 176 (40.93%) | 154 (35.81%) | `two-tone=true` | 114 (26.51%) | 0 / 114 (100%) / 0 | 12.40 px | `not-two-tone`, sufficient |
| 12 | 225 / 155 / 42 | 128 | 34 (26.56%) | 50 (39.06%) | 44 (34.38%) | `two-tone=true` | 34 (26.56%) | 0 / 34 (100%) / 0 | 10.24 px | `not-two-tone`, sufficient |
| 13 | 826 / 581 / 114 | 512 | 88 (17.19%) | 203 (39.65%) | 221 (43.16%) | `two-tone=true` | 159 (31.05%) | 0 / 159 (100%) / 0 | 12.64 px | `not-two-tone`, sufficient |

The individual interiors sum to 307 pixels, with 0 dark and 307 light. Their union is pixel-identical to the interior produced by applying the same erosion to the union of the same frozen solid material. That equality is a consistency check; no group-level decision substitutes for the three component results above.

### Location of frozen dark pixels

| Component | Topology interior | Component/material edge | Partial-alpha edge | Full-alpha edge | 32–63 | 64–127 | 128–191 | 192–254 | 255 |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 0 | 100 | 100 | 0 | 26 | 73 | 1 | 0 | 0 |
| 12 | 0 | 34 | 34 | 0 | 10 | 24 | 0 | 0 | 0 |
| 13 | 0 | 88 | 88 | 0 | 41 | 47 | 0 | 0 | 0 |
| **Total** | **0** | **222** | **222** | **0** | **77** | **144** | **1** | **0** | **0** |

All 222 frozen dark pixels are outside the topology interior. All have alpha below 192; 221/222 have alpha at most 127. They form 71 eight-connected dark subclusters (29, 8, and 34 per component); the largest subcluster is 15 pixels, and no dark cluster reaches the topology interior. This is diagnostic connectedness inside the frozen components and does not alter those components.

## Remaining safety conditions — separate from two-tone

| Component | Achromatic? | WHITE contrast adaptation needed? | Solid chroma intersection | Prior complete wordmark | Prior exterior MASTER context | Prior protected chroma/true-AA/ambiguous contact | Next status |
|---:|---|---|---:|---|---|---|---|
| 4 | Yes, 100% | Yes, weak fraction 80.70% | 0 | Pass | Pass | None at grouped safety-mask level | `ELIGIBLE-FOR-NEXT-SAFETY-GATE` |
| 12 | Yes, 100% | Yes, weak fraction 73.44% | 0 | Pass | Pass | None at grouped safety-mask level | `ELIGIBLE-FOR-NEXT-SAFETY-GATE` |
| 13 | Yes, 100% | Yes, weak fraction 88.67% | 0 | Pass | Pass | None at grouped safety-mask level | `ELIGIBLE-FOR-NEXT-SAFETY-GATE` |

These statuses mean only that the isolated two-tone result no longer blocks a later safety review. They are **not PASS or AUTO-FIX**. The previous logical grouping audit marked the wordmark complete, exterior MASTER context present, and no protected chroma/true-AA/ambiguous contact; V22 also showed no alpha-visible path from these components to frozen chromatic component 1. Contrast adaptation on WHITE is still required. No recolor mask was created.

## Component 4 pixel at (109,73)

The pixel remains in V9 component 4: RGBA `(0,63,63,4)`, alpha 4, earlier Phase 4 label `PROTECTED / OTHER`. Its visible component membership is unchanged. Because V9 material is `alpha >=32`, this pixel is absent from the solid sample and absent from topology interior; it does not affect the frozen or topology-aware two-tone calculation. V23 applies no special case and makes no new ownership determination. No pixel was edited.

## Genuine two-tone positive controls

| Control | Frozen V9 two-tone | Topology material | Topology interior | Interior dark / light / intermediate | Evidence | Topology result |
|---|---|---:|---:|---:|---|---|
| Neosat positive control 1 | true (V9 component 1) | 4,352 px; true | 4,089 px | 2,173 / 1,732 / 184 | sufficient; floor 348.16 | `two-tone` |
| Demirören Medya positive control 2 | true (V9 component 1) | 10,681 px; true | 10,157 px | 4,887 / 4,665 / 605 | sufficient; floor 854.48 | `two-tone` |

Both remain genuine two-tone under the exact topology-aware interior rule. This satisfies the positive-control hard check.

## Regression controls

- **#14607/#14611:** retain frozen negative-control status `REVIEW`; the pair remains byte-identical. V22’s V9 replay has chromatic/two-tone protected components and no WHITE edit. This V23 does not apply the interior result to bypass chroma protection or incomplete grouping.
- **#14593:** remains `REVIEW`: incomplete group, protected contacts, and 14 blocked grouping links. The prior topology-aware group diagnostic was `not-two-tone`; that result did not override those blockers.
- **#14597:** cautious `REVIEW`, with no target and insufficient prior interior evidence. No gold/brand promotion.
- **Digi Slovakia:** V9 `PASS`; 0 changed pixels in WHITE and BLACK; historical output replay remains pixel-identical.
- **#14599:** not accessed.

## Question A / Question B

**A — Are the three frozen V9 results caused by genuine dark+light interior material?** The component-level evidence says no: each component has sufficient interior, all interior pixels are light, and every frozen dark pixel is partial-alpha edge material. This supports an edge/AA-driven false-positive diagnosis for all three components.

**B — Does `not-two-tone` automatically make a component safe to recolor?** **No.** Achromatic, contrast, chroma/AA/ambiguous protection, logical completeness, exterior MASTER context, and the eventual edit-mask safety decision remain separate. The result is only `ELIGIBLE-FOR-NEXT-SAFETY-GATE` for each component; #14700 remains unapproved.

## Invariants and outputs

- Frozen V9 component membership: unchanged; IDs `[4,12,13]` asserted against V22.
- Alpha, source, current WHITE/BLACK, and MASTER: read-only; stored outputs pixel-match pinned Phase 3 replay.
- Thresholds: unchanged; exact values checked from pinned generator.
- Editable pixels: 0. Candidate generated: no. Production picon writes: 0. MASTER/template writes: 0.
- #14607/#14611 remain blocked; Digi PASS is 0-change; both genuine two-tone controls remain two-tone; #14599 untouched.

Artifacts: `PER-COMPONENT-TWO-TONE-AUDIT.csv`, `DARK-PIXEL-AUDIT.csv`, `CONTROL-AUDIT.csv`, `SUMMARY.json`, and `tools/phase4_v23_component_tone.py`. The diagnostic mask map is a Work artifact only.
