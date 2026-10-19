# Vhannibal Motor 13 incremental import

Guarded incremental import prepared on 2026-10-19 from the archive
`PICON Vhannibal Motor 13 set 2026.zip`.

## Immutable inputs

- PiconHub baseline: `febab1e22db9a7f163dc4898f72df4d65d89ea03`
- Source ZIP SHA256: `1ceabf82a4626ac5b933b2554bcaf86acc328746c20aa8a26778b533f2a1b1a4`
- Matching Vhannibal settings: `7d6e75bead934e0307ea54ba0663cdb3e06d7063` (2026-09-13)
- Approved channel QC reference: `76f2f4be11a30144ece35492dfb188a54bd747d4`
- Frozen channel V9 renderer: `tools/rebuild_master_catalog.py` from the same reference commit
- Renderer SHA256: `f931d3eb703021fa90d6c7934e6902cd1ecb49dd7a8e69e087072a9bf00d1722`
- BLACK MASTER SHA256: `61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe`
- WHITE MASTER SHA256: `c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589`

## Result

- source PNGs inspected: 13,903
- service-reference filenames already present and preserved: 8,338
- new complete `transparent` / `black` / `white` triplets: 1,224
- new PNG files: 3,672
- existing files overwritten: 0
- plugin/GUI files changed: 0

Variant provenance for the 1,224 accepted triplets:

- 190 exact service-reference + RGBA matches reused from the approved QC reference
- 1,017 unique pixel-identical transparent logos reused their already approved BLACK/WHITE result
- 17 new triplets passed the frozen channel V9 renderer without a REVIEW result

Fail-closed results were retained in `import-report.tsv.gz`: unresolved provider,
unknown namespace, non-220×132 source, source-QC REVIEW and BLACK/WHITE REVIEW
items were not added to the runtime picon tree.

`summary.json` contains the machine-readable totals and all pinned provenance.
`import-report.tsv.gz` contains one row for every source PNG.

## Safety contract

The importer compares service-reference basenames globally before processing,
refuses every destination overwrite, preserves the accepted transparent source
bytes, writes only the canonical
`picons/<position>/<provider>/{transparent,white,black}/<service-reference>.png`
architecture, and never touches plugin code or GUI graphics.
