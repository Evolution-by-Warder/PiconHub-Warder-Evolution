> Latest development checkpoint — 2026-10-23: Chocholousek 5.0.240904 source imported from upstream into plugin/futuristic-rebuild; per-launch Warder plugin update hook implemented. This supersedes any statement below that the new development branch still lacks an entry point. The historical migration branch remains a skeleton. Modern UI, Warder picon-source integration, packaging and receiver tests remain pending. See ../plugin/STARTUP-UPDATES.md.

> **Current owner decision, 2026-10-23:** modernize the Chocholousek functional base with the Warder interface. This supersedes the retired-line/from-scratch directions in the historical checkpoint below. The code review found that our historical migration runtime directory is a skeleton; original source was reviewed upstream at s3n0/e2plugins, version 5.0.240904. See [the current design proposal](../plugin/design/CHOCHOL-WARDER-INTERFACE.md). No modernized receiver runtime or IPK is claimed yet.

# PiconHub Warder Evolution — current project state

Updated: 2026-10-23 (Europe/Bratislava).

## Identity and authorized next phase

The name **PiconHub Warder Evolution** now belongs to Warder's original futuristic Enigma2 plugin (historical PiconHub 0.6.x / 0.7.x), by Štefan's explicit decision.
The separate s3n0/Chocholousek plugin modernization is retired as a development target. Its older code and documentation remain in historical/working branches preserved by this backup; the user paused further deletion. Do not delete or merge those branches during backup/documentation maintenance.

After the existing skin and picon projects are safely backed up, the user authorized rebuilding the futuristic plugin from the beginning. Complete recovery of its old runtime is no longer a prerequisite for that new build. Preserve the recovered genuine headers and obtain approval for the new screen/function design before presenting it as implemented or receiver-tested.

## Source/data state

Before this documentation operation, main was `fe863a0aa0a22f1fcaffd4c56bd755578921cc04`; picon artwork was last updated at `286b56aa2e7c1d65c1f412b8748e688fa631d3ce`.
Main contains **23,657 PNG files** under `picons/`. This count describes that exact snapshot, not every historical branch.
The separate protected production-data branch `warder-master-production` is preserved. Factory continues on its existing `factory-warder-development` branch; it is not the Enigma2 plugin.

Frozen V9 rules and MASTER files remain authoritative. Preserve service-reference names and layout:
`picons/<satellite-position>/<provider>/{transparent,white,black}/<service-reference>.png`.

Published downloadable archives and the live receiver catalog are in **FullHDGlass-Warder-Evolution**, path `assets/warder/downloads/picons/channels/manifest.json`, not solely in this source tree. That repository is backed up separately in the same set.
Current live catalog: 468 packages, 45 satellite positions, transparent/white/black, sizes 50x30 / 220x132 / 400x240.
The approved Network4 refresh has 72 changed live packages; 639 replaced PNG entries plus 72 aliases matched approved artwork, and all 138 applicable download plans passed. Source evidence remains in migration approval records and the skin publication report.

## Original futuristic recovery findings

Recovered exact updater payload: `plugin/recovery/original-updater/` in main, from commit `6f45821b44559b912cacf21e5bb01932d62766f6`, version 0.6.12.23.
The two JPEGs are top headers, not complete screens: FHD 1920x190 and HD 1280x127. Their Git blob identities are `66243e8053a4d114d9622eb2079aa0b9c18c4087` and `cda60a9b240be668f8e0e519c9c4081902456f77`.
Older updater helper modules also remain recoverable from Git history.

Historical documentation mentions 0.7.0-dev3 and a 1672x941 design with six provider panels. The archived dev2 manifest was unpublished with an empty IPK URL. Neither record is a complete runnable plugin. A separately recovered 0.1.1-dev implementation is a Chocholousek-based rewrite, not the original futuristic runtime.

All 38 current PiconHub branches and their reachable historical paths, nine Trezor branches, 28 skin branches, two GSU branches and the saved 4ac7dec8 Git bundle were examined for original runtime material. No complete original futuristic runtime/IPK was located in that inspected material. The old Trezor piconhub-plugin/server backup directories were placeholders, not uploaded plugin backups.

## Backup and preservation

Set: `warder-backups-20261023`. Preserve all captured heads/tags and reachable history, including old plugin and Factory branches.
The final external BACKUP-MANIFEST.json records final heads, sizes, SHA256 and offline restore results. See `BACKUP-RESTORE.md`.
The earlier 4ac7dec8 bundle requires prerequisite commits and lacks the latest approved picons; it is not the current standalone recovery copy.

This operation updates documentation only. Picons, MASTER templates, Factory code, migration records, provider data and plugin recovery assets are not modified. No new IPK is issued.

## Rebuild development checkpoint — 2026-10-23

Primary Trezor backup is complete. The new `plugin/futuristic-rebuild` branch now contains the catalog and download-integrity core; see `plugin/BUILD-STATUS.md`. Main remains at the backed-up state. The new plugin has no receiver-tested UI or IPK yet. The original recovered assets and production data remain unchanged.
