# Auxiliary mask geometry — combined provider + satellite scope

This report completes the provider scope missing from checkpoint `79c801ade4d51bc9e1ea7c8d7db1f4cab26586ee`.

- Provider inputs were downloaded from the pinned FullHDGlass raw ZIP and verified by exact size/SHA256 before processing.
- The unchanged `HORIZONTAL_GLYPH_RUN_V1`, mask geometry export, and existing classifier replay are imported from `tools/auxiliary_mask_geometry_export.py`.
- Provider scope covers 832 remaining review families / 967 identities. Existing classifier PNG SHA, status, and reason were checked for both BLACK and WHITE.
- Satellite geometry, classifier results, experiment PNGs, and review sheet were adopted from the accepted checkpoint without rerunning satellite processing. Their exact prior artifacts are copied into `satellite-checkpoint-inputs/` with a SHA manifest.
- Candidate outputs are experimental only. No production renderer, thresholds, policy, assets, publication manifests, or TEST202 build were changed.

See `combined-summary.json`, `combined-sha-regression.json`, `combined-experiment-output-qc.json`, `combined-shape-experiment-manifest.jsonl`, and `combined-review-sheet.png`.
