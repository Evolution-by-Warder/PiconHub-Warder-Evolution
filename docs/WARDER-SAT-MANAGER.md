# Warder SAT Picon Manager — jediný koordinátor

Stav: 23. november 2026. Jediná aktívna plánovaná úloha SAT piconov je ChatGPT automatizácia **Warder SAT Picon Manager** (pôvodne „Európske stanice a picony“), každé dva týždne vo štvrtok 08:00 Europe/Bratislava. Nenahrádza rádio ani DAB workflow. SAT Work nesmie pracovať ako druhý nezávislý publikátor tej istej dávky: jeho už vytvorené checkpointy sú vstupom a výsledky podliehajú nezávislému produkčnému auditu.

## Jeden cyklus, nie množstvo pracovných dávok

1. **Východisko**: načítať aktuálny `main` PiconHub a FullHDGlass, tento dokument, `AGENTS.md`, MASTER V9 pravidlá, posledný overený checkpoint a aktuálny produkčný `manifest.json` a `SHA256SUMS`. Pri novej dávke uložiť jednu spoločnú evidenciu.
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

## Posledný prevzatý historický checkpoint

Dávka 22: 54 dokončených TV referencií, 467 integrovaných PNG, 81 blokovaných prípadov bez nového externého dôkazu + 7 samostatných Anuvu prípadov. TV5MONDE Europe HD na 19,2°E a 0,8°W je už obsiahnuté v produkčnom manifeste cez integrovaný PR #110; **nepublikovať znova**. Zdrojový archív: `FullHDGlass-Warder-Evolution` commit `270e9b0b57ade7ab6e685af7c0877782d0631f15`, audit `reports/vhannibal-followup-20261106/scope-batch-20261116-22/independent-audit.json`. Pred každým behom sa toto historické číslo porovná s novším `main` a aktuálnym zdrojovým registrom; nie je napevno nastaveným limitom.

Vlastník 23.11.2026 schválil zlúčenie pravidelných SAT činností do jedného manažéra a odstránenie nepotrebných samostatných spúšťačov. Žiadna zmena na SAT piconoch alebo zmazanie produkčných balíkov z toho automaticky nevyplýva.
