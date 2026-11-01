# PiconHub Warder Evolution

**Produkčná verzia 0.1.38** používa iba krátke názvy IPK. Z 0.1.32 je potrebná jedna ručná inštalácia bez odinštalovania; ďalšie aktualizácie už fungujú s krátkymi názvami. Plugin slúži na sťahovanie a správu piconov v Enigma2.

[Produkčný zápis](PRODUCTION.md) · [Stav overenia](BUILD-STATUS.md) · [Strojový záznam vydania](production.json)

## Aktuálne rozhranie

Výbery aj aktualizácie sa vykonávajú v ľavom paneli. Rovnaký panel používa priebeh sťahovania, spracovanie, výsledok, Log a O projekte. Hlavička a pravý náhľad zostávajú viditeľné. Vlastný priečinok začína v `/` a zobrazuje aj skryté adresáre a odkazy ako `/tmp` a `/hdd`. Schválené ikony, banner, zarovnanie dátumu/času/verzie a pôvodné farebné potvrdenia zostávajú zachované.

## Používanie

Šípkami ←/→ vyber profil; šípkami ↑/↓ vyber riadok a stlač OK. Vyber satelity alebo poskytovateľov, rozlíšenie, pozadie, režim a priečinok. Pri satelitoch OK označuje položky, zelené tlačidlo potvrdí výber a červené sa vráti bez zmeny.

- Rozlíšenia: **50×30, 220×132, 400×240**.
- Pozadia: **Transparent, Biele, Čierne**.
- Ponuka zahŕňa družice a poskytovateľov aj samostatné zdroje **IPTV rádiá SK/CZ**, **DAB / DAB+** a **DVB-T CZ/SK**. Rádiové zdroje používajú vlastné overené katalógy.
- Režimy: podľa TV bouquetov, podľa TV a rádia, doplnenie/aktualizácia všetkých, úplné nahradenie vybraných pozícií.
- **Štyri nezávislé profily** si pamätajú vlastné nastavenia aj označenie po opätovnom otvorení a reštarte GUI.
- **0** označí alebo odznačí otvorený profil. Zelená fajka znamená zaradenie na spracovanie; modrá záložka označuje profil otvorený na úpravu.
- Spracovať možno ľubovoľný jeden, dva, tri alebo všetky štyri profily. Bez označenia je **Stiahnuť (0)** neaktívne.

Červené **Zatvoriť**, zelené **Stiahnuť**, žlté **Aktualizácia pluginu**, modré **O projekte**. Sťahovanie aj spracovanie všetkých pozícií zostáva v jednom okne s históriou riadkov. Po dokončení, chybe alebo zrušení zostanú nastavenia a označenia profilov zachované.

Textové okná používajú rovnaký nepriehľadný podklad. Šípky ↑/↓ posúvajú text, dlhší obsah má posuvník vpravo a dole je červené Naspäť. O projekte obsahuje poďakovanie s3n0 a Chocholousek aj zmeny nainštalovanej verzie dostupné bez internetu.

## Inštalácia a aktualizácie

[Stiahnuť IPK 0.1.38](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/releases/download/v0.1.38/enigma2-plugin-extensions-piconhub_0.1.38_all.ipk).

Skopíruj IPK do `/tmp` a nainštaluj ho cez sprievodcu inštaláciou miestnych rozšírení v prijímači. Existujúcu inštaláciu neodinštaluj. Po aktualizácii reštartuj GUI. Z 0.1.32 je potrebný tento jednorazový ručný prechod; neskoršie podporované verzie získajú 0.1.38 cez aktualizačný kanál.

Plugin sa inštaluje do `/usr/lib/enigma2/python/Plugins/Extensions/WarderPiconHub/`. Existujúce nastavenia sa zachovávajú. Pri každom otvorení prebehne kontrola novšej verzie na pozadí. Inštaláciu používateľ potvrdí; dostupná je aj ručná kontrola žltým tlačidlom. Po úspešnej aktualizácii sa zobrazí jediné oznámenie a GUI sa po 3 sekundách reštartuje. Bez internetu zostane plugin použiteľný.

Jazyky podľa systému: slovenčina, čeština, angličtina, nemčina, poľština, maďarčina, ruština, francúzština, taliančina a španielčina. Nepodporovaný jazyk používa angličtinu.

## Zostavenie

```sh
PYTHONPATH=plugin/src python3 -m unittest discover -s plugin/tests -v
python3 plugin/tools/build_ipk.py --output plugin/build
```

Zdroj vychádza z práce s3n0 a Chocholousek. Pôvodné autorské údaje, gettext katalógy a konfiguračné kľúče zostávajú zachované. Podrobnosti o overení a obmedzeniach sú v produkčnom zápise.

## DAB / DAB+

V riadku Satelity označ **DAB / DAB+**, prípadne aj ďalšie satelitné zdroje. Vyber rozlíšenie **220×132**, pozadie a režim zahŕňajúci rádio. Režim podľa TV a rádia inštaluje iba presné referencie nájdené v rádiových bouquetoch prijímača; pri samostatnom DAB v režime všetkých piconov sa nainštaluje celá dostupná DAB sada. Používa sa nastavený cieľový priečinok, bežne `picon/`.

Aktuálne pokrytie a presné kontrolné súčty určuje [živý DAB katalóg](../picons/DAB/catalog/release.json). ASA DE je súčasťou DAB a celkovej 23.5E, nie Canal+ balíkov. Existujúce picony mimo pokrytia sa zachovávajú. IPK 0.1.38 má **2 883 764 bajtov**; obrázkové ZIPy sa sťahujú samostatne. Prešlo **214 testov** a overenie verejného IPK. Fyzický test tejto verzie na prijímači sa zatiaľ netvrdí.


DAB a DVB-T majú ikony pred názvom; rozlíšenie je samostatná voľba. Obnovený pôvodný archív DVB-T CZ/SK obsahuje 2 674 PNG v prevedení Transparent 220×132. Biele a čierne prevedenie je odvodené z tých istých transparentných log na schválených Warder MASTER podkladoch a je už dostupné v spoločnom katalógu. Historický archív nepredstavuje záruku úplného aktuálneho pokrytia. Opravené filtrovanie DAB pri spoločnom výbere satelitnej pozície.


Dátová aktualizácia 27. októbra 2026: DVB-T CZ/SK 220×132 je dostupné v prevedeniach Transparent, Biele a Čierne. Každé má rovnakých 2 674 referencií; pôvodné transparentné súbory a farby log zostali zachované. Oba odvodené balíky prešli skutočnou inštaláciou cez Warder engine a overením všetkých verejných častí podľa SHA256. IPK sa nemení. [Zdroj a presné hashe](../picons/DVB-T/catalog/variants.json).


## IPTV rádiá SK/CZ

Prvá položka ponuky, s vlastnou ikonou. Rozlíšenia 50×30, 220×132, 400×240; Transparent, Biele a Čierne. Picony pre 247 položiek, v každom variante 263 referenčných PNG. [Obnovené bouquety a pokrytie](../picons/IPTV-SK-CZ/README.md): 321 položiek, z toho 286 URL vrátilo zvukové dáta pri skúške; 74 položiek zatiaľ bez vhodného overeného piconu.

Sťahovanie IPTV spolu s DAB vyžaduje 220×132. Kontrola archívov aj PNG podľa SHA256 a presnej rádiovej referencie; nesúvisiace picony sa zachovajú. Voľba podľa TV tento rádiový zdroj odmietne. Automatická kontrola novšej verzie pri každom otvorení zostáva aktívna.


Dátové doplnenie 28.10.2026 (r2): 247 položiek s piconmi / 263 referencií v každom z deviatich variantov, 74 zatiaľ bez vhodného overeného piconu. Overené Radia.sk, Radia.cz a MyOnlineRadio.cz aj dodané originály. Všetkých deväť verejných archívov a obrázkov prešlo kontrolou; aktuálne dáta sa stiahnu opätovným výberom IPTV rádiá SK/CZ. Verzie IPK sa nemenia. [Zdroje a zhodovanie](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/blob/main/picons/IPTV-SK-CZ/catalog/followup-sources.json).
