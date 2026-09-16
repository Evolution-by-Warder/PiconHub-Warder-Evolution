# Phase 4 — V10 component-mask regression test

Status: TEST DESIGN ONLY — NO PRODUCTION OUTPUT CHANGES
Base commit: `e9b503d76eae3c3c7d7763df4909039a55d3edb8`
Test branch: `phase4-v10-component-mask-test`

## Why this branch exists

Phase 4 visual QC found a reproducible class of failures in Phase 3 REVIEW outputs. Phase 3 itself remains an immutable checkpoint and `main` must not be touched.

The failure is not the old PLAN B fake-transparent-source problem. Source QC/recovery remains approved. The new problem is output component-mask conservatism in some mixed logos.

## Confirmed failure class

Pattern:

1. logo contains a chromatic brand component (symbol, circle, badge, stripe, etc.);
2. logo also contains a logically separate achromatic/light text or symbol directly on the MASTER;
3. the chromatic component is correctly protected;
4. protection/conservative REVIEW handling also leaves the separate achromatic component too light on WHITE (or potentially too dark on BLACK);
5. the achromatic component therefore loses readability even though it is separable and should receive the approved contrast adaptation.

The fix must NEVER recolor the protected chromatic component merely to solve contrast on the MASTER.

## Visually confirmed examples

From Phase 4 review sheets `review-146.jpg` and `review-147.jpg`:

- STAR CINEMA WHITE (`#14593`): yellow star is a protected brand component; separate light text loses contrast on WHITE.
- РУССКИЙ БЕСТСЕЛЛЕР WHITE (`#14597`): visually unacceptable low-contrast WHITE result; any correction must respect protected brand elements and only edit reliably separable achromatic content.
- МИР WHITE (`#14599`): colored circular brand element remains protected while the light `МИР` element loses contrast on WHITE.
- ПРОДВИЖЕНИЕ WHITE (`#14607`, repeated again at `#14611`): blue/red symbol is correctly protected; separate light wordmark nearly disappears on WHITE. This is a canonical V10 failure example because symbol/text separation is visually clear.
- УДМУРТИЯ WHITE (`#14700`): red circular symbol is correctly protected; separate light wordmark loses contrast on WHITE.

These findings mean Phase 3 is NOT approved for merge to `main` yet.

## V10 target rule

For each logical component, evaluate contrast against the background immediately behind that component.

A reliably separable achromatic component directly on the BLACK/WHITE MASTER may receive contrast adaptation even when a nearby chromatic component is protected.

WHITE MASTER:
- reliably separable very-light/white achromatic text/symbol directly on MASTER -> suitable dark/black rendition;
- protected chromatic component -> unchanged.

BLACK MASTER:
- reliably separable dark achromatic text/symbol directly on MASTER -> suitable light rendition;
- protected chromatic component -> unchanged.

If reliable separation cannot be proven, remain REVIEW. Do not guess and do not expand a mask across a protected component.

## Hard protection requirements

- No global recoloring of mixed logos.
- No rectangular/x-boundary shortcut masks.
- No global darkness/lightness threshold that crosses into a protected brand component.
- No outline, halo, shadow or invented graphical treatment.
- Preserve geometry, antialiasing, typography and integral symbols.
- A protected colored component must remain pixel-identical after the common geometric resize.
- If a proposed contrast-edit mask intersects a protected component at all -> REVIEW / reject automatic edit.

## Regression set before any rebuild

### Must-fix cases

At minimum:
- ПРОДВИЖЕНИЕ WHITE (#14607/#14611)
- УДМУРТИЯ WHITE (#14700)
- STAR CINEMA WHITE (#14593)
- МИР WHITE (#14599)

РУССКИЙ БЕСТСЕЛЛЕР (#14597) remains in the failure set but must only be auto-fixed if the relevant achromatic component can be reliably separated; otherwise it remains REVIEW.

### Must-not-regress controls

At minimum:
- recovered PLAN B: red `plan_` block + blue `B` circle remain intact;
- recovered TV5MONDE EUROPE remains intact/readable;
- previously approved V9 mixed/chromatic stress cases remain intact;
- rectangular-brand stress cases remain intact;
- previously approved large monochrome wordmarks continue to receive correct full-wordmark contrast adaptation;
- PASS 0px controls remain unchanged where no adaptation is required.

## Required V10 experiment sequence

1. Inspect current generator/component-mask implementation; do not modify Phase 3 outputs.
2. Implement the smallest possible component-separation change on this test branch only.
3. Generate only an isolated regression batch first — never the whole 9,041-source catalog as the first test.
4. Produce SOURCE / current Phase 3 BLACK+WHITE / V10 BLACK+WHITE comparisons for must-fix and must-not-regress controls.
5. Record changed-pixel masks/counts and verify protected-component pixel identity.
6. Perform visual review with Štefan.
7. If any protected component changes or any canonical control regresses, reject/adjust V10; no production rebuild.
8. Only after explicit visual approval of the V10 regression batch may a full corrective clean rebuild be proposed.
9. Any full corrective rebuild must occur on an explicitly approved working/production path and must again pass complete output QC and targeted visual stress tests.
10. Merge to `main` remains forbidden until explicit final approval.

## Current immutable checkpoints

- Phase 2 approved source recovery: `1ac32e7a81f9d5ff942dcb97df5604f25dc346b3`
- Phase 3 clean rebuild: `e9b503d76eae3c3c7d7763df4909039a55d3edb8`
- 9,041 approved transparent sources remain authoritative.
- BLACK/WHITE Phase 3 outputs remain evidence/current checkpoint while V10 is tested; do not overwrite them merely to experiment.
- MASTER templates remain immutable.
- `main` must remain untouched.
