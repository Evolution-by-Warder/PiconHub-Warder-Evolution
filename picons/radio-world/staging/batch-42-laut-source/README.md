# Laut.fm: finálne overená pracovná dávka

Stav: 435 nových schválených referencií v 24 krajinách; 3915 PNG inštancií, 3897 jedinečných PNG blobov a 433 originálnych obrázkov. Produkcia ani chránené existujúce PNG/ZIPy sa nemenili. Krajinské balíky a downloader testy zabezpečuje root po nahratí a pripnutí producer commitu.

Vstup: 1148 presných laut.fm streamových referencií. Vylúčených 224 HDF, 22 už prijatých referencií a 13 predtým hodnotených/odložených referencií. Zostalo 889 nových kandidátov. Oficiálny verejný API kontrakt je zachovaný v api-contract.json; všetkých 889 staníc je zmrazených v 18 presných primárnych batch JSON odpovediach. Individuálne projekcie station-json sú výslovne označené ako odvodené z týchto primárnych odpovedí. Zo zdrojov je dostupných 887 referencií; dva logové endpointy vrátane pôvodnej verzie vracajú 404.

Zdrojová QA je samostatná fáza: 550 source_pass a 339 source_holds. Finálna skutočná revízia všetkých troch pozadí a veľkostí dala 435 approve a 115 ďalších hold. Index558 Seasalt-Radio bol dodatočne opravený na source hold; jeho lokálny pracovný render sa nikdy neprijíma. source_holds.json obsahuje metadata bez vymyslených variantov; rendered_holds.json obsahuje rozhodnutia k skutočne existujúcim pracovným výstupom. Celkom je 454 odložených a 0 čakajúcich kandidátov.

approved-selection.json, approved-assets.json, visual-ledger.json a ready-proof.json sú hlavné výstupy. Oddelené indexové rozsahy QA boli 0–287, 288–575 a 576–888. Všetky schválené PNG boli okrem vizuálnej kontroly overené podľa SHA256, veľkosti, Git blobSHA1, RGBA/rozmerov a presnej pixelovej kompozície celého originálu s nemennými MASTER šablónami. Sekundárna drobná kópia nemusí byť pri50×30 spoľahlivo čitateľná; výstupy s nedostatočne rozpoznateľnou hlavnou identitou ostávajú hold.

## CI reprodukcia a uloženie

Použi Pillow==13.0.0 a samostatný reproduce_laut_on_github.py. Plány producer-plans/producer-plan-001.json až producer-plan-005.json obsahujú 100/100/100/100/35 finálne schválených referencií. Každý plán samostatne pripína repo commit/path/blob/SHA rendereru, verifieru, MASTERov a katalógu, oficiálne externé source URL/SHA/bytes/Gitblob a presných deväť výstupných hashov každej referencie.

```sh
python reproduce_laut_on_github.py --plan producer-plan-001.json --output-root .
```

Výstup je striktne picons/radio-world/staging/batch-42-laut-source/verified-assets/SHA.png a originals/SHA.img, plus chunk selection/proof/plán. Originály sa ukladajú byte-preserve. source_commit zostáva null, kým ho root po commite explicitne nepripne. Nerovnaký existujúci súbor sa nikdy neprepisuje. Nezmenený repo renderer vytvorí iba dočasné utility ZIPy v TemporaryDirectory, ktoré sa nepublikujú. Verejné URI vyžadujú presný hash; pri upstream zmene runner bezpečne zlyhá. Žiadna nová autentifikácia sa nevytvára.

Prvý100refový plán bol reprodukovaný v samostatnom dočasnom adresári: všetkých900 PNG inštancií/882 jedinečných blobov a98 originálov je byte/hash-identických. local-producer-test-proof.json obsahuje nezávislé prehashovanie; local-producer-reproduction-proof-chunk-001.json je stabilná kópia runner proof. Všetkých850 úspešne zmrazených zdrojových súborov zostalo nezmenených.

## Dôkazy a hranice

evidence-bundle.tar.gz je deterministický archív presných primárnych API odpovedí, source admission, všetkých hlasovaní a skutočných9variantových hashov vrátane odložených renderov. evidence-bundle-manifest.json pripína každý člen SHA/bytes. Časy/UID/GID archívu sú nulové. Odložené zdrojové obrázky sa lokálne zachovávajú v originals; do finálneho producer výstupu vstupujú iba433 schválené originály.

Adresár aborted-overlap nie je súčasťou dôkazového balíka, výberu ani uploadu. Jeden nezaregistrovaný súbežný plán bol zastavený; scheduler používa filelock a hotové chunky001/002/003/005/006/007/008 majú551 unikátnych pracovných indexov. Pracovné utility ZIPy ani zdrojové QA nemajú štatút produkčných balíkov.
