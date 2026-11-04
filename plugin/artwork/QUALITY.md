> Reference artwork quality rules for the plugin and shared picon database. Historical checkpoint figures below describe their recorded import stage, not current runtime totals.

# PiconHub Warder Evolution — MASTER Quality Plan

Status: planning checkpoint — 2026-09-15

## Cieľ
Zjednotiť kompletnú databázu PiconHub do nového Warder Evolution štandardu. Zdrojom loga je vždy príslušný `transparent` picon. BLACK a WHITE varianty sa vytvárajú výhradne pomocou schválených MASTER šablón `plugin/artwork/templates/picons/black-sablona.png` a `plugin/artwork/templates/picons/white-sablona.png`. Originálne záložné ZIPy sú v súkromnom Trezore.

## Nemenná adresárová architektúra
`picons/<satellite-position>/<provider>/{transparent,white,black}/<service-reference>.png`
Zakázané: extra `satellite`, `Satellite 0`, vymyslený/generický provider alebo zmena service-reference filename.

## MASTER šablóny
BLACK a WHITE master PNG sú autoritatívne zdroje pozadia. Nesmú sa prekresľovať, regenerovať, deformovať, farebne meniť ani resizeovať. Používajú sa presne v schválenej podobe.

## Výrobný/QC postup

### 1. Transparentný zdroj
Kontrolovať rozmery, PNG/RGBA/alfa, alfa hrany, ostrosť, resize artefakty a poškodenie. Doostrenie iba pri preukázateľne mäkkom zdroji, jemne a auditovane. Transparentný originál sa svojvoľne nemení.

### 1a. Oficiálna a schválená identita loga
Logo sa nesmie vymýšľať ani nahrádzať iným grafickým variantom iba kvôli farbe MASTER podkladu. Používa sa oficiálna alebo Štefanom schválená podoba transparentného zdroja vrátane vlastného kruhu, badge či farebného políčka. BLACK a WHITE zachovávajú tú istú identitu a kompozíciu; prípustné kontrastné zásahy sa riadia výhradne aktuálnym pravidlom ochrany celého farebného loga nižšie. Iná kompozícia vyžaduje výslovné schválenie.


**Schválený vzor — 27. 10. 2026:** Štefan potvrdil opravenú ukážku Absolut GERMANY slovami „teraz je uz perfektne“. Vo všetkých troch prevedeniach zostáva rovnaký oficiálny transparentný zdroj vrátane jeho vlastného bieleho kruhu. Tento princíp sa používa aj pri Absolut BELLA, HOT a TOP 2000 a pri ďalších piconoch. Schválená ukážka: https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/blob/93823afc4e22be3e0bd16d752103966423e13bce/picons/DAB/preview/review/absolut-germany.png

### 2. Veľkosť a umiestnenie
Určiť skutočný bounding box viditeľného loga bez prázdnych transparentných okrajov. Logo proporcionálne prispôsobiť využiteľnej ploche podľa šírky AJ výšky, zachovať pomer strán, nedeformovať, široké limitovať šírkou, vysoké výškou, ponechať rozumný bezpečný odstup a vycentrovať. MASTER pozadie zostáva nedotknuté.

### 3. Farba a čitateľnosť — celé farebné logo je chránené (2026-11-04)

Toto pravidlo nahrádza predchádzajúce component-mask pravidlá 3, 3a a 3b. **Do farebného loga s písmom sa automaticky nesmie zasahovať.** Zdroj sa posudzuje ako jeden celok: farebný symbol, biele/čierne/sivé písmo, samostatné alebo odpojené písmená, badge, panely, gradienty, alfa a všetky antialias hrany. Pri viditeľnom ne-neutrálnom pixeli sa konzervatívne chráni celé logo, aj pri nízkej alfe.

Pri BLACK aj WHITE sú povolené iba schválené proporcionálne prispôsobenie a centrovanie originálu na nezmenenom MASTER podklade. Výsledok musí byť pixelovo zhodný s kompozíciou nedotknutého zdroja po tejto geometrii. Oddeliteľnosť textu, jeho poloha priamo na MASTER podklade ani nízky kontrast nedávajú povolenie prefarbovať ho. Pri nedostatočnej čitateľnosti nasleduje REVIEW; nie automatická zmena farby, obrys, tieň, halo alebo náhrada loga.

Kontrastná úprava zostáva dostupná iba pre skutočne monochromatické logo podľa zmrazeného enginu a jeho QC. PASS/AUTO-FIXED nie sú vizuálnym schválením identity stanice.

Výnimka platí len pre konkrétny výstup, ktorý vlastník výslovne schválil a ktorého presný SHA256 je zaznamenaný. Nesmie sa preniesť na celú stanicu, rodinu log, podobný zdroj ani nový render. Historické schválenia sú potvrdením svojich presných výstupov, nie všeobecným povolením meniť farebné logá. Jedenásť trojíc schválených 4. 11. 2026 sa zachováva bez regenerovania; ich 33 presných PNG je evidovaných v [owner-approval.json](provenance/warder-approved11-20261104/owner-approval.json).

Kontrola musí bežať cez fail-closed guard `tools/warder_brand_guard.py` s politikou `WHOLE_COLOURED_LOGO_V2`. Ak pôvodný engine navrhne zásah do chráneného loga, guard návrh odmietne; REVIEW/BLOCKED sa neexportuje ako použiteľný picon. Samotné zistenie nezmenených sýtych pixelov alebo bezpečnej masky nestačí.

### 4. Výroba
Vytvoriť `black/<same-service-reference>.png` a `white/<same-service-reference>.png`. Zachovať správne logo, service reference, providera a satelitnú pozíciu. Povolené sú iba schválené operácie: QC, proporcionálne fit/centrovanie a kontrastná zmena iba skutočne monochromatického loga podľa bodu 3.

### 5. Výstupná kontrola
Overiť 220×132, PNG/RGBA/alfa, správnu cestu position → provider → style, service-reference, čitateľnosť textu/symbolov, proporcionálnu veľkosť, centrovanie a čisté hrany. Pri farebnom logu porovnať celý výsledok s kompozíciou nezmeneného originálu po schválenej geometrii na MASTER podklade. Porovnávanie iba sýtych pixelov alebo jednotlivých komponentov nestačí. Každý zásah do písma, pozadia loga, alfa alebo hrán blokuje export, ak nejde o presný už schválený výstup.

## Triedenie QC
1. PASS — originál bezpečne použitý.
2. AUTO-FIXED — auditovaná kontrastná zmena skutočne monochromatického loga; farebné logo sa nemení.
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


## Schválený referenčný checkpoint — 30. 10. 2026

Vlastník po zobrazení všetkých 13 doplnených log v Transparent, WHITE a BLACK výslovne potvrdil: „laska, su perfektne presne podla nasho Warder standardu.“ Týchto 39 presných základných PNG 220×132 je schválenou ukážkou existujúceho Warder štandardu. Potvrdzuje zachovanie identity loga, pomerné umiestnenie na zmrazených MASTER podkladoch a bezpečné kontrastné úpravy oddelených komponentov. Nejde o povolenie meniť iné schválené grafiky alebo hádať nejednoznačné masky.

[Schválenie s presnými SHA256](provenance/picons-assimilated-20261030/owner-approval.json) · [Schválená ukážka](provenance/picons-assimilated-20261030/quality-review.png).

