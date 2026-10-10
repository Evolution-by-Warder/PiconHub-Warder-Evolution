# OpenATV: implementovaná klasifikácia grafickej väzby

Položky s jednoznačným presným SHA-256 dôkazom v rámci skupiny rovnakého OpenATV názvu dostanú stav `EVIDENCE_LINKED` a pole `candidate_service_reference`. Nie sú ďalej počítané medzi úplne nenamapované súbory. `service_reference` zostáva `null`, `identity_verified` zostáva `false`, žiadny Warder ID sa nemení a neprepisujú sa pôvodné súbory. Pri viacnásobných dôkazoch sa nič nepriradí. `EVIDENCE_LINKED` sa neberie ako schválená zhoda ani ako povinná ručná výnimka.

Výsledky sa zobrazujú v hlavnom logu a v `registry-matches-*.json` (evidence_linked / unmapped a source_breakdown). QA a grafické opravy nie sú súčasťou tejto dávky. Na reálnych Windows dátach neoverené.
