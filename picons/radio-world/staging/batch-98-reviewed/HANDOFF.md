# Dávka 98 dokončená

Nezávislý audit **PASS**. Pokrytých je **4 077 z 35 560** referencií, **37 269 PNG** vrátane aliasov a **136 z 219** krajín. Zostáva **31 483** referencií.

Dávka pridala 21 staníc (Curaçao 6, Kirgizsko 3, Lotyšsko 12) a 189 PNG. Z GitHubu bolo obnovených deväť už existujúcich obrazových blobov, ďalších 12 originálov bolo uložených po zhode s pôvodnými SHA-256. Všetky PNG sa zhodujú s uloženými kontrolnými súčtami vizuálnej kontroly a s referenciami v katalógu.

GitHub Actions reprodukoval HTTP 403 pre šesť presných URL na `player.paradisefm.cw`. Päť stiahnutí prešlo s hlavičkami verejného prehrávača a jedno využilo uložený originál. Diagnostika obsahuje názov stanice, referenciu, URL bez parametrov, HTTP stav a očakávaný SHA-256. Pri trvalom zlyhaní zdroja sa stanica odloží a ostatné sa spracujú. [Záznam zdrojov](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/blob/431310bed61e2e1504b41998d1f022f474862f7e/picons/radio-world/staging/batch-98-reviewed/source-recovery.json)

- [Nezávislý beh GitHub Actions](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/actions/runs/43280430436)
- [Audit a 27 kontrolných súčtov ZIPov](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/tree/431310bed61e2e1504b41998d1f022f474862f7e/picons/radio-world/staging/batch-98-reviewed)
- [27 ZIPov](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/commit/cb6c5571d5ad51e677a2aad57c31bd41ebc95bdf) a [tri manifesty](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/commit/cae0fa53fb1e0bf13861abe4baab9dbf729d89ac)

Audit spätného stiahnutia overil SHA-256 a rozmery 21 originálov, SHA-256 a CRC 27 ZIPov, inventáre a referencie, rozmery, RGBA, alfa kanál a presné bajty PNG. V nových ZIPoch zostalo deväť pôvodných PNG bitovo zhodných. Overenie manifestov chránilo všetkých 37 080 položiek predchádzajúceho kandidáta a 31 329 produkčných položiek. Replay downloadera z [Radio PR #21](https://github.com/Evolution-by-Warder/Radio-Warder-Evolution/pull/21) prešiel pri všetkých troch pozadiach 220×132 a zachoval používateľský súbor. Fyzický prijímač sa netestoval.

Z 21 kandidátov dávky zostáva **0**. V dôkazoch je evidovaných ďalších 14 otvorených prípadov mimo tejto sady. Pri 13 chýba jednoznačná väzba na presnú adresu a na adrese Radio Skonto Mūsējie sa teraz uvádza značka SKONTO LV.

[PR #68](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/pull/68) zostáva Draft a otvorený. Produkčný index a stabilné vydania sa nemenili.

## Pokračovanie dávkou 99

Použiť `countries.proposed.json` z dávky 98 a manifestový commit `cae0fa53fb1e0bf13861abe4baab9dbf729d89ac`. Pokračovať oficiálnymi prehrávačmi a zdrojmi s dôkazom presnej adresy streamu. Pri nevyriešených identitách treba nový nezávislý dôkaz vysielateľa.
