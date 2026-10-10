# Plastické WARDER šablóny — integračná dávka

BLACK/WHITE varianty používajú fyzické 220×132 PNG v `templates/picons/` namiesto plochých farieb. Renderer uchováva transparentný pracovný variant a sleduje SHA-256 šablóny pre každú odvodenú variantu. Staré varianty bez signatúry sa pri ďalšom rendri pregenerujú. Chýbajúca šablóna je chyba, nie dôvod na ploché pozadie. Žiadny automatický GitHub zápis ani finálne QA schválenie.

**Zostáva:** prepojiť skutočnú identitu a dôkazy QA na `final_qa_evidence`, zjednotiť opravný renderer a zabezpečiť regeneráciu aj pri nezmenenom zdroji na úrovni plánovača. Balík zatiaľ neinštalovať na Windows.
