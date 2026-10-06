# Auxiliary family contrast-policy pass

Input is the accepted exception-family checkpoint `6ac15b98028ff344c1980cb4ea461a94d22894b1`. This pass classifies existing machine reasons under `docs/PICON-MASTER-QUALITY-PLAN.md`; it does not repeat SHA deduplication, render, change engine code, or modify PNGs.

- Engine-review families: 903
- Policy auto-fix candidates: 0
- Human-review families: 903
- Source-QC: 3 families / 4 identities
- Source-unresolved: 320 families
- The existing engine already auto-fixes clearly isolated achromatic components. Remaining reasons identify protected chromatic and/or two-tone components, or source-QC holds. The report does not persist the mask geometry or semantic text identity needed to apply the plan’s text-aware exception safely.
- Therefore no renderer call was made; output QC is not applicable. The prior reduced sheets remain in the parent checkpoint and are indexed by `remaining-review-sheets.json`.
