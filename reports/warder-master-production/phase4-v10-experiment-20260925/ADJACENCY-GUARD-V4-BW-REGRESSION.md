# V10 adjacency-guard v4 expanded regression — 2026-09-25

## Scope and result

Expanded the v2 scratch guard test across unresolved mixed-logo WHITE cases, one BLACK case, and an unchanged PASS control. The guard associates achromatic components with a one-pixel neighborhood of opaque chromatic seeds. Any ambiguous or associated component is marked REVIEW and is not recolored.

| Review case | Style | Result | Unsafe components | Changed pixels | Different from current output |
|---|---|---|---:|---:|---:|
| #14716 | WHITE | REVIEW (V9 fallback) | 0 | 13,890 internal source pixels | 0 |
| #3163 | WHITE | REVIEW | 7 | 0 | 0 |
| #3133 | WHITE | REVIEW | 7 | 0 | 0 |
| #3172 | WHITE | REVIEW (V9 fallback) | 0 | 1,056 internal source pixels | 0 |
| #3174 | WHITE | REVIEW | 30 | 0 | 0 |
| #12062 | BLACK | REVIEW | 43 | 0 | 0 |
| PASS control | WHITE | PASS | 0 | 0 | 0 |

Six of the seven composites remained pixel-identical to their current outputs. Case #12062 differed in 93 displayed pixels (115 source achromatic pixels recolored); its alpha and protected chromatic source pixels remained unchanged. The selected middle-column cases (#14716, #3163, #3133) are still exactly the outputs Štefan chose.

This establishes a broader non-regression check for these fixtures only. No fixture became AUTO-FIXED, so this does not validate safe automatic recoloring or establish that a one-pixel neighborhood captures every logical mixed component. V10 remains unapproved for production. Continue isolated testing; ambiguous cases remain REVIEW.

## Evidence and protected state

The source and candidate hashes, exact counts, fit boxes and per-fixture assertions are in the tracked audit CSV:
`reports/warder-master-production/phase4-v10-experiment-20260925/ADJACENCY-GUARD-V4-BW-REGRESSION-AUDIT.csv`.

Preview:
`/workspace/scratch/cb84afc29802/v10-regression-prototype/adjacency-guard-v4-bw-expanded/v10-isolated-regression-preview.jpg`.

Only scratch scripts and outputs were changed. No repository PNG or generator code, MASTER, transparent source, approved batch, or `main` was changed. No full rebuild or merge was performed.
