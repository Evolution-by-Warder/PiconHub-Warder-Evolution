# WARDER PICON FACTORY – integrácia aktivácie a rollbacku

- `factory_update_transaction.py`: explicitná autorizácia aktivácie, trvalý záznam rozpracovanej aktualizácie, potvrdenie alebo rollback, ochrana pred stratou starej verzie.
- `factory_launcher.py`: skutočné spustenie procesu, čakanie na GUI heartbeat, timeout, ukončenie chybného procesu a obnova pôvodnej aplikácie.
- `engine.py`: GUI heartbeat až po inicializácii Tk okna; nie len po štarte procesu.
- `test_factory_update_transaction.py`: testy autorizácie, potvrdenia, rollbacku, opakovanej transakcie a chýbajúcej starej verzie.

## Obmedzenia

Online autoupdate zatiaľ nie je end-to-end zapojený: samotná prítomnosť stage nie je oprávnením na inštaláciu; chýba dôveryhodný release manifest, sťahovanie a integrácia do launchera. Nie je implementovaný single-instance lock ani reálny Windows integračný test. Nejde o produkčný inštalátor. GitHub nebol zmenený.
