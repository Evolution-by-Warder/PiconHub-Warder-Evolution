# Chocholousek archive acquisition

This stage acquires only the 2,203 archives in the verified migration manifest. It does not crawl picon.cz and does not attempt to bypass any protection.

## Inputs

Use the verified manifest archived in private Trezor:

`archives/chocholousek-picons/manifest/source_manifest.tsv.xz`

Expected decompressed SHA256:

`78b1d9a44853ffc55dfb5f67746ab3316ded67447ae0bacadf7bfd3cccfceaa2`

Prepare it:

```sh
xz -dc source_manifest.tsv.xz > source_manifest.tsv
sha256sum source_manifest.tsv
```

## First test batch

Run a deliberately small first batch:

```sh
chmod +x acquire_archives.sh
MANIFEST=./source_manifest.tsv OUT=./chocholousek-acquisition LIMIT=10 SLEEP=3 ./acquire_archives.sh
```

The downloader is single-threaded. For each manifest row it performs a normal HTTP download, tests the resulting file with `7z t`, records SHA256 and byte size, and only then adds the row to `state.tsv`.

Restarting the same command is safe: entries already recorded in `state.tsv` are skipped. A partial network file remains in `tmp/` and curl attempts a normal HTTP resume on the next run. Invalid 7z results are quarantined instead of being accepted.

## Checkpoint files

- `state.tsv` — verified successful archives and their checksums/sizes/acquisition time.
- `failures.tsv` — failed download or archive-validation attempts.
- `acquisition.log` — human-readable progress.
- `raw/` — untouched successfully validated source archives.

After the first 10-file batch is confirmed clean, increase `LIMIT` to 50 or 100. Keep acquisition single-threaded and leave a delay between requests.

The archived source files are evidence/reference material only. Do not mix them directly into the maintained `picons/` tree.
