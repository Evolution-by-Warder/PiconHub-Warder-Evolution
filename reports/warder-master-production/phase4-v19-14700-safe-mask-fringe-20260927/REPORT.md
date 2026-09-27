# Phase 4 — #14700 Safe-Mask Completeness / Fringe Significance Test

**Scope:** diagnostic visual-completeness test only. Production ownership guard remains frozen; no production picon was written.

## Variants

- **M0:** 1224 pixels from the already confirmed full wordmark group (solid achromatic core plus its 154 preconfirmed tonal attachments). This is the sole artifact labeled diagnostic candidate; it is not approved.
- **M1:** M0 plus the already diagnosed 40 safe one-hop low-alpha pixels. This is a diagnostic extension only, not equivalent to M0 evidence.
- **Unowned population:** 259 ambiguous + 1 protected/other remain untouched in M0/M1.
- **Full-perimeter reference:** M0 plus all 300 subthreshold perimeter pixels. Hypothetical visual/math reference only; not a safe mask or candidate.

Target is frozen `(16,16,16)`. Only RGB in each stated mask is changed in the source-derived layer; source alpha is bit-identical. Candidate outputs copy CURRENT WHITE outside their edit-mask coordinates, so variant changes outside the mask are zero.

## Pixel differences from full-perimeter reference

All delta distributions below use rendered 8-bit RGB pixel outputs; luminance uses sRGB inverse transfer then linear Rec.709 scaled 0–255. Statistics include every tested perimeter pixel, including zero deltas; per-alpha and per-glyph detail is in JSON.

### M0 vs full reference
- Compared scope: 300 pixels; changed visible pixels: **269**.
- RGB ΔL∞: max 8.0000, mean 1.8567, median 1.0000, p90 4.0000, p95 5.0000.
- Linear Rec.709 luminance delta: max 12.0089, mean 2.4693.

### M1 vs full reference
- Compared scope: 260 pixels; changed visible pixels: **241**.
- RGB ΔL∞: max 8.0000, mean 1.9500, median 1.0000, p90 4.0000, p95 5.0000.
- Linear Rec.709 luminance delta: max 12.0089, mean 2.5977.

### M0 vs CURRENT WHITE
- Compared scope: 1224 pixels; changed visible pixels: **1178**.
- RGB ΔL∞: max 239.0000, mean 119.2018, median 133.5000, p90 239.0000, p95 239.0000.
- Linear Rec.709 luminance delta: max 253.6787, mean 124.8602.

### M1 vs CURRENT WHITE
- Compared scope: 1264 pixels; changed visible pixels: **1206**.
- RGB ΔL∞: max 239.0000, mean 115.4691, median 126.0000, p90 239.0000, p95 239.0000.
- Linear Rec.709 luminance delta: max 253.6787, mean 120.9607.

## Alpha-band detail: M0 vs full reference

| Alpha | Pixels | Visible RGB changes | Mean RGB ΔL∞ | p95 RGB ΔL∞ | Max luminance delta |
|---|---:|---:|---:|---:|---:|
| 1-3 | 95 | 77 | 1.337 | 3.000 | 5.064 |
| 4-7 | 46 | 35 | 1.435 | 4.000 | 6.872 |
| 8-15 | 56 | 56 | 1.214 | 2.000 | 12.009 |
| 16-23 | 80 | 78 | 2.462 | 5.000 | 11.542 |
| 24-31 | 23 | 23 | 4.304 | 6.000 | 10.498 |

## Glyph detail: M0 vs full reference

| Reconstructed glyph ID | Perimeter pixels | Visible RGB changes | Mean RGB ΔL∞ | p95 RGB ΔL∞ | Max luminance delta |
|---|---:|---:|---:|---:|---:|
| 6 | 42 | 37 | 1.548 | 4.000 | 11.542 |
| 7 | 47 | 46 | 2.574 | 6.000 | 8.965 |
| 8 | 51 | 48 | 1.882 | 3.500 | 12.009 |
| 9 | 45 | 39 | 1.156 | 2.000 | 6.688 |
| 10 | 114 | 99 | 1.956 | 4.000 | 10.404 |
| MULTI | 1 | 0 | 0.000 | 0.000 | 0.000 |

## Fringe and edge structure

M0: 48 structurally flagged perimeter pixels in 36 8-connected components; largest=3 px, longest estimated 8-connected segment=3 px, singleton components=25.
M1: 41 structurally flagged untouched perimeter pixels in 31 components; largest=3 px, longest estimated segment=3 px, singletons=22.

A structural flag means a perimeter pixel is outside the luminance interval between a recolored edge-support pixel and the MASTER pixel, is a local 8-neighbor extremum, or reverses the directional luminance gradient. It is not a perceptual threshold and does not classify ownership. Five per-glyph profiles choose the largest measured brightness excess for inspection; sequences and all source/output values are in the CSV/JSON.

## Preservation and controls

M0/M1/reference alpha equals CURRENT WHITE bit-for-bit; source-derived alpha equals source-fit alpha bit-for-bit. The M0/M1 masks intersect frozen chromatic core, true-AA, and ambiguous boundary masks at 0 pixels. All 259 ambiguous and the 1 protected/other low-alpha pixels remain unchanged in M0/M1. One mask pixel was already `(16,16,16)`; every mask pixel is at the target afterward, and no RGB change escaped its mask. Production writes=0; source and MASTER unchanged.

#14607 receives no mask or candidate. Its six low-alpha pixels remain protected; perceptual similarity cannot override protected ownership. #14593 stays REVIEW; #14597 stays cautious REVIEW; Digi Slovakia remains PASS with zero changes; both genuine two-tone controls remain two-tone. #14599 remains CLOSED/TABU and was not accessed.

## Interpretation

**Category B — difference exists but is localized/minor.** M0 differs from the full-perimeter reference at 269/300 visible pixels; RGB ΔL∞ median is 1, p95 is 5, and maximum is 8. The changed pixels form 64 8-connected components; the largest partial-stroke segment is 27 pixels, not a glyph-enclosing ring. Structural luminance-extremum/reversal flags are smaller (48 pixels in 36 components, largest 3). In nearest-neighbor zooms the difference is a subtle edge-tone variation, without a clear continuous bright halo. This evidence concerns only this diagnostic output; the candidate remains unapproved and awaits Štefan’s visual decision. The full-perimeter reference is hypothetical and is not a safe mask. No ownership rule was created or relaxed.

## Hashes

| Artifact | SHA256 |
|---|---|
| Source | `9fa6f6a84bb9e1a98802e638f94d0f693757697648d1167d1b9f3f31fb7724c3` |
| CURRENT WHITE | `e2b1eaf5cdad1acf3b251c7d5173a7bf0066ca3ea1a6eff9a60bd8aa02c76916` |
| WHITE MASTER | `c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589` |
| M0 diagnostic candidate PNG | `581206f0088f40ace49afad5fdfd46377216fb06143588da926f0aa270311242` |
| M1 diagnostic simulation PNG | `58d206a5784fc41378ff47968ad0fe1f80e8af981541c3a080c4608873788784` |
| Full-perimeter diagnostic reference PNG | `44ae10da6f8f4efae98e652aadd46c69ed5da8d028ea601755c1d6d57e8dd929` |

## Artifacts

Only `candidate/DIAGNOSTIC-SAFE-MASK-ONLY-14700-WHITE.png` is designated a candidate. M1 and the full-AA image are simulation/reference PNGs in their own directory. Comparison JPGs and difference maps are under `diagnostics/`. The 560-row fringe-edge CSV records M0 and M1 pixel-level edge measurements; the 300-row delta CSV records M0/M1/reference RGB values and per-pixel differences.
