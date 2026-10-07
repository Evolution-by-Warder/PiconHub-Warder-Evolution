# Auxiliary publishability gate

Strict preparation output based on the accepted auxiliary run. The isolated `safe-candidate-tree/` contains only the 173 complete provider/satellite triads whose transparent source passed source QC, whose native geometry was preserved, whose BLACK and WHITE statuses are PASS/AUTO-FIXED, and whose output PNGs pass exact SHA, 220x132 RGBA, and decode checks.

- Provider: 172 complete identities; 973 review-blocked; 190 source-unresolved.
- Satellite: 1 complete identity; 68 review-blocked; 200 source-unresolved.
- Exclusion manifest covers every other identity with family ID, class, and exact reason.
- Tree QC: 519 files, no missing variants, collisions, invalid PNGs, wrong dimensions, symlinks, REVIEW items, or SOURCE-UNRESOLVED items.

This is a non-production candidate checkpoint. It does not update downloads manifests, production ZIPs, or releases.
