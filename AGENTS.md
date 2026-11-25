# PiconHub-Warder-Evolution – pravidlá pre prácu

## Povinná nezávislá kontrola výstupov SAT Worku (22. 11. 2026)

- **Rozdelenie zodpovednosti:** SAT Work robí odbornú prácu so satelitnými stanicami, servisnými referenciami, grafickými piconmi, master sadami a produkčnými SAT ZIPmi. Spoločný FullHDGlass/Warder Work jeho prácu **vždy nezávisle skontroluje** a overí, či sú výsledky **naozaj publikované**. Nesmie zameniť kontrolu za vykonávanie SAT Worku ani len slepo potvrdiť jeho správu.
- **Pri každom odovzdaní SAT Worku** načítaj najnovší skutočný `main` v FullHDGlass aj PiconHub, pracovné PR a commity, kontrolné súčty a manifesty. Porovnaj ich s konkrétnym deklarovaným výsledkom SAT Worku a s posledným schváleným grafickým základom. Starý commit nie je dôkazom aktuálneho produkčného stavu.
- **Nezávislé overenie správnosti:** skontroluj presné Enigma2 servisné referencie/identitu stanice, skutočnú grafiku (nie iba existenciu súboru), príslušné providery/satelitné pozície, zachovanie schválených Canal+ SK/CZ a ostatných chránených piconov, znovupoužitie správnych originálnych grafík a úplnú maticu **3 rozmerov 50×30, 220×132, 400×240 × 3 pozadia Transparent, WHITE, BLACK** pre každú dotknutú SAT položku a providera. Sezónne či dočasné názvy staníc neprepíš cez trvalú identitu bez potvrdenia.
- **Nezávislé overenie publikovania:** odlišuj zdrojový commit, pripravené lokálne PNG, otvorený PR, merge, produkčný manifest, súbory ZIP a ich časti, úspešné CI, skutočný release a zmenený produkčný updater. Ak sa tvrdí publikovanie, over ich reálnu prítomnosť na GitHube a príslušné SHA-256; iba existencia položky v manifeste nie je dôkaz, že nový obrázok bol reálne vydaný.
- **Výstup kontroly:** jasne označ `OVERENÉ A PUBLIKOVANÉ`, `SPRÁVNE, ALE NEPUBLIKOVANÉ`, `CHYBNÉ`, prípadne `NEOVERENÉ`. Uveď konkrétne chyby a miesto v repozitári; neposielaj používateľa iba naspäť na SAT Work bez nezávislého auditu. Pri zistených chybách priprav SAT Worku jednoznačné zadanie na opravu. Grafiku, SAT balíky a ich produkčné vydanie ponechaj SAT Worku, okrem prípadu, keď vlastník výslovne poverí tento Work ich opravou.
- Zachovaj existujúce bezpečnostné pravidlá a povolený rozsah; **automatické dokončovanie schválenej práce** nenahrádza nezávislé overenie publikovania a neautorizuje prepis cudzích piconov.


## Trvalé pravidlo dokončovania schválenej práce (22. 11. 2026)

Toto pravidlo výslovne požadoval vlastník pre **všetky projekty Evolution-by-Warder**. Je nadradené starším všeobecným formuláciám o opakovanom schvaľovaní každého merge, IPK a produkčného zápisu.

1. **Jedno schválenie na konkrétny rozsah.** Ak vlastník schválil pomenovanú úpravu, celú dávku, vydanie alebo vopred definovanú automatickú aktualizáciu, súhlas zahŕňa aj obvyklé dokončovacie kroky v tomto rozsahu: vytvorenie PR, absolvovanie povinných testov, zlúčenie do `main`, zostavenie/vydanie príslušného finálneho balíka (ak projekt balíky vydáva) a aktualizáciu produkčného kanála. **Nepýtaj sa znovu na ten istý súhlas pri každom kroku ani v novom chate/Worku.** Rozsah a zdroj schválenia zapíš do PR a projektového denníka.
2. **Dokončenie po úspešnej verifikácii.** Pokiaľ rozsah zahŕňa produkčné vydanie a všetky povinné relevantné CI/regresné testy prejdú, bezpečne dokonči merge → release → verifikáciu skutočne publikovaného artefaktu/SHA-256 → aktualizáciu produkcie. Ak je nastavená schválená automatizácia, nech postup vykoná ona. Nevydávaj zbytočné medziverzie a nenechávaj hotové, schválené PR otvorené iba kvôli opakovanému žiadaniu.
3. **Žiadne neautorizované rozšírenie.** Test-only/draft, nová neschválená funkcia, zmena schválenej grafiky, neoverená licencia, zásah do súkromných dát, mazaní/zálohovaní či zmena autentifikácie nesmú byť ticho považované za schválené na produkciu. V týchto prípadoch si vyžiadaj jedno nové konkrétne schválenie.
4. **Povinné stop-podmienky.** Zlyhané alebo neúplné CI, zmena očakávaného SHA, nejasná identita artefaktu, konflikt vetvy, nedostatočné oprávnenia, bezpečnostná chyba alebo neoverená publikácia blokujú merge/vydanie. Skutočný stav a blokáciu zapíš; nikdy netvrď, že automatický merge či release prebehol, ak nie je doložený na GitHube.
5. **Trvalé odovzdanie.** Každý nový chat/Work načíta tieto pravidlá, aktuálny `main`, otvorené PR, CI, posledné vydanie a projektový register. Pokračuj od posledného overeného kroku a dokonči už schválenú prácu bez návratu na staré opakované schvaľovanie. Zachovaj používateľské súbory, existujúce schválené picony a históriu.

Toto je záväzné pravidlo práce vo všetkých repozitároch; **samo vloženie tohto textu nespúšťa GitHub automatizáciu**. Ak chýba mechanizmus automatického vykonania, odlíš pripravenú politiku od reálne aktivovaného workflowu.


Tieto bezpečnostné pravidlá dopĺňajú existujúcu dokumentáciu projektu a chránia produkčné súbory. Rozsah úloh a vlastníctvo príslušných komponentov zostávajú nezmenené.

## Bezpečnosť GitHub prístupu, autentifikácie a nahrávania

- Na všetky projektové repozitáre používaj iba už schválené a autorizované GitHub pripojenia a podporované operácie. Bez výslovného predchádzajúceho súhlasu vlastníka nemeň spôsob autentifikácie, neprechádzaj na nové webové prihlasovanie, nevytváraj tokeny a nežiadaj heslá, jednorazové 2FA kódy ani iné prihlasovacie tajomstvá.
- Ak narazíš na obmedzenie prenosu veľkých alebo binárnych súborov, zastav len dotknutý prenos, zaznamenaj presnú príčinu, chybu a možné bezpečné riešenia. Nový spôsob prihlasovania či prenosu vyžaduje predchádzajúce výslovné schválenie vlastníka. Bežné technické rozhodnutia v rámci už povoleného spojenia môžu pokračovať.
- Neopakuj bez konca zlyhávajúce Base64 uploady ani autentifikačné pokusy. Ak nie je dostupný bezpečný schválený prenos, zachovaj existujúce výsledky a jasne odlíš lokálne pripravené archívy od skutočne nahraných a overených súborov.
- Pracuj na oddelených vetvách a pred každým zásahom over cieľovú vetvu, SHA-256 a integritu už schválených súborov. Nečakaná zmena hashov je blokácia, nie dôvod na automatické prepísanie. Produkčné zlúčenie a publikovanie vyžadujú preukázateľný súhlas s daným rozsahom; už udelený súhlas sa pri technickom dokončovaní neopakuje (pozri trvalé pravidlo vyššie).
- Po každej bezpečne dokončenej dávke ulož overiteľný commit a aktualizuj príslušný projektový register s presným SHA, rozsahom testov, stavom uploadu a zostávajúcimi nespracovanými výstupmi. Bez overenia vzdialeného súboru a hashov netvrď, že upload bol úspešný.

## Technické vykonanie automatického zlúčenia

- Pripravený workflow `.github/workflows/warder-approved-scope-auto-merge.yml` automaticky vyhodnocuje otvorené PR po dokončení relevantného CI, po schvaľovacom komentári a dennou bezpečnostnou kontrolou.
- Po **existujúcom výslovnom schválení konkrétneho rozsahu** doplň na dotknutý PR komentár z autorizovaného účtu vlastníka `Evolution-by-Warder` obsahujúci presne jediný riadok `<!-- WARDER_APPROVED_SCOPE_SHA:<aktualny-40-znakovy-HEAD-SHA> -->`. Ide o technický záznam už udeleného súhlasu, **nie dôvod znovu sa pýtať používateľa**. Po ďalšom commite najprv skontroluj, či je stále v povolenom rozsahu, a potom obnov schvaľovací SHA marker bez novej otázky.
- Workflow zlúči iba nedraftový PR z toho istého repozitára do `main`, po úspechu CI, bez konfliktov a s presne zhodným SHA; ochrany vetvy sa nikdy neobchádzajú. **Bez úspešného CI sa nič automaticky nezlučuje.** Zmeny `AGENTS.md` a `.github/workflows/` zostávajú zámerne pod manuálnou bezpečnostnou kontrolou.
- GitHub zlučovanie samo nevydáva IPK ani nemení produkčný aktualizátor; po merge musí schválený a úspešný projektový vydávací workflow urobiť vlastnú kontrolu oficiálneho artefaktu a až potom publikáciu. Ak publishing nie je automatizovaný alebo zlyhal, hlás to ako blokáciu, nie ako dokončené vydanie.

## Povinná synchronizácia oficiálneho webu pri každom vydaní (25. 11. 2026)

Vlastník výslovne nariadil pre všetky súčasné aj budúce projekty Evolution-by-Warder: **každé nové schválené a overené stabilné vydanie skinu/pluginu musí v tom istom vydávacom cykle aktualizovať aj https://warder-evolution.eu/.** Ide o povinný dokončovací krok, nie voliteľnú úlohu na neskôr. Súhlas s vydaním zahŕňa synchronizáciu v jeho rozsahu bez opakovaného schvaľovania.

- Over skutočne publikovaný stabilný GitHub release, tag, verziu, IPK, dostupnosť a kontrolný súčet artefaktu. Test-only, draft, prerelease a neoverené buildy neuvádzaj ako stabilné.
- V centrálnom repozitári YouTube-Warder-Evolution aktualizuj `docs/index.html` a produktový detail: verziu, status, priame odkazy na IPK a release notes, dátum overenia, popis zmien, funkcie, kompatibilitu, jazykovú podporu a ostatné reálne zmenené údaje vo všetkých štyroch jazykoch SK/EN/DE/RU. Pri dátových aktualizáciách bez nového IPK aktualizuj dotknuté verejné údaje, ak sa zmenili. Zachovaj nedotknuté produkty, grafiku, galérie a právne/autentifikačné stránky. Informačná bublina planéty preberá existujúci obsah detailu, nie duplicitné údaje.
- Pracuj cez webový PR z aktuálneho main, koordinuj súbežné zmeny. Po úspešnom webovom CI zlúč, over úspešné GitHub Pages nasadenie a správnu verejnú verziu a odkazy. Nedostupné verejné overenie či zlyhanie nasadenia zapíš ako blokáciu.
- V projektovom registri a webovej dokumentácii eviduj release/tag, webový PR/commit, testy a nasadenie. Vydanie neoznač za kompletne dokončené, kým nie je synchronizácia webu overená. Pri blokácii rozlišuj vydaný plugin od neaktualizovaného webu. Pri novom projekte doplň katalóg a detail s planétou podľa dokumentácie.
- Platí aj pre automatizované vydania. Samotný zápis pravidla nie je automatický cross-repository trigger; kým taký mechanizmus nie je preukázateľne zavedený, vykonáva synchronizáciu zodpovedný release Work/agent. Existujúce CI, bezpečnostné stop-podmienky a pravidlá autentifikácie zostávajú záväzné.

Centrálne pokyny: [WEBSITE-RELEASE-POLICY.md](https://github.com/Evolution-by-Warder/YouTube-Warder-Evolution/blob/main/WEBSITE-RELEASE-POLICY.md), [zdroj webu](https://github.com/Evolution-by-Warder/YouTube-Warder-Evolution/tree/main/docs), [dokumentácia animácie](https://github.com/Evolution-by-Warder/YouTube-Warder-Evolution/blob/main/docs/WEBSITE-ORBIT.md).

Pre tento projekt: `docs/piconhub.html` v centrálnom webovom repozitári.
