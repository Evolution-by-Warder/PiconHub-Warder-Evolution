# Backup and restore — 2026-10-23

Backup set: `warder-backups-20261023`.

## Scope and source of truth

The set captures every advertised Git ref of FullHDGlass-Warder-Evolution and PiconHub-Warder-Evolution at the recorded snapshot time, including all branch/tag history and all reachable file bytes. This includes Git-stored source, images, IPKs, published channel archives and their parts.

The definitive per-project ref map, bundle/part size and SHA256, integrity result and offline clone result are recorded outside Git in `BACKUP-MANIFEST.json`, alongside `SHA256SUMS`, `restore-backups.py` and `OBNOVA.md`. Keeping the final inventory outside the archived commits avoids a circular checksum/commit reference.

Do not call a filtered/promisor clone or a prerequisite-dependent bundle a complete offline backup. Before packaging, every reachable object must be available. Each final bundle must have no prerequisite commits, restore with network protocols disabled into an empty repository, pass Git object checks and reproduce all captured refs exactly.

## Restore

Download every file listed by the final inventory into one directory. Run:

```sh
python3 restore-backups.py --verify-only
python3 restore-backups.py --destination recovered
```

If a bundle is split, the script checks and joins its ordered parts before offline restoration. Keep all parts; an individual part is not a complete backup.

The restored bare repository can be cloned locally for development. Recovery never requires access to the original GitHub account, original repository, an old cache or a separate prerequisite bundle.

## Boundaries

This is a repository backup, not a backup of the receiver or private PCs. Receiver settings, installed add-ons and uncommitted private work were not accessible. Trezor is a separate historical repository and is not silently included in these two project bundles. Previously missing original futuristic PiconHub runtime files cannot be recreated by backing up the available data.

The earlier PiconHub-OpenATV-4ac7dec8 bundles are historical, require prerequisite commits and predate the latest approved picons. The older FullHDGlass 1.0.4 GOLDEN source archive is historical; neither substitutes for this set.

Never expose private archive inventories, credentials or signed transfer URLs in public project documentation.

## Storage

The primary archival destination is the owner's private Trezor under `backups/warder-backups-20261023/`. A second standalone copy is delivered separately. The final inventory distinguishes verified local restore, durable secondary delivery and actual private-archive publication; none is inferred from a placeholder or a workflow merely starting.
