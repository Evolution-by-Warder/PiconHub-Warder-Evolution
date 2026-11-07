# Warder Radio – overený pracovný kandidát cez dávku 42

Stav: Draft, bez produkčného merge. Testovaný pracovný commit 736c6afef1ae3085153849b73c8bf2b854e55d7c.
CI: https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/actions/runs/42383316414 (SUCCESS).
Index SHA-256: 8dfc9b924bc2c144997c1333840364ae12a2c7497baa2bcf02a9e9c5ef633d70.

219 krajín: 119 dostupných = 12 úplných + 107 čiastočných; 100 nedostupných.
Pokrytých 2 870 / 35 560 krajinských referencií; zostáva 32 690.
26 406 PNG položiek vrátane aliasov: všetkých 10 332 pôvodných bez zmeny a 16 074 nových viazaných na presné prijaté deväťvariantové SHA.
Úplné: SK, CZ, BT, TD, CX, GG, GW, KI, LR, MS, SM, KM.

Dávka 42 pridáva 435 laut.fm a 6 samostatných krajinských referencií: 441 referencií / 3 969 PNG položiek / 30 krajín / 270 nových ZIPov. Všetky nové referencie majú skutočnú vizuálnu kontrolu deviatich variantov. Originály a hotové PNG sú pripnuté k overeným nemenným zdrojovým commitom. 14 CDN vstupov s inými bajtmi bolo nahradených výlučne pôvodnými zmrazenými súbormi.

15 regresných testov vizuálnej brány v CI prešlo. Plytká Git cache zdrojového produceru bola opravená a má 6 samostatných skutočných Git regresných testov. Všetkých 349 nových predbežných source holds zostáva mimo balíkov a nemá vymyslené PNG fingerprinty. Staré zmiešané MS varianty sú blokované; prijatá kompozícia je rovnaký oficiálny badge na všetkých pozadiach. Farebné WF sa nepremaľuje a ostáva oddelené.

Downloader 0.1.9.2 je nezmenený: replay všetkých 119 dostupných krajín, tri pozadia 220×132, 354 verejných ZIP URL; na pozadie 2 869 presných inštalovaných PNG + 1 zachovaný vlastný picon, 0 zlyhaní, opakovaný beh 0 ZIP požiadaviek. Nastavenia, história, obľúbené a vlastné picony zachované. Fyzický prijímač nebol testovaný.

Inventár 1 062 nemenných URL balíkov všetkých deviatich variantov má uložené SHA-256. Najväčší nový ZIP DE WHITE 400×240 má 59 190 697 bajtov, pod limitom 64 MiB. Existujúce produkčné PNG/ZIP/IPK cesty sa nemenia. Historická vetva work/radio-batch33-legacy-payload-20261106 ostáva zachovaná. PR #67 a #68 sú Draft; žiadne IPK ani produkčné zlúčenie.

Ďalšie primary25/contrast3/Zeno zdrojové dávky majú oddelené pracovné vetvy a nie sú započítané do tohto indexu. Celosvetové pokrytie ešte nie je dokončené.
