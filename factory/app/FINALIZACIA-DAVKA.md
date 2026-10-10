# Finalizácia piconov – vývojová dávka

Pridaný `finalize_picons.py` a `test_finalize_picons.py`.

- Finalizácia vyžaduje explicitný stav FINAL_QA_APPROVED; APPROVED_FOR_REVIEW nestačí.
- Overuje oba odvodené PNG (black/white), ich rozmery 220x132, SHA-256 a umiestnenie v 04-WORK/PICONS.
- Kontroluje konflikt existujúcich finálnych PNG a zapisuje do 06-OUTPUT/PICONS.
- Transparentný originál ani pracovné PNG nemaže, GitHub nemení.
- Zatiaľ NIE JE zapojená do tlačidla v galérii. Zatiaľ neexistuje overená finálna QA brána s kontrolou originálnych plastických šablón a kontrastu.
- Testy: python -m unittest -q test_finalize_picons test_review_decisions test_review_gallery
