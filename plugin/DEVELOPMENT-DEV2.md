# PiconHub Warder Evolution 0.1.0-dev2

Vývojové IPK pre prvú skúšku na Enigma2 s Python 3.9+; cieľ používateľa je OpenATV 8.0.1. Fyzický prijímač nebol v tomto prostredí dostupný, preto nejde o potvrdenú stabilnú verziu.

## Implementované

- Natívna hlavná obrazovka vo štýle Warder, pre Full HD aj HD desktop. Nový grafický podklad obsahuje logo a dekor, ale nie pevný dátum, čas ani verziu. Stredový slogan je odstránený. Hodiny sa obnovujú zo systémového lokálneho času prijímača, verzia z nainštalovaného version.txt.
- Tri pôvodné používateľské profily; zachované konfiguračné kľúče Chocholouska a technický adresár. Každý profil má samostatný režim. Profily sa prepínajú šípkami vľavo/vpravo alebo číslami 1–3.
- OK na každom riadku otvorí malé výberové okno. Satelity umožňujú viacnásobný výber, OK označuje a zelené potvrdí celý výber. EXIT zahodí rozpracovaný výber. Ostatné okná potvrdzuje OK; nastavenia sa potom automaticky uložia.
- Satelitné a poskytovateľské položky sú prevzaté zo skutočného SATLIST skinu. IDs sú oddelené od zobrazovaných názvov a od orbitálnej pozície. Canal+ SK/CZ zostávajú dve voľby. Historický SKYLINK selector sa svojvoľne nepridáva. Pri chýbajúcom balíku sa voľba označí ako zatiaľ nedostupná; sťahovanie neprejde na iný balík.
- Rozlíšenia: 50×30, 220×132, 400×240. Pozadia: Transparent, Biele, Čierne. Cieľové priečinky a štyri aktualizačné režimy zodpovedajú ponukám skinu. Nepodporovaná stará veľkosť sa nepremení potichu na inú.
- Náhľady pozadí sú nezmenené PNG zo skutočných balíkov 45°W. Pôvod a SHA256 eviduje images/PREVIEW-SOURCES.json.
- Aktívny ZIP adaptér používa živý produkčný katalóg FullHDGlass Warder Evolution. Pôvodný Chocholousek zdroj je zachovaný; jeho profily a konfigurácia sa používajú v novom rozhraní. Nový adaptér nepotrebuje 7zip.
- Zachovaná kontrola vydania samotného pluginu pri každom otvorení. Neexistuje plánovač piconov ani tichá inštalácia pluginu. Feed zatiaľ neponúka stabilné IPK.

## Zápis piconov

Celý zvolený plán musí byť dostupný. Najskôr sa overia SHA256 častí aj celého archívu a pripravia potrebné PNG. Chyba sťahovania, prázdny balík, chybný rozmer, konflikt rôznych PNG s rovnakou referenciou či zrušenie prípravy nemenia existujúce picony.

Rozdiely sa porovnávajú podľa obsahu, aj keď majú PNG rovnakú veľkosť. Režimy synchronizácie čítajú skutočné TV/rádio bouquety cez pôvodnú pomocnú logiku skinu. Mazanie je obmedzené na kanálové referencie zvolených orbitálnych pozícií; iné pozície a vlastné pomenované PNG zostávajú. Úplné nahradenie si v rozhraní pýta potvrdenie.

Zápis používa prípravu a zálohu na cieľovom súborovom systéme. Pri chybe súborových operácií sa predchádzajúce súbory obnovia, aj naprieč už zapísanými profilmi. Ak samotná obnova zlyhá, záloha sa nezmaže a chyba uvedie jej umiestnenie. Toto nie je garancia transakcie pri strate napájania; rozpracovaný pracovný priečinok a journal v takom prípade treba skontrolovať.

## Pôvod a balenie

- Základ: s3n0/e2plugins, ChocholousekPicons 5.0.240904; presný ref a blob sú v UPSTREAM.json.
- warder_skin_sync.py je nezmenený helper zo skinu, blob 942fdb51f8fb58217ea9ecd91ab32e7c2d0a0681. Dátový zoznam menu je odvodený z jeho väzieb a aktuálneho txt.py SATLIST. Skin ani jeho produkčné balíky sa týmto nemenia.
- Build cez plugin/tools/build_ipk.py. IPK obsahuje pôvodné aj nové Python zdroje, grafiku, katalóg, devíť skompilovaných prekladov a build.json s revíziou. Nastavenia prijímača ani bytecode sa doň nepribaľujú.
- Identita balíka: enigma2-plugin-extensions-piconhub-warder-evolution. Conflicts/Replaces uvádzajú pôvodný enigma2-plugin-extensions-chocholousek-picons, pretože oba používajú zachovaný technický adresár. Prvý prechod na prijímači treba reálne overiť. Inštalácia sama nereštartuje GUI a neodstraňuje používateľské nastavenia z /etc/enigma2/settings.

## Overenie

54 lokálnych testov: katalóg, aktualizátor pluginu, ovládanie natívnych screen controllerov s testovacími náhradami komponentov Enigmy, menu, zachovanie a potvrdenie výberu, profily, lokalizácia hodín, XML pre HD/FHD, reálne súborové operácie, rollback, poškodené archívy a balenie. IPK sa zostavilo opakovateľne a jeho obsah aj MO preklady prešli kontrolou.

Živá skúška adaptéra stiahla tri malé 45°W balíky, overila ich a zapísala po päť PNG do dočasných priečinkov. Tým sa nemenili zdrojové PNG v repozitároch ani nastavenia používateľovho prijímača.

Pred označením za stabilnú verziu zostáva fyzická skúška obrazoviek, ovládača, prechodu z pôvodného balíka a aktualizácie v OpenATV. Vývojový balík nie je zverejnený v stabilnom aktualizačnom feede.
