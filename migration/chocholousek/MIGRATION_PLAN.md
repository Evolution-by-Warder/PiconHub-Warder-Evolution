# Chocholousek picon migration plan

Purpose: one-time migration of only the picon archives that the inherited Chocholousek Picons plugin can request. This is **not** a mirror of all content on picon.cz.

Source of truth: `id_for_permalinks(240624).log` shipped with the original `enigma2-plugin-extensions-chocholousek-picons_5.0.240904_all.ipk`, filtered by the exact resolutions exposed by the plugin and the `_by_chocholousek` archive naming convention.

## Inventory

- 2,202 selectable picon archives
- 1 preview archive (`filmbox-premium-(all)_by_chocholousek_(240626).7z`)
- 2,203 archives total to migrate
- 8 plugin resolutions
- 21 picon backgrounds/styles
- 58 satellite/provider/DTT targets

### Resolution counts

| Resolution | Archives |
|---|---:|
| 50x30 | 165 |
| 96x64 | 56 |
| 100x60 | 330 |
| 150x90 | 110 |
| 220x132 | 979 |
| 400x170 | 165 |
| 400x240 | 384 |
| 500x300 | 13 |
| **Total selectable** | **2,202** |

### Background/style values

`SNPblack`, `SNPtransparent`, `black`, `black3d`, `black80`, `dirtypaper`, `freezeframe`, `freezewhite`, `justblack`, `mirrorglass`, `monochrom`, `noName`, `oled`, `poolrainbow`, `simpleblack`, `srhd`, `transparent`, `transparentdark`, `transparentwhite`, `white`, `win11`.

## Server layout

Keep the imported upstream archives separate from the existing canonical `picons/` tree. Do not mix raw historical archives with maintained PiconHub data.

```text
/chocholousek/
├── raw/
│   ├── 50x30/
│   │   └── <background>/<original archive filename>.7z
│   ├── 96x64/
│   │   └── <background>/<original archive filename>.7z
│   ├── 100x60/
│   ├── 150x90/
│   ├── 220x132/
│   ├── 400x170/
│   ├── 400x240/
│   ├── 500x300/
│   └── preview/
│       └── filmbox-premium-(all)_by_chocholousek_(240626).7z
├── manifest/
│   ├── source_manifest.tsv
│   └── checksums.sha256
└── catalog/
    └── packages.json
```

`raw/` is the immutable one-time import. The existing repository `picons/` remains the maintained/canonical PiconHub dataset that can later be cleaned and updated independently.

## Migration sequence

1. Generate the exact archive manifest from the plugin-shipped permalink catalog.
2. Download each listed archive exactly once from its source ID.
3. Verify that every downloaded file is a valid 7z archive.
4. Record SHA-256 and byte size for every archive.
5. Store the untouched archives under `/chocholousek/raw/` using the structure above.
6. Produce `packages.json` from the verified local copy.
7. Only after the local/server copy is complete and verified, change the plugin backend to PiconHub-Warder-Evolution endpoints.
8. Verify that no runtime code still contacts `picon.cz` (catalog, archive download, preview, connectivity test).
9. From that point onward, update/clean the maintained PiconHub data on our infrastructure; do not depend on the old source server.

## Important scope rule

The optional third-party URLs read by the plugin from `/etc/enigma2/chocholousekpicons.cfg` are user-defined external sources and are **not** part of this migration.

Credits for the imported source data remain with Chocholousek; the original Enigma2 plugin was created by s3n0.
