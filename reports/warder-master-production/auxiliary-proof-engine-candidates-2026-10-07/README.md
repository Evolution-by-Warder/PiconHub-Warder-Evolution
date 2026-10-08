# Auxiliary proof-engine mass candidates — 2026-10-07

Candidate-only output. No production ZIP, runtime publication, FullHDGlass change, or TEST205 build was made.

- Source: Evolution-by-Warder/PiconHub-Warder-Evolution, pinned commit `db5eec9f1cdb7a4d587cb1bcdeebc6b3f0d51819`
- Input root: `reports/warder-master-production/auxiliary-publishability-gate-2026-10-07/safe-candidate-tree`
- Scope: 172 Provider + 1 Satellite identities
- Results: PASS 169, REVIEW 4, FAIL 0
- Generated: 346 PNGs, all valid RGBA 220x132
- Transparent sources: copied byte-for-byte; changed SHA256 count 0
- Review cases: see `audit.jsonl` and `fail-review-001.png`
- PASS verification: 25 pages, 7 rows/page except final page
- Candidate generator: `renderer/proof_renderer.py`; `renderer/run_mass.py`
- Warder engine reference: `tools/rebuild_master_catalog.py`, commit `f27d7bbdbf2a49bd9ff9af8baaf85c26abba91f3`

`audit.jsonl` stores identity, source SHA256, candidate paths and SHA256s, per-variant geometry/contrast/local panel/alpha evidence, status and reasons. `sha256-manifest.jsonl` contains all 519 transparent/black/white file hashes.
