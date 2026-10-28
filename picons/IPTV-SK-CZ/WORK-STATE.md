# Stav 28. októbra 2026

Dáta sú v produkčnej main: 321 položiek bouquetu (88 SK, 233 CZ), audio vzorky pre 286 vybraných URL; picony 213 položiek / 229 referencií × 9 variantov. 108 položiek zatiaľ bez vhodného overeného piconu.

PiconHub 0.1.30 je produkčné vydanie. Zdroj 2338498bb1bde99d921cf2ccf1f237730bea5c27, publikačné CI 40686906248, povýšenie 40687527676. 191 testov, verejné IPK overené, všetkých 9 živých IPTV variantov reálne nainštalovaných do dočasných priečinkov so zachovaním nesúvisiacich súborov.

FullHDGlass 1.0.36 je vydaný a aktívny v update-production.json. Zdroj e672afb9cf46ab61e8ee154ecf618b22e235c861; úplné CI 40687770330 úspešné. Verejné IPK má 14 271 200 bajtov, SHA256 e2a7e43c6cb7fe129c12f7c3bb511bbbdfd2a075ac051ad708adaec29a7d811c. Deväť spoločných modulov v oboch verejných IPK je bajtovo identických. Dokumentácia a continuity sú aktualizované v oboch produkčných repozitároch.

Príprava použila oficiálne alebo vlastníkom schválené logá a zmrazené MASTER podklady. Lifetrance a FreeRaveCZ sú vylúčené pre nevhodný podklad; Relaxace – Moře je vylúčená pre nezhodu SHA 400×240 white s kontrolným záznamom. Kontrolný SHA sa nesmie len prepísať aktuálnymi bajtmi. Radio66 a FreeRadio opravené.

Tento pracovný strom uchováva produkčné recepty a dôkazy. Duplicitné prototypy runtime/current a runtime/patched sa do main neprenášajú. Skutočný runtime je len v plugin/src, presná kópia v skine má SOURCE.json.

Pri ďalšej práci brať skutočný aktuálny runtime z produkčných vetiev, nie z historických runtime/current a runtime/patched v tomto pracovnom kontrolnom bode. Chýbajúcich 108 piconov nedeklarovať ako dokončených.
