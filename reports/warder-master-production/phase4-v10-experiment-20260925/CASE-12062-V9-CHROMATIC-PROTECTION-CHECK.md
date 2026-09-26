# Case #12062 BLACK — V9 chromatic-protection check

Date: 2026-09-26

## Scope

A targeted isolated check was run after the V4 audit listed #12062 as a BLACK fixture with a scratch candidate differing from the current output. This check regenerated only this case from its transparent original using the frozen V9 fit and classifier. It did not reproduce or apply the old V4 scratch candidate.

## Result

- Source: `picons/5.0w/rai/transparent/1_0_16_404_1_217C_DDE0000_0_0_0.png`
- Source SHA256: `d42da6aaf0038082097fb291589aa0af88c29fb896ecd82b1d7cdb545a965bc3`
- BLACK output: `picons/5.0w/rai/black/1_0_16_404_1_217C_DDE0000_0_0_0.png`
- V9 classification: REVIEW; low-contrast pixels occur in chromatic components.
- V9 candidate SHA256: `c0970dba88586f9729e787ce188f049f9402e6595bd5d3f55f19f8894e29bfb5`
- Candidate matches the current BLACK PNG byte-for-byte; displayed pixel difference is 0.
- Alpha is unchanged. The V9 run reports 6,478 protected source pixels and 24 safely isolated contrast pixels changed.
- The visible source colors are green (channel-range 96–140), outside V9's achromatic threshold of 18. Keep this colored wordmark protected; do not broaden the achromatic threshold to force a BLACK correction.
- The V4 scratch script and candidate artifact are not present in the repository or current scratch workspace. Its audit counts alone do not identify a reproducible or approved candidate.

This is a technical regression check, not a user visual approval. No repository PNG, source, MASTER, generator code, or `main` was changed. No full-catalog rebuild was run.
