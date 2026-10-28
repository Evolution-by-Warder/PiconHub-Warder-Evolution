# PiconHub Warder Evolution — ostrá prevádzka

Produkčná verzia **0.1.30**, nasadená 28. októbra 2026 na pokyn vlastníka projektu.

## Vydanie

- Zdroj: `2338498bb1bde99d921cf2ccf1f237730bea5c27`.
- Balík: `enigma2-plugin-extensions-piconhub-warder-evolution_0.1.30_all.ipk`.
- Veľkosť: 2 879 782 bajtov.
- SHA256: `08959228cf12b5c5cadd2e31d3ba2367dc5eca5948ab573ce9e1fc8335fa9d91`.
- Inštalácia: `/usr/lib/enigma2/python/Plugins/Extensions/WarderPiconHub/`.
- [Vydanie](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/releases/tag/v0.1.30), [strojový záznam](production.json).

## Jedno rozhranie

Výber, sťahovanie, spracovanie, výsledok, Log, aktualizácie a O projekte sa zobrazujú v ľavom paneli. Pravý náhľad a hlavička zostávajú viditeľné. Pri otvorení sú voľby neutrálne; po úspechu a návrate sa obnoví úvodný výber. Pri chybe zostáva výber pripravený na opakovanie.

Rozlíšenia: 50×30, 220×132, 400×240. Pozadia: Transparent, Biele, Čierne. Červené Zatvoriť, zelené Stiahnuť, žlté Aktualizácia pluginu, modré O projekte. Výbery majú farebné popisy bez prefixov názvu farby. Dlhý text sa zalamuje a posúva šípkami; priebeh zostáva v jednom spoločnom okne.

## Zdroje

Prvé položky sú IPTV rádiá SK/CZ, DAB / DAB+ a DVB-T CZ/SK; potom družice a poskytovatelia. Rozlíšenie je samostatná voľba.

IPTV má picony pre **213 položiek**, **229 presných referencií** v každom z deviatich variantov. Samostatný obnovený bouquet má **321 položiek** (88 SK, 233 CZ); skúška pri 286 vybraných URL vrátila zvukové dáta. **108 položiek zatiaľ nemá vhodný overený picon.** Iné krajiny v celom pôvodnom bouquete zostávajú zachované. [Bouquety, pokrytie a zdroje](../picons/IPTV-SK-CZ/README.md).

DAB používa samostatný zdieľaný katalóg pri 220×132, s rovnakými schválenými obrázkami aj v príslušných celkových satelitných balíkoch. Aktuálne pokrytie a hashe určuje [živý DAB katalóg](../picons/DAB/catalog/release.json). ASA DE patrí do DAB a celkovej 23.5E, nie do Canal+ balíkov. DVB-T CZ/SK používa obnovenú historickú sadu 2 674 referencií pri 220×132 vo všetkých troch pozadiach; úplné súčasné pokrytie vysielania sa netvrdí.

## Bezpečný zápis

Kontrolujú sa veľkosť a SHA256 archívu, presná referencia, SHA256 a rozmery PNG. Nesúvisiace používateľské picony sa zachovajú. Pred zápisom sa overí priestor a pripraví záloha; chyba má rollback. Pri spoločnom výbere DAB a IPTV sa používa 220×132. IPTV podľa TV a rádia vyberá presné referencie z rádiových bouquetov; TV-only režim rádiový zdroj odmietne.

## Aktualizácie a jazyky

Pri každom otvorení prebehne kontrola novšej verzie na pozadí. Inštaláciu používateľ potvrdí; žlté tlačidlo spustí ručnú kontrolu. Po overenej úspešnej inštalácii sa zobrazí jediné oznámenie a po troch sekundách sa reštartuje GUI. Bez internetu plugin pokračuje. Aktualizačná adresa zostáva `plugin/futuristic-rebuild/plugin/update/stable.json`. Verejné verzie IPK a ich kontrolné súčty sa neprepisujú.

Podporované jazyky podľa systému: SK, CS, EN, DE, PL, HU, RU, FR, IT, ES; anglický fallback. Preložené sú dialógy, dátumové názvy aj poznámky k vydaniu.

## Overenie

191 testov a zostavovacie/publikačné CI **40686906248** prešli. Produkčné povýšenie **40687527676** overilo identitu a verejné bajty IPK. Všetkých deväť verejných IPTV archívov prešlo skutočnou inštaláciou cez aktuálny engine do dočasných priečinkov: po 229 PNG, s uchovaním kontrolného nesúvisiaceho súboru. Fyzický test 0.1.30 na prijímači sa zatiaľ netvrdí.

## Spoločný Warder ekosystém

PiconHub a FullHDGlass používajú rovnaký katalóg a presné zdieľané moduly. Farby a schválené typy log sa zachovávajú, nové značky sa nevymýšľajú. MASTER podklady zostávajú zmrazené. Obrázkové balíky sa sťahujú samostatne; nezväčšujú IPK. Pôvodné autorské údaje s3n0 a Chocholousek aj autorov obrázkov zostávajú zachované. Historické vývojové a recovery podklady sú v Gite.
