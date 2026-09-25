# V10 scratch contrast-gate regression check — 2026-09-25

## Scope

Re-ran all 24 fixtures from the preceding P1 screen with the contrast-only scratch variation. Added the prior protected-component regression probes #3163 and #3133 and fallback case #14716, plus the unchanged PASS control. The test changed only local candidate generation; no repository picon was edited.

## Results

Across 27 review rows, 26 remained REVIEW and one (#5797) was AUTO-FIXED. The unchanged PASS control remained PASS. The #5797 candidate is pixel-identical to its current output, so the screen produced no new visible repair. Alpha and protected chromatic pixels were unchanged in every row.

The former false PASS cases #407 and #1009 now stop at REVIEW. Their candidates differ from the existing outputs in 84 pixels each; eight unsafe two-tone components remain, so neither candidate was applied. Known protected-component failures #3163 and #3133 had zero changed pixels and remained REVIEW. #14716 stayed REVIEW under the achromatic-only fallback.

## Conclusion

The variation removes the unsafe PASS result in this focused regression set, while the guarded candidate for #407/#1009 is close to the existing output. It yields no new applied or visibly changed picon. This limited screen does not validate the prototype for production or authorize a rebuild. Keep all existing picon outputs unchanged.

Per-row hashes and pixel checks are in `ADJACENCY-GUARD-V12-EXPANDED-CONTRAST-TEST-AUDIT.csv`. The comparison sheet and script remain in local scratch test materials.
