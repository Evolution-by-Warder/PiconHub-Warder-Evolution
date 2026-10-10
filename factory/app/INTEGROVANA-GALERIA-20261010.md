# Integrovaná galéria – pracovná implementácia

- Hlavné okno používa horizontálny posuvný Panedwindow (log 45 %, galéria 55 %).
- Galéria je posúvateľná, dávka 10 položiek, filtrovanie podľa pracovnej fronty.
- Každá položka zobrazuje transparentný (iba referenčný), čierny a biely náhľad zo spracovaného výstupu podľa SHA.
- OK / Beriem zapisuje existujúci stav APPROVED_FOR_REVIEW: nie je to publikovanie ani automatické prijatie do Master.
- Opraviť povoľuje len black/white, vyžaduje poznámku, ukladá DEFERRED s prefixom REPAIR_REQUESTED. Samotná oprava obrázka zatiaľ nie je implementovaná.
- Preskočiť zapisuje DEFERRED.
- Bez priameho prepisu originálov a bez produkčného GitHub zápisu.
- Upozornenie: skupinové položky s viacerými SHA aktuálne ukazujú prvý dostupný digest; pred finálnym schvaľovaním celej skupiny bude potrebný výber jednotlivých kandidátov.
- Reálny test na Windows GUI ešte neprebehol.
