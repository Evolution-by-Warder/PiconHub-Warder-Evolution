# Phase 4 — Topology-aware two-tone guard experiment

**Scope:** isolated diagnostic comparison. The frozen guard remains unchanged. No candidate recolor or production write was performed.

## Topology-derived interior

The high-confidence material mask is the existing frozen solid-achromatic group material. The interior is `M ∩ binary_erosion(M, 3×3 eight-neighbor, border_value=0)`, the exact construction used for #14700's prior diagnostic interior (307 pixels). It uses no coordinates, OCR, station-specific logic, bounding-box fill, or logo-tuned threshold. Sufficient evidence requires at least the frozen V9 material-anchor floor: `MATERIAL_FRACTION` (8%) of the largest connected component in the frozen material. A smaller or empty interior returns `INSUFFICIENT_INTERIOR_EVIDENCE` and REVIEW. Luminance cutoffs (dark ≤64, light ≥192) and the 3% per-population fraction are unchanged.

## Genuine two-tone positive controls

Two controls were selected from the committed Phase 3 `catalog-audit.csv` (blob `f0da93969ac925ee032fcd6588389363389603d5`), based on the same achromatic connected component being marked two-tone on both WHITE and BLACK outputs, then checked against their source pixels and rendered source artwork. Both have dark and light populations in topology-derived interior, and their selected achromatic component has zero contact with frozen chromatic core, true chromatic AA, and ambiguous boundary. One is a black field with a white symbol; the other is a black-and-white cube/wordmark. Neither uses a chromatic badge/background. Selection evidence and exact reasons are in `POSITIVE-CONTROL-SELECTION.csv`; visual masks and pixel counts are in `diagnostics/` and `SUMMARY.json`.

## Results

| Fixture | Frozen two-tone | Topology-aware | Interior evidence | Other guards | Final status |
|---|---|---|---|---|---|
| #14700 | True | not-two-tone | 307 px; dark 0, light 307 | complete; exterior; low-alpha perimeter guard still active | REVIEW |
| positive-control-1 | True | two-tone | 4089 px; dark 2173, light 1732 | positive control; no protected contact | validated; no edit |
| positive-control-2 | True | two-tone | 10157 px; dark 4887, light 4665 | positive control; no protected contact | validated; no edit |
| #14607 | frozen negative | not evaluated | no complete target group | incomplete wordmark; frozen chroma guards | REVIEW |
| #14611 | frozen duplicate | not evaluated | duplicate of #14607 | byte-identical regression control | REVIEW |
| #14593 | True | not-two-tone | 1199 px; dark 18, light 1101 | incomplete; protected contacts; 14 blocked links | REVIEW |
| #14597 | component-only | INSUFFICIENT_INTERIOR_EVIDENCE | one small component insufficient | cautious gold/brand; no target | REVIEW |
| Digi Slovakia | not targeted | not evaluated | 0 target pixels | PASS control | PASS; 0 changed |

### #14700 — frozen `True`; topology-aware `not-two-tone`

The frozen mask has 1070 pixels, with dark 222 (20.75%) and light 429 (40.09%). Topology interior has 307 pixels; 763 perimeter pixels are excluded from this decision material. Interior dark=0 (0.00%); light=307 (100.00%). This removes the established edge/AA false-positive. The independent complete-wordmark, exterior, protected contact, and low-alpha perimeter guards remain active. Final status: **REVIEW — no recolor; low-alpha perimeter ownership guard remains active**.

### Positive controls

- positive-control-1: frozen `True`, topology `two-tone`, interior dark=2173 (53.1%), light=1732 (42.4%), protected contact=False.
- positive-control-2: frozen `True`, topology `two-tone`, interior dark=4887 (48.1%), light=4665 (45.9%), protected contact=False.

Both controls retain `two-tone=true` under the topology-derived material and meet the frozen V9 evidence floor. No controls were used to tune thresholds.

### Regression controls

- #14607: 52 8-connected solid-achromatic components; no component material was promoted to a target. Prior incomplete-wordmark REVIEW remains. #14611 is byte-identical to #14607 (source and current WHITE hashes match).
- #14611: 52 8-connected solid-achromatic components; no component material was promoted to a target. Prior incomplete-wordmark REVIEW remains. #14611 is byte-identical to #14607 (source and current WHITE hashes match).
- #14593: frozen group two-tone=True (dark=89, light=2234); topology-aware=not-two-tone (dark=18, light=1101); still REVIEW because the frozen group is incomplete, has protected contacts, and 14 grouping links were blocked.
- #14597: cautious gold/brand probe retained; no edit target. One small component returned INSUFFICIENT_INTERIOR_EVIDENCE; no target was promoted.
- Digi Slovakia: PASS retained; 0 changed pixels and no new target.

## Safety and conclusion

All input source, current WHITE, and MASTER files were read-only. Alpha/chromatic/true-AA/ambiguous invariants are preserved because no pixels were written. `editable_pixels=0`; candidate-vs-current changes=0. #14607/#14611 were not reconstructed or retuned, #14593 remains incomplete with protected blockers, #14597 remains cautious, and Digi Slovakia remains a zero-change PASS.

**Diagnostic outcome: PROMISING.** This is evidence for an isolated candidate-rule experiment only; it is not production approval and does not authorize recolor.
