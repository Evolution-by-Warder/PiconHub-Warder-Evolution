# OpenATV actionable identity categories — 2026-10-10

- Added `actionable_identity_counts` to existing `openatv-identity-triage-*.json` and main run log.
- Cross-style-only dark/light differences are counted as `EXPECTED_CROSS_STYLE_NO_CONFLICT`, not as actionable artwork-variant conflicts.
- `MASTER_ARTWORK_REVIEW` takes precedence over an expected style difference: no Master differences are silently approved.
- Same-style multi-artwork and unknown-provenance multi-artwork remain `ARTWORK_VARIANTS_REVIEW`.
- New service references are candidates only (`NOT_IN_MASTER_CANDIDATE`), not automatic Master additions.
- Legacy `reference_status_counts`, raw registry-match data and existing manual review queue are intentionally unchanged for backwards compatibility. A future step must integrate the new grouping into the UI review queue safely; this batch does not claim to have reduced the existing 20,879 items.
- No source originals, production Master, GitHub, or D: disk cleanup changed.

Verification: 183 local unittest cases passed. Actual Windows run not yet verified.
