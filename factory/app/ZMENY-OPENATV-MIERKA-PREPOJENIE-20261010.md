# OpenATV – oprava prepojenia zhôd podľa mierky

Opravený chýbajúci stav `SCALE_EXACT_SINGLE_MASTER_REF` / `SCALE_EXACT_MULTIPLE_MASTER_REFS` v `openatv_candidate_link.py`. Predtým sa dôkaz nájdený v `openatv_scaled_evidence.py` ignoroval pri prenose na ostatné varianty rovnakého názvu. Jednoznačný dôkaz teraz vytvorí `EVIDENCE_LINKED`, konfliktné referencie zostanú `UNMAPPED`. Všetky identity zostávajú neoverené, bez zápisu do Warder Master.

Opravený aj nepresný popis `evidence_type`, ktorý tvrdil SHA-256 aj pre pixelové/normalizované/škálované dôkazy.

Lokálne overenie: 153 unit testov OK. Reálny Windows beh a počet nových zhôd nie sú overené.
