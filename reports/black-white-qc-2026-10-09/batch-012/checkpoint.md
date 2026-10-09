- Remote branch parent immediately before batch 012 push: `1b1eae810cf5198d12816a10d7c0d3f139ab9b5a`.
# BLACK/WHITE QC batch 012

- Remote branch baseline before this parallel batch: `e42b74943b0aa0d7efe3f8e6e18c4ebfb31f3a47`.
- Pinned production renderer: `tools/rebuild_master_catalog.py` with immutable MASTER templates. Each pre-edit catalog PNG matched the original renderer pixel-for-pixel before repair.
- Repaired 8 exact BLACK/WHITE output PNGs: 4 BBC Earth BLACK, 1 Spectrum BLACK, 2 Strike TV WHITE, 1 VZ Fri BLACK.
- Masks were generated in memory from connected source-alpha components. Hue/saturation were preserved for all color adjustments. BBC green tiles and badge initials, the VZ emblem, the MASTER templates, and all transparent sources remain unchanged.
- All repaired outputs decode as RGBA PNG at 220×132; output changes are confined to the mapped source-mask footprint, with alpha/geometry unchanged; only a 2-pixel Lanczos resampling footprint surrounds the mapped source edit mask.
- See `repair-manifest.csv` and `batch-012-before-after.png` for per-file SHA-256, changed-pixel counts, original-render comparison, and mask visualization.
- Last repaired identifier: `picons/0.8w/telenor/black/1_0_19_1CF7_47_46_E080000_0_0_0.png`. Next work should resume with the parent workflow’s next unprocessed candidate; this batch did not process a contiguous catalog interval.
