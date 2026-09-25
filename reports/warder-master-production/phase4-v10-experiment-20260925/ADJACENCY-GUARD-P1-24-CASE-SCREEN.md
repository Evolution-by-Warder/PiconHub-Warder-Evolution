# V10 contact-fraction P1 screen — 24 cases — 2026-09-25

## Scope and result

Ran the existing isolated contact-fraction test on 24 previously untested P1 mixed chromatic/two-tone fixtures. Selection was limited to WHITE/BLACK review rows with at most 15 component findings and at least 100 changed pixels in the triage audit; already reviewed fixtures and duplicate source paths were excluded. This was a scratch screen using the existing test logic, not a new algorithm version.

All 24 cases remained REVIEW. The unchanged PASS control stayed PASS with zero changed pixels. All rows recorded unchanged alpha and protected chromatic source pixels. No candidate was applied to a repository picon.

## Visual spot checks

- **#10085** — REVIEW, one two-tone component, 7,345 displayed pixels differ from the current output. The V10 test candidate makes several wordmark letters pale against the white background, reducing contrast compared with the current readable dark wordmark.
- **#6019** — REVIEW, one two-tone component, 1,599 displayed pixels differ from current. The V10 test candidate turns only part of a four-part gray motif white and breaks its visual consistency.

Both candidates are scratch-only and should remain unapplied. These spot checks show why the unresolved component guard must continue to hold the cases for review.

## Audit and previews

Per-case hashes, status, changed-pixel counts, output differences, and preservation assertions:
`reports/warder-master-production/phase4-v10-experiment-20260925/ADJACENCY-GUARD-P1-24-CASE-SCREEN-AUDIT.csv`.

Focused previews saved as `case-10085-focused-review.jpg` and `case-6019-focused-review.jpg` in the user's review materials. Full scratch contact sheet:
`/workspace/scratch/cb84afc29802/v10-regression-prototype/adjacency-guard-v8-p1-screen/v10-isolated-regression-preview.jpg`.

This is fixture-limited safety evidence. It does not approve the V10 algorithm or a production rebuild.
