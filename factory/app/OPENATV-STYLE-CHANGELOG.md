# OpenATV SRP style-aware diagnostics

This batch extends the existing identity triage; it does not alter source ingestion, originals, master registry, or publication decisions.

- Source archive fingerprints confirmed in the 2026-10-10 user-supplied SRP audit identify SRP/UTF8SNP and dark/light.
- Each service-reference is grouped by package format and style, with distinct SHA-256 hashes per bucket.
- Cross-style differences are distinguished from multiple hashes within the same bucket.
- Unknown package provenance remains explicitly unresolved.
- Existing reference_status_counts are preserved; new style_diagnostic_counts are emitted to the report and application log.
- These are byte-level differences, not proof of different visual logos or of valid service identity.

## Safety
Read-only diagnostics. No production GitHub changes, no Warder Master writes, no cleanup of D:.

## Verification
`python -m unittest discover -p 'test_*.py' -q`: 179 tests OK in the local environment.
Actual Windows run and real-data category totals remain unverified.
