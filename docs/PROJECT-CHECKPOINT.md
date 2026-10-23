# PiconHub Warder Evolution — recovery checkpoint

> **Current status, 2026-10-23:** This checkpoint below is retained as dated history. Current project identity, the authorized rebuild decision, actual backup status and remaining limits are in [CURRENT-STATUS.md](CURRENT-STATUS.md), [PICONHUB-WORK-PLAN.md](PICONHUB-WORK-PLAN.md) and [BACKUP-RESTORE.md](BACKUP-RESTORE.md). Shared frozen artwork/data rules still apply.


Updated: 2026-10-23

## Current identity

PiconHub Warder Evolution is Warder's original futuristic PiconHub plugin (historical 0.6.x / 0.7.x), explicitly renamed by Štefan on 2026-10-23. The separate Chocholousek/s3n0 modernization line (5.0.240904.x) is retired. Earlier checkpoints assigning this name to that line are superseded.

## Verified recovery

Original updater payload source:
- repository: Evolution-by-Warder/PiconHub-Warder-Evolution
- immutable commit: 6f45821b44559b912cacf21e5bb01932d62766f6
- original directory: plugin/releases/files
- original directory tree: 22ee079bff36d519edfc34e7762a263ea9e1ec56
- restored directory: plugin/recovery/original-updater
- release.py version: 0.6.12.23

The historical channel metadata mentions 0.7.0-dev2 with published=false and an empty IPK URL. It must not be advertised as a recoverable or released package.

## Open blocker

No complete original futuristic runtime or full IPK was located in the inspected active tree, archived updater payload, available Library title results or inspected Trezor trees. Core entry point, main screens, provider extension and approved complete main UI assets remain unverified. The recovered payload alone is not installable.

Never substitute the retired 5.x plugin, the unrelated 0.1.x rewrite, Factory or FullHDGlass. Recover a complete original source/IPK before a runtime rename/build.

## Preserved data

Picons, templates, migration/provenance, Factory and workflows retain their pre-change tree identities. The protected warder-master-production branch and historical commits are not rewritten.

Frozen V9 rules remain in docs/PICON-MASTER-QUALITY-PLAN.md. Preserve templates/picons/black-sablona.png and white-sablona.png exactly. Picon runtime layout remains picons/<satellite-position>/<provider>/{transparent,white,black}/<service-reference>.png.

Read current identity and work plan before continuing.
