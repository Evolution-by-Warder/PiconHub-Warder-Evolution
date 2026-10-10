# OpenATV: propagácia už nájdených kandidátnych väzieb

Oprava `openatv_candidate_link.py`: skupiny názvov teraz berú do úvahy aj riadky, ktoré už majú stav `EVIDENCE_LINKED`. Predtým sa tieto riadky úplne ignorovali a ich dôkaz sa nemohol preniesť na ďalší grafický variant rovnakej stanice.

- Prenos iba ak existuje presne jedna kandidátna referencia v celej skupine.
- Pri konfliktných referenciách sa nepriradí žiadny ďalší súbor.
- Už prepojené riadky sa druhýkrát nepočítajú ako nové prepojenia.
- Všetky kandidátne väzby zostávajú neoverené; žiadny zápis Warder ID do produkcie.
- Skutočný počet dodatočných väzieb závisí od lokálnych dát na Windows a nie je týmto testom potvrdený.
