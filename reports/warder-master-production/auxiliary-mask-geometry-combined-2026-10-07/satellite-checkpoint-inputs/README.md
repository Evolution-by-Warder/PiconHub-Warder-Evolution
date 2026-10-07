# Auxiliary component mask geometry and shape experiment

Input checkpoint: `38e58657e8bed714b6a99922ddaf2d4d16ac5701`.

## Scope and completeness

This run processed all 67 satellite review families, plus the HARMONIC provider regression family (both byte-identical source identities). It exported 1,900 component/variant records for 70 identities across 68 families. It did **not** process the other 832 provider review families because the 11,481,399-byte provider-transparent ZIP could not be read through the connected GitHub file API: the API returned an empty content field for that binary blob. Its pinned source SHA is `93ef555cf09d49a72188c477949d948feaf6416a0fcff047600d36b3a96e4b8f`. Therefore all candidate counts and PNG SHA results below are for the processed subset; no whole-900-family result is claimed.

The satellite transparent input was fetched read-only from `https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/main/assets/warder/downloads/picons/satellites/220x132/piconSat_220x132.zip` and verified against SHA256 `4e8c7d8095aa2c79a30eb1b9af05f4107758a515a31246565da13a6f05da1d5d`. The HARMONIC source fixture is included here and matches SHA256 `7a8173559bd67e2ca863585616bf4a782657d5121f755db9781f688e9a3edb3b`.

## Geometry encoding

`mask-geometry.jsonl.gz` records every processed component with family ID, auxiliary identity, source path/SHA, variant, component ID, engine status/reason, and existing mask signature. It contains a lossless zlib-compressed bit-packed mask (`220x132`, row-major, big bit order), closed boundary contour chain codes, bbox, area, 4-edge perimeter, aspect ratio, bbox fill ratio, 4-connected-background hole count, centroid, compactness, horizontal/vertical projections, and 4-connected subpart count. The compressed masks were decoded and all 1,900 mask hashes, areas, and closed contour perimeters were checked.

## Evidence-only shape rule

`HORIZONTAL_GLYPH_RUN_V1` is a deterministic experimental geometry heuristic; it is not production policy. It accepts a maximal sequence only when its components are low-contrast CHROMATIC, exact isolated masks with no overlap/touch, same recorded representative RGB, aligned top within 3 px and baseline within 2 px, heights within 2 px, positive horizontal gaps no larger than half the adjacent median height, at least four components, combined bbox aspect ratio at least 3, and at least three distinct component bbox aspect-ratio bins. It uses no filename, provider name, OCR, external matching, or classifier.

In the processed subset, 45 component instances across 6 families matched this rule. All six remain partially improvable rather than resolved because each family retains at least one independent review component. The experiment made 7 PNG candidates (the two HARMONIC identity aliases share a source/output hash); all are isolated to the candidate mask and pass output QC. They are review candidates only.

To replay the available scope from this checkout, supply the satellite ZIP at the pinned URL above and run `python3 tools/auxiliary_mask_geometry_export.py --satellite-archive /path/to/piconSat_220x132.zip`. The HARMONIC source fixture is already included.

## HARMONIC sentinel

For `AUX-RF-0301`, BLACK components 3–9 form a seven-piece run: bbox union `[30,55,219,86]`, baseline spread 1 px, top spread 0 px, heights 30–31 px, six distinct bbox-aspect bins, and shared median RGB `[0,39,78]`. Their masks are isolated. They are `STRONG SHAPE CANDIDATE` under the experimental geometry rule. Component 2 has bbox `[1,41,25,100]` and does not join that regular row, so it remains `AMBIGUOUS CHROMATIC`. WHITE component 1 is a separate low-contrast component and also remains ambiguous. The family is only partially improvable; no production decision changed.

## Regression and state

The unchanged production classifier was replayed in memory for 140 BLACK/WHITE variants in the processed scope. Every replay matched the saved candidate SHA, status, and reason. No candidate PNG in the accepted checkpoint was rewritten (`changed PNG = 0` for this scope). The seven experiment outputs are under `experiment-candidates/`; `experiment-output-qc.json` records mask confinement, dimensions, RGBA, post-change contrast, and SHA. `shape-review-sheet.png` shows six families (under the 20-family cap), including source, current and proposed variants, mask and contour overlays.

No production renderer logic, thresholds, templates, existing decisions, production assets, publication metadata, main branch, or FullHDGlass files were changed. TEST202 was not built.
