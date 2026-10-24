# PiconHub Warder Evolution

**Produkčná verzia 0.1.25**, schválená používateľom 24. októbra 2026. Plugin slúži na sťahovanie a správu piconov v Enigma2.

[Produkčný zápis](PRODUCTION.md) · [Stav overenia](BUILD-STATUS.md) · [Strojový záznam vydania](production.json)

## Aktuálne rozhranie

Výbery aj aktualizácie sa vykonávajú v ľavom paneli. Rovnaký panel používa priebeh sťahovania, spracovanie, výsledok, Log a O projekte. Hlavička a pravý náhľad zostávajú viditeľné. Vlastný priečinok začína v `/` a zobrazuje aj skryté adresáre a odkazy ako `/tmp` a `/hdd`. Schválené ikony, banner, zarovnanie dátumu/času/verzie a pôvodné farebné potvrdenia zostávajú zachované.

## Používanie

Šípkami vyber riadok a stlač OK. Vyber satelity alebo poskytovateľov, rozlíšenie, pozadie, režim a priečinok. Pri satelitoch OK označuje položky, zelené tlačidlo potvrdí výber a červené sa vráti bez zmeny.

- Rozlíšenia: **50×30, 220×132, 400×240**.
- Pozadia: **Transparent, Biele, Čierne**.
- Ponuka zahŕňa 53 identifikátorov družíc/poskytovateľov; priložený katalóg obsahuje 468 balíkov.
- Režimy: podľa TV bouquetov, podľa TV a rádia, doplnenie/aktualizácia všetkých, úplné nahradenie vybraných pozícií.
- Profily sa v rozhraní nezobrazujú. Pri otvorení sú voľby neutrálne: „Vyber si…“.

Červené **Zatvoriť**, zelené **Stiahnuť**, žlté **Aktualizácia pluginu**, modré **O projekte**. Sťahovanie aj spracovanie všetkých pozícií zostáva v jednom okne s históriou riadkov. Po úspešnom dokončení a návrate sa obnoví úvodný výber aj náhľad; pri chybe zostanú voľby pripravené na opakovanie.

Textové okná používajú rovnaký nepriehľadný podklad. Šípky ↑/↓ posúvajú text, dlhší obsah má posuvník vpravo a dole je červené Naspäť. O projekte obsahuje poďakovanie s3n0 a Chocholousek aj zmeny nainštalovanej verzie dostupné bez internetu.

## Inštalácia a aktualizácie

[Stiahnuť IPK 0.1.25](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/releases/download/v0.1.25/enigma2-plugin-extensions-piconhub-warder-evolution_0.1.25_all.ipk).

Po skopírovaní konkrétneho balíka do `/tmp`:

```sh
opkg install /tmp/enigma2-plugin-extensions-piconhub-warder-evolution_0.1.25_all.ipk
```

Plugin sa inštaluje do `/usr/lib/enigma2/python/Plugins/Extensions/WarderPiconHub/`. Existujúce nastavenia sa zachovávajú. Pri každom otvorení prebehne kontrola novšej verzie na pozadí. Inštaláciu používateľ potvrdí; dostupná je aj ručná kontrola žltým tlačidlom. Po úspešnej aktualizácii sa zobrazí jediné oznámenie a GUI sa po 3 sekundách reštartuje. Bez internetu zostane plugin použiteľný.

Jazyky podľa systému: slovenčina, čeština, angličtina, nemčina, poľština, maďarčina, ruština, francúzština, taliančina a španielčina. Nepodporovaný jazyk používa angličtinu.

## Zostavenie

```sh
PYTHONPATH=plugin/src python3 -m unittest discover -s plugin/tests -v
python3 plugin/tools/build_ipk.py --output plugin/build
```

Zdroj vychádza z práce s3n0 a Chocholousek. Pôvodné autorské údaje, gettext katalógy a konfiguračné kľúče zostávajú zachované. Podrobnosti o overení a obmedzeniach sú v produkčnom zápise.
