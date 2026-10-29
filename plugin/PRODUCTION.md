# PiconHub Warder Evolution — ostrá prevádzka

Aktuálna produkčná verzia **0.1.32**, schválená vlastníkom 29.10.2026. Riadna aktualizácia z 0.1.30 aj cleanup kandidáta 0.1.31.

- [Vydanie](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/releases/tag/v0.1.32) · [Presný produkčný záznam](production.json).
- Zdroj: `2dc74563c629cad562c85def4cb5d16ca77bbdc6`.
- IPK: **2879214 bajtov**, SHA256 `28b9e238d5689ddf21a0dfaba075cae89440545093750624ae3628766828dde7`.
- **195 testov** a zostavovacie/publikačné CI **40918594093** prešli. Verejný IPK bol samostatne stiahnutý, overený a je bajtovo zhodný s lokálnym zostavením; verejný feed ponúka tú istú verziu, veľkosť a hash.

Priebeh a chyby zostávajú dostupné v Logu v obmedzenej RAM. Automatické súborové/konzolové diagnostiky sú vypnuté; dočasné súbory sa upracú aj pri chybe. Potrebné rollback zálohy, používateľské nastavenia, nainštalované picony a schválené obrázky zostávajú.

Aktualizačná adresa zostáva `plugin/futuristic-rebuild/plugin/update/stable.json`. Kontrola pri otvorení beží na pozadí; používateľ potvrzuje inštaláciu, po úspechu sa reštartuje GUI. Jazyková podpora SK/CS/EN/DE/PL/HU/RU/FR/IT/ES a pôvodné autorské údaje s3n0/Chocholousek sú zachované.

Autoritatívne aktuálne piconové katalógy a ich zdroje zostávajú v main; produkčné povýšenie ich neprepisuje staršou kópiou vývojovej vetvy. Fyzický test celej verzie 0.1.32 na prijímači sa netvrdí.
