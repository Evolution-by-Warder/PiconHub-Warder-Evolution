# CANAL+ SK/CZ: reuse existing artwork

Owner instruction, 2026-11-05: use the completed CANAL+ SK/CZ picons in full 23.5E and on other positions/providers carrying the same station and variant. Do not recreate artwork or replace it with stale Vhannibal logos.

The immutable source is the live catalogue at FullHDGlass commit `0a7f09b96cd73091d7ab53ca3976e8f1957b170b`, sourced from PiconHub `b498c30b11f47f28bbc7a068d5bd671395ca4e8c`. Its 18 CANAL packages (three sizes, three backgrounds, two markets) remain unchanged. PNGs are copied byte for byte; no rendering, resizing, colour or background edits occur.

The existing native 23.5E CANAL reference roster already matches the full-position packages. The reconciliation also validates current November service types and other providers/positions. Existing aliases are preserved; exact current references are added only where independently present in the supplied November lamedb.

Reuse requires exact service identity or a reviewed same-name, same-variant market mapping. Generic/cross-market collisions such as Czech Nova vs Bulgarian NOVA, Hungarian RTL vs German RTL, German ONE vs Egyptian ON E, and test services are held. HD/SD/UHD, regional and language labels are retained. The reviewed mapping contains 480 current services; 161 name candidates are held for missing identity evidence.

`canal235-protection/guard.py` allows the explicit `CANAL_CANONICAL_REUSE` operation only when the target identity and exact source PNG hash match the pinned evidence. It continues to reject source CANAL package writes, unverified hashes/identities and ordinary Vhannibal replacements on protected 23.5E.

Detailed master paths and PNG hashes are recorded in `reports/warder-master-production/canal-reuse-20261105.json`. Live archive propagation is independently validated and reported in FullHDGlass `reports/canal-reuse-20261105/verification.json`; preparing source/master data alone is not live publication.
