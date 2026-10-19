# Vhannibal Motor 18 October 2026 incremental import

Guarded incremental import prepared on 2026-10-19 from the official
`PICON Vhannibal Motor 18 ott 2026.zip` release.

## Immutable inputs

- PiconHub baseline: `e4b12049f19a2c154c89a4e9078d2fb6317d32f9`
- Source ZIP SHA256: `a18cb124beb4d3c3748f12abc82a1668331b27ebeb2e48371cc0e53ddd213ab3`
- Matching Vhannibal Motor settings ZIP SHA256: `df935a3155d092c332fc444c40229ba9d340b4e89eeefdd42aa4857118c7f719`
- Approved PiconHub reference: `e4b12049f19a2c154c89a4e9078d2fb6317d32f9`
- Frozen channel V9 renderer commit: `76f2f4be11a30144ece35492dfb188a54bd747d4`
- Renderer SHA256: `f931d3eb703021fa90d6c7934e6902cd1ecb49dd7a8e69e087072a9bf00d1722`
- BLACK MASTER SHA256: `61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe`
- WHITE MASTER SHA256: `c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589`

## Result

- source PNGs inspected: 14,041
- service-reference filenames already present and preserved: 9,355
- new complete `transparent` / `black` / `white` triplets: 174
- new PNG files: 522
- existing files overwritten: 0
- plugin/GUI/skin/template files changed: 0

Variant provenance for the accepted triplets:

- 171 reused a unique pixel-identical BLACK/WHITE result already approved in PiconHub
- 3 passed the frozen channel V9 renderer without a REVIEW result

Fail-closed results remain only in `import-report.tsv.gz`: 1,508 unresolved
providers, 432 unknown namespaces, 101 non-standard sources, 45 source-QC
reviews, 2,423 variant reviews, and 3 invalid filenames. Generic provider
placeholders are explicitly rejected and cannot create new runtime paths.

## Safety contract

The importer checks service-reference basenames globally, refuses every
destination overwrite, preserves accepted transparent bytes, derives the
orbital position from the Enigma2 namespace, and writes only
`picons/<position>/<provider>/{transparent,white,black}/<service-reference>.png`.
`summary.json` and the compressed 14,041-row audit contain the complete
reproducibility record.

## Complete post-import visual QC

After the first random preview exposed a defective WHITE AXN conversion, all
174 imported triplets were inspected side-by-side at full resolution. The
review found 67 low-contrast WHITE files representing 23 unique artworks; all
67 were rebuilt and visually rechecked. The remaining 107 WHITE files passed
unchanged. All 174 BLACK files and all 174 transparent originals passed and
remain byte-for-byte unchanged.

Repairs are bound to exact source-RGBA digests. They use the auxiliary Warder
V9 renderer from commit `76f2f4be11a30144ece35492dfb188a54bd747d4`
(`b841585ca0441251f7e3e10108f1128c0aba69986c8fe2db17f435351723da30`)
plus explicit protected masks for white brand elements located inside coloured
panels (PRIVATE, Eurosport, MTV, FON MUSIC and Cartoon Network). No text or
logo was painted over as an extra layer.

`white-qc-repair.tsv` records every repaired destination and its before/after
SHA256. `white-qc-summary.json` records the full-scope validation totals, and
`repair_white_qc.py` is the digest-bound reproducibility tool.
