# Phase 4 — Achromatic Glyph / AA Reconstruction Diagnostic

**Date:** 2026-09-27  
**Branch checkpoint:** `phase4-v10-component-mask-test` at `5f5b085fbf0210dfb34f7a6edefc6289115bf25c` (grouping checkpoint saved; HEAD reverified before this experiment)  
**Scope:** diagnostic only; no recolor, candidate, source, master, or production picon was written.

## Question and method

This test asks whether alpha-subthreshold achromatic antialias pixels, excluded from the solid achromatic core, safely connect the tiny core fragments seen in #14607.

The solid core retains the frozen V9 rules: alpha ≥32 and RGB max-minus-min ≤18. Only visible pixels below the alpha floor, still within the frozen achromatic color class, and outside the frozen chromatic core, confirmed chromatic-AA, and ambiguous chromatic-boundary masks are considered AA candidates.

A probable achromatic-AA pixel requires all of the following evidence: 8-neighbor connectivity to exactly one already classified core component; source RGB max-channel distance ≤18 from its supported neighbor; lower alpha than that support; and no 8-neighbor contact with a frozen protected class. This uses the frozen color delta and strict topology/alpha evidence. Multiple-owner bridges, protected neighborhoods, disconnected pixels, and pixels lacking either color or alpha continuity remain ambiguous. The frozen classes are never weakened.

The report retains the original 4-connected solid-core counts used in the previous grouping experiment. It also measures the solid core with 8-connectivity, then the reconstructed glyph mask with both connectivities. The primary glyph/group comparison uses 8-connected components so diagonal AA contact is represented; paired 8-connected baseline counts distinguish any change caused by AA from a connectivity-only change. Wordmark grouping reuses the earlier uniform rule: anchor area ≥ frozen V9 8% material fraction of the largest component; bbox gap ≤ median anchor bbox height. Frozen and ambiguous-AA pixels block proposed links. Contrast, two-tone, exterior-alpha, and complete-wordmark guards remain active.

## Results

| Case | Solid core components (4 / 8) | Original median W×H (4 / 8) | Low-alpha achro candidates → probable / ambiguous | Reconstructed components (4 / 8) | Reconstructed median W×H (8) | Groups (old 4 / old 8 / reconstructed) |
|---|---:|---|---:|---:|---|---:|
| #14607 | 58 / 52 | 1×1 / 1×1 | 361 → 0 / 361 | 58 / 52 | 1×1 | 40 / 39 / 39 |
| #14611 | duplicate of #14607 | duplicate | calculated once | duplicate | duplicate | duplicate regression check |
| #14700 | 19 / 18 | 3×13 / 4.5×8.5 | 995 → 22 / 973 | 25 / 18 | 4.5×8.5 | 1 / 1 / 1 |
| #14593 | 14 / 14 | 11.5×14 / 11.5×14 | 1,349 → 19 / 1,330 | 15 / 14 | 11.5×14 | 1 / 1 / 1 |
| #14597 | 224 / 214 | 1×1 / 1×1 | 597 → 0 / 597 | 224 / 214 | 1×1 | 140 / 138 / 138 |
| Digi Slovakia PASS | 0 / 0 | — | 0 → 0 / 0 | 0 / 0 | — | 0 / 0 / 0 |

### #14607 / #14611

The AA hypothesis is **not supported under the frozen safety evidence**. All 361 low-alpha achromatic candidates remained ambiguous: 115 touch the frozen protected neighborhood; 246 have no 8-connected path to a solid achromatic core. No candidate passed the unique-owner/color-continuity/alpha-attenuation tests. Therefore the AA reconstruction did not lower the 8-connected component count (52→52), change the median 1×1 geometry, or improve the wordmark grouping (39→39). The 4-connected-to-8-connected baseline alone changes 58 components to 52, while the median remains 1×1. That difference comes from diagonal connectivity, not reconstructed AA. The remaining 39 proposals do not form a complete wordmark group.

#14611 has byte-identical source and CURRENT WHITE SHA256 values to #14607 and reuses its calculation as the duplicate regression check.

### #14700

The whole wordmark remains one reconstructed group, containing nine 8-connected glyphs; all contrast-relevant glyphs are grouped, so reconstructed group completeness is true. The guard still returns `REVIEW`: group-level two-tone is true, the group touches ambiguous achromatic AA, and four proposed links cross protected/ambiguous blockers. Exterior-alpha context is true. AA attachment adds 22 pixels but does not reduce the 8-connected component or group count. The six extra 4-connected components in the reconstructed mask are diagonal AA attachments; they do not indicate extra glyphs under the 8-connected topology.

### #14593

The reconstructed grouping remains one group of nine glyphs, but complete-wordmark grouping remains false. The group is two-tone, contacts chromatic core, confirmed chromatic AA, and ambiguous boundary/achromatic AA, with 14 blocked links. Exterior-alpha context is true. Nineteen AA pixels attach, but the 8-connected component count and group count do not change. Fifteen 4-connected components include one diagonal-only AA attachment, so no glyph merger is claimed.

### #14597 and PASS

#14597 remains a cautious probe: no low-alpha achromatic AA pixel met the proof rule, no target was promoted, and no edit was considered. Digi Slovakia remained at **0 changed pixels**.

## Invariants and conclusion

Every case passed the no-write preservation checks: alpha equal, chromatic core equal, confirmed chromatic-AA equal, ambiguous chromatic-boundary equal, zero edit-mask intersections with each protected class, editable pixels = 0, candidate-vs-current changed pixels = 0. No candidate PNG was created. PASS stayed at 0 changes. #14607/#14611 source SHA256 is `edec07adb8a121d7c856271543549717aff4d253f0302fd2d83a909481b2d24c`; CURRENT WHITE SHA256 is `06f73c2c4e1fb1e42aab61f23909fd4a9b43d8b86722f938102164a7c1928089`.

For #14607, the observed median-height fragmentation is not repaired by securely classifiable achromatic AA. Some solid-core fragments meet diagonally, but that alone does not raise the median height. The remaining low-alpha achromatic pixels are either close to frozen chromatic protection or lack local core support, so their ownership remains unresolved. #14700 grouping remains stable while the frozen two-tone and blocker guards still reject recolor. #14593 remains incomplete and protected. This experiment tests glyph representation only; it provides no recolor approval.

## Visual outputs

The Work output contains seven-panel diagnostic images for #14607, #14700, #14593, #14597, and Digi Slovakia PASS, plus `14607-single-pixel-aa-detail.jpg`, which automatically zooms every original one-pixel achromatic-core component. Images are supplied with the response and omitted from the repository commit.

## Artifacts

- `AUDIT.csv` — per-case counts, geometry, AA evidence reasons, old/reconstructed groups, guard results, and invariants.
- `SUMMARY.json` — full machine-readable component and group audit.
- `phase4_achromatic_glyph_aa_diagnostic.py` — reproducible small-fixture diagnostic; no candidate or production output.
