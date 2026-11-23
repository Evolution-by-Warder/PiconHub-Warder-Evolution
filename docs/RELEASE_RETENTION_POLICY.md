# PiconHub Warder Evolution — retencia vydaní (23.11.2026)

**Záväzné schválenie vlastníka:** aktuálna ostrá verzia + maximálne tri predchádzajúce ostré verzie. Staršie TEST/RC alebo historické Releases sa odstránia až po overení aktívnych URL, kompatibility starých klientov a bezpečnej obnovy; nikdy nie paušálne podľa dátumu.

## Aktuálne zachované ostré vydania

- `v0.1.45` (aktuálne)
- `v0.1.44`
- `v0.1.43`
- `v0.1.42`

Po vydaní DTT ITALIA sú dostupné štyri ostré vydania. Oba stabilné kanály ponúkajú `v0.1.45` s overeným verejným IPK. V `main` nie sú staré IPK; binárne inštalačné balíky patria pod GitHub Releases. Súbory v `picons/DAB/packages/` sú *dátové picon ZIPy*, nie inštalačné IPK a **nesmú sa zmazať**. Zachovať MASTER V9, WHOLE_COLOURED_LOGO_V2, CANAL+ SK/CZ, SAT manager registre a nespracované review.

## Trvalé bezpečnostné hranice

Vydávací mechanizmus nesmie pridávať opakované historické IPK do `main`. Pred vydaním preveriť existenciu/obsah GitHub Release, feed URL, SHA-256 a opkg identitu; ochranné a produkčné workflowy nie sú dôvod na automatické zmazanie iných dát. Každé odstránenie starého Release/tagu/assetu je samostatná operácia; zachovať potrebné rollbacky a recovery kópie. Nedostatočne overené staršie prechody zostávajú výnimkou. Git história, osobné nastavenia a všetky existujúce zdrojové testy zostávajú.

Jediný spoločný stav: [FullHDGlass/docs/ECOSYSTEM-CLEANUP-CHECKPOINT-20261123.md](https://github.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/blob/main/docs/ECOSYSTEM-CLEANUP-CHECKPOINT-20261123.md).
