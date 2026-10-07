# Hybrid auxiliary runtime design

## Runtime lookup

Keep the current 220-width consumer lookup unchanged:

- Provider: `piconProv_220x132/` first, then `piconProv/`.
- Satellite: `piconSat_220x132/` first, then `piconSat/`.

No resolver change is required. The safe 220x132 archive writes only into the priority folder. The legacy fallback archive writes only into the base folder.

## One GUI choice, two ordered packages

The GUI continues to expose exactly three Provider variants and three Satellite variants: `Transparentné`, `Čierne`, `Biele`. There is no size selector.

One variant selection resolves to this ordered package pair:

1. **Legacy fallback**: install the existing current coverage into `piconProv/` or `piconSat/`.
2. **Warder-safe priority overlay**: install the approved triad members into `piconProv_220x132/` or `piconSat_220x132/`.

The download executor must validate each archive's exact size and SHA256 before extraction and validate the destination/root before copying. Install the safe overlay only after the fallback stage completes successfully. Return an error/partial result if either stage fails; do not claim the pair succeeded when only one stage did.

This requires a small auxiliary composite-package executor in TEST202. Current auxiliary runtime resolves one catalog entry for each GUI selection, so `candidate-downloads.json` is explicitly marked not runtime-consumable until that executor exists. Do not change the channel-picon backend.

## Archive mapping

| Domain / variant | Fallback archive | Fallback destination | Safe priority archive | Safe destination | Counts |
|---|---|---|---|---|---:|
| Provider / Transparent | `provider-transparent-legacy-fallback.zip` | `piconProv/` | `provider-transparent-warder-safe-220x132.zip` | `piconProv_220x132/` | 1145 legacy; 172 safe |
| Provider / Black | existing `piconProv-black.zip` | `piconProv/` | `provider-black-warder-safe-220x132.zip` | `piconProv_220x132/` | 1297 legacy; 172 safe |
| Provider / White | existing `piconProv-white.zip` | `piconProv/` | `provider-white-warder-safe-220x132.zip` | `piconProv_220x132/` | 1256 legacy; 172 safe |
| Satellite / Transparent | `satellite-transparent-legacy-fallback.zip` | `piconSat/` | `satellite-transparent-warder-safe-220x132.zip` | `piconSat_220x132/` | 69 legacy; 1 safe |
| Satellite / Black | existing `piconSat-black.zip` | `piconSat/` | `satellite-black-warder-safe-220x132.zip` | `piconSat_220x132/` | 269 legacy; 1 safe |
| Satellite / White | existing `piconSat-white.zip` | `piconSat/` | `satellite-white-warder-safe-220x132.zip` | `piconSat_220x132/` | 269 legacy; 1 safe |

Existing black/white fallback archive hashes and sizes are pinned in `candidate-downloads.json` and `archive-manifest.json`. The two repacked transparent fallback ZIPs have new hashes/sizes because their ZIP paths change; every PNG member SHA remains exactly the pinned upstream PNG SHA.

Safe archive member paths are `piconProv_220x132/<filename>` or `piconSat_220x132/<filename>`. Every safe archive contains only the strict-gate identities, with no REVIEW or SOURCE-UNRESOLVED members.

## Coverage outcome

All current legacy filename identities remain in the base fallback layer. Safe identities are additive in the 220x132 priority layer. Resulting lookup counts are preserved or increased:

- Provider Transparent 1145; Black 1306 (1297 legacy + 9 newly supplied safe identities); White 1265 (1256 + 9).
- Satellite Transparent 69; Black 269; White 269.

The additions do not change the legacy classification. REVIEW-BLOCKED and SOURCE-UNRESOLVED identities remain legacy-only and are not included in the Warder-safe manifest.

## Non-destructive install and rollback

- Never remove, rename, or recursively replace `piconProv/`, `piconSat/`, or either priority directory.
- Extract into a temporary directory; accept only regular `.png` members; copy only listed members into the declared destination and verify copied size/SHA as in the preserved `cprmFiles` fix.
- A retry may overwrite only a same-name PNG supplied by that package. Unlisted legacy files remain untouched.
- Rollback: remove only the six Warder-safe filenames listed in the safe migration manifest from the two priority directories, if a rollback is explicitly needed. Keep both base fallback directories and every unlisted file. Reapplying the existing legacy package restores its listed fallback contents without deleting other files.

## Manifest source and security boundary

Safe candidate archives are prepared in the PiconHub review branch and are not production-published. The eventual TEST manifest must use an immutable candidate commit URL and an explicit publication descriptor. The downloader must allow only the exact owner/repository/ref/root declared by that descriptor, reject traversal and cross-ref redirects, and keep size/SHA checks mandatory. Do not broaden the existing raw GitHub allowlist. Do not point the stable manifest or `main` at candidate assets.

## FullHDGlass changes still required before TEST202

1. Add an auxiliary-only two-stage package plan so each of the six existing GUI choices runs its fallback then safe overlay.
2. Bind both archive URL roots to explicit allowed publication descriptors; the current generic auxiliary downloader has a hard-coded `FullHDGlass.../main/assets/warder/downloads/` prefix and cannot consume PiconHub review-branch URLs as-is.
3. Keep exact counts/statuses per stage and preserve task choices on error/cancel.
4. Run the focused channel regression unchanged, including the TEST201 receiver baseline `2643 updated / 0 errors` supplied by the user.
5. Complete the UI checklist in `ui-change-plan.json` and validate gettext for all 19 catalogs before any TEST202 build.
