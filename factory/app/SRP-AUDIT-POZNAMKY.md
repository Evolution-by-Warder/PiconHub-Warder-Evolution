# OpenATV SRP audit – read-only

Spustite `OVER-SRP-BALIKY.cmd` po rozbaleni projektu. Skript iba cita lokalne IPK a stavovy subor. Ziadne originaly, picony, ani GitHub neupravuje.

Vysledok (po úspešnom preflightu): `D:\WARDER-PICON-FACTORY\08-REPORTS\openatv-srp-archive-audit.json`. Checkpoint je v `00-STATE`; archívy zostávajú v `01-SOURCES`.

`regular_srp` znamena skutocne PNG s referencnym nazvom; `symlink_srp` / `hardlink_srp` znamena odkazy s referencnym nazvom, ktore aktualny importer preskakuje. Tento audit je predpokladom cielenej opravy, nie opravou importera. Ak je pri baliku `present: false`, jeho lokalny archiv chyba. Odkazy sa nesmu slepo nasledovat bez validacie ciela a ochrany pred traversal a cyklami.
