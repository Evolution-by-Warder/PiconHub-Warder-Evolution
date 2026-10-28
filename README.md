# PiconHub Warder Evolution

Warder's original futuristic Enigma2 plugin and the shared Warder picon source database.

## Current state — 2026-10-28

**PiconHub Warder Evolution 0.1.30** is the user-approved production baseline. The native Warder interface retains the functional work of s3n0 and Chocholousek. Runtime: `/usr/lib/enigma2/python/Plugins/Extensions/WarderPiconHub/`.

Use the [plugin guide](plugin/README.md), [production record](plugin/PRODUCTION.md), [release manifest](plugin/production.json) and [validation status](plugin/BUILD-STATUS.md). They record the final behavior, automatic plugin updates, package identity, language support and precise receiver-test scope. Earlier rebuild plans are historical and do not override this baseline.

## Plugin data

- `picons/`: source PNGs, organized by satellite, provider and transparent/white/black style.
- `plugin/artwork/templates/`: original frozen V9 BLACK/WHITE MASTER assets.
- `plugin/artwork/provenance/`: provenance and approval evidence for plugin picons.
- `plugin/`: current Enigma2 plugin, build tools, production record and preserved recovery inputs.

The live downloadable ZIP catalog and archive parts used by the skin are in **Evolution-by-Warder/FullHDGlass-Warder-Evolution**, backed up separately in the same set.

Do not redesign approved artwork, renumber identities, invent service mappings or silently replace existing PNGs. Third-party picon artwork retains its original provenance and authorship. Retiring a plugin does not erase credits for reused artwork.

Existing satellite picon data and frozen MASTER assets are preserved.

The repository and Releases are dedicated to the Enigma2 receiver plugin. Plugin picons, approved artwork provenance and templates form its shared picon source data.

The root `picons/` address remains compatible with installed plugin versions that use it for the recent-picons gallery. Current source, artwork references, tests, build and update tools are grouped under `plugin/`. Retired development checkpoints are available in Git history.

## DAB / DAB+ in 0.1.29

Choose **DAB / DAB+** in the source selector. The approved catalog covers **52 labels / 82 exact receiver references** in Transparent, White and Black. Picons install into the configured picon directory; unknown radio picons are retained. See the [DAB guide](picons/DAB/README.md), [live catalog](picons/DAB/catalog/release.json) and [owner authorization](picons/DAB/catalog/publication-approval.json). ASA DE is included using the official vector logo matching the owner-supplied reference. All 80 earlier picons per style remain byte-identical. [ASA source, variants and checks](picons/DAB/asa/approval.json). ASA is included only in standalone DAB and full 23.5E downloads, with provider packages explicitly excluded.

## One Warder ecosystem

FullHDGlass, PiconHub and GSU are applications in one Warder ecosystem. They share approved source data, logo identity rules and consistent controls. DAB radio picons are grouped with their owning satellites and supplied through the same live catalogs used across the ecosystem. In PiconHub 0.1.30 IPTV SK/CZ, DAB and DVB-T lead the source list; standalone DAB uses its own verified catalog and is no longer incorrectly marked unavailable.

The three radio and terrestrial sources have their own shared selector icons. Resolution remains a separate setting. The audited CZ/SK DVB-T collection contains 2,531 receiver-reference PNGs in each 220×132 background. It adds 54 references, updates 148 existing logos and removes 197 obsolete or incorrect filenames. Regional uncertainties and operator-confirmed programmes awaiting exact references are listed explicitly. [Current inventory, cleanup and provenance](picons/DVB-T/README.md).


Dátová aktualizácia 28. októbra 2026: spoločný balík DVB-T/T2 SK/CZ bol doplnený a vyčistený. Všetky tri pozadia prešli reálnou inštaláciou cez Warder engine a overením SHA256. Verzia pluginu a IPK sa nemenia.


## Regional radio data refresh — 27 October 2026

Fun Radio S/V now use the approved Fun Radio Z artwork; Melody S uses Melody V/Z. Regina BA/BB/KE use the owner-supplied regional originals. All three backgrounds and all three supported sizes are live in nine 23.5E satellite archives after auditing 30 relevant satellite/provider archives. Unrelated PNGs and all existing DAB additions were preserved. [Source and verification](picons/radio-refresh-20261027/publication.json). No IPK version changes.


## IPTV SK/CZ radios in 0.1.30

The shared IPTV source leads the list, followed by DAB and DVB-T. Three sizes × three backgrounds, 247 programme picons and 263 exact reference filenames per variant. The refreshed bouquet contains 321 entries (88 SK, 233 CZ); 286 selected streams returned audio during sampling. 74 entries still lack suitable verified artwork. [Bouquets, coverage and provenance](picons/IPTV-SK-CZ/README.md). Archives remain external to the small IPK.


Dátové doplnenie 28.10.2026 (r2): 247 položiek s piconmi / 263 referencií v každom z deviatich variantov, 74 zatiaľ bez vhodného overeného piconu. Overené Radia.sk, Radia.cz a MyOnlineRadio.cz aj dodané originály. Všetkých deväť verejných archívov a obrázkov prešlo kontrolou; aktuálne dáta sa stiahnu opätovným výberom IPTV rádiá SK/CZ. Verzie IPK sa nemenia. [Zdroje a zhodovanie](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/blob/main/picons/IPTV-SK-CZ/catalog/followup-sources.json).
