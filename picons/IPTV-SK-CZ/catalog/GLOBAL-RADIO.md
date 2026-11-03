# Centrálna databáza rádií

Dátová cesta je rovnaká pre každú aktualizáciu: **úplné podporované zdroje → hlavná databáza → zlúčenie streamových identít a krajín → overený katalóg pre box**.

## Súbory v `catalog/global/`

- `world-radio-master.json.gz`: jeden hlavný súbor s pozorovaniami jednotlivých zdrojov, ich identitou a časom posledného úspešného stiahnutia. Duplicity medzi zdrojmi zostávajú auditovateľné.
- `world-radio.json.gz`: zlúčená databáza so stabilnými referenciami, streamovými aliasmi, pôvodom, krajinou, žánrami, jazykmi, bitrate, kodekom a dostupnými odkazmi na logá. Slúži aj budúcim tematickým výberom.
- `world-radio.receiver.json.gz`: čistý komprimovaný zoznam pre Radio Warder Evolution od verzie 0.1.0-test33; obsahuje iba údaje potrebné na zobrazenie a prehrávanie.
- `userbouquet.warder.world.radio`: plný textový bouquet s jednou sekciou pre každú krajinu.
- `countries.json`: počty staníc podľa krajín.
- `build.json`: počty vstupov, spracovania, stav zdrojov, veľkosti a SHA-256 publikovaných súborov.

Starší `bouquets/userbouquet.warder.radio` zostáva samostatným kompatibilným zoznamom. Staré verzie ho môžu naďalej načítať v pôvodných limitoch. Plný katalóg potrebuje podporu komprimovaného prenosu a väčšieho počtu položiek; preto sa nepodsúva starým verziám pod pôvodnou adresou.

## Zdroje a krajiny

Aktívne adaptéry načítajú kompletný verejný export Radio Browser, celý inventár laut.fm a existujúci katalóg Warder. Import laut.fm sa neobmedzuje na prvých 1 000 výsledkov: stránkovanie sa porovnáva s úplným zoznamom názvov a chýbajúce záznamy sa doplnia mennými dávkami. Ostatné kandidátske adresáre z [prehľadu zdrojov](RADIO-SOURCES.md) sa nepovažujú za pripojené, kým nemajú overený podporovaný import.

Poradie je Slovensko, Čechy a ostatné krajiny/územia abecedne; vnútri krajiny sú stanice abecedne. Neznáma alebo rozporná krajina patrí do **Nezaradené**. Krajina sa neodhaduje z názvu, jazyka, voľne uvedeného mesta ani polohy servera. Používa sa kód krajiny z adresára spojený s konkrétnym streamom; vlastné SK/CZ záznamy si zachovávajú svoje zaradenie.

Zlučovanie najprv spojí presné streamové aliasy a potom identity staníc. Rozdiely veľkosti písmen, diakritiky, medzier a explicitných značiek kodeku/kvality sa porovnajú spolu s krajinou a spoločným webom alebo konkrétnym streamovým cieľom. Unicode zostáva zachované aj pre nelatinské názvy. Samotná zhoda názvu nestačí: nejasné homonymá sa odložia na preverenie. Rozdielne tematické názvy, čísla kanálov, jazyky a významové query parametre sa nezlievajú. Náhodné zdvojené písmeno možno opraviť iba pri spoločnom webe/serveri; všeobecná približná zhoda názvov sa nepoužíva.

Každá potvrdená stanica má jeden hlavný záznam a jej transportné varianty zostávajú v metadátach. Uprednostní sa existujúca kurátorovaná identita, názov a referencia. Overený alternatívny stream môže nahradiť potvrdene nefunkčnú adresu bez zmeny identity. Obľúbené uložené v boxe sa nemažú.

Záznamy bez spoľahlivej krajiny, bez webového podkladu, s rozporným priradením krajiny, nejasnými rovnakými názvami alebo potvrdeným chybným streamom sú v `world-radio.review.json.gz`, nie v hlavnom zozname krajín. Vstupné pozorovania sa zachovávajú v master databáze. Nové tematické priradenia Rayo nahlásené prijímačom ako nesprávny program čakajú na potvrdené mapovanie vysielateľa; dostupnosť AAC adresy sama osebe identitu stanice nepotvrdzuje.

Na výslovnú požiadavku vlastníka je úplne poslednou položkou **HDF Radio zoznam**. Ide o samostatný pôvodný zdrojový pohľad so zachovanými názvami, adresami a poradím. Nevykonáva sa nad ním čistenie nášho katalógu a nejde o potvrdenie dostupnosti všetkých jeho staníc. Pôvodný snapshot je v `catalog/source-radio.radio`. Technické lokálne zástupné hlavičky nie sú prehrávateľné stanice. Kópie v tomto pohľade majú samostatný stabilný priestor referencií, aby nepoškodili validáciu a obľúbené hlavného katalógu.

## Priebežné aktualizácie a kontrola

Spoločný týždenný workflow zostaví oba zoznamy v nedeľu o 04:20 UTC a dá sa spustiť aj ručne. Najprv prebehnú testy, potom načítanie a validácia zdrojov a nakoniec jeden Git commit s celým výsledkom. Zmena katalógu nevyžaduje ďalšie IPK pri každej aktualizácii údajov.

Výpadok jedného exportu ponechá jeho posledný úspešný snapshot v hlavnom súbore; ostatné zdroje sa môžu obnoviť. Prvé zostavenie bez dostupných vstupov sa nepovažuje za úspešné. Nečakané zmenšenie vstupu či výsledku pred zámerným čistením, poškodené údaje, prekročenie limitov a neplatné identity zastavia publikovanie. Každý odložený záznam má dôvod a počty sa účtovne kontrolujú.

Pred publikovaním beží obmedzená sieťová kontrola adries: najviac dve súbežné požiadavky na hostiteľa, vzorka najviac 1 KiB audia, päť presmerovaní a časové limity. HTML s HTTP 200 sa nepovažuje za audio. Dve zhodné tvrdé chyby (napr. 404/410 alebo ne-audio odpoveď) a presmerovanie na inú známu stanicu vedú na preverenie; timeout sám osebe neoznačí rádio za zaniknuté. Výsledok bez potvrdeného audia alebo neúplný audit zastaví publikovanie, pretože môže ísť o zlyhanie kontrolného prostredia. Výsledky sú v `stream-audit.json.gz`.

Dostupnosť v adresári aj krátka audio vzorka majú svoje limity: nie sú potvrdením celého programu alebo prehratia každého kodeku na prijímači. Údaje bez krajiny zostávajú na následné doplnenie. Picony sa pripravujú až po schválení vyčisteného katalógu. Žánrové synonymá a tematické výbery sú ďalšia vrstva nad tou istou databázou.
