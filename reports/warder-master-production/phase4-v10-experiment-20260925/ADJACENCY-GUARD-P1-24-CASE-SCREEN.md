# V10 contact-fraction P1 screen — 24 cases — 2026-09-25

## Scope and result

Ran the existing isolated contact-fraction test on 24 previously untested P1 mixed chromatic/two-tone fixtures. Selection was limited to WHITE/BLACK review rows with at most 15 component findings and at least 100 changed pixels in the triage audit; already reviewed fixtures and duplicate source paths were excluded. This was a scratch screen using the existing test logic, not a new algorithm version.

All 24 cases remained REVIEW. The unchanged PASS control stayed PASS with zero changed pixels. All rows recorded unchanged alpha and protected chromatic source pixels. No candidate was applied at the initial screen run. The two later manual approvals are recorded below.

## Visual spot checks

- **#10085** — REVIEW, one two-tone component; 7,345 displayed pixels differ from the current output. Štefan later clarified that “stredne” was approval for this candidate; it is manually approved and applied on the test branch.
- **#6019** — REVIEW, one two-tone component; 1,599 displayed pixels differ from the current output. Štefan later clarified that “stredne” was approval for this candidate; it is manually approved and applied on the test branch.
- **#6216** — REVIEW, five two-tone components, 1,498 displayed pixels differ from current. The V10 candidate changes the dot over the “i” to white, making it disappear against the white master.
- **#14408** — REVIEW, four components touching protected chromatic artwork, 6,507 displayed pixels differ from current. Štefan selected the middle-column CURRENT output; it remains unchanged.
- **#6099** — REVIEW, 34 changed components, 9 unsafe components touching protected chromatic artwork, 11 pixels different from current. Štefan selected the right-hand candidate; it is manually approved and applied.
- **#7191** — REVIEW, 18 changed components, 4 unsafe two-tone components, 49 pixels different from current. Štefan selected the right-hand candidate; it is manually approved and applied.

The user's later manual approvals for #10085 and #6019 supersede the initial visual assessment; both exact candidates are applied with case-level audit. #6216 remains REVIEW automatically; Štefan selected the exact right-hand V10 candidate, which is manually approved and applied on the test branch. #14408 remains REVIEW automatically; Štefan selected the middle-column CURRENT output, so it is retained unchanged. This is case-level manual visual selection, not approval of the algorithm. The automatic classifier still reports REVIEW for #10085 and #6019; these are manual approvals of two exact outputs, not approval of the algorithm. Štefan also selected the exact right-hand candidates for #6099 and #7191; both are manually approved and applied on the isolated test branch. All four still report REVIEW automatically; #14408's middle/current output remains unchanged. These are case-specific approvals only.

## Audit and previews

Per-case hashes, status, changed-pixel counts, output differences, and preservation assertions:
`reports/warder-master-production/phase4-v10-experiment-20260925/ADJACENCY-GUARD-P1-24-CASE-SCREEN-AUDIT.csv`.

Focused comparisons for the manually selected cases are committed as `CASE-10085-MANUAL-APPROVAL.jpg`, `CASE-6019-MANUAL-APPROVAL.jpg`, `CASE-6216-14408-MANUAL-VISUAL-DECISIONS.jpg`, `CASE-14408-MANUAL-VISUAL-DECISION.jpg`, `CASE-6099-MANUAL-APPROVAL.jpg`, and `CASE-7191-MANUAL-APPROVAL.jpg`. Case-level decision records are `CASE-10085-6019-MANUAL-APPROVAL.md` / `.csv`, `CASE-6216-14408-MANUAL-VISUAL-DECISIONS.md` / `.csv`, and `CASE-6099-7191-MANUAL-APPROVAL.md` / `.csv`. Full scratch contact sheet:
`/workspace/scratch/cb84afc29802/v10-regression-prototype/adjacency-guard-v8-p1-screen/v10-isolated-regression-preview.jpg`.

This is fixture-limited safety evidence. It does not approve the V10 algorithm or a production rebuild.
