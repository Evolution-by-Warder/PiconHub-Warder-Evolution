# WARDER PICON FACTORY – oprava hlavnej QA fronty

- Zmenené `review_queue.py`: OpenATV `REGISTRY_MATCH` záznamy s rovnakou overenou service-reference a rovnakým dôvodom kontroly sa zlúčia do jednej rozhodovacej položky. Všetky SHA-256 a cesty zdrojov zostávajú uložené v `source_evidence`.
- Opravené rozpoznanie pôvodu zdroja pri cestách Windows (`D:\\...`).
- Vhannibal, technické QA chyby, kolízie a záznamy bez service-reference zostávajú v pôvodnom režime. Rozličné dôvody kontroly sa nezlučujú.
- Nejde o automatické schvaľovanie ani vymazanie výnimiek. Existujúce rozhodnutia sú použiteľné iba pri nezmenenom dôkaze.
- Testované: 185 unit testov OK. Skutočný počet QA položiek na Windows neoverený; bez miestnych 199 044 PNG nemožno potvrdiť koncový beh.
- Bez zásahu do produkčného GitHubu, originálov alebo Warder Master.
