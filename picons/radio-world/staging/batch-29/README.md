# Batch 29 — working assets, 6 November 2026

Four new references / 36 PNGs. Staging only; no live release or country index changed.

| Country | Station | Exact reference |
|---|---|---|
| AT | Schwendermarkt | `4097:0:2:8741:1C4E:ED:0:0:0:0` |
| CO | laut.fm - Durisima Radio | `4097:0:2:F1C9:A3D7:ED:0:0:0:0` |
| DE | 2000er Hits (by MineMusic) | `4097:0:2:124:4F0E:ED:0:0:0:0` |
| DE | AENA | `4097:0:2:DDDB:C94:ED:0:0:0:0` |

The 22,751-reference historical checkpoint through batch 28 was recovered and checked before selecting these references. All existing batches 23–27 were also excluded. No completed reference or prior checked source was rerendered. Historical batch 28 and current batch 29 remain distinct.

Of 20 candidates, four publisher originals identify the exact platform channel. Existing decisions for 13 checked sources were preserved. One image returned 404, Allkillers Nofillers has an unbranded photo, and Österreich-Radio requires a publisher-approved contrasting original for the black background. All 16 holds are recorded in sources.json.

The original full logos, colours and proportions and the approved Warder masters are preserved. Each reference has 50×30, 220×132 and 400×240 transparent, white and black PNGs. SHA-256, exact inventories, CRC, RGBA and image decoding passed. The actual 220×132 renders were visually reviewed. The staging downloader replay uses injected endpoints and real archive bytes with exact pinned catalogue identities; it preserves a custom picon and requests no ZIP on repeat. Hardware testing remains pending.

Production base: `648c52b5cc69038bd1b6a1d7ad5b5514c308458d`. Source collection: [successful run](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/actions/runs/42226779692). Metadata and original source bytes are frozen in the source-collection commit `4aa03276235830864599eec5d499c9b68661a039`.

Next: integrate these exact bytes into separate AT, CO and DE country candidates while protecting all approved PNG hashes; do not publish them until separately approved.
