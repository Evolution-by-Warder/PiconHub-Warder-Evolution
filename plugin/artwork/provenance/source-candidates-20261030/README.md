# Kandidáti Vhannibal/OpenATV — produkčné dáta 30.10.2026

Na priamy pokyn vlastníka je 10 pomenovaných kandidátov z auditu zapracovaných do spoločného ekosystému FullHDGlass a PiconHub. Testovacie a dátové služby zo širšieho auditu nie sú súčasťou tejto publikácie.

- 10 grafík, 14 overených názvov referenčných PNG.
- Pozície 13°E, 16°E, 19,2°E, 23,5°E a 28,2°E.
- Rozmery 50×30, 220×132, 400×240; pozadia transparentné, biele, čierne.
- 45 aktualizovaných balíkov, 126 pridaných PNG; všetky existujúce PNG zachované.
- Overené plánovačmi skinu a PiconHubu aj skutočným selektívnym inštalátorom skinu.

`source/` zachováva 10 skutočných pôvodných PNG. `artwork/` obsahuje 30 odsúhlasených variantov pre zostavenie. Biele a čierne podklady sú existujúce MASTER šablóny; ich SHA-256 je v pláne. `generate.py` reprodukuje varianty a overuje ich SHA-256, pričom nemá sieťové požiadavky. Grafiky pre 50×30 a 400×240 sa odvodzujú štandardným postupom publikovania so zachovaním alfa kanála.

[Plán a pôvod](publication-plan.json) · [Aktivácia](../../../../reports/source-candidates-activation-20261030.json) · [Spoločná publikácia](https://github.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/blob/main/reports/source-candidates-publication-20261030.json)

Nový IPK nie je potrebný. Aktualizáciu príslušných pozícií stiahnite cez skin alebo PiconHub. Trezor bol vynechaný.
