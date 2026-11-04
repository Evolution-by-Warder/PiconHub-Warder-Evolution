# IPTV rádiá SK/CZ

Spoločná kolekcia pre PiconHub Warder Evolution a FullHDGlass.

Bouquet obsahuje 320 položiek: 88 slovenských a 232 českých. Pri 286 vybraných URL skúška vrátila zvukové dáta; dostupnosť všetkých 321 nie je potvrdená. Picony pokrývajú 318 položiek pôvodného bouquetu, 356 súborov vrátane starších referencií v každom variante. Zvyšné 2 položky zatiaľ nemá vhodný overený podklad. Nevymýšľame náhradné logá.

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

Doplnenie 30. októbra 2026: majiteľ schválil všetky štyri ukážky — 26 grafických predlôh pre 30 chýbajúcich položiek. Všetkých deväť archívov obsahuje rovnaké referencie. Staršie picony zostali byte za bytom zachované. [Schválenie](catalog/radio-logos-approval-20261030.json), [overenie publikácie](catalog/radio-logos-publication-20261030.json). Obnovte IPTV rádiá SK/CZ v PiconHube alebo FullHDGlass; nový IPK netreba.


## Doplnkové zdroje pre online zoznam

Od 3. novembra 2026 sa pri obnove používa aj verejné API laut.fm: aktualizuje známe stanice a preverí najviac 1 000 kandidátov na doplnenie. Nové stanice bez overenej krajiny patria do skupiny laut.fm. SK/CZ časť a existujúce referencie zostávajú zachované; pri výpadku API sa ponechajú predchádzajúce doplnkové údaje. [Spracovanie a limity](catalog/LAUT-FM.md). Nové IPK netreba.

Ďalšie možnosti rozšírenia, vrátane Radio Browser a ďalších adresárov, sú oddelene zhrnuté v [prehľade zdrojov](catalog/RADIO-SOURCES.md); ich uvedenie nie je oznámením hotového importéra.

Doplnenie 4. novembra 2026: 6 overených grafických predlôh a 15 prepojení existujúcich piconov na aktuálne označenia staníc. Všetkých 294 predchádzajúcich PNG v každom variante zostalo bez zmeny. Použité sú pôvodné schválené Warder šablóny. Aktuálny katalóg má picony pre 88 z 89 slovenských a 210 z 250 českých položiek; zvyšné logá alebo identity ešte vyžadujú overenie. Počty pôvodného 321-položkového bouquetu sa od aktuálneho katalógu líšia. [Ukážka 1](sources/warder-radio-20261104/Warder-radio-picony-1.png), [ukážka 2](sources/warder-radio-20261104/Warder-radio-picony-2.png), [pokrytie a nevyriešené položky](sources/warder-radio-20261104/coverage.json), [overenie publikácie](catalog/warder-radio-picons-20261104.json). Nové IPK pre tieto dáta netreba; obnovte IPTV rádiá SK/CZ v PiconHube.

Druhé doplnenie 4. novembra 2026: ďalších 17 overených grafických predlôh. Všetkých 316 predchádzajúcich PNG v každom variante zostalo nezmenených. Picony používajú pôvodné Warder šablóny; tmavé originálne nápisy majú podľa potreby svetlú podložku, aby sa nemenili farby značky. Aktuálny katalóg má picony pre 88 z 89 slovenských a 227 z 250 českých položiek. [Podklady a ukážky](sources/warder-radio-20261104-r2/plan.json), [pokrytie a nevyriešené položky](sources/warder-radio-20261104-r2/coverage.json), [overenie publikácie](catalog/warder-radio-picons-20261104-r2.json). Dáta sa obnovia cez IPTV rádiá SK/CZ v PiconHube, nové IPK netreba.

Tretie doplnenie 4. novembra 2026: ďalších 13 referencií, osem overených grafických predlôh a päť prepojení na overenú identitu programu. Všetkých 333 predchádzajúcich PNG v každom variante zostalo nezmenených. Pôvodné Warder pozadia a rámy sú overené kontrolným súčtom. Aktuálny katalóg má picony pre 88 z 89 slovenských a 240 z 250 českých položiek. [Podklady](sources/warder-radio-20261104-r3/plan.json), [pokrytie a zostávajúce medzery](sources/warder-radio-20261104-r3/coverage.json), [overenie publikácie](catalog/warder-radio-picons-20261104-r3.json). Obnovenie dát cez IPTV rádiá SK/CZ v PiconHube, nové IPK netreba.

Štvrté doplnenie 4. novembra 2026: ďalších deväť referencií, osem dohľadaných grafických podkladov a jedno zdokumentované priradenie spoločnej značky Viva pre stream označený poskytovateľom ako Viva Music (Rvhudba). Ide o odvodené priradenie rodinnej značky, nie o samostatné logo Viva Music. StreamCP používa oficiálny znak poskytovateľa výlučne pri jeho demo položke. Všetkých 346 predchádzajúcich PNG v každom variante zostalo nezmenených. Originálne Warder pozadia a rámy overené kontrolnými súčtami; deväť balíkov obsahuje po 355 PNG. Aktuálne pokrytie: Slovensko 89/89, Česko 248/250. Zostávajú Radio Cesky Jukebox (iba generická profilová ikona R) a Star The Mix (neoverená identita). [Podklady](sources/warder-radio-20261104-r4/plan.json), [pokrytie](sources/warder-radio-20261104-r4/coverage.json), [overenie publikácie](catalog/warder-radio-picons-20261104-r4.json). Obnovte IPTV rádiá SK/CZ v PiconHube a znovu otvorte Warder Radio; nové IPK netreba.

Doplnenie podľa pokynu majiteľa 4. novembra 2026: schválené originálne R pre Radio Cesky Jukebox vo všetkých deviatich Warder variantoch. Star The Mix je odstránené z hlavnej databázy, kurátorovaného bouquetu aj pôvodného zdrojového zoznamu a import ho nesmie vrátiť. Ostatné stanice a ich referencie zostali nezmenené. Picony aktuálne pokrývajú všetkých 89 slovenských a 249 českých položiek krajinského katalógu. Každý picon balík obsahuje 356 PNG; všetkých 355 starších PNG zostalo nezmenených. Dve chýbajúce staré referencie FRM a Student v samostatnom historickom bouquete nepatria medzi medzery aktuálneho krajinského zoznamu. [Schválenie a podklady](sources/warder-radio-20261104-r5/plan.json), [pokrytie](sources/warder-radio-20261104-r5/coverage.json), [úprava databázy](catalog/owner-radio-update-20261104.json). Obnovte rádiový katalóg aj IPTV rádiá SK/CZ v PiconHube; nové IPK netreba.
