> Provenance of picons used by PiconHub Warder Evolution and the shared skin catalog. This is an artwork/source-history record, not the current receiver configuration. Current plugin behavior is documented in [plugin/PRODUCTION.md](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/blob/main/plugin/PRODUCTION.md).

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

## First post-import visual QC (superseded for ghost/underlay acceptance)

After the first random preview exposed a defective WHITE AXN conversion, a
first pass selected 67 low-contrast WHITE files representing 23 unique
artworks. Its historical report is retained, but its acceptance wording is no
longer authoritative: it wrote some candidates even though the raw Warder V9
engine returned `REVIEW`, and a later enlarged preview exposed residual light
artwork below the dark conversion.

The first-pass repairs are bound to exact source-RGBA digests. They use the auxiliary Warder
V9 renderer from commit `76f2f4be11a30144ece35492dfb188a54bd747d4`
(`b841585ca0441251f7e3e10108f1128c0aba69986c8fe2db17f435351723da30`)
plus explicit protected masks for white brand elements located inside coloured
panels (PRIVATE, Eurosport, MTV, FON MUSIC and Cartoon Network).

`white-qc-repair.tsv` records every repaired destination and its before/after
SHA256. `white-qc-summary.json` records the full-scope validation totals, and
`repair_white_qc.py` is the digest-bound reproducibility tool.

## Engine ghost/underlay gate — authoritative final WHITE QC

`scan_repair_white_ghosts.py` reruns the Warder engine and then scans all 174
WHITE outputs for a split logical artwork: darkened pixels adjacent to
unchanged light source pixels. A raw engine `REVIEW` is never promoted to PASS
automatically. Every remaining visual signal must be either repaired and
rescanned or bound to an exact source-RGBA digest with a recorded protected
brand reason; an unresolved `VISUAL_REVIEW` is a hard failure.

Final result:

- 174/174 imported WHITE outputs scanned;
- 92 `PASS`, 77 `PASS_PROTECTED`, 5 `PASS_REPAIRED`;
- 0 unresolved `VISUAL_REVIEW`;
- 5 defective delta WHITE outputs fixed: Asharq Bloomberg plus four OSN
  wordmarks (`showcase classics`, `movies family`, `movies horror`,
  `movies comedy`);
- 12 catalog WHITE files repaired after including pixel-identical existing
  identities;
- transparent, BLACK, both MASTERs, plugin GUI and skin files unchanged.

The repair changes source artwork pixels before compositing onto the immutable
WHITE MASTER. It does not add a covering text layer. OSN masks are selected by
complete neutral logical components seeded by the engine; the coloured `tv`
mark is excluded by content rather than a coordinate rectangle. Asharq is an
exact-digest-bound monochrome wordmark repair.

Authoritative evidence:

- `white-ghost-qc-repair.tsv` — all 12 before/after SHA256 records and raw
  engine REVIEW reasons;
- `white-ghost-qc-scan.tsv` — one final scanner row for every imported WHITE;
- `white-ghost-qc-summary.json` — final counts and immutable-file assertions.
