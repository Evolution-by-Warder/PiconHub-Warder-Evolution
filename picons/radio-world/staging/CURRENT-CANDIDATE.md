# Warder Radio – overený pracovný kandidát cez dávku 71

10. 11. 2026. Draft PR #68, bez produkčného merge. Posledný balíkový/auditný checkpoint: b80b30129ad573ded8e65e57382e14324d411159.

**Pokrytie 3417/35560; zostáva32143. Celkom31329 PNG;131/219 krajín (12úplných,119čiastočných,88nedostupných).**

| Dávka | Referencie | PNG | ZIP verzie | Krajiny | Auditný checkpoint | CI |
|---|---:|---:|---:|---|---|---|
|68|3|27|9|GR|c57063bb2e973fede6d67f7c2f24adceec9d4538|42787430798|
|69|2|18|18|DE,US|41d157b34358747286c09860e8cc29e9d37262a3|42788450468|
|70|2|18|18|MX,US|59380d8ad18b6d97aac79ce4a52892611a95a57e|42789099579|
|71|5|45|27|GH,GR,ZA|b80b30129ad573ded8e65e57382e14324d411159|42789977608|

Spolu12 referencií,108 PNG,72 immutable ZIP verzií v6krajinách. Každá dávka má jeden úspešný záverečný nezávislý audit skutočných ZIPov: SHA256/CRC/členské hashe/rozmery/RGBA/Gitblob. Každý nový PNG je byte-identická kópia schváleného originálu vrátane alfy;0renderov. Všetkých10332 produkčných a všetky staršie kandidátske PNG zachované.923 konfiguračných aj historické source/render holdy bez výnimky. Downloader dotknutých krajín PASS;fyzický prijímač netestovaný.

Index: `batch-71-reviewed/countries.proposed.json`. Payload f43e772dfdda7129ca17ece5b44a081c84c054a9;manifest ae5d198690d2fa671d0c613c8194eace24ca2977. Audit: `batch-71-reviewed/results/independent-postwrite-audit.json`.

Identity68:explicitné Live24 player konfigurácie aCNAME;69:presná cesta Hessen aoficiálne aNONradio porty;70:nové explicitné streamové presmerovania Crystal/KZPS;71:presné pomenované endpointy Nhyira/Groot aoficiálne Radiojar player mappingy Voice/Stokokkino. Pri71 sa query hodnoty neukladajú; presná katalógová URL je viazaná SHA256 a referenciou. Generické ICY ani spoločná IP samostatne nestačili.

Prvý návrh69 s tokenizovanými URL odmietla automatická kontrola; použité bezpečné metadáta bez tokenov. Dávka71 mala jedno prebuild zlyhanie na doslovnej URL kontrole, ešte pred vytvorenímZIPov. Opravený iba dávkový importer na kontrolu presného SHA256 pôvodnej URL; pokračovalo sa z uložených a overených45PNG bez opakovania zdrojového kroku. Záverečný nezávislý audit prebehol raz aPASS.

## Pokračovanie dávkou 72

`batch-71-reviewed/results/next-source-observations.json` obsahuje58 neprijatých porovnaní/54jedinečných referencií z nového scan70 aodkaz na36 starších nevyriešených porovnaní. Zoznamy sa môžu prekrývať; nesčítavať ich ako počet chýbajúcich staníc. Nové porovnanie pokrylo pomenované konečné streamové cesty voči schválenému inventáru; nie je to úplné preskúmanie32143 zostávajúcich referencií.

V tomto preskúmanom výbere nie je ďalší potvrdený alias pripravený na prijatie. Potrebné sú nové publisher/account väzby, napr.Restauracion mp3_320/mp3_64,Ble port8006/8004,Horeb8100, alebo ďalšia nezávislá skupina z inventára. Neopakovať zaznamenané negatívne požiadavky bez nového dôkazu. Qingting20500112/5009 vracali neočakávané údaje inej stanice,res_id1498; neprijaté.

Dávky57–71 sú uzavreté; neobnovovať ich ani opakovať ich audity. Main,produkcia,stabilný downloader,feedy,IPK,skin aSAT zostávajú nezmenené. História je v RADIO_PROGRESS.md na existujúcej pracovnej vetve Radio-Warder-Evolution. Žiadny merge.
