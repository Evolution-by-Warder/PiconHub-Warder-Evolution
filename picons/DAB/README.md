# DAB / DAB+ — PiconHub Warder Evolution

**Shared production picon data — updated on 27 October 2026.**
The owner requested activation of the corrected DAB set and the existing automatic plugin updater. Publication approval is recorded in `catalog/publication-approval.json`; physical receiver validation is recorded separately.

## Current data

The receiver mapping contains **52 station labels and 82 exact ten-field references** from six DAB-over-DVB bouquets. Authentic artwork covers **52 labels / 82 references**, each in Transparent, White and Black: **246 PNG files, 220×132**. Regional labels and service references stay separate even where the broadcaster shares the same logo. **ASA DE is included at both verified 19.2E and 23.5E references.** The exact official vector logo matches the owner-supplied image. All original 80 picons per style remain byte-identical.

- `catalog/DAB_radio_picon_mapping.csv`: original receiver mapping; imported verification flags describe its earlier placeholder stage.
- `catalog/artwork.json`: selected source URLs/revisions, source hashes, contrast operations and frozen master hashes.
- `sources/`: pinned originals, provenance and upstream licence.
- `preview/authentic/`: rendered station logos used by the approved ZIP set; not the old station-name placeholders.
- `preview/review/`: seven contact sheets, the original 51 labels in three styles; ASA source and output hashes are in `asa/approval.json`.
- `catalog/authentic-preview.json`: build output hashes and exact identities. Original review flags are retained; subsequent owner publication authorization is in publication-approval.json.
- `packages/`: deterministic ZIPs, flat exact-reference filenames, one archive per style.
- `catalog/release-candidate.json`: candidate package hashes and immutable Git URLs. **Retained as a historical candidate; the receiver uses release.json.**
- `catalog/release.json`: approved runtime catalog, pinned to immutable ZIP assets.
- `catalog/publication-approval.json`: owner authorization and exact artwork-manifest hash.
- `verified/`: reserved offline export directory; runtime installation uses the approved ZIP catalog.

## Runtime behavior

Choose **DAB / DAB+** in the existing satellite/source selector. It can be combined with normal satellite sources; no fake orbital position or separate destination is created. The configured picon directory is used, normally `picon/`.

DAB requires 220×132 and a mode including radio. TV-only operation does not request DAB packages. TV/radio bouquet mode intersects the package with the receiver's exact references. DAB-only full mode installs all verified DAB references. Native satellite selection filters mixed full-mode packages by position.

The importer validates repository and immutable commit URL, archive byte count and SHA256, every file hash and dimensions, and ZIP members. Network work stays in the existing background runner. All downloads stage before installation; cancellation or validation failure leaves existing picons untouched. Unknown radio picons are retained. Credentials and private stream URLs are never included in filenames or uploaded.

## Reproduce and review

On a build host with Pillow and CairoSVG (neither is added as a receiver dependency):

```sh
PYTHONDONTWRITEBYTECODE=1 python3 picons/DAB/build_artwork.py
PYTHONDONTWRITEBYTECODE=1 python3 picons/DAB/build_review.py
python3 picons/DAB/build_packages.py --revision <40-character-artwork-commit>
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=plugin/src python3 -m unittest discover -s plugin/tests -v
python3 plugin/tools/build_ipk.py --output plugin/build --revision <source-commit>
```

`build_artwork.py` verifies frozen master/source hashes, fits logos proportionally and checks that master pixels outside the overlay remain exact. Contrast changes use explicit vector paths or alpha-connected component IDs; protected components and alpha remain unchanged. The package builder checks output hashes and produces repeatable ZIP bytes.

Review follows `plugin/artwork/QUALITY.md`. `build_packages.py --approval <json>` requires `approved_master_v9: true`, an explicit owner confirmation and the exact SHA256 of `authentic-preview.json`. Only then can it generate `release.json` with status `verified`. Do not fabricate this approval or point production at previews. Asset ZIPs must already exist at the pinned commit before publishing the catalog.

An IPK candidate includes the runtime code, not the logo sources, preview images or ZIP archives. Receiver testing of the new PiconHub candidate remains a separate validation step. The owner has confirmed radio picons display in both FullHDGlass infobars (27 October 2026).

## Recorded owner acceptance — 27 October 2026

The corrected Absolut GERMANY sample was explicitly accepted by the owner ("teraz je uz perfektne"). The accepted composition uses the same official transparent source, including its original white circular backing, on Transparent, White and Black. The same rule is applied to BELLA, HOT and TOP 2000. See `catalog/owner-decisions.json` for the immutable sample/source hashes and the exact scope of this decision. This records the shown sample and composition rule; remaining catalog review and receiver validation are tracked separately.

## Satellite subsets and scan research — 27 October 2026

DAB radio belongs to its owning satellite package, like other radio services. Approved identical PNGs are grouped at `picons/19.2e/dab/{transparent,white,black}` (52 references/style) and `picons/23.5e/dab/{transparent,white,black}` (30/style). The owner explicitly requested these transport folders; provider identities and exact reference names are retained. Git reuses the existing content objects.

Full satellite packages were updated by FullHDGlass workflow 40509308490: all three styles preserve 3,687 existing images on 19.2E and 2,189 on 23.5E. Added DAB counts are 51 and 29 respectively. The live skin channel catalog serves these packages without requiring a skin IPK update. PiconHub 0.1.29 places DAB and DVB-T first and corrects the false unavailable DAB label.

Official OpenATV scan support: `catalog/openatv-feeds.json` pins eight satellite positions and 52 feed definitions. Static transponder data does not contain every station SID: OpenATV reads station IDs and labels live from FIC. Further station picons require independently verified SID/EID metadata, not guessed reference aliases.


## ASA DE — owner-directed completion

The official [ASA SVG](https://www.dabplus.de/wp-content/themes/dabplus21/assets/svg/asa-logo.svg) matches `sources/owner/asa.jpg`. Its geometry, colours and complete Automatic Safety Alert tagline are preserved on the frozen Warder masters. `asa/artwork/` contains 50×30, 220×132 and 400×240 in Transparent, White and Black. `asa/approval.json` records exact reference names, source/master/output hashes and owner authorization. `asa/reproduce.py --output /tmp/asa-rebuild` reproduces this append-only update from its immutable baseline with Pillow and CairoSVG. All previously approved DAB PNG bytes are retained; the three public ZIPs and all 246 member hashes were independently verified before activating release.json. Satellite/provider integration is published separately through the shared FullHDGlass channel manifest, without a new IPK.

The ASA satellite/provider publication is live at FullHDGlass commit `d4042056e8833cfaa8f1c8a09b2dffe66a204080`: **39 archives** across 19.2E, 23.5E, legacy Skylink, Canal+ SK and Canal+ CZ. Every archive received its one exact orbital ASA reference in each available size/style. All original PNGs were preserved; **69 public parts** passed size/SHA256 checks and **36 receiver plans** passed validation. [Publication evidence](https://github.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/blob/d4042056e8833cfaa8f1c8a09b2dffe66a204080/assets/warder/asa-radio-publication.json) · [Successful workflow](https://github.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/actions/runs/40582905419). Standalone DAB remains 220×132; the satellite/provider archives additionally support the existing 50×30 and 400×240 selections. No runtime/IPK version changes.
