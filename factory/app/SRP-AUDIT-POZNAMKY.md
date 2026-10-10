# OpenATV SRP audit – read-only

Spustite `OVER-SRP-BALIKY.cmd` po rozbaleni projektu. Skript iba cita lokalne IPK a stavovy subor. Ziadne originaly, picony, ani GitHub neupravuje.

Vysledok: `D:\WARDER-PICONS\08-REPORTS\openatv-srp-archive-audit.json`.

`regular_srp` znamena skutocne PNG s referencnym nazvom; `symlink_srp` / `hardlink_srp` znamena odkazy s referencnym nazvom, ktore aktualny importer preskakuje. Tento audit je predpokladom cielenej opravy, nie opravou importera. Ak je pri baliku `present: false`, jeho lokalny archiv chyba. Odkazy sa nesmu slepo nasledovat bez validacie ciela a ochrany pred traversal a cyklami.
