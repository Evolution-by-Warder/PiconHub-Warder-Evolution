# PiconHub Warder Evolution — MASTER Quality Plan

Status: planning checkpoint — 2026-09-15

## Cieľ

Zjednotiť kompletnú databázu PiconHub do nového Warder Evolution štandardu. Zdrojom loga je vždy príslušný `transparent` picon. BLACK a WHITE varianty sa vytvárajú výhradne pomocou schválených MASTER šablón:

- `templates/picons/black-sablona.png`
- `templates/picons/white-sablona.png`

Originálne záložné ZIPy master šablón sú uložené v súkromnom repozitári Trezor pod `backups/piconhub/master-templates/`.

## Nemenná adresárová architektúra

`picons/<satellite-position>/<provider>/{transparent,white,black}/<service-reference>.png`

Zakázané:

- žiadny extra adresár `satellite`,
- žiadny `Satellite 0`,
- žiadny vymyslený/generický provider,
- nemení sa service-reference filename.

## MASTER šablóny

BLACK a WHITE master PNG sú autoritatívne zdroje pozadia. Pri hromadnej výrobe sa nesmú prekresľovať, regenerovať, deformovať ani farebne meniť. Pracovné kópie alebo AI aproximácie nie sú master. Uložené MASTER šablóny platia presne v aktuálnej podobe a pri výrobe sa používajú bez úprav.

## Výrobný/QC postup pre každý picon

### 1. Kontrola transparentného zdroja

Pred výrobou BLACK/WHITE skontrolovať:

- rozmery a PNG/RGBA/alfa vlastnosti,
- čistotu alfa hrán,
- ostrosť loga a textu,
- rozmazanie alebo artefakty po starších resize operáciách,
- poškodené alebo nekvalitné zdroje.

Doostrenie sa nesmie aplikovať plošne. Použiť ho iba vtedy, keď QC preukáže, že transparentný zdroj je skutočne príliš mäkký. Úprava musí byť jemná a nesmie vytvárať halo, zubaté hrany alebo meniť dizajn loga.

Ak by sa mal meniť samotný transparentný originál, zmena musí byť auditovaná a vratná.

### 2. Analýza kontrastu loga

BLACK a WHITE sa nesmú vyrábať slepým alpha-composite bez kontroly čitateľnosti.

Pred kompozíciou vyhodnotiť farbu/jas loga a textu voči konkrétnemu master pozadiu. Typické riziká:

- biele alebo veľmi svetlé logo/písmo na WHITE,
- čierne alebo veľmi tmavé logo/písmo na BLACK,
- jemné tenké písmo strácajúce sa v odleskoch/ríme masteru,
- viacfarebné logo, pri ktorom by globálne prefarbenie poškodilo identitu značky.

Cieľom je zachovať pôvodné firemné farby a vzhľad loga vždy, keď je to možné. Nepoužívať primitívne globálne pravidlo typu „biele logo prefarbi na čierne“.

Ak je zásah nutný, použiť iba minimálnu kontrolovanú úpravu potrebnú pre čitateľnosť (napr. vhodná kontrastná verzia, jemný obrys/tieň alebo iné vopred schválené pravidlo). Nejednoznačné prípady automaticky NEHÁDAŤ — zaradiť ich do manuálnej kontroly.

### 3. Výroba

Pre schválené prípady vytvoriť:

- `black/<same-service-reference>.png`
- `white/<same-service-reference>.png`

Výsledok musí zachovať správne logo, service reference, providera a satelitnú pozíciu. Transparentný zdroj sa pri samotnej kompozícii nesmie svojvoľne posúvať, meniť mierku, deformovať ani prekresľovať.

### 4. Výstupná kontrola

Každý výsledok skontrolovať minimálne na:

- presný rozmer 220×132,
- platný PNG/RGBA a alfa kanál,
- správnu cestu position → provider → style,
- zhodný service-reference filename,
- čitateľnosť loga na BLACK aj WHITE,
- ostré a čisté hrany bez halo/resize artefaktov,
- žiadne nechcené zmeny identity loga,
- žiadne chýbajúce alebo nadbytočné varianty.

## Triedenie výsledkov QC

Každý picon zaradiť do jednej z kategórií:

1. PASS — bezproblémový, bezpečne vyrobený automaticky.
2. AUTO-FIXED — použitá presne definovaná a auditovaná korekcia (napr. jemné doostrenie/kontrastné pravidlo).
3. REVIEW — nejednoznačný alebo vizuálne problematický; nesmie byť automaticky schválený ani hádaný.
4. ERROR/SKIP — technicky chybný alebo nespracovateľný; zapísať dôvod.

Pre každý AUTO-FIXED/REVIEW/ERROR musí existovať auditný záznam s dôvodom.

## Bezpečnosť Git operácie

Hromadnú výrobu nerobiť priamo nekontrolovane na `main`. Odporúčaný postup:

1. vytvoriť pracovnú vetvu,
2. vykonať QC a generovanie,
3. vytvoriť audit/report,
4. overiť počty a štruktúru,
5. skontrolovať vzorky a všetky REVIEW prípady,
6. až po úspešnej kontrole merge do `main`.

Existujúce transparentné originály sa nesmú pri výrobe BLACK/WHITE stratiť. Pri plánovanej kompletnej obnove sa existujúce BLACK/WHITE môžu nahradiť novým master štandardom, ale až po schválení presných pravidiel a vzoriek.

## Rozdelenie práce

Chat/Štefan + ChatGPT:

- definovať vizuálne pravidlá,
- pripraviť a schváliť reprezentatívne vzorky,
- rozhodnúť sporné estetické prípady,
- skontrolovať report a výsledok.

Work:

- vykonať hromadnú viacstupňovú operáciu nad celou databázou,
- QC transparentov,
- aplikovať iba vopred schválené automatické pravidlá,
- analýza kontrastu BLACK/WHITE,
- výroba,
- výstupná validácia,
- vytvorenie reportu a Git pracovnej vetvy/PR.

Work nesmie samostatne vymýšľať estetické pravidlá ani automaticky rozhodovať REVIEW prípady.

## Pred spustením celej databázy — zajtrajší checkpoint

Najprv dokončiť a schváliť malú testovaciu sadu reprezentujúcu aspoň:

- svetlé/biele logo,
- tmavé/čierne logo,
- farebné logo,
- jemné alebo malé písmo,
- kvalitný ostrý transparent,
- mäkký/nekvalitný transparent vhodný na test kontrolovaného doostrenia,
- prípad s nízkym kontrastom na WHITE,
- prípad s nízkym kontrastom na BLACK.

Až keď budú tieto prípady vizuálne schválené, zmraziť pravidlá ako Warder Evolution master standard a pripraviť Work na kompletné spracovanie databázy.

## Aktuálny Vhannibal checkpoint

Vhannibal guarded import už pridal 4 601 transparentných piconov. Import nemenil existujúce picony a nevyrábal WHITE/BLACK. Skipped prípady z Vhannibal importu (missing provider, unknown namespace/position, non-220×132) sa nesmú kvôli tejto novej výrobnej fáze svojvoľne zaradiť alebo premapovať.

## Zásada

Kvalita a správnosť majú prednosť pred počtom automaticky spracovaných piconov. Keď automatika nevie bezpečne rozhodnúť, výsledok ide do REVIEW — nie do Git `main` ako odhad.
