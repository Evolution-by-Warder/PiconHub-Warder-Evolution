# DVB-T CZ/SK — shared Warder packages

2674 original receiver filenames, 203 unique original transparent logos. Transparent source bytes are preserved. White and black are derived from those same logos, fitted proportionally inside the immutable Warder MASTER frames without recolouring, guessed identities or invented artwork. Original artwork and trademarks retain their authorship. The original collection is historical and does not guarantee complete current broadcasting coverage.

`catalog/variants.json` records original and resulting PNG hashes, archive/part hashes, source provenance, exact frozen master hashes and the owner instruction of 27 October 2026. The live package index is shared by FullHDGlass and PiconHub; these data packages do not enlarge either IPK.

Reproduction: assemble the six immutable transparent ZIP parts from FullHDGlass commit `176bf39ebe07a35a466ce29c7190f76704934387` under `assets/warder/downloads/picons/channels/`; verify the full transparent SHA256 recorded in the catalog. Run `python3 picons/DVB-T/build_variants.py --source TRANSPARENT.zip --masters plugin/artwork/templates/picons --output ARTIFACTS`. Pillow is required only on the build host. The output contains two deterministic ZIPs, SHA256-addressed parts, exact per-PNG records and an internal review sheet.

For actual installation verification, place the intended shared manifest in ARTIFACTS/manifest.json and run `python3 picons/DVB-T/verify_install.py --artifacts ARTIFACTS`. This uses the real receiver planning/downloading/installing engine, checks all 2674 installed file hashes per style and preservation of unrelated files.
