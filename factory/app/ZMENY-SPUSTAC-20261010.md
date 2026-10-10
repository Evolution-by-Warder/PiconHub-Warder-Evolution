# WARDER FACTORY – integračná dávka spúšťača

- `START-WARDER-FACTORY.cmd`: jediný plánovaný súbor v koreni `D:\` (pri budúcej schválenej inštalácii).
- `factory_launcher.py`: spustí existujúci engine bez neoverenej aktualizácie; log v `08-REPORTS`.
- Python venv očakávaný mimo vymieňaného adresára aplikácie (`11-APP\.warder-venv`).
- `test_factory_launcher.py`: testy chýbajúceho engine, úspešného a neúspešného spustenia.

**Pozor:** tento vývojový ZIP nie je inštalátor. `.cmd` nie je nasadený do `D:\` a nebol otestovaný na Windows. Inštalácia knižníc/venv a transakčné potvrdenie GUI štartu nie sú integrované. Online automatická aktualizácia zostáva vypnutá, kým nebude zabezpečený dôveryhodný manifest.
