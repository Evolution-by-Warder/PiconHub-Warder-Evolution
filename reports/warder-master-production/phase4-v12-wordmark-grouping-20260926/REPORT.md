# Phase 4 — Achromatic Wordmark Grouping Experiment

**Date:** 2026-09-26  
**Scope:** grouping/classification only; no production output changes  
**Input branch checkpoint:** `phase4-v10-component-mask-test` at `7825bd3b84866e026c7d29359a68918027105bc4` (verified against the live branch before repository writes; branch was identical)  
**Result:** grouping succeeds for one complete wordmark (#14700), but no group passed the frozen contrast, two-tone, exterior, and chroma/AA/ambiguous guards. **No candidate PNG was emitted.**

## Rule under test

Achromatic pixels and frozen chroma/true-AA/ambiguous masks were classified using the existing V9/AA experiment rules. The experiment did not change those masks or their thresholds. Candidate geometric links used the same fixture-wide rule in every case: component area at least the frozen V9 8% material fraction of the largest achromatic component, with a link when the component bounding-box gap was no greater than the median anchor bounding-box height. Blocking pixels were excluded from groups; a chroma/AA/ambiguous blocker on a shortest link path caused `REVIEW`.

This is a grouping probe, not a production rule. In fixtures where achromatic material is highly fragmented, the derived geometry scale collapses to one pixel. The resulting many small proposals are explicitly treated as failure to prove a logical wordmark group, not as a reason to relax the rule.

Contrast, two-tone, and exterior-alpha decisions were computed both on each original component and on each proposed group. The original guards remain in force. The complete-wordmark guard requires all contrast-relevant components to belong to a single group and the group to pass all applicable safety checks.

## Results

| Case | Achromatic components | Contrast-relevant components | Proposed groups | Grouping result | Guard result |
|---|---:|---:|---:|---|---|
| #14607 | 58 | 23 | 40 | Partial; seven proposals join multiple target components, but not into one wordmark | `REVIEW`; chroma/boundary contacts and incomplete exterior context; 0 editable pixels |
| #14611 | duplicate of #14607 | duplicate | reused once | Byte-identical source and current WHITE; primary grouping reused | Duplicate regression check; 0 editable pixels |
| #14700 | 19 | 10 | 1 group of 10 | Complete target wordmark grouping; bbox `[65,57,210,73]` | `REVIEW`; group two-tone=true, 8 blocked geometric links, low-alpha perimeter; 0 editable pixels |
| #14593 | 14 | 11 | 1 group of 9 anchors | Partial; target components 6 and 9 are outside the proposed group; bbox `[77,37,210,96]` | `REVIEW`; group two-tone=true and chroma/true-AA/ambiguous contacts plus 14 blocked links; 0 editable pixels |
| #14597 | 224 | 0 | 140 | Cautious probe only; no contrast-relevant achromatic target | No promotion of gold/brand elements; 0 editable pixels |
| Digi Slovakia PASS | 0 | 0 | 0 | No group proposed | PASS; 0 changed pixels |

For #14700, the group-level contrast calculation says `FIX-NEEDED` (low-contrast fraction 0.837383) and group exterior contact is proven. The group-level two-tone check is also true, and eight proposed component links cross frozen blockers. Grouping therefore exposes why component fragmentation was obscuring the whole-wordmark analysis, while the retained two-tone and blocker guards still prevent an unsafe recolor.

For #14593, group-level contrast is `FIX-NEEDED` (0.972702) and exterior contact is proven. The group combines dark and light luminance classes, touches chroma, true-AA, and ambiguous masks, and two contrast-relevant components remain outside it. The whole-wordmark interpretation is not proven safe.

For #14607/#14611, 95 achromatic pixels resolve into 58 components; the median anchor bbox height is 1 px. The resulting 40 proposals are pixel-fragment groups rather than a coherent whole wordmark. The logotype itself is substantially chromatic, and the frozen chroma/boundary protections remain decisive.

## Invariant audit

All six audit rows passed: alpha equality, chroma-core equality, true-AA equality, zero edit-mask intersection with chroma/true-AA/ambiguous masks, zero proposed editable pixels, zero candidate-vs-current changes, and candidate hash equal to current WHITE hash. Digi Slovakia remained at **0 changed pixels**. #14607 and #14611 have identical source SHA256 `edec07adb8a121d7c856271543549717aff4d253f0302fd2d83a909481b2d24c` and current WHITE SHA256 `06f73c2c4e1fb1e42aab61f23909fd4a9b43d8b86722f938102164a7c1928089`.

No candidate comparison panel was generated because no complete group passed every guard. The six-panel diagnostics show the proposed groups and blocker maps for each unique fixture.

## Visual diagnostics

Five diagnostic JPGs were generated for unique fixtures and supplied with the Work output: #14607, #14700, #14593, #14597 and Digi Slovakia PASS. They are omitted from the repository commit; no candidate PNG was generated.

## Artifacts

- `AUDIT.csv` — per-case audit, including component-level and group-level decisions, bboxes, blocker paths, and all invariants.
- `SUMMARY.json` — full machine-readable summary and component/group detail.
- `phase4_achromatic_wordmark_grouping.py` — reproducible experiment script.
- `grouping-masks/` — per-unique-case diagnostic images.

**Conclusion:** `GROUPING SUCCESSFUL / EDIT NOT PROVEN SAFE` applies to #14700 only. All cases remain unapproved for production. No source, master, plugin, skin, or production picon was modified.
