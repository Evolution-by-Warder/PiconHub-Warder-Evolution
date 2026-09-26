# Phase 4 color-class topology regression — 2026-09-26

## Scope and branch state

This is an isolated five-fixture experiment for `phase4-v10-component-mask-test`, based on verified branch HEAD `281b0ae3bb6728a64a7de4067cfdba82f18df506`. No production picon, transparent source, MASTER, plugin, skin, Phase 3 checkpoint, or `main` content was changed. All candidate output files were kept outside the production picon tree.

Fixtures: #11359 Turksat WHITE, #5136 ARD/NDR WHITE, #14406 Harmonic WHITE, #10954 Demirören WHITE, and the Digi Slovakia PASS control.

## Experiment

The script uses the frozen V9 values from `tools/rebuild_master_catalog.py`: opaque alpha 32, achromatic RGB delta 18, achromatic fraction 98.5%, contrast ratio 2.50, material fraction 8%, and two-tone fraction 3%.

Visible pixels below alpha 32 are treated as ambiguous and do not join either class. Solid achromatic pixels are segmented with 4-connectivity; solid chromatic pixels with 8-connectivity. The chromatic core and its immediate visible 8-neighbor boundary ring are protected. A candidate mask may contain only a separate achromatic core. Any such core touching the protected region is rejected and left REVIEW. No rectangular or positional masks are used.

## Result

The topology split generated candidates for #11359, #5136, and #14406 while preserving alpha and every protected chromatic/boundary pixel. However, the side-by-side comparisons show no new visible repair over the current WHITE output: the current output already displays the relevant text in dark, readable form. The pixel differences (983, 600, and 584 output pixels respectively) are subtle raster differences and do not establish a visibly improved repair. These remain REVIEW; this does not approve the algorithm or any production change.

For #10954, all three contrast-relevant achromatic cores touched the protected chromatic/AA boundary ring. The algorithm rejected all three, emitted the current WHITE image unchanged, and retained REVIEW. This is the required conservative outcome for this fixture.

The PASS control had 0 edited achromatic pixels and 0 output pixels changed relative to current. It remains PASS.

| Case | Topology result | Edited achromatic core pixels | Candidate vs current pixels | Protected chromatic/boundary pixels equal | Ambiguous/rejected components | Final |
|---|---:|---:|---:|---|---:|---|
| #11359 Turksat | candidate generated | 4,984 | 983 | yes | 0 | REVIEW |
| #5136 ARD/NDR | candidate generated | 4,606 | 600 | yes | 1 | REVIEW |
| #14406 Harmonic | candidate generated | 4,534 | 584 | yes | 0 | REVIEW |
| #10954 Demirören | all cores rejected at protected boundary | 0 | 0 | yes | 3 | REVIEW |
| PASS control | no edit | 0 | 0 | yes | 0 | PASS |

`candidate vs current pixels` counts differ on the composed 220×132 WHITE output. `edited achromatic core pixels` counts are the actual recolor mask size before compositing. The audit also records all source/current/candidate SHA256 values, component counts, fit geometry, and alpha/protected-pixel checks.

## Decision

The experiment demonstrates that color-class topology can split achromatic cores from an alpha-connected mixed logo without changing protected chroma or its immediate visible boundary. It does not produce a new visibly improved repair in this batch because the three accepted-looking candidates already match the readable state of the current output; the stronger mixed-logo case remains inseparable under the explicit boundary guard. No production picon is approved or written. Keep all four target cases in REVIEW and do not proceed to a catalog rebuild from this result.

## Artifacts

- `phase4_color_class_topology_regression.py` — isolated runner; reads only the five fixture files.
- `audit.csv` — per-case hashes, changed-pixel counts, component decisions, and invariants.
- `summary.json` — machine-readable run summary.
- `comparison.jpg` — SOURCE | CURRENT WHITE | CANDIDATE comparison sheet.
