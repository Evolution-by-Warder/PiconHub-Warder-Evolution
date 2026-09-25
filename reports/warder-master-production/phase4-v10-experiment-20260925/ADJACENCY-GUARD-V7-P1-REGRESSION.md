# V10 adjacency-guard v7 expanded P1 regression — 2026-09-25

## Scope

Extended the isolated contact-fraction V10 test with five additional unresolved mixed-logo WHITE cases from the P1 triage set: #628, #7352, #220, #858, and #13193. The prior seven fixtures and PASS control were rerun using the same algorithm and frozen V9 rendering path. No generator, MASTER, source, production PNG, or `main` branch was changed.

## New fixture results

| Case | Status | Unsafe components | Source pixels recolored | Output pixels different from current | Reason |
|---|---|---:|---:|---:|---|
| #628 | REVIEW | 2 | 12,062 | 1 | touches protected chromatic artwork |
| #7352 | REVIEW | 2 | 5,355 | 1 | two-tone component |
| #220 | REVIEW | 1 | 4,723 | 4 | touches protected chromatic artwork |
| #858 | REVIEW | 7 | 14 | 0 | two-tone components |
| #13193 | REVIEW | 9 | 147 | 86 | two-tone components |

All five cases remained REVIEW. The run preserved alpha and protected chromatic source pixels. The PASS control stayed PASS and unchanged. Previous regression fixtures retained their prior outputs and statuses; #15551 remains separately recorded as a manual visual approval while the classifier still reports REVIEW.

This is fixture-limited safety evidence. It does not establish an automatic repair rule or approve the V10 algorithm for production. New candidate PNGs and the preview remain scratch-only.

## Audit and preview

The per-case source/output hashes, counts, and assertions are in:
`reports/warder-master-production/phase4-v10-experiment-20260925/ADJACENCY-GUARD-V7-P1-REGRESSION-AUDIT.csv`.

Scratch preview:
`/workspace/scratch/cb84afc29802/v10-regression-prototype/adjacency-guard-v7-expanded-p1/v10-isolated-regression-preview.jpg`.
