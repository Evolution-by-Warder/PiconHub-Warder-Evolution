# Factory temp — diagnostické súhrny

Tento adresár v existujúcom verejnom repozitári prijíma **iba anonymizované JSON súhrny** z WARDER PICON FACTORY. Zápis je povolený len do vetvy `factory-warder-development`, nie do `main` alebo `warder-master-production`.

- Povolené: počty spracovaných súborov, QA úloh a chýb, verzia aplikácie a identifikátor behu.
- Zakázané: PNG, pôvodné logy, absolútne cesty, názvy zdrojových súborov, identifikátory staníc, tokeny a osobné údaje.
- Prístupový token zostáva výhradne na používateľskom počítači v konfigurácii aplikácie; nikdy sa nezapisuje do Git.
- Po spracovaní možno súhrny odstrániť z aktuálnej vetvy. **História Git commitov ich môže naďalej obsahovať**, preto sa anonymizácia vykonáva pred prenosom.
- Ak upload zlyhá, pôvodný report zostáva lokálne na opakovanie.

Lokálne reporty: `D:\WARDER-PICON-FACTORY\08-REPORTS\`.
