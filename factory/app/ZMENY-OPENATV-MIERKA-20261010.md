# OpenATV – zhodné logá pri odlišnej mierke

- Pridaný `openatv_scaled_evidence.py` s dvomi presnými normalizovanými odtlačkami (48/96 px).
- Kandidátna zhoda neznamená potvrdenú identitu a neprepisuje Warder Master.
- Viacnásobné referencie ostávajú nejednoznačné.
- Integrácia v `engine.py` pred propagáciou názvových kandidátov.
- Bez zmien zdrojových PNG, Chocholouska či produkčného GitHub.
- Lokálne: `python -m unittest discover -p 'test_*.py' -q` – 151 testov OK.
- Skutočný počet dodatočných OpenATV kandidátov musí potvrdiť Windows beh.
