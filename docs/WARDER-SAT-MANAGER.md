# Warder SAT Picon Manager — jediný koordinátor

Stav: 23. november 2026. Jediná aktívna plánovaná úloha SAT piconov je ChatGPT automatizácia **Warder SAT Picon Manager** (pôvodne „Európske stanice a picony“), každé dva týždne vo štvrtok 08:00 Europe/Bratislava. Nenahrádza rádio ani DAB workflow. SAT Work nesmie pracovať ako druhý nezávislý publikátor tej istej dávky: jeho už vytvorené checkpointy sú vstupom a výsledky podliehajú nezávislému produkčnému auditu.

## Jeden cyklus, nie množstvo pracovných dávok

1. **Východisko**: načítať aktuálny `main` PiconHub a FullHDGlass, tento dokument, `AGENTS.md`, MASTER V9 pravidlá, spoločný register `reports/sat-manager/state.json`, posledný overený checkpoint a aktuálny produkčný `manifest.json` a `SHA256SUMS`. Register najprv porovnať s archívnym dôkazom a aktualizovať ho iba pri skutočne zmenených dôkazoch alebo úspešnom publikovaní; nezapĺňať ho duplicitnými kontrolnými pokusmi.
2. **Objavovanie**: Vhannibal (vrátane pôvodného pomocného skriptu `plugin/tools/audit_vhannibal_nov2026.py`), KingOfSat, LyngSat, aktuálne operátorské a oficiálne zdroje. Pokrytie odvodiť z aktuálneho produkčného manifestu; nesústrediť sa iba na vybrané pozície.
3. **Inkrementálna evidencia**: identita = (orbitálna pozícia, provider, úplná Enigma2 referencia). Vstupný dôkaz = identita stanice, oficiálny zdroj/jeho zmena, presný hash grafiky a SDT/PMT/servisný dôkaz. Ak je výsledok už PUBLISHED/PASS alebo BLOCKED a žiadny relevantný dôkaz sa nezmenil, **SKIP**. Nemení sa stav = žiadne opätovné sťahovanie všetkých ZIPov, renderovanie, testovanie ani nový commit. Rovnaká stanica sa na viacerých pozíciách neprerenderuje bez potreby.
4. **Spracovanie**: iba zmeny s presnou identitou. Zachovať schválenú originálnu grafiku; pri nových bezpečne overených prípadoch doplniť 50×30, 220×132, 400×240 a transparentné, BLACK, WHITE pozadie — spolu 9 variantov. Dodržať `plugin/artwork/QUALITY.md`, `WHOLE_COLOURED_LOGO_V2`, presné OWNER schválenia a CANAL+ SK/CZ. Nejednoznačná grafika, typ služby, namespace či nesúlad podpisov => REVIEW, nie publikovanie.
5. **Jediné produkčné vydanie dát**: zmeniť iba dotknuté obsahovo adresované ZIPy a ich `.partNN` časti. S novým manifestom a `SHA256SUMS` vykonať jednu relevantnú integračnú kontrolu; skutočne stiahnuť a overiť dotknuté ZIPy, ich CRC, rozmery, SHA, 9 variantov a neporušené chránené balíky. Potom iba so schváleným rozsahom zlúčiť, publikovať a **znovu nezávisle načítať** produkčné objekty z `main`. Nevydávať IPK, nemení sa runtime ani feed verzií skinu.
6. **Jedna správa**: jediný slovenský súhrn zmenených SAT pozícií, nových/opravených referencií, PNG, skutočne aktualizovaných produkčných ZIPov, commit SHA a otvorených REVIEW. Ak je všetko nezmenené, oznámiť „0 zmien, 0 ZIPov, 0 commitov“ a skončiť.

## Stop-podmienky a ochrana proti nekonečnému testovaniu

- Nepúšťať znova úspešne uzavreté ani blokované referencie bez **nového konkrétneho dôkazu**; nepridávať ďalšie testovacie cykly iba preto, že test trvá dlho.
- Skutočne zmenené ZIPy majú jednu úplnú kontrolu pred publikovaním a jednu read-back kontrolu po publikovaní. CI je povinné, ale **žiadne opakované zostavovanie identických archívov**.
- Nula zmien => nula ZIPov, nula commitov; review kandidáti nesmú blokovať nezávislé bezpečné zmeny.
- Pri zlyhaní CI, neistom artworku, konflikte vetiev, nedostatku oprávnení alebo nemožnosti preniesť binárny súbor stav explicitne BLOCKED/UNPUBLISHED; neoznačovať ho za ostrý.
- Pravidelné kontroly nezmazávajú produkčnú históriu, staršie obsahovo adresované súbory potrebné na rollback, zálohy ani schválené grafiky.
- Samostatný GitHub workflow `audit-vhannibal-nov2026.yml` je odstránený ako duplicitný **spúšťač**. Jeho skript je zachovaný ako interný zdrojový adaptér. Historické reporty sa zachovávajú ako dôkaz, nie ako aktívne úlohy.

## Aktuálne potvrdený produkčný základ — 19. november 2026

Neskoršia publikácia z 19. 11. 2026 **nie je nový prírastok k číslu 54 TV / 467 PNG** z pôvodného Vhannibal checkpointu; tieto skupiny referencií sa bez presného identitného porovnania nesmú sčítavať.

- PiconHub zdrojový commit: `5ba72330557e31973439407fbc17671e3d52c589`.
- FullHDGlass produkčné zverejnenie: `ec65c7bb1c58b6af1a95114c9dbdc4c74401f81e`; technické vyčistenie nepoužitých fragmentov: `7e72d6e2b6d70eeb095b770d34430b3f53af9a2b`.
- Audit: `FullHDGlass/reports/satellite-picon-audit-20261119.json`, stav `PRODUCTION_REPAIR_VERIFIED`: 20 overených referencií (13 nových, 7 opravených), 60 zdrojových PNG, 180 cieľových variantov, 18 aktualizovaných ostrých ZIPov na selektoroch 530E a 70W. Staré/nezmenené balíky sa nezostavujú ani znovu nepublikujú.
- K 23. 11. 2026 bola každá z 18 deklarovaných produkčných položiek osobitne porovnaná s aktuálnym `main` manifestom, všetkých 18 názvov a SHA-256 ZIPov sa zhoduje. Aktuálny manifest Git blob `7a7c6b4b96d9b8dc2da60a29c85ae1bd2069b715`, SHA-256 `d90c5f63779eebb70ab5d25302584988cf525b8f787f1b3095fe2d389c6004d2`, 498 balíkov, 2 131 parts a 18 CANAL+ balíkov.
- Jednotlivé presné pozícia/provider/Enigma2 referencie a 18 ZIP digestov sú v jedinom `reports/sat-manager/state.json` v `last_verified_production_publication`. Pre totožné nezmenené vstupné dôkazy je **SKIP**. Zápis tohto checkpointu je iba zosúladenie evidencie, nie nový SAT audit ani produkčné vydanie.
- Ponechať `last_official_run: null`, kým nový centrálny manažér neskončí vlastný úplný overený cyklus. Historický údaj o produkčnej dávke nie je dôkaz o úspechu nového automatického cyklu.

### Krátkodobé Sky premenovania

Sky Mockingjay HD na 28,2°E je **dočasné premenovanie** existujúceho Sky Cinema kanála 303 (SID 6033, TSID 2030, NID 2, 12284,90 V), nie dôkaz novej stálej TV služby. [Sky: novembrový rozpis](https://helpforum.sky.com/t5/What-s-On/Changes-to-the-TV-Guide-November-2026/m-p/5413663) uvádza 19. 11. premenovanie Sky xXx HD na Mockingjay HD a na 23. 11. ďalšie plánované premenovanie na Chipmunks HD; [KingOfSat 28,2°E](https://en.kingofsat.net/news.php?pos=28.2E) eviduje rovnaký SID. `state.json/temporary_services_review` preto drží prípad ako `REVIEW_ONLY`; nevytvárať nový trvalý picon, negenerovať deväť dočasných variantov ani znovu neprebaliť ZIP bez nového dôkazu trvalého rebrandingu. Toto pravidlo platí všeobecne aj pre podobné Sky Cinema pop-up kanály.

## Posledný prevzatý historický checkpoint

Dávka 22: 54 dokončených TV referencií, 467 integrovaných PNG, 81 blokovaných prípadov bez nového externého dôkazu + 7 samostatných Anuvu prípadov. TV5MONDE Europe HD na 19,2°E a 0,8°W je už obsiahnuté v produkčnom manifeste cez integrovaný PR #110; **nepublikovať znova**. Zdrojový archív: `FullHDGlass-Warder-Evolution` commit `270e9b0b57ade7ab6e685af7c0877782d0631f15`, audit `reports/vhannibal-followup-20261106/scope-batch-20261116-22/independent-audit.json`. Pred každým behom sa toto historické číslo porovná s novším `main` a aktuálnym zdrojovým registrom; nie je napevno nastaveným limitom.

Vlastník 23.11.2026 schválil zlúčenie pravidelných SAT činností do jedného manažéra a odstránenie nepotrebných samostatných spúšťačov. Žiadna zmena na SAT piconoch alebo zmazanie produkčných balíkov z toho automaticky nevyplýva.
