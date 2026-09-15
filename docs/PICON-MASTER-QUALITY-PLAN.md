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

### 3. Farba a čitateľnosť — text-aware pravidlo
BLACK a WHITE sa posudzujú samostatne. Základom je zachovať originálne brand farby a grafické prvky všade, kde sú čitateľné.

**Text a textové časti loga sa posudzujú samostatne z hľadiska čitateľnosti.** Ak text na konkrétnom masteri zaniká, jeho farba sa môže zmeniť na vhodnú kontrastnú farbu bez zmeny ostatných dobre čitateľných brand prvkov. Tmavý text na BLACK sa zmení na vhodnú svetlú farbu; veľmi svetlý text na WHITE sa zmení na vhodnú tmavú farbu. Mení sa celý logický textový prvok konzistentne, nie jednotlivé pixely alebo náhodné časti písmen.

Príklad: pri TV DUGA+ zostáva farebná časť `DUGA+` zachovaná; ak tmavý text `TV` na BLACK zaniká, zmení sa iba celý textový prvok `TV` na svetlú kontrastnú farbu. Brand farby `DUGA+` sa kvôli tomu nemenia.

Logá, ktorých podstatou je prevažne text — napríklad rádiové wordmarky/názvy staníc — sa môžu z hľadiska kontrastu považovať za textový celok. Ak takýto textový wordmark zaniká na BLACK, môže sa celý textový wordmark zmeniť na svetlú farbu; na WHITE analogicky na tmavú. Tvar, typografia, rozostupy a symboly, ktoré sú integrálnou súčasťou wordmarku, zostávajú zachované.

Pri grafickom symbole/piktograme platí podobná zásada iba vtedy, keď je symbol sám o sebe jednofarebný alebo jednoznačne oddeliteľný a na pozadí zaniká: celý tento logický grafický prvok možno prefarbiť jednotne na vhodnú svetlú/tmavú farbu. Farebné brand prvky, ktoré sú dobre čitateľné, sa nemenia.

Zakázané sú pixelové/lokálne kontrastné opravy, rozbíjanie jedného písmena alebo symbolu na rôzne farby podľa pozadia, automatické obrysy, tiene, halo a agresívne celoplošné prefarbenie celého farebného loga len kvôli jednému problematickému prvku.

Monochromatické logo alebo jednoduchý textový wordmark môže mať celú svetlú verziu pre BLACK a celú tmavú verziu pre WHITE. NOS a RÁDIO SLOVAKIA INTERNATIONAL sú vzorové typy, kde je takáto jednotná textová/monochromatická alternatíva prípustná.

Ak automatika nevie spoľahlivo rozlíšiť logické prvky (text vs. grafika), nevie určiť hranice celého textového prvku alebo by zmena mohla poškodiť identitu, prípad ide do REVIEW. REVIEW má prednosť pred chybnou automatickou úpravou.

### 4. Výroba
Vytvoriť `black/<same-service-reference>.png` a `white/<same-service-reference>.png`. Zachovať správne logo, service reference, providera a satelitnú pozíciu. Povolené sú iba schválené operácie: QC, proporcionálne fit/centrovanie a bezpečná kontrastná zmena celého logického textového alebo monochromatického grafického prvku.

### 5. Výstupná kontrola
Overiť 220×132, PNG/RGBA/alfa, správnu cestu position → provider → style, service-reference, čitateľnosť všetkých textových prvkov a symbolov, proporcionálnu veľkosť, centrovanie, čisté hrany, žiadne pixelové prefarbenie, zachovanie brand farieb dobre čitateľných prvkov, identitu loga a kompletnosť variantov.

## Triedenie QC
1. PASS — originál bezpečne použitý.
2. AUTO-FIXED — použitá presne schválená a auditovaná zmena celého logického textového/monochromatického prvku.
3. REVIEW — nejednoznačný vizuálny prípad; automatika ho nesmie hádať.
4. ERROR/SKIP — technicky chybný alebo nespracovateľný.

AUTO-FIXED/REVIEW/ERROR musia mať auditný dôvod.

## Bezpečnosť Git operácie
Hromadnú výrobu nerobiť nekontrolovane na `main`: pracovná vetva → QC/generovanie → audit/report → kontrola počtov/štruktúry → vzorky + REVIEW → až potom schválený merge. Transparentné originály sa nesmú stratiť. Existujúce BLACK/WHITE možno nahradiť až po schválení presných pravidiel a vzoriek.

## Rozdelenie práce
Štefan + ChatGPT definujú a schvaľujú vizuálne pravidlá a reprezentatívne vzorky. Work neskôr vykoná hromadnú operáciu iba podľa zmrazených pravidiel; nesmie vymýšľať estetické pravidlá ani rozhodovať REVIEW prípady.

## Pred spustením celej databázy
Schváliť reprezentatívnu testovaciu sadu: svetlé/tmavé monochromatické, farebné a viacfarebné logo, textový wordmark, logo s oddeleným textom a grafikou, jemné písmo, ostrý a mäkký zdroj, nízky kontrast na BLACK/WHITE, široké a vysoké logo. Až potom zmraziť Warder Evolution master standard.

## Aktuálny Vhannibal checkpoint
Guarded import pridal 4 601 transparentných piconov, bez výroby WHITE/BLACK a bez prepisovania existujúcich piconov. Skipped missing-provider, unknown-position a non-220×132 prípady sa nesmú svojvoľne zaradiť.

## Zásada
Kvalita a správnosť majú prednosť pred počtom. Keď automatika nevie bezpečne rozhodnúť, výsledok ide do REVIEW — nie do Git `main` ako odhad.
