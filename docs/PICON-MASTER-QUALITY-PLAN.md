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

### 3. Farba a čitateľnosť — konzervatívne pravidlo
BLACK a WHITE sa posudzujú samostatne.

Základ je **zachovať originálne farby loga**. Automatika nesmie meniť logo len preto, že obsahuje tmavé alebo svetlé pixely. Pri farebných a viacfarebných logách sa originál ponechá, pokiaľ je logo ako značka rozpoznateľné a použiteľné na danom masteri.

Zakázané sú lokálne kontrastné opravy jednotlivých pixelov, písmen, pásov alebo segmentov. Žiadne automatické obrysy, tiene, halo ani skladanie čiernych a bielych častí podľa pozadia.

**Celoplošná zmena farby je povolená iba ako jedna jednotná verzia CELÉHO loga.** Takáto celá svetlá verzia pre BLACK alebo celá tmavá verzia pre WHITE je vhodná najmä pri monochromatických logách a môže byť použitá aj pri jednoduchom viacfarebnom logu, ak výsledná silueta zachová kompletný tvar, text, symboly a vizuálnu identitu loga a výsledok je zreteľne lepší.

Dôležité: samotná existencia jednej slabo kontrastnej farby **nie je dôvodom** prefarbiť celé viacfarebné logo. Agresívne automatické prefarbenie farebných log ako TV DUGA+ alebo NAB nie je dovolené. Ak pôvodné farebné logo zostáva rozpoznateľné, ponechá sa originál.

Naopak, jednoduché logo typu RÁDIO SLOVAKIA INTERNATIONAL môže použiť jednotnú celú svetlú verziu na BLACK a jednotnú celú tmavú verziu na WHITE, ak sa tým zachová celý nápis/symbolika a výsledok je čitateľnejší. Rovnako monochromatické NOS môže mať celú svetlú/tmavú alternatívu podľa mastera.

Ak automatika nevie s vysokou istotou rozlíšiť, či jednotná celoplošná verzia zachová identitu a bude lepšia než originál, prípad ide do REVIEW. **REVIEW je preferovaný pred zbytočným prefarbením.**

### 4. Výroba
Vytvoriť `black/<same-service-reference>.png` a `white/<same-service-reference>.png`. Zachovať správne logo, service reference, providera a satelitnú pozíciu. Povolené sú iba schválené operácie: QC, proporcionálne fit/centrovanie a v bezpečných prípadoch jednotná verzia celého loga.

### 5. Výstupná kontrola
Overiť 220×132, PNG/RGBA/alfa, správnu cestu position → provider → style, service-reference, čitateľnosť, proporcionálnu veľkosť, centrovanie, čisté hrany, žiadne lokálne prefarbenie, zachovanie identity a kompletnosť variantov.

## Triedenie QC
1. PASS — originál bezpečne použitý.
2. AUTO-FIXED — použitá presne schválená a auditovaná celková korekcia.
3. REVIEW — nejednoznačný vizuálny prípad; automatika ho nesmie hádať.
4. ERROR/SKIP — technicky chybný alebo nespracovateľný.

AUTO-FIXED/REVIEW/ERROR musia mať auditný dôvod.

## Bezpečnosť Git operácie
Hromadnú výrobu nerobiť nekontrolovane na `main`: pracovná vetva → QC/generovanie → audit/report → kontrola počtov/štruktúry → vzorky + REVIEW → až potom schválený merge. Transparentné originály sa nesmú stratiť. Existujúce BLACK/WHITE možno nahradiť až po schválení presných pravidiel a vzoriek.

## Rozdelenie práce
Štefan + ChatGPT definujú a schvaľujú vizuálne pravidlá a reprezentatívne vzorky. Work neskôr vykoná hromadnú operáciu iba podľa zmrazených pravidiel; nesmie vymýšľať estetické pravidlá ani rozhodovať REVIEW prípady.

## Pred spustením celej databázy
Schváliť reprezentatívnu testovaciu sadu: svetlé/tmavé monochromatické, farebné a viacfarebné logo, jemné písmo, ostrý a mäkký zdroj, nízky kontrast na BLACK/WHITE, široké a vysoké logo. Až potom zmraziť Warder Evolution master standard.

## Aktuálny Vhannibal checkpoint
Guarded import pridal 4 601 transparentných piconov, bez výroby WHITE/BLACK a bez prepisovania existujúcich piconov. Skipped missing-provider, unknown-position a non-220×132 prípady sa nesmú svojvoľne zaradiť.

## Zásada
Kvalita a správnosť majú prednosť pred počtom. Keď automatika nevie bezpečne rozhodnúť, výsledok ide do REVIEW — nie do Git `main` ako odhad.
