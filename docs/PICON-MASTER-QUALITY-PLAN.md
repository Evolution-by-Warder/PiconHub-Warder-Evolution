# PiconHub Warder Evolution — MASTER Quality Plan

Status: planning checkpoint — 2026-09-15

## Cieľ
Zjednotiť kompletnú databázu PiconHub do nového Warder Evolution štandardu. Zdrojom loga je vždy príslušný `transparent` picon. BLACK a WHITE varianty sa vytvárajú výhradne pomocou schválených MASTER šablón `templates/picons/black-sablona.png` a `templates/picons/white-sablona.png`. Originálne záložné ZIPy sú v súkromnom Trezore.

## Nemenná adresárová architektúra
`picons/<satellite-position>/<provider>/{transparent,white,black}/<service-reference>.png`
Zakázané: extra `satellite`, `Satellite 0`, vymyslený/generický provider alebo zmena service-reference filename.

## MASTER šablóny
BLACK a WHITE master PNG sú autoritatívne zdroje pozadia. Nesmú sa prekresľovať, regenerovať, deformovať, farebne meniť ani resizeovať. Používajú sa presne v schválenej podobe.

## Výrobný/QC postup

### 1. Transparentný zdroj
Kontrolovať rozmery, PNG/RGBA/alfa, alfa hrany, ostrosť, resize artefakty a poškodenie. Doostrenie iba pri preukázateľne mäkkom zdroji, jemne a auditovane. Transparentný originál sa svojvoľne nemení.

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
Vytvoriť `black/<same-service-reference>.png` a `white/<same-service-reference>.png`. Zachovať správne logo, service reference, providera a satelitnú pozíciu. Povolené sú iba schválené operácie: QC, proporcionálne fit/centrovanie a bezpečná kontrastná zmena presne oddeleného logického prvku.

### 5. Výstupná kontrola
Overiť 220×132, PNG/RGBA/alfa, správnu cestu position → provider → style, service-reference, čitateľnosť textu/symbolov, proporcionálnu veľkosť, centrovanie a čisté hrany. Pri každej kontrastnej úprave overiť, že všetky chránené farebné komponenty zostali pixelovo nezmenené po geometrickom resize a že maska úpravy nezasiahla ich pozadie, vnútorné písmo, okraje ani antialias pixely.

## Triedenie QC
1. PASS — originál bezpečne použitý.
2. AUTO-FIXED — použitá presne schválená a auditovaná zmena presne oddeleného logického prvku.
3. REVIEW — nejednoznačný vizuálny prípad alebo neistá maska; automatika ho nesmie hádať.
4. ERROR/SKIP — technicky chybný alebo nespracovateľný.
AUTO-FIXED/REVIEW/ERROR musia mať auditný dôvod.

## Bezpečnosť Git operácie
Hromadnú výrobu nerobiť nekontrolovane na `main`: pracovná vetva → QC/generovanie → audit/report → kontrola počtov/štruktúry → vzorky + REVIEW → až potom schválený merge. Transparentné originály sa nesmú stratiť. Existujúce BLACK/WHITE možno nahradiť až po schválení presných pravidiel a vzoriek.

## Rozdelenie práce
Štefan + ChatGPT definujú a schvaľujú vizuálne pravidlá a reprezentatívne vzorky. Work neskôr vykoná hromadnú operáciu iba podľa zmrazených pravidiel; nesmie vymýšľať estetické pravidlá ani rozhodovať REVIEW prípady.

## Pred spustením celej databázy
Schváliť reprezentatívnu testovaciu sadu: svetlé/tmavé monochromatické, farebné a viacfarebné logo, textový wordmark, logo s oddeleným textom a grafikou, text vo farebnom badge/políčku, susediace komponenty s antialias hranou, jemné písmo, ostrý a mäkký zdroj, nízky kontrast na BLACK/WHITE, široké a vysoké logo. Až potom zmraziť Warder Evolution master standard.

## Aktuálny Vhannibal checkpoint
Guarded import pridal 4 601 transparentných piconov, bez výroby WHITE/BLACK a bez prepisovania existujúcich piconov. Skipped missing-provider, unknown-position a non-220×132 prípady sa nesmú svojvoľne zaradiť.

## Zásada
Kvalita a správnosť majú prednosť pred počtom. Keď automatika nevie bezpečne rozhodnúť, výsledok ide do REVIEW — nie do Git `main` ako odhad.
