# PiconHub Warder Evolution — MASTER Quality Plan

Status: production-QA checkpoint — 2026-09-15

## Cieľ
Zjednotiť kompletnú databázu PiconHub do nového Warder Evolution štandardu. Zdrojom loga je vždy príslušný `transparent` picon, ktorý musí najprv prejsť vstupným SOURCE QC. BLACK a WHITE varianty sa vytvárajú výhradne pomocou schválených MASTER šablón `templates/picons/black-sablona.png` a `templates/picons/white-sablona.png`. Originálne záložné ZIPy sú v súkromnom Trezore.

## Nemenná adresárová architektúra
`picons/<satellite-position>/<provider>/{transparent,white,black}/<service-reference>.png`
Zakázané: extra `satellite`, `Satellite 0`, vymyslený/generický provider alebo zmena service-reference filename.

## MASTER šablóny
BLACK a WHITE master PNG sú autoritatívne zdroje pozadia. Nesmú sa prekresľovať, regenerovať, deformovať, farebne meniť ani resizeovať. Používajú sa presne v schválenej podobe.

## Výrobný/QC postup

### 1. Transparentný zdroj — povinný SOURCE QC
Pred akýmkoľvek BLACK/WHITE generovaním sa kontroluje každý transparentný zdroj. Kontrolovať rozmery, PNG/RGBA/alfa, alfa hrany, ostrosť, resize artefakty, poškodenie, prázdny alpha obsah a pravosť transparentného pozadia. Doostrenie iba pri preukázateľne mäkkom zdroji, jemne a auditovane. Transparentný originál sa svojvoľne nemení, neprepisuje ani nemaže.

### 1a. FAKE-TRANSPARENT / OPAQUE-BACKGROUND QC
Súbor uložený v `transparent/` sa nesmie automaticky považovať za skutočne transparentný picon. SOURCE QC musí odhaliť najmä nepriehľadné alebo prakticky nepriehľadné obdĺžnikové/rastrové pozadie, ktoré je súčasťou zdrojového obrázka a nie loga.

Detekcia nesmie byť založená iba na jednoduchom pravidle „veľa nepriehľadných pixelov“, pretože legitímne logo môže byť veľké a plné. Má kombinovať viac signálov, napríklad alpha pokrytie, súvislú obdĺžnikovú plochu, správanie rohov a hrán komponentu, pomer plochy k viditeľnému bboxu a ďalšie bezpečné indikátory. Podozrivý zdroj sa nikdy nesmie poslať do automatickej kontrastnej recolorizácie ako bežný achromatický komponent.

Kanonický produkčný nález: PLAN B TELEVISION na `80.0E/orion-express`. Zdroj uložený v `transparent/` obsahoval plný tmavý obdĺžnik. Automatika následne nesprávne vyhodnotila takmer celý obdĺžnik ako achromatický komponent a BLACK/WHITE výstup zničila. Tento prípad je referenčný príklad FAKE-TRANSPARENT SOURCE a dôkaz, že SOURCE QC musí predchádzať component-mask/AUTO-FIX fáze.

### 1b. Evidencia chybných zdrojov — nič nestratiť
Každý zdroj, ktorý SOURCE QC neprejde, sa najprv zapíše do samostatného recovery/audit zoznamu a až potom sa vyradí z normálnej automatickej výroby. Záznam musí podľa dostupnosti obsahovať minimálne satelitnú pozíciu, providera, service-reference, cestu, SHA256 pôvodného súboru, typ/dôvod chyby a stav recovery.

Pôvodný chybný súbor sa automaticky nemaže ani neprepisuje. BLACK/WHITE vytvorené z takého zdroja sa nesmú považovať za schválený produkčný výstup. Identické chybné zdroje s rovnakým SHA256 sa evidujú tak, aby bolo možné rozpoznať duplicity, ale každá service-reference zostáva zachovaná.

Odporúčané stavy recovery: `SOURCE-ERROR`, `SOURCE-REVIEW`, `RECOVERY-SEARCH`, `RECOVERY-CANDIDATE`, `RECOVERED-PASS`, `SOURCE-UNRESOLVED`.

### 1c. WEB RECOVERY chybných transparentných zdrojov
Až po dokončení prvého SOURCE QC priechodu celej databázy sa spracuje recovery zoznam. Pre každý chybný zdroj sa možno pokúsiť nájsť skutočný transparentný originál na webe.

Identita stanice/loga sa musí určiť spoľahlivo z dostupných údajov. Priorita zdrojov: oficiálny web stanice, providera alebo oficiálne brand/media assets; potom dôveryhodný sekundárny zdroj. Nesmie sa použiť náhodné alebo iba podobne pomenované logo. Automatika nesmie logo prekresľovať, domýšľať, esteticky meniť ani nahradiť podobným variantom.

Pri každom stiahnutom recovery kandidátovi sa auditovane zaznamená zdroj/URL a dostupná identifikácia. Kandidát nikdy automaticky nenahrádza pôvodný transparent. Najprv musí prejsť rovnakým SOURCE QC vrátane kontroly alpha/transparencie, fake backgroundu, integrity, kvality hrán, správnej identity/varianty a ostatných pravidiel tohto plánu.

Ak recovery kandidát prejde, môže sa z neho pripraviť korektný transparentný picon pri zachovaní service-reference, providera a satelitnej pozície; až potom sa z neho vyrábajú BLACK/WHITE varianty podľa nemenných MASTERov a celý výsledok prejde výstupným QC. Pôvodný chybný zdroj musí zostať auditovateľný/zálohovaný podľa schváleného postupu.

Ak sa spoľahlivý transparentný originál nenájde, identita je neistá alebo kandidát SOURCE QC neprejde, nič sa nehádá. Položka zostáva `SOURCE-UNRESOLVED`/REVIEW na manuálne rozhodnutie a nevstupuje do schválenej produkcie.

### 1d. Povinné poradie SOURCE recovery pipeline
`SOURCE QC → ERROR/RECOVERY LIST → WEB RECOVERY → SOURCE QC #2 → TRANSPARENT NORMALIZATION → BLACK/WHITE MASTER BUILD → OUTPUT QC → VISUAL REVIEW`

WEB RECOVERY je opravný mechanizmus, nie povolenie na kreatívnu tvorbu loga. Kvalita, identita a auditovateľnosť majú prednosť pred úplnosťou katalógu.

### 2. Veľkosť a umiestnenie
Určiť skutočný bounding box viditeľného loga bez prázdnych transparentných okrajov. Logo proporcionálne prispôsobiť využiteľnej ploche podľa šírky AJ výšky, zachovať pomer strán, nedeformovať, široké limitovať šírkou, vysoké výškou, ponechať rozumný bezpečný odstup a vycentrovať. MASTER pozadie zostáva nedotknuté.

### 3. Farba a čitateľnosť — text-aware + local-background + component-mask pravidlo
BLACK a WHITE sa posudzujú samostatne. Základom je zachovať originálne brand farby a grafické prvky všade, kde sú čitateľné.

**Text ležiaci priamo na MASTER pozadí** sa posudzuje samostatne z hľadiska čitateľnosti. Ak na konkrétnom masteri zaniká, jeho farba sa môže zmeniť na vhodnú kontrastnú farbu bez zmeny ostatných dobre čitateľných brand prvkov. Tmavý text na BLACK sa zmení na vhodnú svetlú farbu; veľmi svetlý text na WHITE na vhodnú tmavú. Mení sa celý logický textový prvok konzistentne.

**Text vložený do farebného políčka, badge, pásu, kruhu alebo iného vlastného grafického pozadia loga sa podľa BLACK/WHITE MASTERU NESMIE prefarbovať.** Jeho kontrast sa posudzuje voči vlastnému lokálnemu farebnému pozadiu. Farba vnútorného písma, jeho farebné políčko a ich antialias/prechodové pixely sa zachovávajú ako jeden chránený brand prvok.

### 3a. Presná ochrana logických komponentov
Kontrastná úprava sa smie vykonať iba po spoľahlivom oddelení celého logického komponentu, ktorý sa má meniť, od všetkých susedných brand prvkov. **Nesmie sa používať hrubý obdĺžnik, súradnicová hranica typu `x < ...`, globálny prah tmavosti ani iná maska, ktorá môže zasiahnuť susedné farebné políčko, jeho pozadie, vnútorné písmo alebo antialias hranu.**

Chránený farebný komponent musí zostať pixelovo nedotknutý po celej svojej ploche vrátane okrajov a antialias pixelov. Ak maska úpravy čo i len čiastočne pretína chránený farebný komponent, automatická úprava sa nevykoná a prípad ide do REVIEW.

Príklad TV DUGA+: `TV` je samostatný logický textový komponent ležiaci priamo na masteri a na BLACK môže byť zosvetlený. Celý farebný blok `DUGA+` — všetky farebné políčka, vnútorné písmená, `+`, okraje a antialias — je chránený a musí zostať pixel za pixelom zhodný so zdrojovým logom po geometrickom resize. Úprava `TV` nesmie zasiahnuť ani jediný pixel bloku `DUGA+`.

Logá, ktorých podstatou je prevažne text — napríklad rádiové wordmarky/názvy staníc — sa môžu považovať za textový celok. Ak wordmark leží priamo na masteri a zaniká, môže sa celý zmeniť na svetlú farbu na BLACK alebo tmavú na WHITE. Tvar, typografia, rozostupy a integrálne symboly zostávajú zachované.

Pri grafickom symbole/piktograme platí podobná zásada iba vtedy, keď je symbol jednofarebný alebo jednoznačne oddeliteľný a leží priamo na masteri. Farebné brand prvky s vlastným grafickým pozadím sa nemenia.

Zakázané sú náhodné pixelové kontrastné opravy, rozbíjanie jedného písmena/symbolu, prefarbovanie vnútorného textu farebných badge podľa mastera, automatické obrysy, tiene, halo a agresívne celoplošné prefarbenie farebného loga kvôli jednému prvku.

Monochromatické logo alebo jednoduchý textový wordmark môže mať celú svetlú verziu pre BLACK a celú tmavú verziu pre WHITE. NOS a RÁDIO SLOVAKIA INTERNATIONAL sú vzorové typy takejto alternatívy.

### 3b. V9 schválenie — zmiešané logo so svetlým textom
Štefan vizuálne schválil princíp ukázaný vo V9 na vzorkách 5 a 6: ak zmiešané/farebné logo obsahuje **biely alebo veľmi svetlý text ležiaci priamo na WHITE MASTER pozadí**, tento text sa má zmeniť na **čierny/tmavý**, pokiaľ ho component-mask dokáže bezpečne oddeliť. Ostatné farebné brand prvky (napr. červený symbol, farebné `FM`, badge alebo grafika) musia zostať bez zmeny vrátane okrajov a antialias pixelov. Rovnaká zásada platí opačne pre tmavý text zanikajúci na BLACK MASTER: bezpečne oddelený text sa zmení na svetlý a ostatné farebné prvky zostanú nedotknuté.

V9 vzorky 5 a 6 potvrdili aj QC zásadu: samotné zistenie „farebné logo“ nestačí na automatický PASS. Najprv sa musí posúdiť čitateľnosť jednotlivých logických komponentov na konkrétnom MASTER pozadí. Ak bezpečné oddelenie svetlého/tmavého textu nie je garantované, prípad zostáva REVIEW a automatika nesmie hádať.

Ak automatika nevie spoľahlivo rozlíšiť komponenty alebo vytvoriť masku bez zásahu do susedného chráneného prvku, prípad ide do REVIEW. REVIEW má prednosť pred chybnou automatickou úpravou.

### 4. Výroba
Vytvoriť `black/<same-service-reference>.png` a `white/<same-service-reference>.png` iba zo zdroja, ktorý prešiel SOURCE QC alebo úspešným auditovaným recovery procesom. Zachovať správne logo, service reference, providera a satelitnú pozíciu. Povolené sú iba schválené operácie: QC, proporcionálne fit/centrovanie a bezpečná kontrastná zmena presne oddeleného logického prvku.

### 5. Výstupná kontrola
Overiť 220×132, PNG/RGBA/alfa, správnu cestu position → provider → style, service-reference, čitateľnosť textu/symbolov, proporcionálnu veľkosť, centrovanie a čisté hrany. Pri každej kontrastnej úprave overiť, že všetky chránené farebné komponenty zostali pixelovo nezmenené po geometrickom resize a že maska úpravy nezasiahla ich pozadie, vnútorné písmo, okraje ani antialias pixely.

Výstupný audit musí umožniť spätne rozlíšiť pôvodný SOURCE PASS, AUTO-FIXED, recovery zdroj, unresolved zdroj a všetky dôvody REVIEW/ERROR.

## Triedenie QC
1. PASS — originál bezpečne použitý.
2. AUTO-FIXED — použitá presne schválená a auditovaná zmena presne oddeleného logického prvku.
3. REVIEW — nejednoznačný vizuálny prípad alebo neistá maska; automatika ho nesmie hádať.
4. ERROR/SKIP — technicky chybný alebo nespracovateľný.
5. SOURCE-ERROR / SOURCE-REVIEW — vstupný transparent neprešiel SOURCE QC; nevstupuje do normálnej BLACK/WHITE výroby.
6. RECOVERED-PASS — náhradný transparentný originál bol spoľahlivo identifikovaný, zdroj auditovaný a prešiel SOURCE QC #2.
7. SOURCE-UNRESOLVED — spoľahlivý recovery zdroj sa nenašiel alebo neprešiel; vyžaduje manuálne rozhodnutie.
AUTO-FIXED/REVIEW/ERROR/SOURCE/RECOVERY stavy musia mať auditný dôvod.

## Povinný full-catalog recheck po náleze PLAN B
Produkčná vizuálna QA 2026-09-15 odhalila FAKE-TRANSPARENT PLAN B TELEVISION. Doterajší rebuild na vetve `warder-master-production` sa preto nesmie považovať za finálne schválený a nesmie sa mergeovať do `main`.

Po implementácii rozšíreného SOURCE QC sa musí znovu prehnať kontrolou **celý katalóg transparentných zdrojov**, nie iba už známe chybné kusy. Postup:
1. full SOURCE QC všetkých transparentných piconov;
2. vytvoriť recovery/error zoznam ešte pred vyradením chybných vstupov;
3. spracovať web recovery kandidátov a SOURCE QC #2;
4. zachovať unresolved prípady na REVIEW bez hádania;
5. kompletne nanovo vytvoriť BLACK/WHITE iba z platných zdrojov pomocou originálnych MASTERov;
6. vykonať automatický output QC a audit;
7. vykonať nové vizuálne stresové testy vrátane AUTO-FIXED, zmiešaných farebných komponentov, recovered zdrojov a REVIEW;
8. až po výslovnom vizuálnom schválení Štefanom je možné uvažovať o merge do `main`.

Predchádzajúci produkčný checkpoint sa nemaže ani neprepisuje z histórie; zostáva auditovateľným checkpointom, ktorý umožnil chybu odhaliť. Oprava pokračuje ďalšími commitmi výhradne na `warder-master-production`.

## Bezpečnosť Git operácie
Hromadnú výrobu nerobiť nekontrolovane na `main`: pracovná vetva → SOURCE QC → recovery → QC/generovanie → audit/report → kontrola počtov/štruktúry → vzorky + REVIEW → až potom schválený merge. Transparentné originály sa nesmú stratiť. MASTERy sa nesmú zmeniť. Existujúce BLACK/WHITE možno nahradiť až podľa schválených pravidiel a po úplnom rechecku.

## Rozdelenie práce
Štefan + ChatGPT definujú a schvaľujú vizuálne pravidlá a reprezentatívne vzorky. Automatika/Work vykonáva hromadnú operáciu iba podľa zmrazených pravidiel; nesmie vymýšľať estetické pravidlá, hádať identitu recovery loga ani rozhodovať nejednoznačné REVIEW prípady.

## Pred spustením celej databázy
Schváliť reprezentatívnu testovaciu sadu: svetlé/tmavé monochromatické, farebné a viacfarebné logo, textový wordmark, logo s oddeleným textom a grafikou, text vo farebnom badge/políčku, susediace komponenty s antialias hranou, jemné písmo, ostrý a mäkký zdroj, nízky kontrast na BLACK/WHITE, široké a vysoké logo, FAKE-TRANSPARENT zdroj a úspešne recovered transparentný zdroj.

## Aktuálny Vhannibal checkpoint
Guarded import pridal 4 601 transparentných piconov, bez výroby WHITE/BLACK a bez prepisovania existujúcich piconov. Skipped missing-provider, unknown-position a non-220×132 prípady sa nesmú svojvoľne zaradiť.

## Zásada
Kvalita, správna identita a auditovateľnosť majú prednosť pred počtom. Keď automatika nevie bezpečne rozhodnúť, výsledok ide do REVIEW/SOURCE-UNRESOLVED — nie do Git `main` ako odhad.
