# Porovnanie piconov — 30.10.2026

Porovnaných všetkých 45 aktuálnych satelitných balíkov 220×132 transparent; kontrola veľkosti a SHA-256 každého archívu. Vhannibal: picony a setting **30.10.2026**. OpenATV/OE-Alliance feed: **28.10.2026**. [Podrobný záznam](picon-source-comparison-20261030.json).

| Výsledok | Vhannibal | OpenATV/OE-Alliance |
|---|---:|---:|
| PNG referencie v zdrojovom balíku | 14 056 | 30 176 |
| Chýbajúce služby po odfiltrovaní typu služby a overení v dnešnom settingu Vhannibal | 841 | 85 |
| Referencie mimo dnešného settingu, nevydávané za aktuálne novinky | 411 | 4 026 |

Všetkých 85 aktuálnych chýbajúcich služieb z OpenATV je aj v rozdiele Vhannibal. Spoločný počet je teda **841 priradení**, nie 926. Nie je to počet nových staníc či nových grafík. Časť tvoria testy, dátové služby a ďalšie referencie už známych staníc; pri 325 priradeniach Vhannibal sa zhoduje názov alebo kľúč loga so známou službou. Zvyšok je zoznam kandidátov na ručné preverenie, nie potvrdených rebrandov.

Praktické príklady chýbajúcich priradení s overeným názvom a dostupným obrázkom:

| Pozícia | Stanica v dnešnom settingu |
|---|---|
| 23,5°E | TVGE Internacional |
| 28,2°E | Disney+CineHD — grafika Disney Cinema |
| 19,2°E | CANAL+FOOT UHD HDR, RMC SPORT 1, volksmusik.tv |
| 13°E | Sky Voices, TV5 Monde Info, TBN Rus |
| 16°E | Klan Nostalgji, Aurora TV |

Na 23,5°E je 31 chýbajúcich priradení: 16 označených Test, 12 DSNS Informed a 3 ďalšie služby (Belarus Tomorrow, SBN International a TVGE Internacional). Tento výsledok sa nesmie interpretovať ako 31 nových programových log.

Odlišný vzhľad, rozmer či kompresia PNG nie sú dôkazom zmeny loga. Túto časť treba posúdiť vizuálne pri jednotlivých návrhoch. Existujúce schválené obrázky, balíky, aktualizátory a automatizácie neboli týmto auditom menené. Trezor bol vynechaný.
