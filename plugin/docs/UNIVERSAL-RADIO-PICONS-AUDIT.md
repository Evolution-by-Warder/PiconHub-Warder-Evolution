# Universal Radio Picons — audit 2026-10-27

Target: PiconHub Warder Evolution **0.1.25**, current production runtime `Plugins/Extensions/WarderPiconHub`. See issue #10. Development branch only; no production changes.

## Verified source findings

Source: `plugin/src/Plugins/Extensions/WarderPiconHub/plugin.py`, current main.

- Existing mode values: `sync_tv`, `sync_tv_radio`, `all_inc`, `all`.
- `sync_tv` enumerates `/etc/enigma2/userbouquet.*.tv`.
- `sync_tv_radio` enumerates both `userbouquet.*.tv` and `userbouquet.*.radio` via `glob.glob`. This **already includes generated DAB radio bouquet files if their filenames match**.
- After reading bouquet text, it runs:
  ```python
  re.findall(r'.*#SERVICE\s([0-9a-fA-F]+_0_[0-9a-fA-F_]+0_0_0).*\n*', bq_contents.replace(':', '_'))
  ```
  The restrictive matching pattern is the likely bottleneck for nonstandard DAB+/IPTV radio service references. Do not claim all such references are currently excluded until actual samples are tested.
- Existing local PNG inventory glob `[0-65535]_0_*.png` and synchronization deletion path also require review before changing service-reference acceptance. Avoid accepting a reference that can never be matched to an archive PNG or renderer lookup.

## Implementation sequence

1. Obtain actual OpenATV 8.x generated DAB+ bouquet sample and verify exact service reference syntax, including `#SERVICE` and `#DESCRIPTION` entries.
2. Extract a **pure, testable** service-reference normalization function. Only accept actual playable service entries, ignore markers, directory refs and bouquet references; preserve Enigma2 picon naming conventions.
3. Add unit tests for DVB radio, DAB+ generated references, stream URLs, malformed entries, markers, duplicate services and regional stations.
4. Check archive catalog for DAB+ PNG coverage and alias resolution before enabling synchronization. Unknown/ambiguous stations must be reported, not guessed.
5. Audit deletion/rollback and renderer lookup paths. Ensure TV-only behavior and existing production modes remain unchanged.
6. Run full existing test suite plus new cases. Present code diff and any new graphics for approval before production release.

## Guardrails

Do not touch approved UI or V9 MASTER templates. Do not merge into main or publish IPK without receiver verification and owner approval. This document records source audit only; **implementation is not yet complete**.
