# PiconHub Warder Evolution — ostrá prevádzka

Zápis z 27. októbra 2026 na výslovný pokyn vlastníka projektu. Schválená produkčná základňa: **0.1.29**. Tento dokument nahrádza staré vývojové popisy; historické podklady zostávajú zachované.

## Identita vydania

- Balík: `enigma2-plugin-extensions-piconhub-warder-evolution_0.1.29_all.ipk`.
- Tag: `v0.1.29`.
- Zdrojový commit: `93fd4546b2e3ebc617404a4c271a5278f763fadd`.
- Veľkosť: **2 875 124 bajtov**.
- SHA256: `076eaf60dca9d7d5f7a929462f4be56ee5a2820fcba5f047adfcc8de60fb6233`.
- Inštalačný priečinok: `/usr/lib/enigma2/python/Plugins/Extensions/WarderPiconHub/`.
- [Vydanie a IPK](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/releases/tag/v0.1.29).

Produkčné označenie nemení už vydané bajty IPK. Samostatný workflow pred zrušením označenia Pre-release overí verejne stiahnutý balík, jeho SHA256, veľkosť, zdrojový commit a súlad s [production.json](production.json). Repozitár je určený pluginu do prijímača. Produkčná propagácia nastaví jeho schválené vydanie ako GitHub Latest.

## Dohodnuté rozhranie

- Schválené futuristické rozhranie, chrómová lebka z náhľadu vľavo hore bez jej spodného nápisu; samostatný veľký názov PICONHUB zostáva. Žiadne riadky „More channels / Better…“.
- Dátum s preloženým dňom a mesiacom, živý čas s menšími bielymi sekundami a tyrkysová verzia v hlavičke.
- Šesť posledných pridaných piconov v čiernom štýle; úvodné logo v náhľade, po výbere náhľad zodpovedá pozadiu a rozlíšeniu.
- Päť riadkov: Satelity, Rozlíšenie, Pozadie, Režim, Priečinok. Vstup cez OK otvorí výber v ľavom paneli hlavnej obrazovky; neutrálne hodnoty „Vyber si…“.
- Rozlíšenia 50×30, 220×132 a 400×240; pozadia Transparent, Biele a Čierne. Menu družíc a poskytovateľov podľa skinu; poskytovatelia SK a CZ sa nezamieňajú.
- Pri družiciach jasne zelené označenie a ikony. Päta: Vybrať s OK, zelené Potvrdiť výber, červené Naspäť; názvy neobsahujú prefix názvu farby.
- Hlavná päta: červené Zatvoriť, zelené Stiahnuť, žlté Aktualizácia pluginu, modré O projekte.
- Jednotné nepriehľadné textové okná: automatické zalamovanie, posuvník vpravo podľa potreby, šípky ↑/↓ a iba červené Naspäť. Pri aktívnom sťahovaní zostáva aj modré Log.
- O projekte: „Plugin vychádza z práce s3n0 a Chocholousek.“ Pod tým prehľad zmien aktuálne nainštalovaného vydania, pribalený v IPK pre offline čítanie.

## Aktuálne rozhranie 0.1.29

Výbery, aktualizačné hlásenia, sťahovanie, spracovanie, výsledok, Log aj O projekte sa zobrazujú v ľavom paneli. Banner a pravý náhľad zostávajú viditeľné. Hlavička má upravený horizont a zarovnanie údajov. Vlastný priečinok sa vždy otvára od `/`; zahŕňa skryté adresáre a funkčné odkazy na priečinky ako `/tmp` a `/hdd`. Pri potvrdení odkazu sa uloží overená skutočná cesta. Farebné potvrdenie aktualizácie zostáva pôvodné.

## Sťahovanie a bezpečný zápis

Jedno okno uchováva postupne pribúdajúce riadky sťahovania a spracovania každej pozície. Percentá aktualizujú aktuálny riadok a dokončené spracovanie má značku ✓. História sa dá posúvať šípkami a priebeh sleduje nové riadky, pokiaľ používateľ nečíta staršiu časť.

Po úspechu a návrate sa všetkých päť volieb vráti na „Vyber si…“, kurzor na prvý riadok a náhľad na úvodné logo. Uložená konfigurácia sa tým nemaže. Pri chybe výber zostáva na opakovanie.

ZIP časti aj celý balík sa kontrolujú podľa veľkosti a SHA256. Pred zápisom sa overujú PNG a rozlíšenie, dostupnosť úložiska a miesto. Cudzie orbitálne aliasy sa filtrujú pred kontrolou duplicít; 130E sa používateľovi zobrazuje ako 13.0E. Existujúce symbolické odkazy sa nahradia bez zmeny ich cieľových súborov a pri chybe sa obnovia. Skutočné adresáre na mieste PNG zostávajú chránené. Zápis má zálohu a rollback; neúspešná obnova ponechá zálohu na opravu.

## Aktualizácia samotného pluginu

Feed zostáva na existujúcej adrese:

`https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/plugin/futuristic-rebuild/plugin/update/stable.json`

Pri každom otvorení plugin skontroluje GitHub na pozadí; novšiu verziu ponúkne na potvrdenie. Žlté tlačidlo vyvolá ručnú kontrolu. Bez siete sa normálne pokračuje. IPK sa pred inštaláciou overí. Po úspechu sa zobrazí jediné oznámenie, po 3 sekundách nasleduje reštart GUI.

Balík zachováva starý `ChocholousekPicons/version.txt` počas prechodu, aby bežiace staršie hodiny pri výmene súborov nespadli. Staré zvyšky sa archivujú pod `/var/lib/warder-piconhub/previous-runtime/`; po novom importe GUI sa odstráni iba vlastný dočasný prechodový záznam. Druhá položka pluginu sa nevytvára. Pôvodné konfiguračné kľúče v `/etc/enigma2/settings` zostávajú kvôli kompatibilite; nie sú starou inštalačnou cestou.

## Jazyky

SK, CS, EN, DE, PL, HU, RU, FR, IT, ES. Výber podľa jazyka systému; neznámy jazyk má anglický fallback. Preložené sú dialógy, tlačidlá, dátumové názvy aj poznámky k vydaniu.

## DAB / DAB+ vo verzii 0.1.29

Zdroj DAB v existujúcom výbere, 220×132, Transparent/Biele/Čierne. Schválený katalóg má 51 označení / 80 presných desaťpolových referencií. Používa nastavený priečinok; žiadne vymyslené satelitné pozície ani nové duplicitné adresáre. ASA DE zostáva vynechaná. Zdrojový manifest, jednotlivé PNG aj archívy majú SHA256, archívy odkazujú na konkrétny commit a pred zápisom sa overujú. Existujúce rádiové picony mimo pokrytia sa zachovávajú.

## Skutočné overenie

- **176 automatizovaných testov**; pred zlúčením oba workflow úspešné (40505582290, 40505582208).
- Úspešný zostavovací a publikačný workflow **40548069323** pre zdroj `93fd4546b2e3ebc617404a4c271a5278f763fadd`.
- Verejné IPK má overenú veľkosť a SHA256 a zodpovedá zverejnenému kontrolnému súčtu.
- Živý aktualizátor ponúka prechod 0.1.25 → 0.1.29; balík prešiel validáciou aktualizátora.
- Skutočné stiahnutie a zápis zo živého DAB katalógu do dočasných priečinkov: 80 piconov v každom z troch štýlov; kontrolný existujúci rádiový picon zostal zachovaný.
- Štefan po prijatí opraveného oficiálneho vzoru výslovne prikázal nasadenie. Súhlas a presné hashe sú zaznamenané v DAB katalógu.
- Fyzický test PiconHub 0.1.29 na prijímači sa zatiaľ netvrdí. Predchádzajúce výsledky konkrétnych verzií zostávajú v histórii. Používateľ potvrdil fungovanie rádiových piconov v oboch infobaroch FullHDGlass.

## Ďalšie vydania

Schválenú grafiku a správanie zachovať. Existujúce verejné IPK, tagy a checksumy neprepisovať; pre funkčnú zmenu zvýšiť verziu. Udržiavať poznámky vo všetkých jazykoch a rovnakú verziu poznámok aj runtime. Zachovať aktuálnu aktualizačnú adresu a názov balíka. Pred novým produkčným povýšením aktualizovať production.json podľa overeného feedu a zdrojového commitu; produkčný workflow overí verejné bajty a označí konkrétny plugin release.

Autorské údaje a chránené MASTER picony zostávajú zachované. Staré recovery a vývojové podklady zostávajú v histórii Gitu; aktuálny strom obsahuje iba potrebnú prácu k pluginu. PC Factory adresár a jeho vydania boli na následný pokyn vlastníka odstránené; aktuálne Releases patria pluginu do prijímača.

## Upratanie repozitára

Aktuálny plugin je dostupný aj v hlavnej vetve main. Factory aktualizačný priečinok a nesúvisiace vydania sú odstránené. Potrebné šablóny a pôvod piconov sú pod plugin/artwork/. Adresa picons/ zostáva kvôli kompatibilite galérie v nainštalovaných verziách. Funkčné zdroje pluginu, IPK, checksum a aktualizačná adresa sa uprataním nemenia.

## DAB a DVB-T v 0.1.29

Prvé dve položky výberu sú DAB a DVB-T. Samostatný overený DAB katalóg sa pri označení dostupnosti posudzuje oddelene od natívneho satelitného katalógu. Identické schválené picony sú aj v picons/19.2e/dab a picons/23.5e/dab a v celkových balíkoch príslušných pozícií (51 a 29 referencií pre každý z troch štýlov). Pôvodné obrázky zostali zachované. Warder je jeden ekosystém so spoločnými dátami a pravidlami; jednotlivé pluginy nezakladajú vlastné nezávislé databázy.


DAB a DVB-T majú ikony pred názvom; rozlíšenie je samostatná voľba. Obnovený pôvodný archív DVB-T CZ/SK obsahuje 2 674 PNG v prevedení Transparent 220×132. Biele a čierne prevedenie zatiaľ nemá overený balík. Historický archív nepredstavuje záruku úplného aktuálneho pokrytia. Opravené filtrovanie DAB pri spoločnom výbere satelitnej pozície.
