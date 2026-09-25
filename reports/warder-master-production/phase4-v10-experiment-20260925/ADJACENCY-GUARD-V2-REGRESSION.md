# V10 adjacency-guard v2 regression — 2026-09-25

## Result

A scratch-only correction was tested after the v1 failure. The former guard checked intersection between mutually exclusive achromatic and chromatic masks, so it could not associate neutral lettering with nearby colored artwork. V2 instead marks an achromatic component unsafe when it touches the one-pixel neighborhood of opaque chromatic seeds. Unsafe cases receive REVIEW and are left unchanged.

| Fixture | V2 result | Changed pixels | Unsafe components | Different from current middle-column output |
|---|---:|---:|---:|---:|
| #14716 | REVIEW (V9 fallback) | 13,890 internal source pixels | 0 | 0 |
| #3163 | REVIEW | 0 | 7 | 0 |
| #3133 | REVIEW | 0 | 7 | 0 |
| PASS control | PASS | 0 | 0 | 0 |

All four final composited candidates are pixel-identical to the current WHITE outputs. Alpha stayed unchanged and protected chromatic pixels were unchanged in every fixture.

The selected variants remain the current middle-column outputs recorded in `USER-VISUAL-SELECTION.md`. This test did not write or commit any PNG or generator code. It demonstrates that this narrow adjacency guard avoids the two known regressions; it does not prove that one-pixel adjacency finds every complete logical mixed-logo component. V10 is still not approved for a production rebuild. Continue isolated regression testing; classify uncertain cases as REVIEW.

## Test evidence

The source hashes, candidate PNG hashes, exact changed-pixel counts, fit boxes, and per-fixture assertions are retained in the scratch CSV:
`/workspace/scratch/cb84afc29802/v10-regression-prototype/adjacency-guard-v2/regression-audit.csv`.

The comparison sheet is:
`/workspace/scratch/cb84afc29802/v10-regression-prototype/adjacency-guard-v2/v10-isolated-regression-preview.jpg`.

## Protected state

- Branch: `phase4-v10-component-mask-test`
- `main`, MASTER templates, transparent sources, approved batches, and all current PNG outputs remain untouched.
- No full-catalog rebuild, merge, rebase, or force-push was performed.
