# WARDER PICON FACTORY — záväzná adresárová štruktúra

Jediný inštalačný koreň: `D:\WARDER-PICON-FACTORY\`. Žiadny ďalší koreň `D:\WARDER-PICONS\` sa nesmie vytvárať.

| Cesta pod koreňom | Účel |
|---|---|
| `00-STATE/` | Stav behov a checkpointy |
| `01-SOURCES/` | Zdrojové archívy a `LOCAL-INBOX/` |
| `02-ORIGINALS/` | Nemenné originálne PNG |
| `03-REGISTRY/` | Referenčné identity a mapovania Warder Master |
| `04-WORK/` | Pracovné súbory a dočasné renderované PNG |
| `05-QA/` | QA výnimky a rozhodnutia |
| `06-OUTPUT/` | Finálne varianty PNG |
| `07-PUBLISH-STAGING/` | Návrhy publikovania, bez automatického zverejnenia |
| `08-REPORTS/` | JSON reporty a diagnostika |
| `09-LOGS/` | Diagnostické logy |
| `10-TOOLS/` | Servisné nástroje |
| `11-APP/WARDER-PICON-FACTORY/` | Engine, GUI, aktualizátor a spúšťač |
| `11-APP/.factory-data/` | Trvalá databáza, zdrojové checkpointy a rozhodnutia |
| `11-APP/.runtime/` | Lokálne Python závislosti |
| `12-ARCHIVE/` | Archivované historické dáta |

## Pravidlá
- Picon originály, databáza, checkpointy, schválené výsledky a QA rozhodnutia sa pri upratovaní nemažú.
- Pracovné dočasné súbory sa mažú iba po potvrdení, že nie sú potrebné; neznáme súbory sa nemažú.
- Export čakajúcich piconov: jediný súbor `D:\WARDER-PICONS-PENDING.zip` (nie v `08-REPORTS`).
- Aktualizácia musí zachovať používateľské dáta a pracovať iba v jednom inštalačnom koreni.
- Diagnostické reporty sa nesmú odosielať na produkčnú vetvu ani obsahovať tokeny.
- Dokument opisuje cieľový kontrakt. Samotná existencia dokumentu nedokazuje jeho vynútenie v kóde.
