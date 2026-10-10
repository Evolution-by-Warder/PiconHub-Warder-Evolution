# Automatické upratovanie pri štarte

Pri každom vytvorení Factory motora sa pred synchronizáciou zdrojov spustí bezpečné upratovanie priečinka `08-REPORTS`.

- Ponechá posledné **3 behy** podľa identifikátora behu; staršie generované JSON reporty odstráni.
- Rozpoznáva len reporty s presnými názvami generovanými engine.py: `warder-master-index`, `identity-collisions`, `registry-matches`, `qa`, `empty-source`, `publication-exclusions`, `review-queue`, `integrity`, `report`.
- Nedotkne sa neznámych súborov, podpriečinkov, symlinkov, `.log` súborov, zdrojových ZIP/PNG, databázy, cache, rozhodnutí, originálov a výsledných piconov.
- Neúspešné vymazanie zaznamená do GUI a nezastaví spracovanie.
- Pri ďalšom behu ostanú zachované reporty posledných 3 predchádzajúcich behov; práve vznikajúci nový beh sa pridá, a najstarší sa vyčistí pri ďalšom štarte.

Poznámka: Zámerne sa nemažú neidentifikované logy ani JSON mimo `08-REPORTS`, pretože môžu obsahovať rozhodnutia a dôležitý stav.
