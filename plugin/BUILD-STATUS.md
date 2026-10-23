# Production baseline — 2026-10-23

PiconHub Warder Evolution **0.1.13** is the user-approved production baseline.

- Runtime: `/usr/lib/enigma2/python/Plugins/Extensions/WarderPiconHub/`.
- Published package and update feed: [production record](production.json).
- Final behavior and maintenance rules: [PRODUCTION.md](PRODUCTION.md).
- Validation: 118 automated tests and successful GitHub CI. The user supplied a successful four-position receiver result for 0.1.9. Later UI and About changes are covered by tests/CI; a complete receiver run of 0.1.13 is not claimed.

Retired development and recovery files are preserved in Git history. The current tree contains the production plugin, its required artwork sources, build tools, tests and update configuration.
