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

Zlučovanie používa presnú streamovú adresu, overený presmerovaný alias z adresára a identitu stanice platformy. Samotná zhoda názvu nestačí. Rozdielne mounty, bitrate a parametre URL sa automaticky nezlievajú. Zachovávajú sa existujúce referencie; pri potvrdených duplicitách zostane jedna kanonická referencia. Obľúbené uložené v boxe sa tým nemažú. Všetky vlastné SK/CZ referencie, názvy a streamy zostávajú zachované.

## Priebežné aktualizácie a kontrola

Spoločný týždenný workflow zostaví oba zoznamy v nedeľu o 04:20 UTC a dá sa spustiť aj ručne. Najprv prebehnú testy, potom načítanie a validácia zdrojov a nakoniec jeden Git commit s celým výsledkom. Zmena katalógu nevyžaduje ďalšie IPK pri každej aktualizácii údajov.

Výpadok jedného exportu ponechá jeho posledný úspešný snapshot v hlavnom súbore; ostatné zdroje sa môžu obnoviť. Prvé zostavenie bez dostupných vstupov sa nepovažuje za úspešné. Nečakané zmenšenie vstupu či výsledku, poškodené údaje, prekročenie limitov a neplatné identity zastavia publikovanie. Nové položky označené zdrojom ako nefunkčné sa do ostrého zoznamu nezaradia. Jediná neúspešná kontrola už publikovanú stanicu automaticky nezmaže.

Dostupnosť je údaj poskytovateľa, nie potvrdenie prehratia všetkých streamov na každom prijímači. Workflow neprehráva tisíce streamov ani neposiela staniciam hromadné zvukové požiadavky. Údaje bez krajiny zostávajú na následné doplnenie. Žánrové synonymá a zložitejšie tematické výbery sú ďalšia vrstva nad tou istou databázou.
