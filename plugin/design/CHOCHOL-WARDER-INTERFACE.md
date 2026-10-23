> Implementation checkpoint: the design and subsequent user refinements are implemented in development 0.1.0-dev2. The native controllers, XML layouts and package pass local checks; physical receiver validation is pending. Historical pending statements below describe earlier checkpoints. See ../DEVELOPMENT-DEV2.md.

# Návrh rozhrania PiconHub Warder Evolution

Dátum: 23. októbra 2026. Stav: návrh po statickom rozbore; obrazovky ešte nie sú implementované ani otestované na prijímači.

## Platné zadanie

Použiť Chocholousek Picons ako funkčný základ a modernizovať jeho rozhranie v štýle Warder. Toto rozhodnutie používateľa nahrádza predchádzajúci plán vytvoriť celý runtime od nuly. Zachovať pôvod autora s3n0, nastavenia a zrozumiteľné správanie. Prvá dávka nového čítača Warder katalógu zostáva samostatným adaptérom pre neskoršiu integráciu.

## Skontrolovaný zdroj

- Projekt: https://github.com/s3n0/e2plugins/tree/84a40ed6b01f8dc7d49b632f886525b9c51773c7/ChocholousekPicons
- Deklarovaná verzia: 5.0.240904.
- plugin.py: blob a8e4c4e86984f384415a65ad640eef5095c6bbad; posledná zmena súboru 893492286b18eadf3581079b06bf4369531aca0f.
- Statický rozbor 1 960 riadkov, štyroch Screen tried, konfigurácie, callbackov, aktualizačného toku, archívov a sťahovania; kontrola syntaktickým parserom. Enigma2 runtime nebol spustený.
- Naša plugin-warder-evolution-migration obsahuje pracovnú kostru a metadáta; jej runtime priečinok aktuálne neobsahuje plugin.py. Skoršie tvrdenie o zachovanom celom runtime v tejto vetve bolo nepresné. Skutočný zdroj pre túto analýzu je vyššie uvedený upstream.

## Prepojenie existujúceho kódu a návrhu

| Pôvodná časť | Čo zachováme | Nové rozhranie |
|---|---|---|
| mainConfigScreen | Profily, ich zapnutie, konfigurácia a automatické ukladanie | Prehľad s profilmi 1–3 hore, zoznamom nastavení vľavo, náhľadom vpravo |
| satellitesConfigScreen | Výber viacerých satelitov, použiť alebo zrušiť zmeny | Čitateľný zoznam so zaškrtnutím a počtom vybraných položiek |
| directoryBrowserScreen | Výber a vytvorenie priečinka | Celá cesta, dostupné úložiská, počet piconov; mazanie oddelene v možnostiach |
| piconsUpdateJobScreen | Spracovanie profilov, bouquetov, archívov, počítadlá a log | Fázy úlohy, aktuálny balík, výsledky a rozbaliteľný technický log |

Viditeľné profily sú tri (1–3). Interná položka 0 nie je štvrtý používateľský profil a nemožno ju svojvoľne premapovať. Už uložené hodnoty config.plugins.chocholousekpicons sa zachovajú; technický adresár ChocholousekPicons sa pri prvej modernizácii nepremenuje len kvôli značke.

## Hlavná obrazovka — odporúčaný návrh

Full HD 1920×1080; samostatne prispôsobený HD variant 1280×720. Hore naše originálne hlavičky, tmavomodré pozadie, biele texty a cyan zvýraznenie. Efekty zostanú v pripravených bitmapách; netreba priebežné animácie ani video.

Hlavná plocha:
- Hore záložky Profil 1 / Profil 2 / Profil 3 a jasné zapnutie aktuálneho profilu.
- Vľavo riadky: Satelity; Rozlíšenie; Pozadie; Režim aktualizácie; Priečinok.
- Vpravo picon vybraného štýlu v správnom pomere strán a stručný súhrn. Pri chýbajúcom náhľade výslovne zobraziť jeho nedostupnosť.
- Dostupnosť kombinácie rozlíšenia, štýlu a satelitov určuje zdroj balíkov. Žiadna tichá zámena.
- Zachovať automatické ukladanie konfigurácie a uviesť ho na obrazovke. Zelené tlačidlo preto označiť Aktualizovať, nie Uložiť.
- Červené Späť; zelené Aktualizovať; žlté Satelity; modré Možnosti. Reset profilu a aktualizácia pluginu patria do Možností.
- Šípky hore/dole menia fokus; v riadku hodnoty ľavá/pravá mení nastavenie; OK otvára detail satelitov či priečinka. Profily sa šípkami menia až po presunutí fokusu na záložky.

Šesť poskytovateľských dlaždíc z prvého obrázka nie je vhodná náhrada konfigurácie Chocholouska. Možno ich neskôr použiť vo výbere balíkov Warder, keď bude tento zdroj naozaj pripojený. Pôvodný engine vyberá satelitné 7z balíky z picon.cz, nie naše ZIP balíky.

## Režimy a správanie

Použiť zrozumiteľné názvy existujúcich režimov: Podľa TV bouquetov; Podľa TV a rádia; Doplniť a aktualizovať všetky; Úplne nahradiť. Zachovať ich význam; SNP ponechať iba pri režimoch, ktoré pôvodný engine podporuje.

Aktualizačná obrazovka má fázy Príprava → Sťahovanie → Rozbaľovanie → Dokončenie. Počet spracovaných balíkov zobraziť z reálnych udalostí. Percentá stiahnutých bajtov až po doplnení príslušných callbackov; počas neurčitej operácie použiť neurčitý indikátor. Výsledok musí odlíšiť úspech, čiastočný výsledok a zlyhanie.

## Technické úpravy potrebné pri integrácii

Tieto body sú zistenia a návrhy, nie hotové opravy:
- proceedCfgProfile vracia niektoré chyby, ale volajúci mainFunc ich nevyhodnocuje. Chyby jednotlivých archívov sa tiež nemajú stratiť za všeobecným výsledkom.
- Pôvodný tok vie mazať existujúce picony pred stiahnutím náhrad. Pripraviť nové súbory a overiť ich pred zásahom do cieľa; zmenu tohto správania testovať samostatne.
- Inkrementálna aktualizácia porovnáva veľkosť PNG. Pri Warder zdroji využiť kontrolné súčty aj na rovnako veľké zmenené obrázky.
- downloadFile načíta celé sťahovanie naraz a nemá callback pre bajty. Pridať streamovanie a udalosti pre GUI; dlhé operácie nespúšťať v GUI vlákne.
- Zachovať odovzdávanie GUI aktualizácií do hlavného vlákna. Nahradiť blokujúce sleep v ukončení úlohy časovačom.
- Nemeniť globálne overovanie TLS pri importe; obnoviť overovanie certifikátov v integračnej dávke.
- Aktualizátor pluginu musí pri Warder balíku sledovať Warder vydania, aby pôvodný updater neprepísal nové rozhranie upstream balíkom.
- Napojenie Warder JSON/ZIP a pôvodného 7z/picon.cz oddeliť adaptérom zdroja. Zachovať existujúcu logiku profilov a bouquetov; nesľubovať, že oba formáty už fungujú.

## Postup implementácie

1. Zachytiť pôvodný zdroj a jeho závislosti s presným pôvodom.
2. Pripojiť nové XML skiny, náhľady a mapovanie ovládača k existujúcim funkciám.
3. Doplniť udalosti a správny výsledok aktualizačnej úlohy.
4. Samostatne integrovať Warder zdroj, bezpečnú prípravu súborov a distribúciu IPK.
5. Overiť profily, všetky režimy, satelity, vlastné cesty a chyby; potom reálne OpenATV testy.

Žiadne produkčné picony, staré vetvy, MASTERy ani obnovovacie grafiky sa týmto návrhom nemenia.

## Doplnenie hlavičky podľa používateľa — 23. októbra 2026

Vpravo hore zobraziť deň v týždni, pod ním dátum a vedľa veľký digitálny čas HH:MM podľa dodaného logo.jpg. Texty oddeliť tenkými cyan zvislými čiarami; napravo zobraziť aktuálnu nainštalovanú verziu pluginu namiesto označenia ENIGMA2. Zachovať zvyšok navrhnutého rozhrania.

V implementácii ide o živé textové widgety napojené na systémový čas a časové pásmo prijímača, nie o dátum a hodiny vypálené do podkladovej bitmapy. Hodnoty obnovovať počas otvorenia obrazovky vrátane zmeny dňa; rešpektovať jazyk Enigmy a nastavené letné/zimné časové pásmo. Použiť čas prijímača bez samostatnej internetovej synchronizácie z pluginu. Grafický podklad musí byť pod týmito widgetmi bez starého dátumu a času.

Náhľad s údajmi Piatok, 23. októbra 2026, 10:48 je statická ilustrácia tejto požiadavky. Živé hodiny zatiaľ nie sú implementované ani overené na prijímači.

## Verzia pluginu v hlavičke — doplnenie používateľa

Vpravo od hodín zobrazovať aktuálnu nainštalovanú verziu PiconHub Warder Evolution, nie text ENIGMA2. Hodnotu čítať zo spoločného runtime údaja verzie použitého aj pri zostavení balíka; nesmie byť vypálená do pozadia ani predstavovať dostupnú online verziu. V návrhu sa používa vývojové označenie v0.1.0-dev1. Údaj o dostupnej aktualizácii zobrazovať osobitne v Možnostiach. Zatiaľ ide o návrh, živý widget nie je implementovaný.

## Odstránenie stredového sloganu — doplnenie používateľa

Z hornej lišty odstrániť oba stredové riadky More channels. a A better TV experience. Oblasť ponechať ako čisté grafické pozadie bez náhradného textu. Logo PICONHUB by Warder, menší text pod logom, deň/dátum/čas a aktuálna verzia pluginu zostávajú. Ide o úpravu návrhu; pôvodné obnovovacie hlavičky zachovať bez prepísania.

## Výberové okná a ponuky zo skinu — potvrdenie používateľa

Každý riadok sa otvorí tlačidlom OK ako malé výberové okno. Satelity umožnia označiť viac položiek a potvrdiť výber zeleným tlačidlom. Rozlíšenie, pozadie a režim používajú jednotlivý výber; priečinok výber umiestnenia. EXIT zavrie rozpracovaný výber bez zmeny.

Pozadie zatiaľ ponúka iba Transparent, Biele a Čierne. Spoločné ponuky vychádzajú z rovnakých dostupných možností a dostupnosti balíkov ako v našom skine; historické položky, ktoré skin neponúka, nepridávať automaticky do menu len preto, že existujú v katalógu.

## Kontrola verzie pri každom otvorení — spresnenie používateľa

Automatická aktualizácia znamená automaticky skontrolovať GitHub pri každom novom otvorení pluginu a pri novšom zverejnenom vydaní ponúknuť inštaláciu. Nejde o autoaktualizáciu piconov, denný plánovač ani tichú inštaláciu v pohotovostnom režime. Odmietnutie ponuky nič neinštaluje. Výpadok internetu neblokuje otvorenie pluginu. Súčasťou implementačnej dávky je tento hook v pôvodnej hlavnej obrazovke; moderné výberové okná a finálna hlavička ešte čakajú na implementáciu.
