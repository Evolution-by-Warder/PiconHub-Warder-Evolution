# BLACK/WHITE QC batch 004

- Remote baseline checkpoint: `9674c13692cf7f03c9b982e20286d2880546c8a0`.
- Reviewed and repaired 5 variants: 2 BLACK and 3 WHITE (Spectrum, CGTN, Kanal 1 Sport, Love Nature, hirTV).
- Color changes were made to hue-matched pixels in temporary in-memory copies of the transparent sources; checked-in transparent PNGs were not written.
- Rendering used the pinned production renderer and exact MASTER templates. Before-render matched current output byte-for-pixel for both styles on all five identities.
- Recolored only each named wordmark. Brand hue, source alpha, logo geometry, and all pixels outside the selected source mask were preserved.
- Visual comparison and per-file hashes are in this directory.
- Last processed: `0.8w/digislovakia/black/1_0_1_4A6_3_1_E080000_0_0_0`. Next: next flagged candidates in review sheets 001–013.
