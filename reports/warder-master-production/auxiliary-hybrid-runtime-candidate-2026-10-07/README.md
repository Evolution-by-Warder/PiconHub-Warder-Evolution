# Hybrid auxiliary runtime candidate (TEST202 preparation)

Status: prepared, not published; TEST202 not built.

This package candidate is derived only from the accepted strict safe tree at PiconHub checkpoint `a97acf919b93e4efaa1fc31766c55a634b487208`. No PNG was rendered or normalized in this step. The six safe archives are byte copies of the existing 519 approved PNG outputs. Two additional transparent legacy fallback archives repack the pinned current transparent ZIPs without changing any PNG bytes; the only change is placing those files under the existing base fallback directory. Existing black/white fallback ZIPs remain pinned, unchanged FullHDGlass runtime assets.

See `hybrid-runtime-design.md`, `candidate-downloads.json`, `archive-manifest.json`, `migration-manifest.jsonl`, `lookup-coverage.json`, `static-regression-report.json`, and `ui-change-plan.json`.
