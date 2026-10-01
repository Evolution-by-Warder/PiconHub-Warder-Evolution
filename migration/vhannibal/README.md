# Vhannibal picon import

This directory records the guarded Vhannibal Motor import into the PiconHub hierarchy. The original one-time transparent-only importer remains documented by `import-report.tsv`, `import-summary.txt`, and `import_vhannibal.py`. The later user-approved Motor27 APPROVED13 set is a distinct, frozen addition described below.

## APPROVED13 production set

APPROVED13 is the authoritative Motor27 set integrated into `warder-master-production`: **295 complete service triplets, 885 PNG total** (transparent, black, and white), each 220×132. The exact approved bytes were copied from `candidate-picons-295-WARDER-APPROVED13-CANDIDATE.zip` (SHA256 `701c0717edbe0e4bacc9a4c6ef552c6e1d56408c6975942e47ca4e2f7ce8f3af`). They were not rerendered, resized, recolored, recompressed, or converted.

Repository paths follow the established layout:

`picons/<satellite-position>/<provider>/{transparent,black,white}/<service-reference>.png`

Before integration, the exact 885 paths were checked against the production tree at `5f3a952449fa13ababbd80ac919e71eef0770bd2`; there were no existing-path collisions. APPROVED13 files are additive.

Committed evidence in this directory:

- `WARDER-Vhannibal-Motor27-APPROVED13-295-TRIPLETS.tsv` — authoritative 295 triplet/path index.
- `WARDER-Vhannibal-Motor27-APPROVED13-885-SHA256.tsv` — per-file byte integrity and image metadata.
- `WARDER-Vhannibal-Motor27-APPROVED13-GIT-BLOB-MANIFEST.tsv` — expected Git blob IDs for exact candidate bytes.

The candidate ZIP remains preserved in ChatGPT Library as the source archive; no duplicate FINAL ZIP is added to this repository. Do not regenerate or modify APPROVED13 assets. The new files receive no new Warder IDs; existing permanent ID records remain unchanged.

## Source and credit

Picon source: **Vhannibal – Picon Vhannibal Motor** (`vhannibal.net`). Provider/service metadata used for classification: public `OpenVisionE2/Vhannibal-settings`, `vhannibal.motor/lamedb`. The source collection credits multiple upstream picon projects/authors; PiconHub-Warder-Evolution preserves those origins and does not claim authorship of the original graphics.

The historical `import-report.tsv` and `import-summary.txt` record accepted and rejected files from the original guarded transparent-only import.
