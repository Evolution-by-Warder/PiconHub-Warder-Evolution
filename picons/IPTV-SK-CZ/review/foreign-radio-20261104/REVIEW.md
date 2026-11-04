# Radio Warder picony – overené originály AT/DE (kontrolná dávka 2026-11-04)

**Stav:** IBA vizuálna kontrola, žiadna zmena produkčných ZIP, PiconHubu ani katalógu rádií.

Automatizácia [GitHub Actions run 41888237726](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/actions/runs/41888237726) stiahla dva presne špecifikované originálne SVG, overila ich **originálne SHA-1 z Wikimedia Commons**, uchovala SHA-256 vo výstupoch a vygenerovala 2 × 9 Warder PNG **bez prekreslenia alebo prefarbenia**. Biele a čierne MASTER pozadia sa použili iba po kontrole ich zmrazených SHA-256.

## 1. Antenne Kärnten, Rakúsko

- Referencia: `4097:0:2:45CD:FE8F:EC:0:0:0:0`
- [Warder ukážka (3 štýly)](antenne-kaernten/review-sheet.png)
- Oficiálny pôvod loga: [Wikimedia Commons, Antenne Kärnten 2024](https://commons.wikimedia.org/wiki/File:Antenne_K%C3%A4rnten_logo_(2024).svg), pôvodne zo stránok vysielateľa; originál SVG 7 083 B, SHA-1 `8be6b45cf3ddd85400316e62d58737f2568fca01`.
- Licencia **CC BY-SA 4.0**: [atribúcia a pravidlá](antenne-kaernten/ATTRIBUTION.md). Pre prípadné zverejnenie treba zachovať správne označenie autora, zdroja, úprav a kompatibilnú licenciu pre odvodený výstup.
- Vizuálna kontrola: pôvodná červeno-čierna typografia na žltom poli, správny pomer strán, čitateľné v oboch rámikoch. Pripravený kandidát, ale zatiaľ **bez schválenia produkčnej publikácie**.

## 2. radio3 (rbb), Nemecko

- Referencia: `4097:0:2:C634:62DF:ED:0:0:0:0`
- [Warder ukážka (3 štýly)](radio3-rbb/review-sheet.png)
- Pôvod: [Commons radio3 2024](https://commons.wikimedia.org/wiki/File:Radio_3_Logo_2024.svg), SHA-1 `0b360468e4ee5646a734eace4b8642e58185daf3`. Licencia na Commons: PD-textlogo, ochranná známka môže stále platiť.
- Rádio je naďalej vedené pod týmto názvom na [aktuálnom webe rbb](https://www.rbb-online.de/unternehmen/presse/programmwochen/radio3/).
- **Výsledok vizuálnej kontroly:** šedé písmená „radio“ sú na BLACK masteri príliš tmavé. Nesmie sa automaticky zosvetliť farebné logo ani vytvoriť vlastná verzia bez potvrdenia. **BLACK = REVIEW/BLOCKED**, čaká sa na oficiálnu alternatívu pre tmavé pozadie alebo ďalšie schválenie. Transparent/White sú len kandidáti.

### Alternatíva z oficiálnej stránky rbb – celý originálny obraz

Nové bezpečné **review-only** riešenie je JPG priamo z [aktuálnej oficiálnej stránky rbb](https://www.rbb-online.de/unternehmen/presse/programmwochen/radio3/), ktorý obsahuje úplné logo „radio3 rbb“ aj jeho vlastný tmavozelený podklad.

- [Ukážka 3 štýlov Warder bez prefarbenia](radio3-official-rbb/review-sheet.png)
- Originál: [rbb broadcaster JPG](https://www.rbb-online.de/content/dam/rbb/rbb/unternehmen/presse/presseinformationen/2024/03/radio3_Logo_auf_Hintergrund-1-.jpg.jpg/size=966x543.jpg), 966×543 px, 23 124 B.
- SHA-256: `776d8651a30f1733844c3ddc0f3c37abd27a3aff6c77c45a90648e68b81a54c1`.
- Oficiálny JPG v rámci schválenej proporcionality: 185×104 px, deväť kontrolných PNG v `radio3-official-rbb/artwork/`, inventár SHA256 v [provenance](radio3-official-rbb/provenance.json).
- **Kontrast na BLACK vyriešený iba zmenou na iný originálny zdroj od vysielateľa.** Celé pôvodné logo s vlastným podkladom zostáva bez farebných a typografických zásahov, verzia zo sivého Commons SVG zostáva blokovaná.
- Finálne zaradenie čaká na kontrolu práv na ďalšie šírenie a vizuálne schválenie tejto konkrétnej kompozície. Nejde o publikovaný picon.

## Ďalšie dve stanice z prvej dávky

- **Kossuth Rádió (HU)**: **pozor na neaktuálny zdroj loga.** Vysielateľ oznámil relaunch 24. augusta 2026 a médiá uvádzajú aj novú grafickú identitu. Staré logo z 2024 **nepoužiť**, kým nepreveríme aktuálne originálne grafické podklady. [Oficiálne oznámenie](https://mediaklikk.hu/cikk/2026/08/23/augusztus-24-en-indul-a-megujult-kossuth/).
- **ESKA ROCK (PL)**: vizuálne známe červeno-bielo-čierne značenie, ale kandidát z agregátorov sa nepovažuje za dostatočný originál. Treba oficiálne logo a aktuálny pôvod z [eskarock.pl](https://www.eskarock.pl/).

## Warder štandard a rozhodnutie

Nijaký nový picon nie je produkčne vydaný. Pôvodný rádiový projekt ostáva stabilný. Súbory v `artwork/` slúžia na vizuálny audit a každá kombinácia 50×30 / 220×132 / 400×240 a Transparent / White / Black má svoj SHA-256 v `provenance.json`.

**Nasledujúca brána:** overiť aktuálne logo a licenciu, porovnať všetky tri štýly, rozhodnúť o kontraste BLACK bez prekreslenia originálu, a až potom pripraviť deväť závislých produkčných archívov so zachovaním starých PNG.
