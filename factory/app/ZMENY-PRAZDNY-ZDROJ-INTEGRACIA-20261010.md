# Integrácia prázdneho zdroja – 2026-10-10

- engine.py volá empty_source_report po QA a vytvára empty-source-<run>.json.
- Vytvára publication-exclusions-<run>.json so SHA a tromi cestami variantov.
- Pôvodné PNG a výstupné varianty sa nemažú ani nemenia.
- Tento manifest nie je samostatná publikačná brána: každý budúci export/publisher ho musí vynucovať.
- Neznáme rovnomenné grafiky sa nepoužívajú ako automatická náhrada.
- Lokálne unittest discover: 142 testov OK. Reálny Windows beh zatiaľ neoverený.
