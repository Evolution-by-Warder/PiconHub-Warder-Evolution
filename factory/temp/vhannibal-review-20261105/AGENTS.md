# Owner constraint for Vhannibal work

Do not overwrite picons already processed in CANAL+ SK/CZ on 23.5E. Preserve their current artwork in every size/background and corresponding satellite/MASTER copies. Vhannibal's Jednotka, Dvojka, RTVS/STVR 24, Sport and other logos can be stale.

Before any 23.5E/CANAL publication, MASTER replacement, source-database write or package rebuild, run canal235-protection/guard.py on the complete proposed write plan and honor every block/hold. Baseline and owner policy are alongside it. Different service types/namespaces, a newer archive and a generic approval of previews do not bypass protection. Never invent aliases from the protection comparison. New references need independent current-CANAL identity/variant checks and correct existing artwork reuse.

Astra235 batch07 is withdrawn from export. Its 39 protected groups must keep current CANAL artwork; 9 other groups are held. Historical ZIPs/previews do not override the current manifest. Other satellites continue under their existing rules. Radio work remains separate.

## Reuse CANAL graphics across positions and providers

Owner extension, 2026-11-05: reuse the completed CANAL+ SK/CZ artwork in the full 23.5E set and every other position/provider carrying the same station and variant. Before making a new graphic, look up the canonical source. Copy existing native-size/background PNG bytes; do not render the same artwork again. Keep country, language, regional and HD/SD/UHD variants distinct.

The guard now permits only the explicit CANAL_CANONICAL_REUSE operation for a verified target identity and exact pinned PNG hash, while source SK/CZ packages stay immutable. Ordinary Vhannibal writes to the verified reused identities are blocked on every position, including service-type aliases. Reuse evidence is in canal235-protection/reuse-evidence.json; missing or generic cross-market name evidence stays held.

## Completed approved Vhannibal batch

All 157 owner-approved graphics from batches 01–06 and Film Europe are complete: 138 approved PNG triplets, 8 existing same-variant master reuses and 11 protected CANAL reuses. The integration binds 175 exact non-CANAL references and is live in FullHDGlass PR40, commit d86f25e628fe910e54f5bbc8c71dcb5b4682ed57. Do not recreate, requeue or ask for approval of these graphics. Read the completion record and exclude its completed_source_pixel_keys before selecting new work. The remaining supplied usable source was subsequently completed; see the final completion record below. The separate withdrawn Astra235 batch07 and its 9 held groups retain their own constraints.

Completion record: approved-publication/completion.json.

## Entire supplied Vhannibal input completed

The 3 November Motor source is closed with explicit terminal exceptions. All 14,081 PNG items are classified; all 12,503 accepted current references are published in the full satellite sets in all nine size/background slots (FullHDGlass PR41, content commit c772496c2648d544c54fe92420551454ac50925b). Read ../vhannibal-final-20261105/completion.json, plans.json and source-dispositions.json before doing any follow-up. There is no remaining automatic usable-source queue. Do not recreate 670 accepted source artwork groups, reused Master/CANAL artwork, or the earlier 157 approved graphics. Only revisit an entry in ../vhannibal-final-20261105/exceptions.json when new independent identity/variant evidence resolves its recorded reason.

All original CANAL provider packages remain immutable. The guard additionally permits PRESERVED_NATIVE_SIZE_DERIVATIVE only for package paths, the identical full source/target reference, 50x30 or 400x240, and the exact native/output hashes in canal235-protection/published-native-reuse.json. It never authorizes fresh upstream 23.5E artwork or Master replacements. Keep every country/regional/HD/SD distinction and frozen background. Radio plugin work remains separate.
