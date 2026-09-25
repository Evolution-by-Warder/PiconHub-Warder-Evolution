# V10 component-mask follow-up — P1 screen 2 — 2026-09-25

## Scope and result

Screened 24 additional, previously untested P1 mixed-logo review fixtures using the same isolated component-mask prototype, plus the unchanged PASS control. Source paths were unique within this screen. No picon output was written to the repository.

The prototype classified 7 fixtures AUTO-FIXED and 17 REVIEW. However, six of the seven AUTO-FIXED candidates are pixel-identical to their existing WHITE output. The seventh (#1606) differs by only 2 displayed pixels. The PASS control remained pixel-identical with zero changed pixels. Alpha and protected chromatic pixels were unchanged in all 25 rows.

This result supplies no new visible repair. The AUTO-FIXED label alone is not evidence that the candidate improves the current output. No candidate was applied.

## Audit

`ADJACENCY-GUARD-V9-P1-24-CASE-SCREEN-AUDIT.csv` records source and current-output hashes, candidate hash, style, classifier status, changed counts, output pixel differences, and preservation assertions. The local scratch comparison sheet contains all fixtures.

This is fixture-limited test evidence. It does not approve the prototype or a production rebuild.
