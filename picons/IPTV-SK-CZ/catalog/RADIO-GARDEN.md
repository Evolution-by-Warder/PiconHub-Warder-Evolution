# Radio Garden — overenie neoficiálneho API

Overené 3. novembra 2026 proti živému verejnému HTTPS rozhraniu. [Diagnostický beh](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/actions/runs/41699557028) prešiel; [overovací kód](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/blob/654767c84a47362d1cc0f77e2bd18aeebf374ce3/picons/IPTV-SK-CZ/tools/check_radio_garden.py) je na oddelenej vetve a nemení produkčný katalóg.

## Komunitná špecifikácia

- Projekt: https://github.com/jonasrmichel/radio-garden-openapi
- Skontrolovaná revízia: `b8fd90106e75a08d23709a369e9bd9e67f7cfe2d`.
- OpenAPI verzia 0.1.0 sama uvádza, že je neoficiálna. Repo hlási posledný push v decembri 2021; jeho novší údaj updated_at preto nie je dôkazom čerstvosti špecifikácie.
- Historický článok https://til.simonwillison.net/jq/radio-garden-jq je z februára 2021. Jeho údaj 1,4 MB nie je aktuálne meranie.

## Výsledky živého testu

- HTTP adresa indexu vrátila 301 na HTTPS.
- `https://radio.garden/api/ara/content/places`: 1902995 bajtov, 12892 miest, 229 jedinečných textových označení krajín/území; API verzia 1.
- Index obsahuje ID a názov mesta, označenie krajiny, súradnice a počet priradených staníc. Nie je to plochý zoznam všetkých staníc ani streamov.
- Bratislava: ID `NvkKyFxE`, endpoint jej kanálov vrátil 30 odkazov na stanice.
- Berlín: ID `6lcXHtKK`, endpoint jeho kanálov vrátil 206 odkazov na stanice.
- Na dvoch staniciach z každého mesta boli overené detaily vrátane krajiny aj HEAD presmerovanie 302 na streamovaciu adresu. Šlo o Best FM, Dobré Rádio, 80s80s - Bowie a 80s80s - Darkwave.
- Presmerovanie Best FM smerovalo na AAC adresu. Prípona `channel.mp3` na smerovači teda nedokazuje formát výsledného streamu.
- Audio dáta ani všetky stanice sveta sa v teste nesťahovali. Nejde o skúšku prehrávania na boxe.

## Správna cesta identifikátorov

1. `/api/ara/content/places` poskytne ID mesta.
2. `/api/ara/content/page/{placeId}/channels` poskytne odkazy na stanice; ID stanice je na konci jej odkazu `/listen/nazov/{channelId}`.
3. `/api/ara/content/channel/{channelId}` poskytne názov, mesto, krajinu a ďalšie podrobnosti.
4. `/api/ara/content/listen/{channelId}/channel.mp3` v overených prípadoch vráti 302 s adresou streamu.

ID prideľuje služba; negenerujeme ich. ID mesta a stanice sa nedajú zamieňať. Označenia krajín sú texty služby, nie overené ISO countrycode polia.

## Použitie v našom projekte

Technická cesta je týmto potvrdená ako kandidát pre ďalší doplnkový import. Automatický import z Radio Garden zatiaľ nie je pripojený. Pri jeho implementácii bude potrebné postupné dávkovanie a cache mestských/stanicových údajov, zachovanie existujúcich referencií a SK/CZ dát, zlučovanie skutočných streamových adries a limit výsledného katalógu. Tieto požiadavky neznamenajú, že sa má pri každom štarte boxu sťahovať celý svet.

Úplný ohraničený výsledok je v [strojovom reporte](radio-garden-check-20261103.json). HTTPS endpointy boli overené bez prihlásenia alebo API kľúča; neoficiálne rozhranie nemá týmto testom garantovanú budúcu dostupnosť.
