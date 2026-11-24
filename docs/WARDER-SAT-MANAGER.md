# Warder SAT Picon Manager — jediný koordinátor

## 24. 11. 2026 — Azzurra: plánovaný Cloud Browser, nie GitHub Actions

V mimoriadnom plánovanom behu Warder SAT Picon Manager o 08:52 (Europe/Bratislava), ID behu `9a53d81f-f064-8324-95db-6d12a0f542b8`, report zaznamenal PASS pre Chrome/CDP, verejné vlákno bez prihlásenia a stiahnutie PNG 151974 cez Playwright downloadMedia. Súbor mal 21 689 B, PNG magic `89504e470d0a1a0a` a SHA-256 `f2c1d4f903b5e29c39fd86d1c0006f239f5a5a5b0dd0a2237deb329a6d6ee70e`. Celkový systémový stav behu bol failed; celý produkčný cyklus a nový checkpoint neboli potvrdené. Ide o dôkaz akvizície podľa reportu behu, nie o nezávislé opätovné stiahnutie alebo publikáciu.

GitHub-hosted runner v [prihlasovacom teste](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/actions/runs/45346332798) aj [verejnom teste](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/actions/runs/45348061001) vrátil HTTP 403. Nové rozhodnutie vlastníka: Azzurra 157954 získavať cez natívny Cloud Browser existujúceho plánovaného SAT manažéra bez prihlásenia a bez Secrets. Starší návrh sťahovania cez GitHub Actions v PR PiconHub #88 a FullHDGlass #159 nie je produkčná závislosť; nezlučovať jeho nefunkčnú akvizičnú cestu. GitHub Actions možno využívať na následné spracovanie a publikovanie bezpečne overených vstupov. Verejný RSS pre ostatné vlákna zostáva nezmenený.

Automatizácia bola opätovne aktivovaná, jednorazový termín odstránený; najbližší pravidelný beh 3.12.2026 08:00 Europe/Bratislava, každý druhý štvrtok. Porovnávať s historickým registrom 483 príloh a najnovším doloženým checkpointom; sťahovať iba nové/zmenené prílohy Azzurra, overiť formát, plný SHA-256, presné Vhannibal referencie, MASTER V9 a 9 variantov. Pri blokácii alebo neúplnom prenose neposúvať checkpoint a pokračovať ostatnými zdrojmi. Žiadne nové IPK, žiadny ďalší časovač. Úplný inkrementálny produkčný beh s novou prílohou zatiaľ neoverený.


Stav: 23. november 2026. Jediná aktívna plánovaná úloha SAT piconov je ChatGPT automatizácia **Warder SAT Picon Manager** (pôvodne „Európske stanice a picony“), každé dva týždne vo štvrtok 08:00 Europe/Bratislava. Nenahrádza rádio ani DAB workflow. SAT Work nesmie pracovať ako druhý nezávislý publikátor tej istej dávky: jeho už vytvorené checkpointy sú vstupom a výsledky podliehajú nezávislému produkčnému auditu.

## Jeden cyklus, nie množstvo pracovných dávok

1. **Východisko**: načítať aktuálny `main` PiconHub a FullHDGlass, tento dokument, `AGENTS.md`, MASTER V9 pravidlá, spoločný register `reports/sat-manager/state.json`, posledný overený checkpoint a aktuálny produkčný `manifest.json` a `SHA256SUMS`. Register najprv porovnať s archívnym dôkazom a aktualizovať ho iba pri skutočne zmenených dôkazoch alebo úspešnom publikovaní; nezapĺňať ho duplicitnými kontrolnými pokusmi.
2. **Objavovanie**: Vhannibal (vrátane pôvodného pomocného skriptu `plugin/tools/audit_vhannibal_nov2026.py`), KingOfSat, LyngSat, aktuálne operátorské a oficiálne zdroje. Pokrytie odvodiť z aktuálneho produkčného manifestu; nesústrediť sa iba na vybrané pozície.
3. **Inkrementálna evidencia**: identita = (orbitálna pozícia, provider, úplná Enigma2 referencia). Vstupný dôkaz = identita stanice, oficiálny zdroj/jeho zmena, presný hash grafiky a SDT/PMT/servisný dôkaz. Ak je výsledok už PUBLISHED/PASS alebo BLOCKED a žiadny relevantný dôkaz sa nezmenil, **SKIP**. Nemení sa stav = žiadne opätovné sťahovanie všetkých ZIPov, renderovanie, testovanie ani nový commit. Rovnaká stanica sa na viacerých pozíciách neprerenderuje bez potreby.
4. **Spracovanie**: iba zmeny s presnou identitou. Zachovať schválenú originálnu grafiku; pri nových bezpečne overených prípadoch doplniť 50×30, 220×132, 400×240 a transparentné, BLACK, WHITE pozadie — spolu 9 variantov. Dodržať `plugin/artwork/QUALITY.md`, `WHOLE_COLOURED_LOGO_V2`, presné OWNER schválenia a CANAL+ SK/CZ. Nejednoznačná grafika, typ služby, namespace či nesúlad podpisov => REVIEW, nie publikovanie.
5. **Jediné produkčné vydanie dát**: zmeniť iba dotknuté obsahovo adresované ZIPy a ich `.partNN` časti. S novým manifestom a `SHA256SUMS` vykonať jednu relevantnú integračnú kontrolu; skutočne stiahnuť a overiť dotknuté ZIPy, ich CRC, rozmery, SHA, 9 variantov a neporušené chránené balíky. Potom iba so schváleným rozsahom zlúčiť, publikovať a **znovu nezávisle načítať** produkčné objekty z `main`. Nevydávať IPK, nemení sa runtime ani feed verzií skinu.
6. **Jedna správa**: jediný slovenský súhrn zmenených SAT pozícií, nových/opravených referencií, PNG, skutočne aktualizovaných produkčných ZIPov, commit SHA a otvorených REVIEW. Ak je všetko nezmenené, oznámiť „0 zmien, 0 ZIPov, 0 commitov“ a skončiť.

## Ďalšie reálne prehľadávané zdroje SAT piconov — od 23. 11. 2026

Jediná plánovaná automatizácia **Warder SAT Picon Manager** má teraz konkrétny zdrojový register `reports/sat-manager/sources.json`, sedem overených vetiev v `reports/sat-manager/source-watch-state.json` a jeden ľahký inkrementálny skener `plugin/tools/sat_source_watch.py`. **Nepribúda žiadna druhá plánovaná úloha.** Ôsmy zdroj SatDigitalne.cz je popísaný nižšie; nejde o GitHub vetvu.

1. **OpenATV / OE-Alliance aktuálny picon feed**: `oe-alliance/picons-feed`, vetva `gh-pages`, iba textový index `Packages`; obsahuje IPK picon balíky (index k 23. 11. obsahuje vydanie 17. 11. 2026). Skontroluj LEN nové názvy/verzie/metadáta. **Žiadne stiahnutie ani spustenie IPK**. Táto distribúcia často pochádza z Picons Project — počítaj ju raz ako jeden pôvod, nie ako ďalšie nové logá.
2. **Picons Project**: `picons/picons`, `master`, udržiavané originálne predlohy a SRP; zdroj prednostne pre vizuálne porovnanie. GPL-3.0 nie je povolenie bez kontroly meniť naše schválené diela.
3. **Picons Project Enigma2 zoznamy**: `picons/channellists`, `master`, doplnkové DVB referencie; nie druhá nezávislá zbierka grafík.
4. **Jungla Team – Movistar+**: `jungla-team/Picon-enigma2-Movistar`, `main`, skutočné Enigma2 picony, hlavne španielske programy.
5. **MarhyCZ**: `MarhyCZ/picons`, `master`, CZ/SK identity a grafiky pre porovnanie, bez automatického importu webových štvorcových dlaždíc.
6. **Dobes TV Picons**: `mdobes/tvpicons`, `main`, CZ/SK SVG/tile zdroje; tieto **nie sú priamo Enigma2 servisné picony**. Obidva CZ/SK zdroje sa zlučujú do jednej logickej skupiny.
7. **Pelajustrana Movistar+**: `pelajustrana/Enigma2-Picons-Mplus-Spain`, `master`, sekundárny španielsky zdroj s menšou aktualitou; nepodvojovať Jungla Team.

Historické `openatv-picons/*` repozitáre s poslednými aktualizáciami z roku 2015 **nepoužívať ako dnešný OpenATV zdroj**. Používame oficiálny aktuálny feed `https://github.com/oe-alliance/picons-feed/tree/gh-pages`. Služba `dreamboxone/online-picons` je najmä sťahovací plugin, nie nezávisle potvrdená originálna kolekcia, preto sa duplicitne nepreberá.

### Inkrementálny automatický postup

Z koreňa PiconHub pri plánovanom/ručnom SAT cykle:

```sh
python3 plugin/tools/sat_source_watch.py --validate-only
python3 plugin/tools/sat_source_watch.py --output /tmp/warder-sat-source-watch.json
```

Skener načíta verejné GitHub HEAD SHA a **len pri zmene** porovná cesty od posledného checkpointu. Neťahá obrazové balíky, IPK ani archívy a **nikdy sám nepublikuje**. V jednom výslednom reporte spája všetky nové referencie, zmeny SVG/PNG a OpenATV `Packages` ako **kandidátov na dôkaz**. `picons/picons` a OE feed deduplikuj podľa pôvodu. Automatické výsledky cudzieho SRP nikdy neprepisujú manuálne schválené grafiky alebo service reference.

Ak GitHub compare vráti neúplný rozsah, chybu či odklon vetvy, zdroj zostáva `NO_ADVANCE`; žiadne donekonečna opakované sťahovanie. Odozva `UNCHANGED_SKIP` znamená nulovú prácu. Pri úspešnom odbornom vyhodnotení/archivovaní zdrojových rozdielov možno explicitne potvrdiť checkpoint cez `--advance`, nikdy automaticky na neoverených kandidátoch. Aktualizovať checkpoint len pri skutočnej zmene vstupného zdroja, nie pri nulovej zmene. Nenarušovať pravidlo trvalo vyradených 75 a zachovať samostatnú ochranu 6 + 7 blokácií.

## Ôsmy SAT zdroj: SatDigitalne.cz / 005jon — 23. november 2026

Vlastník pridal na preverenie `https://feed.satdigitalne.cz/picon/`. Priama kontrola verejného feedu 23. 11. 2026 potvrdila rozličné `srp.*.tar.xz` piconové sady so servisnými referenciami a typickými rozmermi 220×132 / 400×240. Aktuálna stránka obsahuje **CanalPlus (23.10.2026)**, **Multi 13/16/19/23/28E (25.10.2026)**, **AntikSAT a FreeSAT (05.09.2026)**, **DigiSK/TellyCz, Hotbird 13E, Astra 19.2E, Eutelsat 16E, Ciefp Motor 75E–34W (01.07.2026)** a **Turksat 42E (30.08.2026)**. Výpis obsahuje aj archivované CZ/SK a DVB-T SNP sady, OSCam šablóny a plugin PiconCZSK — tie **nie sú vstupom do SAT piconovej automatizácie**.

- Pridaný **ôsmym zdrojom toho istého manažéra**, bez nového časového spúšťača: `reports/sat-manager/sources.json` a `source-watch-state.json`, id `satdigitalne-sat-picons`.
- `plugin/tools/satdigitalne_source_watch.py` číta iba verejné HTML a výhradne hlavičky **HEAD** maximálne 32 transparentných referenčných SAT archívov, bez sťahovania binárnych `.tar.xz`, `.ipk`, `.deb`, `.7z`. Rozpozná stabilné mená archívov, sleduje etag / last-modified / dĺžku; fail-closed pri chýbajúcom dôkaze zmien, nedostupnom serveri alebo neúplnej stránke.
- V prvom behu zostáva `index_sha256: null` a stav `INITIAL_BASELINE_REVIEW_REQUIRED`: **nesmie sa vymyslieť ani označiť za už prekontrolovaný obsah**. Ak server poskytne potrebné hlavičky, nový obsah sa najprv porovná s našimi produkčnými piconmi; až po odbornom vyhodnotení sa výslovne posunie zdrojový checkpoint. Nesťahovať celé balíky len kvôli tomu, že sa objaví nový dátum stránky.
- Autor grafík je označený ako **005jon**; z feed stránky sa nepotvrdila licencia povoľujúca automatické preberanie. Potrebné je overiť licenciu/povolenie a presnú Enigma2 identitu každej služby. **Žiadny bezpodmienečný import cudzieho artworku a najmä žiadne prepísanie schválených CANAL+ SK/CZ alebo MASTER**.
- Aktualizácia SAT piconov zostáva samostatný neskorší, úplne auditovaný krok. Ak sa nič doložiteľné nezmenilo, nula nových PNG a nula nových ZIPov.

## Deviaty a desiaty nezávislý zdroj — GioppyGio a LinuxSat-Support (23. 11. 2026)

**GioppyGio:** `https://gioppygio.it/ful-trs-1.html` je aktuálna zbierka Enigma2 SNP (podľa **názvu programu**, NIE servisnej DVB referencie). Ponúka balíky Ful-Trs pre 220×132 a 417×250 na satelitných pozíciách a motor 34°W–70°E, plus Egami, Silver a ďalšie dekoratívne štýly. Nový adaptér `plugin/tools/gioppygio_source_watch.py` **číta iba jednu verejnú HTML stránku a HEAD hlavičky najviac 32 ZIPov**: iba Ful-Trs 220×132 ako jeden kanonický monitorovací variant. Všetky ostatné farebné štýly/rozmery nepovažuje za nezávislé zdroje loga a nesťahuje ich. `index_sha256: null` = prvá nezávislá kontrola serverového obsahu neprebehla. Žiadny ZIP sa automaticky nepreberá a meno stanice sa nesmie hádať na Enigma2 službu.

**LinuxSat Support — Enigma2 Picons:** verejná sekcia `https://www.linuxsat-support.com/board/19-enigma2-picons/` má odkázaný RSS kanál `https://www.linuxsat-support.com/thread-list-rss-feed/19/`. Zdroje Nephilim, stefanbenno6, ZET 71, Chocholoušek a diskusie GioppyGio môžu upozorniť na nové logá, ale fórum nie je autoritatívnym dôkazom DVB identity. `plugin/tools/linuxsat_source_watch.py` číta **iba verejný RSS XML zoznam tém** (max 512 KiB), ich URL/ID/názov/dátum, obmedzuje prístup na doménu LinuxSat a ignoruje ostatné DTT/IPTV vlákna. Výnimkou je Azzurrovo vlákno 157954. Témy GioppyGio sa označujú ako **duplicitný pôvod `gioppygio-sat-snp`** — žiadne druhé spracovanie tých istých piconov. Stiahnutie príloh, prehliadanie prihlasovaných vlákien alebo automatické vytvorenie účtu je zakázané. Fórum výslovne upozorňuje, že množstvo sťahovaní a tém je pre hosťa skrytých; RSS je preto iba signál nových diskusií, nie dôkaz existencie správnych PNG. Verejný RSS odkaz bol potvrdený; telo RSS nebolo ešte nezávisle načítané ako XML, preto `index_sha256: null` a prípadný neúspech znamená `SOURCE_ERROR_NO_ADVANCE`, nie falošné PASS.

**Jedna automatizácia, nie množstvo úloh:** obe nové zdrojové definície sú v `reports/sat-manager/sources.json` (celkom 10 vrátane 7 GitHub, SatDigitalne, GioppyGio a LinuxSat). Prísny inkrementálny skener `plugin/tools/sat_source_watch.py` spracúva všetkých desať počas **toho istého** dvojtýždňového SAT cyklu, so zdrojovým checkpointom `reports/sat-manager/source-watch-state.json`. Žiadny nový cron, ďalšia automatizácia, import grafiky či nový produkčný ZIP sa nevytvára. V prvom behu sa zdrojové metadáta výslovne overia, až potom po odbornej kontrole možno uložiť checkpoint. Chýbajúce dáta servera = bez nového checkpointu. Zachovať 75 trvalo archivovaných, 6 pomenovaných TV blokácií, 7 Anuvu a schválené MASTER/CANAL+ SK/CZ.

## Trvalé vyradenie technických a neidentifikovaných položiek z piconovej práce (23. 11. 2026)

Vlastník rozhodol, že technické, testovacie a neidentifikované služby sa nesmú donekonečna prechádzať kvôli grafickým TV piconom. Z pôvodných **81** nezodpovedaných referencií je **75** presunutých do `reports/sat-manager/state.json/archived_nonprogram_references`. Sú **trvalo mimo automatickej SAT piconovej fronty**: žiadne vyhľadávanie nových grafík na tie isté nezmenené referencie, žiadne testovacie ZIPy, žiadne opakovanie predchádzajúcich analýz, žiadny automatický reopen ani na základe náhodného zdrojového refreshu. Opätovná aktivácia iba po **novom výslovnom rozhodnutí vlastníka**, s úplnou overenou identitou TV stanice.

Pozor: vyradenie z *workflowu piconov* **nie je technické potvrdenie, že všetkých 75 je dátových či rádiových**. Napríklad 16 testovacích SID na 23,5°E má A/V a niektoré číselné služby môžu vysielať. Keďže stále nemajú dôveryhodnú, presne pripnutú identitu trvalého TV programu, mimo bežného brandového zadania sú to archívne prípady, nie dôvod vyrábať falošné picony. Auditné záznamy sú úplne zachované a žiadna existujúca grafika, príjem ani produkčný balík sa tým nemení.

**V aktívnej fronte zostáva 6 konkrétne pomenovaných kandidátov:** RADIO CLASSICA TV, Oracle TV, EL JUMHURIA TV, AL-KAFEL TV, StarzPlay-Movies a 1TV IRAQ. Samostatných **7 Anuvu** má naďalej chýbajúcu úplnú Enigma2 identitu; ich stav sa nemení. Všetkých šesť aktívnych aj Anuvu je `BLOCKED`, kým nepribudne presný dôkaz. Historický súčet 81 = 75 archívnych + 6 aktívnych; nikdy neprezentovať 75 ako chýbajúce logá.

**Štyri pôvodné Spare referencie na 7°W** už existujú v produkčných piconoch zo schválenej novembrovej dávky, no ich názvy a účel zostávajú v starom audite nepreukázané. Archivácia **neautorizuje zmazanie ani prepísanie existujúcich piconov**. Takéto sporné identity sa nevyhlasujú za vyriešené iba kvôli prítomnosti súboru.

Pri ďalšom cykle najprv načítaj obe množiny `blocked_references` (6) a `archived_nonprogram_references` (75), ako aj `separate_anuvu_blockers` (7). **Archive filter má prednosť pred všetkým automatickým vyhľadávaním, renderovaním aj prípravou balíka.** Nové značky neoznačuj automaticky starým testovým SID; založ nový dôkazný prípad. Ak sa nemení žiaden iný kandidát, ukonči beh bez zmien a bez ďalších testov.

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

Dávka 22: 54 dokončených TV referencií, 467 integrovaných PNG. Pôvodných 81 blokovaných prípadov bolo 23. 11. roztriedených na 75 trvalo archívnych (mimo automatického spracovania) a 6 aktívnych pomenovaných TV kandidátov; ďalších 7 Anuvu je vedených samostatne. TV5MONDE Europe HD na 19,2°E a 0,8°W je už obsiahnuté v produkčnom manifeste cez integrovaný PR #110; **nepublikovať znova**. Zdrojový archív: `FullHDGlass-Warder-Evolution` commit `270e9b0b57ade7ab6e685af7c0877782d0631f15`, audit `reports/vhannibal-followup-20261106/scope-batch-20261116-22/independent-audit.json`. Pred každým behom sa toto historické číslo porovná s novším `main` a aktuálnym zdrojovým registrom; nie je napevno nastaveným limitom.

Vlastník 23.11.2026 schválil zlúčenie pravidelných SAT činností do jedného manažéra a odstránenie nepotrebných samostatných spúšťačov. Žiadna zmena na SAT piconoch alebo zmazanie produkčných balíkov z toho automaticky nevyplýva.

## DTT ITALIA a talianske feedy (23. novembra 2026)

Spoločný dvojtýždňový skener od tejto zmeny zaradí aj vlákno Azzurra s ID 157954, keď ho verejný LinuxSat RSS oznámi ako nové alebo zmenené. Ostatné pozemné a IPTV vlákna naďalej filtruje. RSS neposkytuje kompletný archív príloh. Pri aktualizácii treba prírastok porovnať s posledným evidovaným príspevkom a identitu overiť v aktuálnom lamedb a bouquetoch Vhannibal Motor DTT Italia. Posledný kontrolovaný príspevok v tejto dávke je z 17. novembra 2026. Žiadny ďalší časovač sa nezavádza.

V pôvodných desiatich stranách bolo 183 príspevkov. Kontrolná dávka podľa nastavení z 22. novembra pokrýva 285 pozemných referencií, 439 na 9°E a 260 na 5°W. Katalóg obsahuje 507 balíkov, z toho deväť pre samostatný výber DTT ITALIA. Lokálny katalóg v IPK obsahuje rovnaký manifest ako FullHDGlass. Obe krajinské voľby DTT majú samostatný identifikátor. Pri čistení adresára sa cudzia pozemná stanica nesmie odstrániť iba podľa spoločného menného priestoru EEEE.

Prebehlo 54 skúšobných inštalácií cez PiconHub v režimoch doplnenia a synchronizácie TV bouquetu. Fyzický prijímač sa pri tejto kontrole nepoužil. Zo 48 zdrojových grafík vzniklo 45 rôznych sád. Pri Rai 5 a RTV San Marino sa tri bajtovo totožné deväťvariantové sady ukladajú len raz. Dňa 23. novembra vlastník po prezretí schválil všetkých 45 výsledných sád vrátane 80 kombinácií označených kontrolou MASTER V9. [Schválené odtlačky 405 PNG](https://github.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/blob/main/reports/dtt-italia-20261123/owner-approval.json). [Náhľady a výsledky overenia všetkých 181 stiahnutých dielov](https://github.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/blob/main/reports/dtt-italia-20261123/README.md). Matica referencií, zdroje, presné hashe a porovnávacie náhľady sú v sprievodnej zmene FullHDGlass v priečinku `reports/dtt-italia-20261123/`.

## 23. 11. 2026 — DTT ITALIA a talianske feedy 9°E a 5°W sú overené a publikované

[FullHDGlass 1.0.89](https://github.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/releases/tag/v1.0.89) a [PiconHub 0.1.45](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/releases/tag/v0.1.45) sú dostupné cez produkčné aktualizátory. Pre každú aplikáciu boli skontrolované verejný IPK, jeho kontrolný súčet, verzia v metadátach opkg a obsah inštalovaného výberu. FullHDGlass má zhodný produkčný a testovací kanál. PiconHub má zhodné aktualizačné údaje na `main` a na kompatibilnej vetve `plugin/futuristic-rebuild`.

| Vydanie | Veľkosť IPK | SHA-256 verejného IPK | Oficiálne zostavenie |
| --- | ---: | --- | --- |
| [FullHDGlass 1.0.89](https://github.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/releases/download/v1.0.89/enigma2-plugin-skins-fullhdglass_1.0.89_all.ipk) | 18 395 176 B | `50dd57e5e525688d7327c7915f6dfe1a9a5609f773ce017e87546b138cf53425` | [priebeh vydania](https://github.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/actions/runs/45271414450) |
| [PiconHub 0.1.45](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/releases/download/v0.1.45/enigma2-plugin-extensions-piconhub_0.1.45_all.ipk) | 3 038 080 B | `83758c52c4d5d6675183865239b0e38e9cc0e83340c378f5b2ed7e467adc9d45` | [priebeh vydania](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/actions/runs/45271765476) |

Opätovné stiahnutie z produkcie overilo 181 dielov a 27 archívov. V 891 väzbách servisná referencia / variant sa všetkých 405 schválených PNG zhodovalo s odtlačkami uloženými pri schválení. Katalóg v PiconHube má rovnaký SHA-256 ako živý katalóg FullHDGlass, `40db67977de066be65fa8f37f5a73041aa1b337b7a5c9cdf40233edaf537094a`.

