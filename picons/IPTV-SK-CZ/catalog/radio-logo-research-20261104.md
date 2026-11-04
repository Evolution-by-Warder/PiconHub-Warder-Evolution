# Warder Radio — radio-picon discovery, 4 November 2026

**Scope:** Research and identity validation only. No production archives or existing Warder images are changed. The purpose is to extend *Warder quality* while preserving official station identity and the approved Transparent, White and Black artwork variants.

## Verified baseline

- `warder-radio-picons-20261104-r5.json`: 320 SK/CZ stations, 318 covered by original Warder picons, **2 uncovered**; 356 reference PNGs in **each** of 9 public style/size archives, all nine archive checks reported verified. The full country package catalogue is separate from logo coverage.
- `catalog/missing-artwork.csv` independently names the same two services: **Radio FRM** and **Radio Student**.
- `catalog/artwork-sources.json` has 321 research rows; 253 rows have source-logo URLs and 68 have no source-logo URL. **68 does not mean 68 missing Warder picons**: already-approved owner-supplied and alias graphics can be present without a current external source record.
- `catalog/package-inventory.json` describes an **older 229-reference-per-variant build**; do *not* use that index to claim the latest 356-reference packages are missing 107 graphics. Reconcile with the latest published archive inventory before making new assets.

## Highest priority: two exact missing references

### 1. Radio FRM, CZ — probable Fajn Rock Music alias

- Missing service: `4097:0:2:9423:81E4:EC:0:0:0:0`
- Existing original stream: `http://icecast1.play.cz/fajnrock128.mp3`
- Related named service **Fajn rock music**: `4097:0:2:2FFE:2E69:EC:0:0:0:0`, `http://icecast2.play.cz/fajnrock192.mp3`
- Both paths use the same `fajnrock` program identity but different bitrate/host. This is **an alias candidate**, not yet a validated cross-reference.
- Original operator's website for brand and logo review: https://www.fajnrockmusic.cz/ . A broadcaster-branded app icon exists on its [App Store page](https://apps.apple.com/us/app/fajn-rock-music/id6444030528).
- **Next gate:** verify live stream/program identity (not only URL similarity); compare the current approved Warder Fajn rock master, if it exists, and use its exact rendered bytes under the extra service reference. If no approved master exists, source and review official logo before rendering.

### 2. Radio Student, CZ — probable university Radio R alias

- Missing service: `4097:0:2:57EC:2C91:EC:0:0:0:0`
- Existing original stream: `http://radior.video.muni.cz:8000/FSS_mp3-64.mp3`
- Related **Radio R** entry: `4097:0:2:A90:A8A5:EC:0:0:0:0`, `http://radior.video.muni.cz:8000/FSS_mp3-128.mp3`
- Same `radior.video.muni.cz` host and `FSS_mp3` path with bitrate suffix strongly suggests one program, **pending live validation**.
- Authoritative station source: [Masaryk University — Radio R](https://www.muni.cz/portal-pro-studujici/zapojeni-do-komunity/studentske-spolky/radio-r); university logo [official asset](https://www.muni.cz/media/16680/radior.png?anchor=center&bgcolor=fff&heightratio=1&width=1170); station [Faculty of Social Studies page](https://medzur.fss.muni.cz/studentska-media/radio-r).
- **Next gate:** confirm this archived `Radio Student` stream truly serves the current Radio R program. Do not accidentally substitute the unrelated Slovenian **Radio Študent** or any other station named `Student`.

## Warder production rules

1. Identity before graphics: verify exact stream, provider and service-reference aliases; preserve all existing station entries, favourites and primary reference names.
2. If an existing owner-approved Warder master matches, **reuse** it, avoid duplicate artwork authoring. If a real new logo is required, take primary evidence from the broadcaster, review trademark-safe proportions, legibility and alpha.
3. Produce **3 Warder styles (Transparent / White / Black) × 3 sizes (50×30, 220×132, 400×240)** for every confirmed new reference, in the existing package directories.
4. Run master-template SHA-256 checks, transparent edge checks, source-file provenance, a contact sheet, 9 archive inventories and safe receiver-plugin merge/install checks. Do not overwrite unrelated picons.
5. No automatic unreviewed radio-logo scraping, third-party `Radio X` substitutions, copyrighted image redistribution or speculative service aliases.
6. Keep this report as a tracking note until exact identities and the *latest published 356-reference archive baseline* are revalidated. Research-only at this stage.

**Proposed work order:** the two listed missing CZ services first; then broader countries from the current country manifest, using official station branding, validated aliases and the frozen Warder masters as separate evidence layers.
