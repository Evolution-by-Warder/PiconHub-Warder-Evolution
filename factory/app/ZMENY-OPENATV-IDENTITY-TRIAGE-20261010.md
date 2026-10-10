# OpenATV identity-level triage

- SRP identity grouped by unique service reference, not physical PNG count.
- Multiple artworks for one SRP are reported as review, never silently approved.
- Named assets without SRP remain separate and are not assigned Warder IDs.
- Report: `08-REPORTS/openatv-identity-triage-<run>.json`.
- Summary also embedded in registry-matches JSON and displayed in main GUI log.
- No production GitHub writes, no Warder Master changes.
- Unit tests: `python -m unittest discover -q`.
