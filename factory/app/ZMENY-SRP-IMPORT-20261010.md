# SRP import – 2026-10-10

- Overené z používateľského auditu: každý SRP balík má 22 983 SRP symlinkov a 7 030 pomenovaných PNG.
- `ipk_import.py`: bezpečne materializuje odkazy na lokálne PNG v rámci archívu, bez vytvárania filesystem symlinkov; odmieta traversal a chýbajúce ciele.
- `engine.py`: kontroluje verziu importu, staré extrakty preimportuje z už stiahnutého IPK; starý extrakt odloží ako `.pre-srp-import`.
- 173 lokálnych unit testov prešlo. Reálny Windows beh a konečný počet SRP ešte nie sú overené.
- Žiadny produkčný GitHub zápis.
