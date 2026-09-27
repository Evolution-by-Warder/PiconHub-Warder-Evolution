# V27 — True→false transition forensics / approved-control safety study

## Result: A — TRANSITION-MECHANISM-SUPPORTED

V27 extracted transitions from the exact V26 `COMPONENT-AUDIT.csv` comparison column, then independently replayed frozen Phase 3 fitting, alpha-visible 8-connected membership, frozen solid sampling, and the exact V26/V23 topology function. The extracted set was 9 components: #14700 3, #3032 4, #3072 2. Any count or replay mismatch stopped the run.

## Nine transitions

`TRANSITION-AUDIT.csv` contains every required metric and alpha histograms. `DARK-PIXEL-FORENSICS.csv` contains every frozen-dark source pixel and its topology/edge classification. Across the nine, frozen dark material pixels = 753; dark inside topology interior = 0; dark on material edge = 753; dark at partial-alpha material edge = 753; dark at full-alpha material edge = 0.

## Approved #3032/#3072 output evidence

The approved WHITE artifact hashes were verified against the existing approval ledger: #3032 `e773849404809cec90fdec50825bfc02ea2eeb20187537a38bdcdcb8c2d123bf` and #3072 `e3427b452a70b52a062e64f01b28623553b884b294208ef44eba52ababd4a3da`. The rendered artifacts were compared with the exact fitted source composited on the verified WHITE MASTER. Per transition, `APPROVED-OUTPUT-COMPARISON.csv` records changed RGB pixels inside/outside the component, alpha changes, edge-dark/interior changes, and exact agreement with a diagnostic `(16,16,16)` component composite. The target composite is a mathematical comparator only; no candidate was created. Existing approval decisions remain CLOSED and were not revisited.

A prior approved output is independent historical evidence for the already accepted rendered result, not proof that the topology classifier is generally safe. For the six #3032/#3072 transitions, every frozen-dark edge sample remained unchanged in the approved WHITE, while 56–1,929 topology-interior pixels per component changed and 90.2–99.7% of those interiors match the diagnostic target-16 composite. This is consistent with interior contrast correction plus untouched dark edge samples; it does not establish rule-wide safety. The exact componentwise measurements, not approval status alone, determine the forensic interpretation.

## Positive genuine two-tone controls

T-NEOSAT and T-DEMIR were replayed in both historically used mask scopes. V23 selected 8-connected components of the solid achromatic core (`alpha>=32`, channel spread `<=18`), then selected component ID 1. V26 instead labels `alpha>0` components and samples every `alpha>=32` pixel in the enclosing alpha-visible component. The fitted RGBA canvases are byte-identical between the V23 helper and pinned Phase 3 fit path, so the count difference is due to scope, not resizing.

| Control | V23 selected material | V23 interior dark/light | V26 full alpha-component solid | V26 interior dark/light |
|---|---:|---:|---:|---:|
| T-NEOSAT | 4,352 px | 2,173 / 1,732 | 9,357 px | 2,283 / 5,616 |
| T-DEMIR | 10,681 px | 4,887 / 4,665 | 11,366 px | 5,311 / 4,665 |

The V26 solid sets are the union of three separate achromatic-core islands inside each alpha-visible component: T-NEOSAT `4,352 + 2,374 + 2,631 = 9,357`; T-DEMIR `10,681 + 327 + 358 = 11,366`. V23 selected island 1 and V26’s larger aggregate both retain interior dark and light populations and return `two-tone=true`. This reconciles the historical counts and confirms both positive-control lanes; it does not change V26’s generalization verdict.

## Other gates and 201 insufficient-evidence components

The V26 conservative result for `INSUFFICIENT_INTERIOR_EVIDENCE` is not `not-two-tone`: it retains frozen/protected behavior and cannot release a component. The 201 components are therefore not promoted by this substitution. Existing independent statuses remain in force: #14593 incomplete grouping/protected contacts; #14597 cautious gold/brand review; #14607/#14611 protected chroma/AA/ambiguous and incomplete grouping; #10954/#5136 protected-boundary blockers; #11359/#14406 no newly established visible repair. These prior dispositions were carried forward, not re-run as ownership decisions.

## Visual diagnostics

The PNG sheets show source, approved WHITE, transition component map, topology interior, and frozen-dark pixels, plus nearest-neighbor zooms. They are diagnostic only and contain no approval/rejection judgement. #14700 is included as the approved reference pattern.

## Invariants

No source, BLACK/WHITE picon, MASTER/template, approval ledger, generator, or classifier was modified. No candidate was created. #14599 was not accessed. V26 remains `RULE-GENERALIZATION-NEEDS-MORE-EVIDENCE`.

## Reproduction

`python tools/phase4_v27_true_to_false_transition_forensics.py --repo-root . --phase3-generator tools/rebuild_master_catalog.py --v26-audit reports/warder-master-production/phase4-v26-topology-two-tone-generalization-20260927/COMPONENT-AUDIT.csv --v26-selection reports/warder-master-production/phase4-v26-topology-two-tone-generalization-20260927/CONTROL-SELECTION.csv --white-master templates/picons/white-sablona.png --out reports/warder-master-production/phase4-v27-true-false-transition-forensics-20260927`
