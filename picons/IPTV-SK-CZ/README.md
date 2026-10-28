# IPTV rádiá SK/CZ

Spoločná kolekcia pre PiconHub Warder Evolution a FullHDGlass Warder Evolution.

Bouquet obsahuje 321 položiek: 88 slovenských a 233 českých. Pri 286 vybraných URL skúška vrátila zvukové dáta; dostupnosť všetkých 321 nie je potvrdená. Picony pokrývajú 248 položiek, 264 súborov vrátane starších referencií v každom variante. Zvyšných 73 položiek zatiaľ nemá vhodný overený podklad. Nevymýšľame náhradné logá.

Dostupné sú rozmery 50×30, 220×132 a 400×240, vždy Transparent, Biele a Čierne. Inštalátor kontroluje SHA256 archívu aj jednotlivých PNG a nemení nesúvisiace používateľské picony. Oba projekty používajú rovnaký katalóg a rovnaký kód sťahovania.

- [Samostatný SK/CZ bouquet](bouquets/userbouquet.warder.sk-cz.radio)
- [Warder Radio Streams — celý zoznam](bouquets/userbouquet.warder.radio) — vlastné SK/CZ stanice na začiatku, zahraničné sekcie sa obnovujú týždenne.
- [Chýbajúce picony](catalog/missing-artwork.csv)
- [Overené archívy a ich kontrolné súčty](catalog/release.json)

Bouquet importujte správcom bouquetov. Pred nahradením existujúceho rovnomenného súboru vytvorte zálohu. PNG patria priamo do používateľom nastaveného priečinka picon, napríklad /media/hdd/picon/. Nepridávajú sa názvy priečinkov podľa rozlíšenia.

Zdroje streamov: pôvodný používateľský zoznam, verejný katalóg Radio Browser a overenie na stránkach staníc. FMSTREAM nebol dostupný na automatické načítanie. Logá pochádzajú z oficiálnych stránok alebo z predtým schválených podkladov Warder. Značky a autorské práva zostávajú ich vlastníkom. Snímka zoznamu: 28. októbra 2026.


Doplnenie 28. októbra 2026: preskúmané Radia.sk, Radia.cz (93 záznamov) a MyOnlineRadio.cz (dve stránky, 110 obrazových záznamov), použité aj dodané originály. Počet položiek s piconmi vzrástol z 213 na 247. [Pôvod a overenie](catalog/followup-sources.json). Nové IPK nie je potrebné; znovu stiahnite IPTV rádiá SK/CZ v PiconHube alebo skine.

## Týždenné obnovenie sveta

Workflow `Refresh Warder Radio Streams` beží v nedeľu o 04:20 UTC a dá sa spustiť aj ručne. Dočasne načíta verejný zoznam, vynechá jeho slovenské a české sekcie a pred zahraničné stanice vloží presný obsah nášho samostatného SK/CZ bouquetu. Vlastné referencie aj existujúce picony zostávajú zachované. Zdrojový súbor sa neukladá do repozitára.

Odstraňuje zdrojovú hlavičku, neprehrateľné lokálne zástupné adresy a presné duplicity. Zástupné nadpisy mení na skutočné oddeľovače. Všetky stanice zostávajú rádiovými službami. Pri neúplnom alebo výrazne zmenšenom zdroji sa starý výsledok neprepíše. Kontrola štruktúry nie je overením dostupnosti každého streamu. Existujúci satelitný automat sa nemení.

Pôvod zahraničných údajov: verejný zoznam [OpenHDF/hdfradio](https://github.com/openhdf/hdfradio), súbor `userbouquet.iptv_radio.radio`. Nejde o pôvodný výtvor Warder; Warder spravuje vlastnú SK/CZ časť, zlúčenie a referencie. Označenie zdroja je v tejto dokumentácii, používateľský bouquet má hlavičku Warder Radio Streams.

Overenie a počty posledného spracovania: [world-radio-update.json](catalog/world-radio-update.json).

Doplnený originál od vlastníka: 897. Všetkých deväť variantov používa dodaný podklad bez zmeny farieb a písma. [Overenie publikácie](catalog/owner-artwork-publication.json).
