# Centrálna databáza rádií

**Potvrdené redakčné opravy majú prednosť pred dostupnosťou audia aj ochranou pred výpadkom.** Rádio Pyramída ukončilo vysielanie 28. februára 2025; potvrdzuje to [programový koncept STVR, strana 25](https://www.stvr.org/download.pl?ID=31453&hash=dwSLRbHysLAXglOCE0FdLRE5JM9bnPYQ). Staré názvy a zdroje Pyramída/Klasika sú v hlavnom katalógu blokované aj pri HTTP 200 a zostávajú auditovateľné v pracovných záznamoch. Nejde o vyradenie na základe timeoutu. Pôvodný samostatný zdrojový pohľad sa nemení.

Rádio Patria a starý názov SRo5 Rádio Pátria /RSI sú jeden program na dvoch známych zdrojoch vysielateľa: `icecast.stv.livebox.sk/patria_128.mp3` a `live.slovakradio.sk:8000/Patria_128.mp3`. Obe audio odpovede sa identifikujú ako Rádio Patria a odkazujú na `patria.stvr.sk`; [vysielateľ uvádza aktuálny zdroj](https://www.stvr.org/programove-sluzby/radio-patria). Zachová sa pôvodný záznam, referencia a URL s logom; starý názov, referencia a adresa sú aliasy. Samostatné RSI, regionálne programy, iné porty a významové query parametre sa nezlievajú. Pôvodných 88 slovenských položiek sa touto konkrétnou opravou nemení; odstránili sa dve nadbytočné importované položky.

**Pôvodné Slovensko je vlastníkom potvrdený základ, nie nový import.** Všetkých 88 pôvodných položiek sa zachová s presným názvom, streamom a referenciou aj počas výpadku alebo neúspešnej vzdialenej sondy. Overené nové stanice možno dopĺňať. Kontrola z inej siete nesmie pôvodnú adresu prepísať ani stanicu vyradiť; neistý výsledok je iba stav kontroly. Nové neoverené a sporné importované záznamy naďalej čakajú v pracovnej databáze. Toto pravidlo nahrádza skoršie plošné vyradenie všetkých nepotvrdených streamov.

Známe fungujúce a kurátorované stanice v ostatných krajinách zostávajú pri prechodnom výpadku v ponuke. Neúspešné sondy musia byť zaznamenané v troch odlišných dátumoch s odstupom najmenej 48 hodín, kým sa stanica odloží pre dlhodobú nedostupnosť. Opakovanie tej istej cache ani dva pokusy počas jednej aktualizácie sa nepočítajú ako viac dní. Prístupové obmedzenie, odložená sonda a neoverený playlist nie sú dôkazom zániku. Úspešná odpoveď históriu výpadku vynuluje; identita a história sa zachovávajú aj v pracovných záznamoch na opätovné zaradenie. Presmerovanie na iný známy program naďalej vyžaduje kontrolu identity.

Jazykové či staršie názvy sa porovnávajú aj podľa konkrétneho zdroja vysielania: rovnaký HTTP/HTTPS cieľ, názov programu v profile streamu, uzly toho istého poskytovateľa a zodpovedajúci web vrátane jeho jazykových sekcií. Rozdielne programy, čísla, porty, významové query parametre a samostatné jazykové kanály sa nezlievajú. Napríklad Classic Praha/Classic Prague a zahraničné ČRo Rádio Praha/Radio Prague International majú spoločnú identitu. Regionálne Rádio Praha používa iný program a zostáva samostatné. Rozlíšenie zahraničného a regionálneho programu potvrdzujú stránky vysielateľa: [zahraničný program](https://cesky.radio.cz/moznosti-poslechu-8699878), [regionálna stanica](https://praha.rozhlas.cz/o-stanici-7447118). Pôvodné názvy a referencie zlučovaných položiek sú uložené v aliasoch; slovenský pôvodný základ sa pritom nemení.

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

Každá potvrdená stanica má jeden hlavný záznam a jej transportné varianty zostávajú v metadátach. Uprednostní sa existujúca kurátorovaná identita, názov a referencia. Overený alternatívny stream môže nahradiť potvrdene nefunkčnú adresu bez zmeny identity. Obľúbené uložené v boxe sa nemažú. Publikovaná referencia zostáva priradená k hlavnému streamovému zdroju, aj keď má program ďalšie profily alebo sa použije overená alternatíva; poradie prechodu vstupov ju nepresúva na náhodný variant.

Záznamy bez spoľahlivej krajiny, bez webového podkladu, s rozporným priradením krajiny, nejasnými rovnakými názvami alebo potvrdeným chybným streamom sú v `world-radio.review.json.gz`, nie v hlavnom zozname krajín. Vstupné pozorovania sa zachovávajú v master databáze. Nové tematické priradenia Rayo nahlásené prijímačom ako nesprávny program čakajú na potvrdené mapovanie vysielateľa; dostupnosť AAC adresy sama osebe identitu stanice nepotvrdzuje.

Na výslovnú požiadavku vlastníka je úplne poslednou položkou **HDF Radio zoznam**. Ide o samostatný pôvodný zdrojový pohľad so zachovanými názvami, adresami a poradím. Nevykonáva sa nad ním čistenie nášho katalógu a nejde o potvrdenie dostupnosti všetkých jeho staníc. Pôvodný snapshot je v `catalog/source-radio.radio`. Technické lokálne zástupné hlavičky nie sú prehrávateľné stanice. Kópie v tomto pohľade majú samostatný stabilný priestor referencií, aby nepoškodili validáciu a obľúbené hlavného katalógu.

## Priebežné aktualizácie a kontrola

Spoločný týždenný workflow zostaví oba zoznamy v nedeľu o 04:20 UTC a dá sa spustiť aj ručne. Najprv prebehnú testy, potom načítanie a validácia zdrojov a nakoniec jeden Git commit s celým výsledkom. Zmena katalógu nevyžaduje ďalšie IPK pri každej aktualizácii údajov.

Výpadok jedného exportu ponechá jeho posledný úspešný snapshot v hlavnom súbore; ostatné zdroje sa môžu obnoviť. Prvé zostavenie bez dostupných vstupov sa nepovažuje za úspešné. Nečakané zmenšenie vstupu či výsledku pred zámerným čistením, poškodené údaje, prekročenie limitov a neplatné identity zastavia publikovanie. Každý odložený záznam má dôvod a počty sa účtovne kontrolujú.

Pred publikovaním beží obmedzená sieťová kontrola adries: najviac dve súbežné požiadavky na vstupného hostiteľa, vzorka najviac 1 KiB audia, päť presmerovaní a časové limity. HTML s HTTP 200 sa nepovažuje za audio. Dve zhodné tvrdé chyby (napr. 404/410 alebo ne-audio odpoveď) a presmerovanie na inú známu stanicu vedú na preverenie. Nové stanice sa do hlavného zoznamu krajín zaraďujú až s potvrdenou audio vzorkou. Pôvodné slovenské a známe fungujúce stanice sa riadia pravidlami zachovania uvedenými vyššie. Nový neoverený import s timeoutom, obmedzeným prístupom alebo playlistom bez audio vzorky zostáva v pracovnej databáze; nie je označený ako zaniknuté rádio. Po štyroch nepotvrdených spojeniach bez jedinej HTTP odpovede sa ďalšie adresy toho hostiteľa označia ako neoverené bez ďalšej záťaže servera, nie ako nefunkčné. Výsledok bez potvrdeného audia alebo neúplný audit zastaví publikovanie, pretože môže ísť o zlyhanie kontrolného prostredia. Výsledky sú v `stream-audit.json.gz`.

Dostupnosť v adresári aj krátka audio vzorka majú svoje limity: nie sú potvrdením celého programu alebo prehratia každého kodeku na prijímači. Údaje bez krajiny zostávajú na následné doplnenie. Picony sa pripravujú až po schválení vyčisteného katalógu. Žánrové synonymá a tematické výbery sú ďalšia vrstva nad tou istou databázou.

Sieťová fáza má dva obmedzené päťminútové priechody. Druhý opätovne nepýta čerstvo potvrdené odpovede a uprednostní adresy, na ktoré sa v prvom priechode nedostalo. Pomalé hlavičky aj telo odpovede stráži absolútny socketový limit. Záznam s `requested: false` neznamená vykonanú audio kontrolu: je výslovne odložený a sám osebe nedokazuje funkčnosť nového importu ani nefunkčnosť známej stanice. Také adresy majú prioritu pri ďalšom cykle. Pracovný audit sa archivuje aj pri zlyhaní workflow, aby sa predišlo strate výsledkov.

Jednorazová oprava označená predmetom commitu `Apply reviewed Slovak catalogue corrections:` použije publikovaný master a audit bez nového importu či celosvetového sieťového skenu. Publikovanie musí overiť presné vyradenie dvoch skontrolovaných referencií Pátria/Pyramída a nezmenený obsah každej ostatnej položky prijímača vrátane pôvodného zdrojového pohľadu. Iný výsledok publikovanie zastaví. Bežné push, ručné a týždenné aktualizácie naďalej vykonávajú úplné stiahnutie a sieťový audit.
