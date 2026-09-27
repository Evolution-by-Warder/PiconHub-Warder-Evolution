# Conservative subthreshold-fringe rule-definition experiment

**Outcome: B — STRUCTURAL RULE TOO AMBIGUOUS.** No new rule adopted, no candidate generated, and #14700 remains REVIEW.

## Method and anti-overfit

The exact previous Class P/N/T controls were reused. The sole tested structural candidate was frozen after Class P analysis: all direct core-to-perimeter-to-MASTER edge-normal luminance profiles must be monotonic nondecreasing; any reversal or untraceable profile is REVIEW. `Was #14700 used to derive this condition? NO.` No threshold was fitted. The rule's pseudocode, limitations and gate order are in `RULE-SPEC.md`.

The profiles use the frozen fitted 220×132 source grid, nearest directly adjacent confirmed core support, sign-normal ray through existing source pixels, straight-alpha compositing over the actual WHITE MASTER and linear Rec.709 luminance. No blur, interpolation, dilation or new source pixels are used.

## Class P results

| Case | Prior gates | Perimeter | Monotonic profiles | Reversal pixels | Unresolved | Fringe result | Final experimental status |
|---|---|---:|---:|---:|---:|---|---|
| P-AB1 | PASS | 715 | 169 | 546 | 0 | FRINGE-REVIEW | EXPERIMENTAL-GATE-REVIEW |
| P-MEGA | PASS | 620 | 38 | 198 | 384 | FRINGE-REVIEW | EXPERIMENTAL-GATE-REVIEW |
| P-CNBC | PASS | 976 | 74 | 351 | 551 | FRINGE-REVIEW | EXPERIMENTAL-GATE-REVIEW |
| P-MTA3 | PASS | 328 | 55 | 273 | 0 | FRINGE-REVIEW | EXPERIMENTAL-GATE-REVIEW |
| P-NTV | PASS | 520 | 54 | 466 | 0 | FRINGE-REVIEW | EXPERIMENTAL-GATE-REVIEW |

The condition has no acceptance cases among the five Class P controls (0/5 pass; every control has at least 198 reversals). Counterexample B also returns REVIEW with exactly the same 546 reversal profiles as the unmodified AB1 baseline, so the predicate does not isolate its one-pixel perturbation. This is evidence of an over-conservative, non-discriminating condition, not evidence that the safe controls have unsafe fringe.

## Decision pipeline and frozen controls

| Case | First blocker / ordered gate result | Fringe gate | Final experimental status |
|---|---|---|---|
| #14607 | BLOCKED: complete contrast-relevant wordmark/group not confirmed (frozen grouping incomplete) | NOT REACHED | REVIEW; fringe cannot override prior blocker |
| #14611 | BLOCKED: complete contrast-relevant wordmark/group not confirmed (frozen grouping incomplete) | NOT REACHED | REVIEW; fringe cannot override prior blocker |
| #14593 | BLOCKED: incomplete wordmark group; 14 blocked links; protected chroma/AA/ambiguous contacts | NOT REACHED | REVIEW; fringe cannot override prior blocker |
| #14597 | REVIEW: no confirmed editable target; gold/brand and badge ownership unresolved | NOT REACHED | REVIEW; fringe cannot override prior blocker |
| #10954 | BLOCKED: complete safe edit mask not confirmed; all three contrast cores rejected at protected chromatic boundary | NOT REACHED | REVIEW; fringe cannot override prior blocker |
| #5136 | BLOCKED: complete safe group/edit mask not confirmed; one of two principal cores rejected at protected boundary | NOT REACHED | REVIEW; fringe cannot override prior blocker |
| T-1-NEOSAT | BLOCKED: topology-aware genuine two-tone | NOT REACHED | BLOCKED: genuine two-tone |
| T-2-DEMIRÖREN | BLOCKED: topology-aware genuine two-tone | NOT REACHED | BLOCKED: genuine two-tone |
| Digi Slovakia | PASS control; no contrast target; 0 changed pixels | NOT REACHED | PASS |

#14607/#14611 are byte-identical source and CURRENT WHITE duplicates. #14593, #14597, #10954 and #5136 retain their prior frozen statuses; no fringe score is used to clear them.

## Synthetic counterexamples

| Case | Geometry-derived change | Reversal profiles | Reversal components | Cycle components | Rule result |
|---|---|---:|---:|---:|---|
| A_CONTINUOUS_BRIGHT_RING | 715 px; all confirmed-mask subthreshold perimeter samples | 691 | 234 | 0 | REVIEW |
| B_ISOLATED_EDGE_NOISE | 1 px; deterministic singleton 8-connected perimeter pixel | 546 | 251 | 0 | REVIEW |
| C_SUSTAINED_PARTIAL_STROKE | 74 px; largest proper 8-connected perimeter component | 604 | 243 | 0 | REVIEW |

Synthetic A/B/C preserve source and render alpha and geometry. They are diagnostic overlays only; no production pixels are written.

## #14700 evaluated last

Prior gates PASS: complete group and exterior context; protected intersections and blocked links are zero; topology-aware two-tone is false; M0 is 1,224 px (1,070 core + 154 proven attachments). Its exact 300-pixel ownership perimeter remains outside M0: 40 SAFE one-hop, 259 ambiguous, 1 channel-spread>18 ownership-unresolved other pixel. Prior audit confirms no perimeter pixel intersects a frozen protected mask; all remain untouched.
Using the prior M0 render SHA 581206f0088f40ace49afad5fdfd46377216fb06143588da926f0aa270311242 and frozen 300 perimeter coordinates: 116 monotonic profiles, 89 reversals, 95 untraceable; final EXPERIMENTAL-GATE-REVIEW. No ownership is inferred, no candidate is generated, editable/changed pixels = 0, and #14700 remains diagnostic REVIEW.

## Invariants

WHITE MASTER hash matches. No production picon, source, CURRENT BLACK/WHITE, template, or mask was written. Synthetic alpha equals input alpha. #14607/#14611 source and CURRENT WHITE hashes match; both genuine two-tone controls remain two-tone; Digi Slovakia remains 0 changes; #14599 untouched.

See diagnostics/COUNTEREXAMPLES-A-B-C.jpg and synthetic images; full profiles are in SUMMARY.json.