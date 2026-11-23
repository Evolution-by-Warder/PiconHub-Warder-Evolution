# PiconHub Warder Evolution – Enigma2 plugin

PiconHub poskytuje sťahovanie a správu satelitných piconov, providerov, DAB/DAB+, DVB-T CZ/SK a DTT ITALIA.

**Runtime:** `/usr/lib/enigma2/python/Plugins/Extensions/WarderPiconHub/`

**Verzia pluginu:** 0.1.45. Overenie verejného vydania a aktualizačných kanálov sa riadi súbormi `plugin/PRODUCTION.md`, `plugin/update/` a `plugin/TESTOVANIE.md`, ak sú v repozitári dostupné.

## Ovládanie

- Vyberte jeden alebo viac profilov. Sťahovanie spracuje len označené profily.
- Vyberte satelitné pozície/poskytovateľov, DAB alebo DVB-T, veľkosť a pozadie podľa dostupnosti.
- Nastavte cieľ na interné úložisko, HDD, USB alebo vlastný priečinok.
- Zelené tlačidlo spustí sťahovanie, červené zatvorí, žlté otvorí aktualizáciu, modré informácie.
- Kontroly kontrolných súčtov a bezpečná inštalácia chránia používateľské súbory.

## Vývoj

```sh
PYTHONPATH=plugin/src python3 -m unittest discover -s plugin/tests -v
python3 plugin/tools/build_ipk.py --output plugin/build
```

Satelitné, DAB a terestriálne picony zostávajú samostatnými katalógmi a ZIP balíkmi. Neprebiehajú žiadne automatické zmeny používateľských súborov mimo potvrdenej akcie.
