# OpenATV artwork evidence — 2026-10-09

- Pri UNMAPPED sa do reportu uchováva `candidate_sha256`.
- Pri každom UNMAPPED sa vyhľadá presná SHA-256 zhoda s transparentným Warder Master obrázkom.
- Stav: `EXACT_ARTWORK_SINGLE_MASTER_REF`, `EXACT_ARTWORK_MULTIPLE_MASTER_REFS`, `NO_EXACT_MASTER_ARTWORK`.
- `identity_verified` zostáva `false`; `service_reference` zostáva `null`. Grafická zhoda nie je identita služby.
- Súhrn v `registry-matches-*.json` -> `artwork_evidence_counts` a v GUI logu.
- Testy: `python -m unittest discover -q` (123/123).
- Neoverené na lokálnych OpenATV PNG z Windows; nové výsledky budú známe až pri ďalšom behu.
- Chocholousek zostáva vypnutý. Žiadny produkčný GitHub zápis.
