# PiconHub Warder Evolution

PiconHub Warder Evolution is Warder's original Enigma2 plugin with the approved futuristic PiconHub interface, together with the shared Warder picon database.

## Project decision — 2026-10-23

Štefan explicitly selected the original futuristic PiconHub (historical 0.6.x / 0.7.x), renamed it **PiconHub Warder Evolution**, and retired the separate s3n0/Chocholousek plugin modernization line (5.0.240904.x). Earlier documents assigning this name to that modernization line are superseded.

The retired plugin source workspace, packaging and test update payload have been removed from the active main tree. Historical Git commits remain historical evidence, not active releases.

## Plugin recovery status

The original 0.6.12.23 updater payload has been recovered byte-for-byte from commit `6f45821b44559b912cacf21e5bb01932d62766f6` into `plugin/recovery/original-updater/`. It is a partial update payload, not a complete runnable plugin. The historical 0.7.0-dev2 channel was unpublished; its checksum alone is not a recoverable IPK.

The complete original runtime, entry point and approved main-screen assets must be recovered before a renamed runnable IPK can be built. Do not replace them with the retired plugin, Factory or FullHDGlass, and do not invent a new UI.

See [current identity](docs/PICONHUB-PROJECT-LINES.md), [work plan](docs/PICONHUB-WORK-PLAN.md) and [checkpoint](docs/PROJECT-CHECKPOINT.md).

## Shared picon data

The existing `picons/`, `templates/`, `migration/`, `factory/` and download consumers are preserved by this identity change. Provider and satellite picons are data, not the retired plugin.

Runtime data layout remains:

`picons/<satellite-position>/<provider>/{transparent,white,black}/<service-reference>.png`

The approved V9 rules and original BLACK/WHITE MASTER templates remain frozen. See `docs/PICON-MASTER-QUALITY-PLAN.md`. Existing third-party picon provenance and credits remain applicable to those assets; retiring a plugin does not change authorship of shared artwork.
