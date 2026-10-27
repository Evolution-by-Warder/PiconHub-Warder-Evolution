# PiconHub Warder Evolution

**Produkčná verzia 0.1.27**, schválená používateľom 27. októbra 2026. Plugin slúži na sťahovanie a správu piconov v Enigma2.

[Produkčný zápis](PRODUCTION.md) · [Stav overenia](BUILD-STATUS.md) · [Strojový záznam vydania](production.json)

## Aktuálne rozhranie

Výbery aj aktualizácie sa vykonávajú v ľavom paneli. Rovnaký panel používa priebeh sťahovania, spracovanie, výsledok, Log a O projekte. Hlavička a pravý náhľad zostávajú viditeľné. Vlastný priečinok začína v `/` a zobrazuje aj skryté adresáre a odkazy ako `/tmp` a `/hdd`. Schválené ikony, banner, zarovnanie dátumu/času/verzie a pôvodné farebné potvrdenia zostávajú zachované.

## Používanie

Šípkami vyber riadok a stlač OK. Vyber satelity alebo poskytovateľov, rozlíšenie, pozadie, režim a priečinok. Pri satelitoch OK označuje položky, zelené tlačidlo potvrdí výber a červené sa vráti bez zmeny.

- Rozlíšenia: **50×30, 220×132, 400×240**.
- Pozadia: **Transparent, Biele, Čierne**.
- Ponuka zahŕňa 53 identifikátorov družíc/poskytovateľov a samostatný zdroj **DAB / DAB+**. Pôvodný satelitný katalóg obsahuje 468 balíkov; DAB má vlastný overený katalóg.
- Režimy: podľa TV bouquetov, podľa TV a rádia, doplnenie/aktualizácia všetkých, úplné nahradenie vybraných pozícií.
- Profily sa v rozhraní nezobrazujú. Pri otvorení sú voľby neutrálne: „Vyber si…“.

Červené **Zatvoriť**, zelené **Stiahnuť**, žlté **Aktualizácia pluginu**, modré **O projekte**. Sťahovanie aj spracovanie všetkých pozícií zostáva v jednom okne s históriou riadkov. Po úspešnom dokončení a návrate sa obnoví úvodný výber aj náhľad; pri chybe zostanú voľby pripravené na opakovanie.

Textové okná používajú rovnaký nepriehľadný podklad. Šípky ↑/↓ posúvajú text, dlhší obsah má posuvník vpravo a dole je červené Naspäť. O projekte obsahuje poďakovanie s3n0 a Chocholousek aj zmeny nainštalovanej verzie dostupné bez internetu.

## Inštalácia a aktualizácie

[Stiahnuť IPK 0.1.27](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/releases/download/v0.1.27/enigma2-plugin-extensions-piconhub-warder-evolution_0.1.27_all.ipk).

Po skopírovaní konkrétneho balíka do `/tmp`:

```sh
opkg install /tmp/enigma2-plugin-extensions-piconhub-warder-evolution_0.1.27_all.ipk
```

Plugin sa inštaluje do `/usr/lib/enigma2/python/Plugins/Extensions/WarderPiconHub/`. Existujúce nastavenia sa zachovávajú. Pri každom otvorení prebehne kontrola novšej verzie na pozadí. Inštaláciu používateľ potvrdí; dostupná je aj ručná kontrola žltým tlačidlom. Po úspešnej aktualizácii sa zobrazí jediné oznámenie a GUI sa po 3 sekundách reštartuje. Bez internetu zostane plugin použiteľný.

Jazyky podľa systému: slovenčina, čeština, angličtina, nemčina, poľština, maďarčina, ruština, francúzština, taliančina a španielčina. Nepodporovaný jazyk používa angličtinu.

## Zostavenie

```sh
PYTHONPATH=plugin/src python3 -m unittest discover -s plugin/tests -v
python3 plugin/tools/build_ipk.py --output plugin/build
```

Zdroj vychádza z práce s3n0 a Chocholousek. Pôvodné autorské údaje, gettext katalógy a konfiguračné kľúče zostávajú zachované. Podrobnosti o overení a obmedzeniach sú v produkčnom zápise.

## DAB / DAB+

V riadku Satelity označ **DAB / DAB+ (220×132)**, prípadne aj ďalšie satelitné zdroje. Vyber rozlíšenie **220×132**, pozadie a režim zahŕňajúci rádio. Režim podľa TV a rádia inštaluje iba presné referencie nájdené v rádiových bouquetoch prijímača; pri samostatnom DAB v režime všetkých piconov sa nainštaluje celá dostupná DAB sada. Používa sa nastavený cieľový priečinok, bežne `picon/`.

Aktuálna sada: **51 označení staníc / 80 presných referencií**, každá v troch pozadiach. ASA DE zostáva vynechaná. Existujúce picony mimo pokrytia sa zachovávajú. Balík pluginu má **2 864 610 bajtov**; obrázkové ZIPy sa sťahujú samostatne. Prešlo **175 testov**, CI, kontrola verejného IPK aj skutočné sťahovanie všetkých troch štýlov. Fyzické overenie 0.1.27 v prijímači sa zatiaľ netvrdí.
