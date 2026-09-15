# Warder MASTER production report

Generated: 2026-09-15T17:40:39.158769+00:00
Branch baseline: `1ac32e7a81f9d5ff942dcb97df5604f25dc346b3`

This is the Phase 3 clean rebuild. The generator removed all 18,080 historical
BLACK/WHITE PNGs before producing this catalog; no historical output was used
as an input. Inputs were limited to the 9,041 approved transparent sources and
the two immutable MASTER PNGs.

## Source classification

- PASS: 5
- AUTO-FIXED: 335
- REVIEW: 8701
- ERROR/SKIP: 0

## Variant classification

- PASS: 1603
- AUTO-FIXED: 754
- REVIEW: 15725
- ERROR/SKIP: 0

## Validation

- Transparent sources: 9041
- BLACK outputs: 9041
- WHITE outputs: 9041
- Output validation errors: 0
- Source bytes changed: 0
- MASTER bytes changed: 0

## Artifacts

- Full production audit: `catalog-audit.csv.gz`
- Summary: `summary.json`
- Largest approved contrast edits: `contact-sheets/largest-contrast-component-actions.jpg`
- Mixed/chromatic stress sample: `contact-sheets/mixed-color-logo-stress.jpg`
- Rectangular-brand stress sample: `contact-sheets/rectangular-brand-stress.jpg`
- Recovered PLAN B and TV5MONDE: `contact-sheets/recovered-plan-b-tv5monde.png`
- All PASS sources: `contact-sheets/all-pass.png`
- Every REVIEW variant: `contact-sheets/all-review/review-001.jpg` through
  `contact-sheets/all-review/review-158.jpg`, mapped by
  `contact-sheets/all-review-index.csv.gz` and `contact-sheets/all-review-manifest.json`.

REVIEW candidates are generated with their original brand colours intact. They are
not automatically approved and this branch must not be merged before visual review.
