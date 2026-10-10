# Publikačná brána – vynútenie vylúčenia prázdnych PNG

`publication_gate.plan_publication(..., exclusion_manifest=...)` teraz odmieta kandidátov, ktorých cesta je uvedená v manifeste `publication-exclusions-*.json`. Kontroluje schému, SHA-256, počet a presnú väzbu všetkých troch variantov na výstupný koreň. Pri chýbajúcom, poškodenom alebo cudzom manifeste skončí výnimkou namiesto tichého povolenia.

Toto je bezpečnostná podmienka pri plánovaní publikácie; plánovač stále nevykonáva Git ani sieťové zápisy. Volajúci musí explicitne odovzdať aktuálny manifest ako `exclusion_manifest`. Samotná aplikácia zatiaľ automaticky nepublikuje.
