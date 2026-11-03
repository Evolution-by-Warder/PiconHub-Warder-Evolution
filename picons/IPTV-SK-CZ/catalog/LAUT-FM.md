# Doplnkový zdroj laut.fm

Týždenná aktualizácia používa aj verejné API https://api.laut.fm (dokumentácia: https://docs.api.laut.fm/).
Najprv obnoví údaje známych laut.fm staníc a potom načíta najviac 1 000 kandidátov z verejného katalógu na jedno spustenie. To nie je kompletný import všetkých laut.fm staníc. Kandidáti môžu obsahovať už známe stanice; nové položky sa zlučujú podľa identifikátora stanice naprieč HTTP/HTTPS a variantmi streamovacej adresy. Limit možno znížiť argumentom `--laut-discovery-limit`, hodnota 0 vypne hľadanie nových kandidátov.

Vlastný SK/CZ bouquet, jeho referencie aj picony sa zachovávajú. Existujúce zahraničné položky si ponechajú názov, referenciu a zaradenie. Nové bez overenej krajiny patria do skupiny **laut.fm**. Pri výpadku API zostanú posledné platné doplnkové údaje; aktualizácia nepovažuje chýbajúcu odpoveď za dôkaz zániku stanice.

## Krajiny

Oficiálna schéma API 1.0.4 obsahuje filtre podľa žánru, počiatočného písmena a súradníc. Neobsahuje endpoint ani filter podľa krajiny. Stanica má voľný text `location` a `lat`/`lng`, nie overený kód krajiny. Samotný text alebo súradnice preto neurčujú krajinu v našom zozname. Toto bolo overené proti živej API schéme a odpovediam 3. novembra 2026.

## Spracovanie a limity

Čítanie používa overované HTTPS, dávky najviac 50 známych staníc, časový rozpočet 90 sekúnd, najviac 4 MiB na odpoveď a 12 MiB spolu. Výsledný bouquet zostáva do 4 MiB a 20 000 staníc, čo zodpovedá limitom rádio pluginu. Kontrola štruktúry a `active` v API nepotvrdzuje skutočnú dostupnosť každého audio streamu.

`--source-file` zachová offline správanie bez API požiadaviek; `--without-laut` vynechá API a zachová predchádzajúce doplnkové údaje. Kontroly sú v `test_laut_radio.py` a `test_world_radio.py`.

Aktualizujú sa online dáta v repozitári; nové IPK nie je potrebné.


## Overenie publikácie — 3. november 2026

Pridanie zdroja: 598ab14d608dc0dc2c5e909e6319df65d0bcb125. Živý skúšobný beh: https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/actions/runs/41697720515.
Publikačný beh: https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/actions/runs/41698216802 — úspešný; 23 testov zlučovania a chýb zdroja prešlo.
Výsledný zoznam: **6358 staníc**, z toho vlastné SK 88 / CZ 233. Doplnok pridal 914 nových staníc a obnovil 192 adries existujúcich staníc pri zachovaní referencií.
Verejný bouquet má 823472 bajtov; SHA-256 v publikovanom reporte: `693b8b3af8039d25bb602274425b9b85f8bad46e9f4a42d08e0ef9bece5b6a1f`.
Súbory dát publikoval commit `46331b15bb0035179ede0abc007c390bf21ecdbe`. Kontrola jednotlivých audio streamov ani skutočné načítanie na prijímači sa týmto nepreukazuje. Radio Browser a ostatné zdroje z prehľadu ešte nie sú pripojené ako automatické importéry.
