# Zdroje pre rozšírenie rádiového katalógu

Overené 3. novembra 2026. Ide o dátové zdroje pre zostavenie zoznamu na Gite; plugin dostáva výsledný spoločný bouquet. Aktívne zdroje a zostavenie centrálnej databázy sú opísané v [GLOBAL-RADIO.md](GLOBAL-RADIO.md). Kandidátske adresáre sa nepripájajú automaticky.

| Zdroj | Krajiny a lokalita | Vhodné použitie |
|---|---|---|
| Radio Browser | ISO kód krajiny, jazyk, žánre; výsledok posledných kontrol streamu | Pripojený úplný verejný export do centrálnej databázy; kódy krajín, žánre, jazyk a stav kontroly. |
| laut.fm | Žánre, písmená a voľná lokalita/súradnice; bez country filtra v oficiálnej schéme | Pripojený celý inventár platformy do centrálnej databázy; krajina sa doplní len pri spoľahlivej streamovej zhode. Starší kompatibilný zoznam používa skupinu laut.fm. |
| Radio Garden | Neoficiálne API poskytuje mestá, textové označenia krajín a detaily staníc | Živým testom overené 3.11.2026: 12 892 miest, 229 označení krajín/území a 4 streamové presmerovania. [Výsledky a cesta ID](RADIO-GARDEN.md). Automatický import zatiaľ nie je pripojený. |
| World Radio Map | Mestá, krajiny a zoznamy FM/AM frekvencií | Overenie lokalít a staníc. Jeho zverejnené podmienky vyžadujú výslovné povolenie pre automatické dopyty; automat nie je pripojený. |
| Online Radio Box | Regióny, krajiny a žánre | Vyhľadanie a porovnanie staníc; podporovaný prístup pre náš pravidelný import zatiaľ nie je overený. |
| radio.net | Medzinárodný katalóg a regionálne stránky | Doplnkové porovnanie staníc. Zdokumentovaná Meta Data Push API posiela dáta vysielateľa do radio.net; nie je dôkazom voľného exportu adresára pre náš import. |

## Overené odkazy

- https://docs.radio-browser.info/ — Station, countrycode, countrycodes, search, hidebroken a výsledky kontrol.
- https://www.radio-browser.info/ — verejné použitie zozbieraných údajov.
- https://docs.api.laut.fm/ — živá schéma API 1.0.4 bola načítaná aj zo schema URL v diagnostike.
- https://radio.garden/settings/radio-garden — oficiálny popis služby.
- https://worldradiomap.com/ — mestá/frekvencie/počúvanie.
- https://worldradiomap.com/about/terms — podmienky automatických dopytov.
- https://onlineradiobox.com/ — regióny, krajiny, žánre.
- https://corporate.radio.net/broadcasters/ — účel Meta Data Push API.

Pri ďalšom dopĺňaní zostáva dôležitá identita streamu, zachovanie existujúcich referencií a piconov, rozlíšenie alternatívnych bitrate/kanálov, dostupnosť a správny kód krajiny. Samotná prítomnosť v adresári nedokazuje aktuálnu prehrateľnosť na každom boxe.
