# Audit zdrojov a stav overenia

## Audit priloženého archívu

Archív: `WARDER-FACTORY-ZDROJOVE-KODY-PRE-WORK(1).zip`

| Pracovný adresár v archíve | Zistenie | Použitie v zjednotenej aplikácii |
|---|---|---|
| `warder_factory_v09` | Jednosúborová Tkinter aplikácia a `.cmd` spúšťač. | Zachované správanie jednoduchého spustenia a prehľadového GUI; integrované do finálneho `engine.py`. |
| `WARDER-PICON-FACTORY-WORK` | Kód aplikácie je obsahovo zhodný s v0.9; obsahuje doplnkovú validáciu a testy. | Bez druhej distribuovanej aplikácie; užitočné bezpečnostné kontroly zlúčené do jediného projektu. |
| `WARDER-FACTORY-FINAL-WORK` | Modulárny engine, zdrojové a QA moduly, publikovacie brány a regresné testy. | Základ jedinej distribuovanej aplikácie; doplnený o živé zdrojové adaptéry, cache, registry výnimky a Windows build konfiguráciu. |

V archíve nebol `.git` adresár, lokálny Warder Master dataset ani používateľský stav aplikácie. Preto sa nedali lokálne overiť pracovné vetvy repozitárov alebo ich súbory. Známa produkčná vetva PiconHub bola kontrolovaná iba na čítanie; zaznamenaný HEAD počas auditu: `f936138f49fd37c845939d1222d9589951bcae79`. Žiadny GitHub zápis, merge, release ani produkčná zmena sa nevykonali.

## Čo aplikácia robí

- Jeden Tkinter desktopový tok automaticky synchronizuje zdroje, importuje kandidátov, deduplikuje obsah, porovnáva presné service-reference názvy s read-only Warder Master, vytvára varianty a QA reporty.
- Vhannibal zisťuje aktuálnu položku „Picon Vhannibal Motor“ na oficiálnej stránke; Motor číslo nie je zafixované.
- OpenATV 8 číta aktuálny index OE-Alliance, overuje Git blob SHA-1 a feedom publikovaný SHA-256 archívov.
- Chocholousek zostáva aktívny; jeho updater index sa kontroluje najviac raz týždenne a sťahuje iba nové archívy.
- Warder Master používa uložený zoznam ciest posledného úspešne synchronizovaného production commitu. Staršie stiahnuté súbory zostávajú nedotknuté, no už sa nevydávajú za aktuálny register.
- Zdrojové originály sa nemenia. Výstupné PNG majú 220×132 px, priehľadnú verziu a nepriehľadné čierne/biele pozadie. Bezpečná oprava zálohuje prepísané varianty; nízky kontrast, identita a nejednoznačná grafika sa posúvajú na kontrolu.
- Výnimky majú stabilné ID, pôvodné cesty, názvy zdrojov, dôvod, návrh postupu a náhľady dostupných variantov. Rozhodnutie sa neprekladá na automatické publikovanie.
- SQLite a checkpointy umožňujú pokračovanie po prerušení. Nezmenené zdroje používajú veľkosť/čas zmeny, výstupná QA cache používa veľkosť/čas zmeny variantov.

## Overené v tomto prostredí

- `python -m py_compile *.py` — úspešné.
- `python -m unittest discover -v` — **88 testov úspešných**.
- Syntetický integračný tok nad tromi zdrojovými priečinkami prebehol dvakrát. Overil deduplikáciu rovnakého PNG, ponechanie odlišných variantov v identitnej výnimke a preskočenie opakovanej QA pri nezmenených výstupoch.
- Ručne vytvorený PNG prešiel renderom; všetky tri výstupy mali 220×132 px a čierny/biely variant bol plne nepriehľadný.
- Bezpečnostné testy pokrývajú archívne limity, cestovné cesty, checksumy, zdrojové checkpointy, identitné konflikty, rozhodnutia výnimiek a draft-only publikovanie.

## Zostávajúce neoverené veci

- Tento runtime nemá Windows, Wine ani PyInstaller. Windows EXE preto nie je vytvorený, spustený ani vizuálne testovaný. ZIP obsahuje Windows build spec a skript, no nie hotový EXE.
- Priame outbound sieťové spojenia aplikácie sú v tomto prostredí blokované. Živé sťahovanie všetkých picon archívov a aktuálny stav zdrojových stránok v behu aplikácie preto neboli odskúšané.
- `py7zr` nebol v tomto prostredí nainštalovaný; syntetické testy pokrývajú parser/cooldown, nie živú extrakciu Chocholousek 7z archívu.
- Chýbali skutočné používateľské picon dáta aj kompletný Warder Master checkout. Po prvom behu na cieľovom PC sa má skontrolovať report zdrojov a registry pred použitím návrhu publikovania.

Tento balík je jeden zjednotený a testovaný zdrojový produkt pripravený na Windows build. Nie je označený za hotový Windows EXE ani za kompletný živý beh na cieľových dátach.

## 2026-10-09 OpenATV fallback batch
- Added SHA256-verified fallback to picons/picons latest GitHub release when OE-Alliance feed discovery fails.
- Strict release asset name, host, path, size and digest checks; downloads remain atomic and SHA256-verified.
- 107/107 local tests pass (`python -m unittest discover -p 'test_*.py' -q`).
- Live GitHub API/download and real Windows end-to-end import NOT tested in this runtime.

2026-10-09: Chocholousek HTML archive link parsing, origin and filename validation; 109 local unittest tests passed. Live picon.cz download not verified.
