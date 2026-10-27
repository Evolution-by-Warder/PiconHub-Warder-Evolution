# DAB / DAB+ picons — Warder Evolution

This directory is the designated location for **DAB/DAB+ station-reference picons** in the PiconHub repository.

## Layout

- `picons/DAB/preview/` — development-only station-name fallback artwork, **not** approved MASTER V9 or authentic station logos.
- `picons/DAB/verified/` — future approved Warder MASTER V9 artwork with verified station logos, provenance and licensing.
- `picons/DAB/catalog/` — mapping manifests for Enigma2 service references.

Picon filenames must match the **exact ten-field Enigma2 service reference**, separated by underscores, with a `.png` extension (for example `4115_0_2_...`). Do not use a generic logo for unrelated regional stations. Multiple service references for one station may point to identical approved artwork, but must each have their own correctly named file.

## Deployment

Enigma2 renderers typically look in the configured picon directory, **not** in the Git repository's `picons/DAB` path. The plugin must explicitly copy the approved `verified/*.png` files to its configured picon destination using their exact basenames. This repository folder alone does not activate or install icons.

Do **not** point production downloads at `preview/` or treat its placeholders as official logos. Source license and original artwork provenance must be documented before publishing verified artwork. TV-only synchronization must not change.

Status: development branch `feature/universal-radio-picons`. No production deployment approved.
