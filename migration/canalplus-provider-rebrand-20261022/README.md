# CANAL+ provider rebrand preparation — 2026-10-22

This directory prepares the canonical CANAL+ provider artwork requested for
the future replacement of Skylink/freeSAT branding. It does **not** activate a
provider rename and does not overwrite existing SKYLINK or FREESAT identities.

## Source and output

- exact official CANAL+ Group PNG:
  `https://www.canalplusgroup.com/uploads/CANAL_logo_25cd1ffd9f.png`
- pinned source SHA256:
  `9df59b91e2c73f5444b34da25f96a47190db5cca20568c3358b6ce71c078154c`
- canonical filename: `CANAL+.png`
- prepared variants: transparent artwork, BLACK MASTER, WHITE MASTER
- output format: PNG/RGBA, 220×132

The wordmark shape is extracted from the official 1920×1080 source, fitted
proportionally inside the 8 px safe area and centred. The approved MASTER
templates are loaded byte-for-byte and are never modified.

## Activation boundary

Activation remains pending until live provider/service metadata proves the
exact identities and mappings. The preparation must not guess references,
rename provider directories, alter the plugin GUI/skin, or silently replace
legacy SKYLINK/FREESAT assets.

`manifest.json` records source/output SHA256 values and immutable MASTER pins.
`build_canalplus_provider_logo.py` reproduces the prepared pair from the pinned
official source.
