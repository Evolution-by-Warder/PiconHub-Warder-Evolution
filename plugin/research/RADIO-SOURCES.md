# Rádiové picony — prieskum 27. 10. 2026

## Výsledok a rozsah

Overené zdroje sú použiteľným základom pre rozšírenie PiconHubu. Produkčný plugin 0.1.25 sa týmto prieskumom nemení; nový rádio adaptér zatiaľ nie je zapojený. Samostatná oprava infobaru FullHDGlass 1.0.28 je vydaná a prešla CI, čaká na potvrdenie na prijímači.

RDS je sprievodný údaj rádia, nie samostatný formát piconu. Rovnaké logo stanice môže slúžiť pre satelit, internet a DAB, ale identifikátory služby sa líšia. DAB SlideShow/obal prehrávanej skladby nie je trvalé logo stanice a nesmie sa automaticky uložiť ako picon.

## 1. picons/picons — prioritný dávkový zdroj

- Projekt: https://github.com/picons/picons
- Vydania: https://github.com/picons/picons/releases
- Overené vydanie: `2026-10-25--00-12-17`.
- Overený zdrojový commit indexov: `7756215d8b34b319f12d0332a315f28e4caef9ef`.
- Indexy obsahujú 23 178 riadkov SRP a 32 783 riadkov UTF8SNP. Sú to počty všetkých mapovaní, NIE počty rádiových staníc.
- Overené logá a mapovania: BAYERN 3, Schwarzwaldradio, Rádio Slovensko. Ich SVG predlohy existujú v `build-source/logos/`.
- SRP balík 220×132 bol skutočne stiahnutý a jeho SHA256 zodpovedá GitHub release digestu. Obsahuje 6 999 bežných súborov a 16 178 hardlinkov; vzorka PNG má 220×132. Referencie uvedených troch staníc sú prítomné.
- Úplné názvové balíky UTF8SNP sú vhodný kandidát pre internetové rádio a DAB; presné pokrytie konkrétneho prijímača ešte nie je overené.
- Licencia repozitára je GPL-3.0. Zachovať pôvod, licenciu a zmeny. Práva k značkám/logám nepovažovať automaticky za neobmedzené.

Balíky `dark/light on transparent` nie sú našimi tromi pozadiami Transparent/Biele/Čierne. Nesmú sa iba premenovať na naše štýly.

## 2. RadioDNS / Project Logo — doplnkový zdroj vysielateľa

- https://radiodns.org/campaigns/project-logo/
- https://radiodns.org/campaigns/project-logo/walkthrough-finding-radio-station-logos/
- https://radiodns.org/campaigns/project-logo/frequently-asked-questions/
- https://radiodns.org/coverage/

Postup: identita FM/DAB → DNS CNAME → SRV `_radioepg._tcp` → SI.xml → zodpovedajúci bearer → multimedia logo. DAB potrebuje GCC/ECC, ensemble, service ID a component ID; satelitná referencia Enigmy tieto údaje sama nenahrádza. Oficiálny návod obsahuje aj príklad BAYERN 3. Pokrytie nie je úplné; nejde o jeden univerzálny ZIP.

Podmienky použitia určuje vysielateľ v SI dokumente. Zobrazenie a lokálna cache v prijímači sa musia odlíšiť od zrkadlenia a redistribúcie v našom verejnom balíku. Žiadne hromadné preberanie bez posúdenia konkrétnych podmienok. Pre tento zdroj nebol vykonaný živý DNS/SI download ani audit konkrétneho loga; overená je dokumentácia a mechanizmus.

## Navrhnuté zapojenie do PiconHubu

1. Zachovať existujúce satelitné balíky aj chránené Warder MASTER picony. Nevytvárať duplicitné adresáre s rozmermi. Výstup 220×132 naďalej do používateľom zvoleného `picon/`.
2. Rádio filtrovať podľa overenej servisnej databázy prijímača/zoznamu staníc; SRP index sám nerozlišuje spoľahlivo TV a rádio. Nepremeniť všetky TV referencie na rádio.
3. Najprv vlastné overené logo, potom importovaný balík, až potom individuálny zdroj vysielateľa. Zachovať presnú referenciu aj názvové aliasy; nepoužiť názov ako globálne unikátny identifikátor.
4. Import na serveri premeniť na existujúci overovaný ZIP formát. TAR hardlinky nerozbaľovať slepo v prijímači: overiť cesty, korene a cieľ každého odkazu, odmietnuť symlinky a únik z archívu, zaviesť limity. Až potom materializovať samostatné PNG.
5. Z SVG/masterov pripraviť tri naše štýly bez deformácie a bez straty užitočnej bielej plochy loga; zachovať pomer strán. Nevkladať veľké rádiové balíky do IPK.
6. Nový katalóg musí mať pôvod, zdrojový commit/tag, SHA256, veľkosť, rozmery a spôsob mapovania. Stiahnutie a spracovanie mimo GUI; zrušenie a zlyhanie nesmú zmazať vlastné picony.
7. Pred aktiváciou porovnať reálne satelitné RDS, bežné rádio, internet a DAB/DAB-over-DVB. Overiť BAYERN 3 a Schwarzwaldradio v zozname, RDS paneli aj OK infobare. Získať skutočné DAB referencie; nevymýšľať ich z FM/DVB údajov.

## Čo ešte zostáva pred vydaním

Implementácia a testovanie adaptéra, úplný audit vybraného názvového balíka, inventár existujúcich Warder DAB stagingov a reálne referencie DAB služieb. V main v čase kontroly nebol adresár `picons/DAB`; nezakladať automaticky ďalšiu konkurenčnú štruktúru bez porovnania s už pripravenými podkladmi. Nebola deklarovaná úplná dostupnosť log všetkých európskych rádií.
