> Development 0.1.0-dev2 now uses the modern Warder screen with this same per-launch checker. A development IPK is built; the stable feed remains empty. Earlier UI/IPK-pending text below is historical. Physical receiver validation remains pending.

# Kontrola aktualizácie samotného pluginu

Stav: implementované v pracovnej vetve, nie otestované na fyzickom prijímači. Moderné obrazovky a inštalačné IPK ešte nie sú dokončené.

## Správanie podľa spresnenia používateľa

Pri každom novom otvorení hlavnej obrazovky sa na pozadí skontroluje manifest vydaní Warder. Neexistuje globálna zábrana, ktorá by ďalšie otvorenia v rovnakej relácii Enigmy preskočila. Obnovenie layoutu už otvorenej obrazovky nevytvorí duplicitnú kontrolu.

Ak existuje novšie zverejnené vydanie, zobrazí sa nainštalovaná a nová verzia, poznámky a ponuka inštalácie. Bez súhlasu sa nič neinštaluje. Automatická kontrola pri chybe siete iba zapíše chybu; neotvára chybové okno a nezatvára plugin. Pri zavretí pluginu sa neskorý výsledok už nezobrazí. Ak je otvorený výberový dialóg, ponuka počká na návrat do hlavnej obrazovky.

Tlačidlo pôvodného ručného aktualizátora používa rovnakú kontrolu Warder. Nepripája sa k upstream inštalačným balíkom s3n0, ktoré by mohli prepísať naše úpravy. Žiadny plánovač, režim autoaktualizácie piconov ani tichá inštalácia neboli pridané.

## Implementácia

- Pôvodný runtime 5.0.240904 a 26 podporných súborov boli importované z s3n0/e2plugins, ref 84a40ed6b01f8dc7d49b632f886525b9c51773c7. Pôvod autora aj technický adresár ChocholousekPicons sú zachované. Podrobnosti sú v runtime súbore UPSTREAM.json.
- mainConfigScreen vytvorí vlastný StartupUpdateCheck. Ten sa spustí po vytvorení layoutu a ukončí zobrazovanie pri zatvorení obrazovky. Sieťová práca beží vo vlákne; GUI pracuje iba cez časovač v hlavnom vlákne.
- warder_update.py overuje manifest, produkt, kanál, poradie verzií a presnú adresu prílohy vydania nášho repozitára. Porovnanie je číselné a rozlišuje vývojovú a stabilnú verziu.
- Po potvrdení sa IPK pripraví v súkromnom dočasnom priečinku, skontroluje sa veľkosť, SHA256 a IPK údaje Package, Version, Architecture. Až potom sa zavolá opkg install bez force/downgrade prepínačov. Chyba správcu balíkov sa nesmie hlásiť ako úspech. Reštart GUI je samostatná používateľská voľba.
- Pôvodné globálne vypnutie kontroly TLS bolo odstránené. Nový aktualizátor používa explicitne overovaný HTTPS kontext. Historické obnovovacie súbory zostávajú nezmenené.

## Vydania

plugin/update/stable.json má aktuálne release: null. Žiadne IPK zatiaľ nie je ponúkané ani publikované. Kontrola nepovažuje nový Git commit za novú inštalovateľnú verziu.

Vývojový manifest sa číta z plugin/futuristic-rebuild. Pri prvom vydaní sa FEED_URL prepne na main a manifest vyplní až po zverejnení overenej prílohy vydania. Identita budúceho balíka je enigma2-plugin-extensions-piconhub-warder-evolution. Prvé balenie a prechod z pôvodného balíka Chocholousek treba overiť samostatne; aktuálna dávka nevydáva nový IPK.

Zachované pôvodné obrazovky sú integračný základ. Nie sú prezentované ako už implementovaný schválený moderný vzhľad. Rovnako pôvodný engine zatiaľ používa svoj zdroj piconov; prepojenie na Warder katalóg/ZIP ešte čaká na implementáciu.

## Overenie

26 lokálnych testov zahŕňa opakované otvorenie, duplicitný layout, pomalú odpoveď po zavretí, vnorený dialóg, výpadok siete, odmietnutie inštalácie, cudzie URL, verzie, poškodené a skrátené stiahnutie, obidva IPK kontajnery, nesprávnu identitu balíka a zlyhanie opkg. Správca balíkov je v testoch nahradený testovacím runnerom; v tomto prostredí sa nič neinštalovalo. Fyzická Enigma2 a reálne vydanie budú ďalšia úroveň overenia.
