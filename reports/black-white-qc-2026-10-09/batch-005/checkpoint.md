# BLACK/WHITE QC batch 005

- Remote baseline: batch 004 commit `80a50236df258f83f28c1d0d53d8aabf109ff96d`.
- Reviewed and repaired 5 variants: 1 BLACK and 4 WHITE.
- Epic Drama emblem and DRAMA line were brightened; DRAMA antialiased coverage was smoothly increased 3× (capped at 255) in the temporary render mask because its original opacity made it unreadable on BLACK. The EPIC plaque and letters remain unchanged.
- SuperOne correction is confined to O/N/final E of ONE. SUPER and the turquoise accent remain unchanged.
- Rendering used the pinned renderer and MASTER files. Transparent sources and MASTERs were not written. The output alpha changes only for Epic Drama's DRAMA glyph; other geometries/alpha are unchanged.
- See exact before/after and SHA256 audit in this directory.
- Last processed: `0.8w/digitv/white/1_0_1_DE8_C_1_E080000_0_0_0`; next: next visually flagged candidate.
