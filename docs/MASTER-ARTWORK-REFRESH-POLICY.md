# MASTER artwork refresh

Owner instruction, 2026-11-05: “laska ked mame nevsie a lepsie loga tak ich nahrad aj v master sadach”. This authorizes replacing older station artwork in MASTER sets when the same station has a newer and better, owner-approved replacement. Existing Master artwork is no longer an automatic reason to hold such an update.

Compare old and new artwork first. A newer archive date alone does not prove a logo is newer or better. Preserve programme identity, exact service-reference filenames, regional/language variants and SD/HD/UHD markings. Use the exact approved Transparent/WHITE/BLACK PNG triplet consistently in every verified reference for that artwork. Retain before/after hashes and the owner approval binding in Git history. Distinct variants remain separate.

Unapproved alternatives remain review candidates. Pixel-identical images, size-only changes and changes without a clear quality or brand improvement do not trigger a replacement. Background MASTER templates and rendering-engine code remain unchanged.

Applied first to ShopLC: approved Astra batch03 artwork 19 replaces the older all-blue logo with the approved blue/red version at three existing Shop LC references, nine MASTER PNGs. The new artwork has no HD marking; exact existing service types remain intact. Factory source copies are synchronized separately. Live download packages are a separate publication stage.

## Specific owner exception — preserve CANAL+ SK/CZ on 23.5E

Owner instructions dated 2026-11-05 take precedence over the general refresh rule above: do not overwrite already processed CANAL+ SK/CZ picons on 23.5E. Vhannibal's Jednotka, Dvojka, RTVS/STVR 24, Sport and other artwork can be old. Preserve current CANAL artwork in provider, full-satellite and MASTER sets across all sizes/backgrounds. A generic approval of previews or a later archive date does not revoke this protection. New references require independent current-CANAL identity and variant checks and existing correct artwork reuse. Run the fail-closed guard before any proposed write. See docs/VHANNIBAL-CANAL235-PRESERVATION.md and the pinned baseline/guard under reports/warder-master-production/canal235-protection/ on this branch (or factory/temp/vhannibal-review-20261105/canal235-protection/ on factory-warder-development).
