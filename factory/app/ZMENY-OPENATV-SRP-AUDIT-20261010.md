# OpenATV SRP audit – 2026-10-10

- Rozlíšenie SRP a UTF8SNP podľa názvu feed balíka.
- Diagnostika počtu balíkov oboch rodín v GUI logu.
- Ak je index feedu nezmenený, overuje sa aj prítomnosť lokálne extrahovaných dát každého balíka.
- Pri chýbajúcom archíve alebo extrakcii sa vykoná opätovný bezpečný import.
- Nepriraďuje sa neoverené Warder ID a nemení sa produkčný GitHub.
- Bez aktuálneho sieťového feedu sa nedá tvrdiť, či je SRP balík v danej chvíli dostupný.
