# DAB / DAB+ — PiconHub Warder Evolution

Development candidate **0.1.26**, branch `feature/universal-radio-picons`, PR #11.
Production remains **0.1.25**. Nothing in this directory changes the stable update feed.

## Current data

The receiver mapping contains **52 station labels and 82 exact ten-field references** from six DAB-over-DVB bouquets. Authentic artwork covers **51 labels / 80 references**, each in Transparent, White and Black: **240 PNG files, 220×132**. Regional labels and service references stay separate even where the broadcaster shares the same logo. **ASA DE (two references) is unresolved**; no invented replacement is installed and existing picons remain intact.

- `catalog/DAB_radio_picon_mapping.csv`: original receiver mapping; imported verification flags describe its earlier placeholder stage.
- `catalog/artwork.json`: selected source URLs/revisions, source hashes, contrast operations and frozen master hashes.
- `sources/`: pinned originals, provenance and upstream licence.
- `preview/authentic/`: genuine station logo candidates, not the old station-name placeholders.
- `preview/review/`: seven contact sheets, all 51 labels in three styles.
- `catalog/authentic-preview.json`: output hashes, exact identities and explicit pending visual acceptance.
- `packages/`: deterministic ZIPs, flat exact-reference filenames, one archive per style.
- `catalog/release-candidate.json`: candidate package hashes and immutable Git URLs. **Rejected by the receiver installer while status is candidate.**
- `verified/` and production `catalog/release.json`: reserved for the approved distribution.

## Runtime behavior

Choose **DAB / DAB+ (220×132)** in the existing satellite/source selector. It can be combined with normal satellite sources; no fake orbital position or separate destination is created. The configured picon directory is used, normally `picon/`.

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
