# PiconHub Warder Evolution

Warder's original futuristic Enigma2 plugin and the shared Warder picon source database.

## Current state — 2026-10-27

**PiconHub Warder Evolution 0.1.29** is the user-approved production baseline. The native Warder interface retains the functional work of s3n0 and Chocholousek. Runtime: `/usr/lib/enigma2/python/Plugins/Extensions/WarderPiconHub/`.

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

Choose **DAB / DAB+** in the source selector. The approved catalog covers **51 labels / 80 exact receiver references** in Transparent, White and Black. Picons install into the configured picon directory; unknown radio picons are retained. See the [DAB guide](picons/DAB/README.md), [live catalog](picons/DAB/catalog/release.json) and [owner authorization](picons/DAB/catalog/publication-approval.json). ASA DE remains excluded pending a verified logo.

## One Warder ecosystem

FullHDGlass, PiconHub and GSU are applications in one Warder ecosystem. They share approved source data, logo identity rules and consistent controls. DAB radio picons are grouped with their owning satellites and supplied through the same live catalogs used across the ecosystem. In PiconHub 0.1.29 DAB and DVB-T lead the source list; standalone DAB uses its own verified catalog and is no longer incorrectly marked unavailable.

The first two source rows use the official DAB badge and shared DVB-T icon. Resolution remains a separate setting. The native live catalog now includes the restored original CZ/SK DVB-T transparent 220×132 package (2,674 PNGs); verified white/black variants are not yet available. Position filtering is shared with FullHDGlass and handles the canonical receiver position labels.
