# OpenATV – presná zhoda dekódovaných pixelov

- Dopĺňa byte-exact SHA-256 o SHA-256 dekódovaných RGBA pixelov vrátane rozmerov.
- Porovnáva iba transparentné Warder Master grafiky.
- Nemení Warder ID ani nepovažuje grafickú zhodu za potvrdenú identitu služby.
- Pri jedinej referencii využíva existujúci EVIDENCE_LINKED mechanizmus; pri konflikte nepriraďuje.
- Ukladá lokálnu cache podľa cesty, veľkosti a mtime; originály nemení.
- Prvý beh môže trvať dlhšie, pretože vytvára pixelové odtlačky master grafík.
- Bez reálneho Windows behu nie je známe, koľko z 33 104 nenamapovaných PNG sa dodatočne prepojí.
- Chocholousek zostáva vypnutý. Žiadne GitHub zápisy.
