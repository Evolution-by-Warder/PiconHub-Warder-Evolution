# Owner constraint for Vhannibal work

Do not overwrite picons already processed in CANAL+ SK/CZ on 23.5E. Preserve their current artwork in every size/background and corresponding satellite/MASTER copies. Vhannibal's Jednotka, Dvojka, RTVS/STVR 24, Sport and other logos can be stale.

Before any 23.5E/CANAL publication, MASTER replacement, source-database write or package rebuild, run canal235-protection/guard.py on the complete proposed write plan and honor every block/hold. Baseline and owner policy are alongside it. Different service types/namespaces, a newer archive and a generic approval of previews do not bypass protection. Never invent aliases from the protection comparison. New references need independent current-CANAL identity/variant checks and correct existing artwork reuse.

Astra235 batch07 is withdrawn from export. Its 39 protected groups must keep current CANAL artwork; 9 other groups are held. Historical ZIPs/previews do not override the current manifest. Other satellites continue under their existing rules. Radio work remains separate.

## Reuse CANAL graphics across positions and providers

Owner extension, 2026-11-05: reuse the completed CANAL+ SK/CZ artwork in the full 23.5E set and every other position/provider carrying the same station and variant. Before making a new graphic, look up the canonical source. Copy existing native-size/background PNG bytes; do not render the same artwork again. Keep country, language, regional and HD/SD/UHD variants distinct.

The guard now permits only the explicit CANAL_CANONICAL_REUSE operation for a verified target identity and exact pinned PNG hash, while source SK/CZ packages stay immutable. Ordinary Vhannibal writes to the verified reused identities are blocked on every position, including service-type aliases. Reuse evidence is in canal235-protection/reuse-evidence.json; missing or generic cross-market name evidence stays held.
