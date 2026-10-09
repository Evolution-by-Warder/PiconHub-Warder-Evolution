# Batch 017 checkpoint — review sheets 036–041

- Scope: review IDs 3501–4100 (sheets 036–041), 600 BLACK/WHITE variants visually inspected from the current catalog outputs and `all-review-index.csv.gz`.
- Local repository HEAD at checkpoint: `719dd59ec5ef09a28503d21d3f21bad011de442a`.
- Remote branch HEAD before this batch push: `f305093c7918390a7b756ce662140f996b35e319`.
- Output: 9 high-confidence low-contrast defects repaired (5 BLACK, 4 WHITE); 591 other variants were visually reviewed and no safe localized correction was selected from this pass. The manifest lists only the 9 files changed. Borderline brand-color cases were not reported as PASS or altered.
- Checks: all 9 repaired outputs decode as PNG RGBA 220×132; every edited output was compared with a pinned `fit_logo` + master render before modification; changed masks are recorded in `repair-manifest.csv`; gold TFC flame and HRT red marks/numeral were verified unchanged. Transparent sources and master templates were read-only.
- Comparison: `batch-017-before-after.jpg` contains the 9 source-rendered before/after pairs.
- Next review identifier after this batch: 4101.
- Batch image fixes and 600 individual audit outcomes are prepared for incremental push; no production/main writes.

- Remote branch HEAD before push: `f305093c7918390a7b756ce662140f996b35e319`.
