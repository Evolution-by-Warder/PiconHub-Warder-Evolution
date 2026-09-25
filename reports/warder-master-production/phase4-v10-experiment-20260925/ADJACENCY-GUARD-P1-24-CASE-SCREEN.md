# V10 contact-fraction P1 screen — 24 cases — 2026-09-25

## Scope and result

Ran the existing isolated contact-fraction test on 24 previously untested P1 mixed chromatic/two-tone fixtures. Selection was limited to WHITE/BLACK review rows with at most 15 component findings and at least 100 changed pixels in the triage audit; already reviewed fixtures and duplicate source paths were excluded. This was a scratch screen using the existing test logic, not a new algorithm version.

All 24 cases remained REVIEW. The unchanged PASS control stayed PASS with zero changed pixels. All rows recorded unchanged alpha and protected chromatic source pixels. No candidate was applied at the initial screen run. The two later manual approvals are recorded below.

## Visual spot checks

- **#10085** — REVIEW, one two-tone component; 7,345 displayed pixels differ from the current output. Štefan later clarified that “stredne” was approval for this candidate; it is manually approved and applied on the test branch.
- **#6019** — REVIEW, one two-tone component; 1,599 displayed pixels differ from the current output. Štefan later clarified that “stredne” was approval for this candidate; it is manually approved and applied on the test branch.
- **#6216** — REVIEW, five two-tone components, 1,498 displayed pixels differ from current. The V10 candidate changes the dot over the “i” to white, making it disappear against the white master.
- **#14408** — REVIEW, four components touching protected chromatic artwork, 6,507 displayed pixels differ from current. The V10 test candidate leaves much of the large wordmark pale on white while other letters turn black.

The user's later manual approvals for #10085 and #6019 supersede the initial visual assessment; both exact candidates are applied with case-level audit. #6216 and #14408 remain unapplied. The automatic classifier still reports REVIEW for #10085 and #6019; these are manual approvals of two exact outputs, not approval of the algorithm.

## Audit and previews

Per-case hashes, status, changed-pixel counts, output differences, and preservation assertions:
`reports/warder-master-production/phase4-v10-experiment-20260925/ADJACENCY-GUARD-P1-24-CASE-SCREEN-AUDIT.csv`.

Focused comparison images are committed as `CASE-10085-MANUAL-APPROVAL.jpg` and `CASE-6019-MANUAL-APPROVAL.jpg`; the approval record is `CASE-10085-6019-MANUAL-APPROVAL.md` and `.csv`. Full scratch contact sheet:
`/workspace/scratch/cb84afc29802/v10-regression-prototype/adjacency-guard-v8-p1-screen/v10-isolated-regression-preview.jpg`.

This is fixture-limited safety evidence. It does not approve the V10 algorithm or a production rebuild.
