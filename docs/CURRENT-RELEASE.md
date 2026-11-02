# PiconHub 0.1.40

Aktívne ostré vydanie pre OpenPLi a OpenATV.

Spoločná verzia pre OpenPLi a OpenATV. Opravená inštalácia a štart aktualizátora bez modulu dataclasses, overovanie verzií balíkov a prispôsobenie zoznamov v HD/FHD/WQHD/UHD. Zachované sú štyri nezávislé profily, nastavenia, stiahnuté picony a doterajšie úpravy OpenATV 8.1/GLES. Po aktualizácii reštartujte GUI.

[Stiahnuť IPK](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/releases/download/v0.1.40/enigma2-plugin-extensions-piconhub_0.1.40_all.ipk)

SHA-256: `909dd86f2872857ec78f93db5c59bbd4f3cef7200a2a39adaee604d9659a2af9`

Overené verejné bajty, dodané inštalačné kontroly a natívne rozhrania OpenPLi/OpenATV. Úplné fyzické testovanie všetkých modelov a rozlíšení sa netvrdí.

## Text pre web

**PiconHub 0.1.40 – opravy inštalácie, aktualizácií a kompatibility**

Nová ostrá verzia PiconHubu spája posledné opravy pre OpenPLi a OpenATV. Aktualizácia sa zameriava na spoľahlivú konfiguráciu balíka, správne vyhodnocovanie verzií a prispôsobenie používateľského rozhrania rôznym rozlíšeniam.

Hlavné zmeny:

- **Opravená konfigurácia balíka na obrazoch bez modulu `dataclasses`** – aktualizačná časť už tento samostatný modul nevyžaduje.
- **Upravené spracovanie označení verzií**, ktoré odstraňuje problém s hlásením „Invalid plugin version“ pri dotknutých testovacích vydaniach.
- **Úpravy rozloženia obrazoviek a zoznamov** pre HD, Full HD, WQHD a UHD vrátane kompatibility s OpenATV 8.1 a GLES.
- **Zachované štyri nezávislé profily sťahovania** s vlastnými nastaveniami a možnosťou spracovať vybranú kombináciu profilov.
- **Zachované kontroly integrity aktualizácií a nainštalovaných súborov**, ktoré pomáhajú overiť úplnosť balíka a úspešné dokončenie inštalácie.

Aktualizácia zachováva používateľské nastavenia, uložené profily aj stiahnuté picony.

Verzia **0.1.40** je spoločná pre OpenPLi aj OpenATV a je dostupná cez aktualizátor pluginu. Pri prechode zo starej verzie **0.1.32** zostáva potrebná jednorazová ručná inštalácia aktuálneho IPK cez existujúcu inštaláciu, bez odinštalovania pluginu.

**Po aktualizácii reštartujte GUI.**
