# OpenATV triedenie po skupinách bez duplicitných zdrojov

- `openatv_triage.py` vytvára záznam pre každý názov stanice a unikátnu SHA-256 grafiku.
- Opakované kópie z viacerých balíkov sa spočítajú, nie opakovane prezentujú ako nové grafiky.
- Rozlišuje stanice bez dôkazu, s jedným neovereným kandidátom a s konfliktnými kandidátmi.
- Ani presná grafická zhoda, ani názov stanice automaticky neprideľujú service-reference.
- Report `08-REPORTS/openatv-triage-*.json` je oddelený od pôvodných reportov; nič neprepisuje v produkcii.
- Nie je to automatické dokončenie mapovania OpenATV; na overené ID treba autoritatívny service-reference zdroj.
