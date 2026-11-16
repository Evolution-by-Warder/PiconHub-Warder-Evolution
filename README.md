# PiconHub Warder Evolution

Správca piconov Enigma2 pre OpenATV a OpenPLi.

## Aktuálna stabilná verzia

**PiconHub 0.1.44** – [oficiálne vydanie](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/releases/tag/v0.1.44).

PiconHub spravuje schválené picony pre satelitné pozície, poskytovateľov, DAB/DAB+ a DVB-T CZ/SK. Výber profilu, rozmeru, pozadia a cieľového úložiska určuje, čo sa stiahne. Súbory sa inštalujú s kontrolou SHA-256, zachovaním používateľských piconov a obnoviteľným priebehom.

- Satelitné picony a provideri: tri rozmery (50×30, 220×132, 400×240) a pozadia Transparent, White, Black podľa dostupnosti schválených balíkov.
- DAB/DAB+: vlastný overený katalóg s natívnymi referenciami.
- DVB-T CZ/SK: samostatné overené balíky.
- Štyri oddelené profily s vlastnými nastaveniami; používateľ volí aktívne profily.
- Cieľové úložiská prijímača, HDD/USB a vlastný priečinok, kontrola integrity a aktualizácie.

Satelitné a DAB picony zostávajú zachované. Všetky ďalšie dáta sú uložené mimo samotného IPK.

## Projekt a autorstvo

Pokračovanie Warder Evolution na základe pôvodného PiconHubu a schválených grafických zdrojov. Pôvodné autorstvo zdrojových diel sa zachováva. Zdrojové dáta sa nachádzajú v `picons/`, runtime plugin v `plugin/` a nastavenia vydania v `plugin/PRODUCTION.md`.

## Inštalácia

[Stiahnuť PiconHub 0.1.44](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/releases/download/v0.1.44/enigma2-plugin-extensions-piconhub_0.1.44_all.ipk)

Po inštalácii alebo aktualizácii reštartujte GUI.
