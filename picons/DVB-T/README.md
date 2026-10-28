# DVB-T / DVB-T2 Slovensko a Česko — audit 28. 10. 2026

Spoločný zoznam a picony pre PiconHub aj FullHDGlass. Runtime ponuka zostáva `DVB-T-SK-CZ`, 220 × 132, Transparent / Biele / Čierne. Inštalácia smeruje do používateľom zvoleného priečinka piconov; nevzniká nový priečinok podľa rozlíšenia.

## Čo bolo skontrolované

- 198 kombinácií SID / TSID / ONID z verejných meraní SatelitnáTV.sk: 127 slovenských a 71 českých.
- 11 existujúcich slovenských rozhlasových referencií; nejde o nové fyzické meranie prijímačom.
- 18 ďalších položiek potvrdených prevádzkovateľom bez spoľahlivo priradenej terestriálnej referencie.
- Pôvodný balík: 2 674 názvov PNG, 203 odlišných obrázkov. Ani jeden z týchto počtov nie je počet súčasných staníc.

Výsledný zoznam má 227 riadkov. Jedna stanica sa môže objaviť vo viacerých multiplexoch, regiónoch alebo verziách. `catalog/station-list.csv` je čitateľný prehľad; JSON zachováva pôvodný SDT názov, zdroj, dátum merania, identifikátory a stav priradenia.

## Doplnenie balíkov

54 nových názvov PNG, oprava alebo aktualizácia 148 existujúcich transparentných PNG a zodpovedajúcich bielych/čiernych variantov. Odstránených je 197 zastaraných alebo chybných názvov PNG. Výsledok: **2 531 PNG v každom z troch balíkov**. Ostatné ponechané PNG zostávajú nezmenené. Medzi doplneniami sú JOJ Šport 2, Kanal 1, RiK, Nickelodeon, Prima LOVE SK, Markíza Krimi, VIXEN, Music Box Classic, ČRo Pohoda, Český Impuls, Rádio Čas a Čas Rock, nové pozície JOJ Family a CS Mystery. Opravené sú aj zámeny Sport 1 a Regina Stred/Východ, staré WAU a testovacie obrázky pri konkrétnych pomenovaných staniciach.

Použité sú existujúce schválené Warder picony alebo logá priamo od vysielateľa či prevádzkovateľa siete. Žiadne logo nie je vymyslené. Pôvodný transparentný obrázok sa pri existujúcich schválených trojiciach neprekresľuje. Pri nových zdrojových logách sa zachováva pomer strán aj farby; biele a čierne pozadie používa nemennú šablónu Warder.

## Vyčistenie starého balíka

Odstránené sú referencie potvrdene ukončených ČT3, Rádio Pyramída, Paramount Network CZ, TUTY TV, NASA TV UHD, Sport 5, O2 TV Free, Naživo a Barrandov News/Family, staré Sporty TV a generické testovacie obrázky bez identity. Ak je ich referencia už použitá overenou aktuálnou stanicou, zostáva zachovaná s novým správnym logom. Zmeny brandov, napríklad WAU → JOJ KRIMI, a staré rozhlasové logá sa aktualizujú na všetkých existujúcich aliasoch. Dôvody a zdroje pre každý odstránený súbor sú v `catalog/removals.json`; prehľad programov v `catalog/obsolete-stations.json`. Neoverené regionálne položky sa nevydávajú za zrušené.

## Čo nie je potvrdené

77 riadkov má otvorený stav: chýbajúce schválené logo, rozporná regionálna identita alebo neoverená aktuálna referencia. Toto číslo nie je 77 chýbajúcich staníc: viaceré riadky sú opakovania v regiónoch. Obzvlášť všeobecný `Regio T2` nemožno priradiť jedinému logu pre celé Česko. `Service 1–5` a `Test-1/2` zostávajú technickými názvami bez vymyslenej identity. Prima Sport je potvrdený prevádzkovateľom MUX 24, ale bez potvrdeného terestriálneho SID sa nevytvára odhadnuté priradenie. Staré merania RTVS na MUX 1 a Paramount Network sú označené oddelene od aktuálnej ponuky prevádzkovateľa. Regionálne merania nie sú zárukou aktuálneho vysielania.

## Hlavné zdroje

- [Plustelka: aktuálne štyri celoplošné multiplexy](https://plustelka.sk/technicke-informacie)
- [České Radiokomunikace: MUX 21–23 a regionálne siete](https://www.digistranky.cz/naladte-si/programova-nabidka)
- [Digital Broadcasting: MUX 24, regionálne programy a rádiá](https://www.multiplex24.cz/images/document/20260103-l7RIZWTQ.pdf)
- [Prima Sport v MUX 24 od 17. augusta 2026](https://www.multiplex24.cz/detail-aktuality/novy-televizni-program-prima-sport-od-17-srpna-2026)
- [Slovenské rozhlasové vysielanie DVB-T2](https://www.radia.sk/frekvencie)
- [SatelitnáTV.sk: vlastné merania vysielačov](https://www.satelitnatv.sk/vysielace/dvb-t/)

TV referencia s typom `1` a namespace `EEEE0000` je kompatibilný názov pre zdokumentované fallback vyhľadávanie OpenATV/FullHDGlass. Nie je tvrdením o skutočnom SDT type konkrétneho HD/HEVC programu. Rádiá dostávajú typ `2` a kompatibilný typ `1`; existujúce presné referencie a frekvenčné aliasy zostávajú zachované. SID/TSID/ONID sa zo zdrojov čítajú v desiatkovej sústave a do názvu PNG sa zapisujú šestnástkovo.

Manifest sa aktivuje až po overení SHA-256 všetkých troch archívov a všetkých verejných častí. Táto aktualizácia dát nemení verzie aplikácií, IPK ani aktualizačné kanály pluginov.
