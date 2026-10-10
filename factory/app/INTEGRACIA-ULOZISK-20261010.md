# Integrácia dvoch úložísk – pracovná dávka

- `04-WORK/PICONS`: všetky rozpracované varianty (SHA adresáre) a ich QA náhľady.
- `06-OUTPUT/PICONS`: iba explicitne QA-schválené výsledky; žiadne automatické publikovanie.
- `warder_storage_policy.py`: overený atomický zápis schváleného PNG s SHA-256.
- Opravený predvolený root a text GUI; pôvodný výstupný hash layout sa zachováva v pracovnom úložisku.
- Súčasný GUI tok zaznamenáva rozhodnutia, ale ešte neprenáša schválené PNG do finálneho úložiska. Toto nie je finálna inštalačná aktualizácia.
- Pred nasadením treba migrovať existujúce lokálne dáta a vyriešiť kompatibilitu starých stavových ciest.
- GitHub sa nemenil. Nič sa nemaže.
