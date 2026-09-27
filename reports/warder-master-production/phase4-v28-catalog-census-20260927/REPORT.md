# V28 — Full-catalog read-only census

## Outcome

**CATALOG-FACTORY-MAP-READY** for the catalog actually present at `110dade00e1ccc96b5d41fbea1144d6431ae5d7d`. This is a read-only census, not a generator qualification or rollout. The repository contains **9,041** transparent sources, not 150,000. No repair, candidate, or production write occurred.

## Scope and duplicates

- Physical transparent source PNGs: **9,041**
- Unique byte-identical source images (SHA-256): **6,604**
- Duplicate groups (2+ references): **1,042**; references in those groups: **3,479**
- Unique pixel analyses saved by deduplication: **2,437** (27.0% of physical references)
- Satellite/position directories: **39**; providers: **583**
- WHITE outputs: **9,041**; BLACK outputs: **9,041**; missing WHITE pairs: **0**; missing BLACK pairs: **0**.
- Physical source bytes: **41,324,026**; unique bytes analyzed: **30,953,211**.

All source PNGs were hashed; each unique image was decoded and analyzed once. V9 component membership, achromatic/two-tone/contrast decisions and V23 topology evidence use the pinned generator/rule constants. This census does not use or infer new detector thresholds.

## Source format and geometry

Unique-image formats: `{"PNG": 6604}`. Native dimensions: `{"220x132": 6604}`. Modes: `{"LA": 2, "P": 6292, "RGBA": 310}`. Source anomalies (non-PNG, missing alpha channel, fully transparent, or nonstandard V9 geometry): `{}`. Decode errors: **0**; these remain F7 and do not stop the scan.

## WHITE / BLACK factory buckets

Each source has independent WHITE and BLACK dispositions; service references inherit the unique-source result. Bucket counts below include unique images and physical service references.

| Style | Bucket | Unique images | Physical refs | % unique | % physical |
|---|---|---:|---:|---:|---:|
| WHITE | F0 | 199 | 251 | 3.01% | 2.78% |
| WHITE | F1 | 86 | 90 | 1.30% | 1.00% |
| WHITE | F2 | 6 | 13 | 0.09% | 0.14% |
| WHITE | F3 | 5,791 | 7,979 | 87.69% | 88.25% |
| WHITE | F4 | 424 | 578 | 6.42% | 6.39% |
| WHITE | F5 | 85 | 112 | 1.29% | 1.24% |
| WHITE | F6 | 11 | 15 | 0.17% | 0.17% |
| WHITE | F7 | 2 | 3 | 0.03% | 0.03% |
| BLACK | F0 | 1,126 | 1,352 | 17.05% | 14.95% |
| BLACK | F1 | 23 | 23 | 0.35% | 0.25% |
| BLACK | F2 | 1 | 1 | 0.02% | 0.01% |
| BLACK | F3 | 4,838 | 6,813 | 73.26% | 75.36% |
| BLACK | F4 | 524 | 732 | 7.93% | 8.10% |
| BLACK | F5 | 85 | 109 | 1.29% | 1.21% |
| BLACK | F6 | 5 | 8 | 0.08% | 0.09% |
| BLACK | F7 | 2 | 3 | 0.03% | 0.03% |

No-action F0 covers **199** unique / 251 physical refs on WHITE and **1,126** / 1,352 on BLACK. That is the observed likely-no-further-work estimate under frozen V9 results, not a guarantee of visual approval. Historical Phase3 statuses from its audit: `{"black": {"AUTO-FIXED": 347, "ERROR-SKIP": 1, "PASS": 1352, "REVIEW": 7341}, "white": {"AUTO-FIXED": 411, "ERROR-SKIP": 1, "PASS": 251, "REVIEW": 8378}}`.

F2 known false-two-tone counts: WHITE **6** unique / 13 refs; BLACK **1** / 1. V27 supports the edge/AA mechanism, while V26 remains `RULE-GENERALIZATION-NEEDS-MORE-EVIDENCE`; F2 is a classification queue, not permission to edit.

## Highest-impact clusters

| Cluster | Style | Unique | Physical refs | Impact | Mechanism status |
|---|---|---:|---:|---:|---|
| C01 — edge/AA false two-tone transition | WHITE | 6 | 13 | 0.09% | yes, V27 transition mechanism; V26 remains needs-more-evidence |
| C02 — protected chromatic or mixed component | WHITE | 5,791 | 7,979 | 87.69% | yes, protected mixed components are frozen blockers |
| C03 — insufficient topology interior evidence | BLACK | 524 | 732 | 7.93% | yes, fail-safe insufficiency semantics; broad frequency census only |
| C04 — genuine interior two-tone | WHITE | 85 | 112 | 1.29% | yes, two V26/V27 positive controls, not a complete corpus |
| C05 — other frozen REVIEW | WHITE | 11 | 15 | 0.17% | no single mechanism |

No-new-rule-work estimate (F0+F1): WHITE 285/6,604 unique (4.32%); BLACK 1,149/6,604 (17.40%). This is classifier disposition, not visual approval.

The tracked docs and file manifests contain no 150,000-source catalog manifest or ingestion plan; the checkpoint identifies 9,041 transparent sources.

## Historical source-hash provenance anomalies

The current source files were read-only during V28. Three source references (two unique current hashes) differ from the source SHA recorded in the Phase 3 audit. These current bytes were fully analyzed, but both WHITE and BLACK dispositions are conservatively placed in F7 until provenance is reconciled. This is a mismatch against historical audit metadata, not a V28 source edit.

- `picons/23.5e/skylink/transparent/1_0_1_1B03_3FE_1_C00000_0_0_0.png` — current `1da179c187414e4511167e93989389f2297a38c7af26d8a5a161cd94ef8be3a2`, Phase 3 audit `3a9d989efb79825210897109b53e212c017f727b2579901a1eba9455eaab8844`, historical status `ERROR-SKIP`.
- `picons/80.0e/orion-express/transparent/1_0_1_198_CA_1_3200000_0_0_0.png` — current `a7ee7ce90ca89b38eb212849e972a7b4637afd0c7f0e0ce8c0a51009e5a49f1d`, Phase 3 audit `25d4857741b6329f8c3e813669f661c0b8ac9d248698470a42c98f2da1ba0efd`, historical status `AUTO-FIXED`.
- `picons/80.0e/orion-express/transparent/1_0_1_353_D1_1_3200000_0_0_0.png` — current `a7ee7ce90ca89b38eb212849e972a7b4637afd0c7f0e0ce8c0a51009e5a49f1d`, Phase 3 audit `25d4857741b6329f8c3e813669f661c0b8ac9d248698470a42c98f2da1ba0efd`, historical status `AUTO-FIXED`.


Historical V9 status replay parity excluding those hash-mismatch paths: **18,076/18,076 path/style checks matched**; remaining divergences: **0**. This is a consistency check against prior audit metadata, not a visual approval.

For the next scale-up qualification, C01/F2 has the best current impact-confidence-risk balance: the mechanism is supported by V27 and #14700 is the one specific approved example, while V26 still requires more evidence. C01 is small (6 WHITE plus 1 BLACK unique source-style rows), so this is an efficient qualification target, not a rollout recommendation. C02 has the highest impact but high implementation risk because it contains protected chromatic components; C03 has volume but lacks sufficient topology evidence.

The current implementation has no rectangle/badge detector, so V28 reports that feature as unavailable instead of inventing a geometric heuristic. Historical approvals are attached only where a loaded text/CSV record matched a source SHA; they remain locked metadata and do not promote other sources. #14700 stays a specific manual approval. #14599 remains CLOSED/TABU and was not visually revisited.

## Performance and 150,000-reference estimate

- Total measured run: **384.53 s**; hashing: **0.89 s**; unique-image pixel analysis: **377.57 s**.
- Unique-image throughput: **17.5 images/s**; peak resident memory: **186.9 MiB**.
- At the observed duplicate ratio (1.369 physical refs per unique image), 150,000 references imply about **109,568 unique analyses**, or **1.74 h** at this measured CPU rate. Without deduplication: **2.38 h**. This is a same-host estimate; file retrieval, storage, output encoding and QC add time.

A practical factory is staged: inventory and SHA-256 dedupe; one feature analysis per unique source; map decisions to all service refs; write isolated BLACK/WHITE outputs only for already-qualified classes; run hash/alpha/pair validation; route F2–F7 or any invariant failure to a compact human review queue. The census itself does not authorize those writes.

## Limits and read-only invariants

V9/V23 do not implement a rectangular/badge structure detector; `likely_rectangular_badge` is therefore unavailable, not guessed. Existing Phase3 audit status and matched historic approval records are metadata only. This report does not reopen manually approved visual decisions and does not change any approval.

- `picons/` writes: **0**; transparent/WHITE/BLACK writes: **0**
- MASTER/template writes: **0**; generator changes: **0**; approval changes: **0**
- Candidate/rebuild generation: **none**; #14700 remains unchanged; #14599 untouched.

Reproduce from a complete checkout with: `python tools/phase4_v28_catalog_census.py --repo-root .`. Machine-readable details are in `CATALOG-SUMMARY.json`, `SOURCE-FEATURES.csv.gz`, `SERVICE-MAPPING.csv.gz`, `FACTORY-BUCKETS.csv.gz`, `PROBLEM-CLUSTERS.csv`, `DUPLICATE-GROUPS.csv.gz`, and `PERFORMANCE.json`.
