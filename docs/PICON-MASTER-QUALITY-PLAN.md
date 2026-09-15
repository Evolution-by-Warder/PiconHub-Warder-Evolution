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

Pred výrobou BLACK/WHITE skontrolovať rozmery, PNG/RGBA/alfa vlastnosti, čistotu alfa hrán, ostrosť loga a textu, rozmazanie alebo artefakty po starších resize operáciách a poškodené alebo nekvalitné zdroje.

Doostrenie sa nesmie aplikovať plošne. Použiť ho iba vtedy, keď QC preukáže, že transparentný zdroj je skutočne príliš mäkký. Úprava musí byť jemná a nesmie vytvárať halo, zubaté hrany alebo meniť dizajn loga. Ak by sa mal meniť samotný transparentný originál, zmena musí byť auditovaná a vratná.

### 2. Veľkosť a umiestnenie loga

Pred vložením na BLACK/WHITE master určiť skutočný bounding box viditeľného loga; prázdny transparentný priestor okolo loga sa nepovažuje za jeho rozmer.

Logo sa proporcionálne prispôsobí využiteľnej ploche master panela podľa šírky AJ výšky. Zachovať pôvodný pomer strán, nikdy logo nenaťahovať ani nedeformovať, široké logo limitovať šírkou, vysoké logo výškou, využiť plochu panela rozumne s bezpečným odstupom od okrajov a výsledné logo vycentrovať. MASTER pozadie samotné sa nikdy neresizuje ani nemení.

Cieľom je konzistentná vizuálna veľkosť loga na paneli, nie mechanické vloženie pôvodného 220×132 plátna 1:1.

### 3. Farba a čitateľnosť loga

BLACK a WHITE sa posudzujú samostatne voči konkrétnemu master pozadiu.

Záväzné pravidlá:

- ak je originálne logo na danom pozadí dobre čitateľné vo všetkých podstatných častiach, jeho pôvodné farby sa nemenia,
- farebné a viacfarebné logá sa majú zachovať v originálnych farbách, iba ak žiadna podstatná časť loga na danom masteri vizuálne nezaniká,
- nestačí priemerný kontrast celého loga: QC musí zachytiť aj podstatnú tmavú časť viacfarebného loga strácajúcu sa na BLACK a podstatnú svetlú časť strácajúcu sa na WHITE,
- automatika NESMIE lokálne prefarbovať iba jednotlivé pixely, písmená alebo časti jedného loga podľa lokálneho kontrastu,
- nesmie vzniknúť nekonzistentný výsledok typu časť jedného loga svojvoľne čierna a časť biela,
- pri jednofarebnom/monochromatickom logu, ktoré na danom masteri zaniká, je dovolené zmeniť farbu CELÉHO loga jednotne na vhodnú kontrastnú farbu,
- ak viacfarebné logo na konkrétnom masteri stratí podstatnú časť, originál sa na tomto masteri nepovažuje za PASS,
- pri takom viacfarebnom logu sa môže použiť iba JEDNOTNÁ alternatívna verzia CELÉHO loga pre dané pozadie, ktorá zachová tvar, proporcie, text a všetky grafické prvky; nesmú sa opravovať iba jednotlivé problémové segmenty,
- bezpečná automatická alternatíva môže byť napríklad celá svetlá verzia pre BLACK alebo celá tmavá verzia pre WHITE, ale iba vtedy, keď tým nevznikne strata významu alebo identity loga,
- ak jednotnú alternatívnu verziu celého viacfarebného loga nemožno bezpečne odvodiť bez poškodenia identity, výsledok ide do REVIEW a automatika ho nesmie hádať,
- žiadne automatické obrysy, tiene, halo alebo lokálne kontrastné efekty bez samostatného výslovného schválenia.

Praktický QC princíp: hodnotí sa viditeľnosť všetkých podstatných častí loga, nie iba jeho priemerná farba. BLACK a WHITE môžu preto použiť odlišnú celkovú verziu toho istého loga, ale každá výsledná verzia musí byť vnútorne jednotná a nesmie byť poskladaná z lokálne kontrastne opravovaných častí.

### 4. Výroba

Pre schválené prípady vytvoriť `black/<same-service-reference>.png` a `white/<same-service-reference>.png`.

Výsledok musí zachovať správne logo, service reference, providera a satelitnú pozíciu. Povolené zmeny loga sú iba tie, ktoré vyplývajú z vyššie schválených pravidiel veľkosti, centrovania, QC a jednotnej celkovej farebnej verzie pre daný master.

### 5. Výstupná kontrola

Každý výsledok skontrolovať minimálne na presný rozmer 220×132, platný PNG/RGBA a alfa kanál, správnu cestu position → provider → style, zhodný service-reference filename, čitateľnosť všetkých podstatných častí loga na BLACK aj WHITE, správnu proporcionálnu veľkosť a centrovanie, ostré a čisté hrany bez halo/resize artefaktov, žiadne nechcené lokálne prefarbenie častí loga, zachovanie identity loga a žiadne chýbajúce alebo nadbytočné varianty.

## Triedenie výsledkov QC

Každý picon zaradiť do jednej z kategórií:

1. PASS — bezproblémový, bezpečne vyrobený automaticky.
2. AUTO-FIXED — použitá presne definovaná a auditovaná schválená celková korekcia.
3. REVIEW — nejednoznačný alebo vizuálne problematický; nesmie byť automaticky schválený ani hádaný.
4. ERROR/SKIP — technicky chybný alebo nespracovateľný; zapísať dôvod.

Pre každý AUTO-FIXED/REVIEW/ERROR musí existovať auditný záznam s dôvodom.

## Bezpečnosť Git operácie

Hromadnú výrobu nerobiť priamo nekontrolovane na `main`. Odporúčaný postup: vytvoriť pracovnú vetvu, vykonať QC a generovanie, vytvoriť audit/report, overiť počty a štruktúru, skontrolovať vzorky a všetky REVIEW prípady a až po úspešnej kontrole merge do `main`.

Existujúce transparentné originály sa nesmú pri výrobe BLACK/WHITE stratiť. Pri plánovanej kompletnej obnove sa existujúce BLACK/WHITE môžu nahradiť novým master štandardom, ale až po schválení presných pravidiel a vzoriek.

## Rozdelenie práce

Chat/Štefan + ChatGPT definujú vizuálne pravidlá, pripravia a schvália reprezentatívne vzorky, rozhodnú sporné estetické prípady a skontrolujú report a výsledok.

Work vykoná hromadnú viacstupňovú operáciu nad celou databázou, QC transparentov, aplikuje iba vopred schválené automatické pravidlá, analýzu BLACK/WHITE čitateľnosti, výrobu, výstupnú validáciu a vytvorenie reportu a Git pracovnej vetvy/PR. Work nesmie samostatne vymýšľať estetické pravidlá ani automaticky rozhodovať REVIEW prípady.

## Pred spustením celej databázy — checkpoint

Najprv dokončiť a schváliť malú testovaciu sadu reprezentujúcu svetlé/biele monochromatické logo, tmavé/čierne monochromatické logo, farebné logo, viacfarebné brand logo, jemné alebo malé písmo, kvalitný ostrý transparent, mäkký/nekvalitný transparent, nízky kontrast na WHITE, nízky kontrast na BLACK, široké logo limitované šírkou a vysoké logo limitované výškou.

Až keď budú tieto prípady vizuálne schválené, zmraziť pravidlá ako Warder Evolution master standard a pripraviť Work na kompletné spracovanie databázy.

## Aktuálny Vhannibal checkpoint

Vhannibal guarded import už pridal 4 601 transparentných piconov. Import nemenil existujúce picony a nevyrábal WHITE/BLACK. Skipped prípady z Vhannibal importu (missing provider, unknown namespace/position, non-220×132) sa nesmú kvôli tejto novej výrobnej fáze svojvoľne zaradiť alebo premapovať.

## Zásada

Kvalita a správnosť majú prednosť pred počtom automaticky spracovaných piconov. Keď automatika nevie bezpečne rozhodnúť, výsledok ide do REVIEW — nie do Git `main` ako odhad.
