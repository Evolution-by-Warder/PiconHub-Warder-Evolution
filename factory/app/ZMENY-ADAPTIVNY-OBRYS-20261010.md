# Adaptívny kontrastný obrys

- Pre viacfarebné logá, kde nemožno bezpečne prefarbiť originál, sa skúša 2-, 3- a 4-pixelový vonkajší obrys.
- Po každom pokuse sa overí viditeľnosť obrysu rovnakým kritériom ako QA.
- Ak sa obrys nedá bezpečne overiť, výsledok sa neprepíše a problém sa ponechá na kontrolu.
- Transparentný variant a zdrojové PNG sa nemenia. Existujúce zálohovanie variantov zostáva zachované.
- Testy overujú zachovanie farieb aj úplne prázdne transparentné zdroje.
- Reálny výsledok na dvoch zostávajúcich kontrastných variantoch ešte nie je potvrdený.
