# Radio world – dávka 99: odovzdanie a pokračovanie

**Stav:** dôkazy uložené, PNG/ZIP 0. Tento súbor **nie je** označením dokončenia dávky.

## Nemeniť dokončenú dávku 98
- Dokončený audit PASS: https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/actions/runs/43280430436
- Posledný potvrdený checkpoint: `9dae1dcb2ac13326cba9e6e35d8dda1a8191b2bc`
- Krajinský baseline: `picons/radio-world/staging/batch-98-reviewed/countries.proposed.json`
- Commit manifestov: `cae0fa53fb1e0bf13861abe4baab9dbf729d89ac`
- Pokrytie: **4 077 / 35 560**, otvorených **31 483**, **37 269 PNG**, **136 / 219** krajín. Od dávky 98 pribudlo 21 referencií, 189 PNG, 27 ZIP.
- PR #68 je Draft: **neprepínať na main, nemergovať ani nepridávať nevysledovateľné zmeny do produkcie**.

## Prehľad dávky 99
Autoritatívne záznamy a SHA256 originálov sú v `official-source-evidence.json`.

**Dva overené kandidáty na vyhotovenie deviatich variantov na referenciu:**
1. City FM 89 (Pakistan), referencia `4097:0:2:6921:C93B:ED:0:0:0:0`. Oficiálny originál `https://cityfm89.com/wp-content/uploads/2024/04/89logo.png`, SHA256 `093346134c24ac64c63b37e302a2e1badf95393c53eef2bf18ddfd9110643acf` (89×118 PNG).
2. Биринчи Радио (Kyrgyzstan), referencia `4097:0:2:B409:A36F:ED:0:0:0:0`. Oficiálny originál `https://utrk.kg/img/radio/bir.jpg`, SHA256 `ae9a5f453bfdee9cd05599334c42fbf7a247d017d2e443bf58c969608fc74741` (1205×693 JPEG).

**Odložené:** deväť položiek bez potvrdenej grafiky a dva konflikty identity (Bahawalpur MW vs FM 93 Lahore; Fm.94.4 vs Saut-ul-Quran). Nespájať bez nového nezávislého dôkazu.

## Bezprostredná práca
1. Stiahnuť dva existujúce overené originály; striktne skontrolovať dĺžku, SHA256, rozmery, identitu a platnú grafiku. Pri 403 použiť výhradne pôvodný potvrdený zdroj / dôkaz a uložený blob; nepoužívať náhodnú podobnú grafiku.
2. Vyrobiť **18 PNG** (2 referencie × 3 rozmery × 3 farebné varianty) podľa aktuálneho schváleného renderera a oficiálnych pozadí projektu. Skontrolovať alfa kanál a kontrast.
3. Opatrne doplniť príslušné krajinské/providero vé balíky (ZIP) a manifesty, nikdy neprepisovať existujúce schválené položky; zachovať všetkých 37 269 pôvodných PNG a všetky chránené archívy.
4. Spraviť nezávislý audit spätného stiahnutia: PNG SHA256, varianty/rozmery/RGBA, ZIP CRC a inventár, SHA256 archívov, presné referencie, manifesty, bitovú ochranu starých súborov a downloader replay.
5. Každú úspešnú poddávku uložiť na pracovnú vetvu, zapísať presný commit a nové počty do `WARDER_PROGRESS.md`, PR #68 nechať Draft až do samostatného schválenia na merge.
6. Pri deviatich otvorených položkách nájsť oficiálne logá viazané na konkrétny stream. Neoverené záznamy odložiť, nie odhadovať.

## Vedľajší backlog, nie prekážka pri piconoch
Návrh Radio by Warder na automatické dohľadávanie log uložený ako [Radio issue #23](https://github.com/Evolution-by-Warder/Radio-Warder-Evolution/issues/23). Radio Browser `favicon` a web favicony používať iba ako kandidátov pre manuálne overenie, **nikdy na automatické prepisovanie schválených piconov**.
