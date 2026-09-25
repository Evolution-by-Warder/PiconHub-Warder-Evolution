# V10 scratch contrast-gate check — 2026-09-25

## Test

Ran a targeted scratch-only variation of the component-mask prototype on 13 review fixtures: the newly found #407/#1009 duplicate-source case, prior protected-component failures #3163 and #3133, earlier adjacency regression cases, and a PASS control. The variation removes a directional mean-luma precondition; the neutral component is instead judged by the contrast threshold, while two-tone and chromatic-adjacency guards remain in place.

## Result

The 13 review rows remained REVIEW; the PASS control stayed PASS and pixel-identical. Alpha and protected chromatic pixels remained unchanged in all rows.

For #407 and #1009, the false PASS classification is now blocked: each is REVIEW with 8 unsafe two-tone components. The prototype recoloured 5,631 source pixels, while the rendered candidate differs from the current output by 84 pixels. The focused comparison keeps the neutral lettering dark and legible. The remaining unsafe components keep the row at REVIEW, so the candidate remains unapplied. This is a safer stop condition and a promising fixture result, not approval of the candidate or the algorithm.

Known protected-artwork cases #3163 and #3133 each had zero recoloured pixels and remained REVIEW. The PASS control had zero changed pixels and zero display difference.

## Conclusion

This variation corrects the unsafe PASS label for the focused duplicate-source case, but produces no approved repair and does not establish the component-mask prototype as production-safe. Keep all picon outputs unchanged and do not use it for a rebuild.

The per-case audit is `ADJACENCY-GUARD-V11-CONTRAST-GATE-TEST-AUDIT.csv`. The focused script and comparison sheets remain in local scratch test materials, including `case-407-v11-review.jpg`.
