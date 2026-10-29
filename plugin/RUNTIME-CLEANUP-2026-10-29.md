# PiconHub — kontrola prevádzkových zápisov, 29. 10. 2026

Prejdený celý inštalovaný zdrojový runtime: **20 Python modulov**, inštalačné skripty a pomocné procesy. Pre každý modul je uložený SHA256 v sprievodnom JSON zázname. Kontrola zahŕňa výstup do konzoly, súborové logy, atómové zápisy, pracovné priečinky a správanie pri chybe. Vývojové skripty bežiace na PC/CI nie sú diagnostika prijímača.

- Priebeh v tlačidle Log zostáva dostupný, ale iba v RAM: najviac 160 riadkov, každý najviac 1024 znakov; zobrazenie najviac 24000 znakov.
- Odstránené piconhub-picons.log aj staré chocholousekpicons.log; starý priebeh GUI je obmedzený na 24000 znakov.
- Starý runShell číta priamo z procesovej rúry a nepoužíva chocholousekpicons-cmd.log. Bežné konzolové debug výpisy a automatické chyby kontroly aktualizácií sú vypnuté.
- Selektívne rozbaľovanie používa jedinečný dočasný zoznam a finally cleanup. Stage uprace aj neúspešnú inicializáciu.
- Zámok inštalácie, overovací katalóg (aj starý názov id_for_permalinks*.log), posledné picony, nastavenia a zálohy pri neúspešnom rollbacku sú funkčné dáta, nie diagnostický odpad.

Inštalačné kroky odstránia iba presne pomenované vlastné staré logy, ak ide o bežné súbory a nie symbolické odkazy. Neodstraňujú cudzie logy ani všeobecné priečinky. Nastavenia, nainštalované picony a používateľské obrázky zostávajú zachované.

Kandidát je určený na overenie v prijímači. Statická kontrola a simulované Enigma2 rozhrania nepotvrdzujú fyzické správanie na všetkých boxoch. Produkčné aktualizačné feedy zostávajú nezmenené. Žiadne tvrdenie o čistení už bežiaceho prijímača: zmeny sa uplatnia po inštalácii nového balíka.
