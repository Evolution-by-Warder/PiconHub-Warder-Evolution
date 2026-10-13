# Factory temp — anonymizované diagnostické súhrny a review evidence

Tento adresár v existujúcom verejnom repozitári prijíma diagnostiku WARDER PICON FACTORY výhradne na vetve `factory-warder-development`. Vetvy `main` a `warder-master-production` sú zakázané.

Povolené sú allowlistované číselné súhrny a položkové review dôkazy bez obrazových súborov. Položkový export obsahuje stabilné review ID, SHA-256 a dekódované pixel fingerprinty; service reference a source-relative identifikátory sú pred odoslaním pseudonymizované. Bezpečné názvy služieb sa môžu uviesť ako štítky.

Zakázané sú originálne alebo renderované PNG a iné obrazové payloady, absolútne lokálne cesty, názvy používateľských súborov, prihlasovacie údaje, tokeny a osobné údaje. Zdrojové cesty sú exportované iba ako stabilné hashe relatívnych identifikátorov.

Veľké review reporty sa prenášajú ako gzip časti s manifestom. Každá časť a manifest sa po zápise načítajú späť a overia SHA-256. Pri chybe uploadu zostáva report lokálne na neskorší retry bez opätovného skenovania.

Existujúce súbory v `evidence/` sú historické dôkazy; ich pôvod sa musí overiť samostatne. Nová automatická diagnostika PNG nenahráva.

Prístupový token zostáva výhradne na používateľskom počítači v konfigurácii aplikácie; nikdy sa nezapisuje do Git. Odstránenie reportu z aktuálnej vetvy neodstráni historické Git commity.
