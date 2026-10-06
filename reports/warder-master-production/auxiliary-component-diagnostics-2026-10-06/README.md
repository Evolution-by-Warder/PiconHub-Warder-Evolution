# Auxiliary Warder component diagnostics — 2026-10-06

Diagnostic-only run against accepted checkpoint `2b200aed2d60d1ba1fc088c4bc0a62029aa788a3`.

- Scope: 903 engine-review families / 1,041 identities; 1,037 identities passed source QC and were run through both existing BLACK/WHITE renderer variants; four identities were recorded as source-QC blocked. HELLASAT 300W was verified as the geometry sentinel.
- Renderer: existing `tools/rebuild_master_catalog.py::classify_and_render`; optional diagnostics export only serializes values already measured in each connected-component pass. No thresholds, rules, templates, or decisions changed.
- Reproduction command is in `tools/auxiliary_component_diagnostics.py`; it compares each in-memory PNG SHA/status/reason with the checkpoint's existing machine report and candidate PNGs and fails on any mismatch.
- `component-diagnostics-NN.jsonl.gz` contains one UTF-8 JSONL row per identity with per-variant component diagnostics. `component-diagnostics-index.json` lists part checksums.
- `family-diagnostic-summary.jsonl` maps each family to the component evidence without changing its existing REVIEW decision.
- `candidate-tree-sha-regression.json.gz` records expected and observed SHA256 for every existing checkpoint PNG.
- `harmonic-evidence.json` contains all AUX-RF-0301 member/component evidence. `hellasat-regression.json` records the native placement regression.

Results: 16,188 component instances; 2,074 renderer variant comparisons; all in-memory output hashes, engine statuses, and reasons matched; all 3,630 published-to-checkpoint candidate PNGs matched their checkpoint hashes; zero PNG files changed. The renderer ran in memory only to reproduce existing candidates; no candidate PNG file was written. Production assets and `downloads.json` were not changed. TEST202 was not built.
