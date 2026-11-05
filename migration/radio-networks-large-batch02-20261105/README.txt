WARDER · VEĽKÁ RÁDIOVÁ DÁVKA 02 · PLUGIN RADIO
5. november 2026

129 grafických podkladov, 147 nových servisných referencií, 1 323 piconov PNG.
Každá referencia: 50×30, 220×132, 400×240; Transparent, White, Black.
V rámci dávky ide o 1 161 odlišných grafických variantov. Formáty a regionálne
referencie môžu používať rovnakú grafiku pod rôznymi názvami súborov.

ROZSAH: GRAFIKY / REFERENCIE / PNG
80s80s: 18 / 18 / 162
90s90s: 17 / 23 / 207
bigFM: 25 / 26 / 234
RPR1.: 37 / 38 / 342
R.SA: 4 / 5 / 45
Rockland Radio: 1 / 5 / 45
RADIO BOB! doplnenie: 27 / 32 / 288
Zo 129 grafík je 114 nových na vizuálnu kontrolu a 15 grafík BOB! je prevzatých
presne z predchádzajúcej schválenej dávky. Všetkých 147 referencií je mimo nej.

IDENTITA A ZDROJE
Zdrojové stránky, ich kontrolné súčty a presné adresy jednotlivých obrázkov sú
v reprodukcia/source-plan.json. Zmrazené stránky a odvodené programové registre
sú v reprodukcia/evidence/. Zoznamy pochádzajú priamo zo streamových domén
80s80s, 90s90s, bigFM, RPR1., R.SA, RADIO PSR, Rockland Radio a RADIO BOB!.
Overený je hostiteľ, programová cesta a kodek-bitrate. Ďalšia časť cesty označuje
prehrávač alebo agregátor a nie je novou programovou identitou. Pôvodné názvy,
adresy a referencie v katalógu sa neprepisovali.
Pri bigFM a RPR1. je programová grafika priamo priradená k streamu v dátach
aktuálneho oficiálneho prehrávača. Tieto podklady obsahujú vlastné nápisy.
Pri 80s80s, 90s90s a R.SA sú použité kompletné logá z oficiálnych streamových
zoznamov. Samotné fotografické pozadia či farebné vzory sa nevydávajú za logá.
RADIO PSR a ďalšie položky bez úplného overeného loga zostávajú na preverenie.

ROCKLAND RADIO
Päť regionálnych referencií používa spoločné pôvodné firemné logo z oficiálnej
stránky vysielateľa. Zdrojové SVG je priložené spolu s jeho zmrazeným PNG
prevodom cez Inkscape 1.2.2 s exportnou šírkou 1200. Pôvodný pomer strán,
žlté pozadie, čierne plochy a nápisy zostali zachované. Regionálne nápisy sa
nevymýšľali. Presná väzba SVG/PNG a kontrolné súčty sú zaznamenané v evidence/.
Offline overenie používa priložený zmrazený PNG prevod a overí aj pôvodné SVG.

UPRESNENIE PREDCHÁDZAJÚCEJ KONTROLY BOB!
Predchádzajúci výber porovnával aj tretiu časť cesty a časť odložených položiek
opísal ako chýbajúci formát. Táto časť však označuje prehrávač, nie kodek.
Správne porovnanie hostiteľa a prvých dvoch častí cesty potvrdilo ďalších
32 referencií. Sú zahrnuté tu ako samostatné doplnenie. Predchádzajúci schválený
ZIP, jeho picony a kontrolné súčty sa nemenili ani nepočítali znova.
Presné opravené odôvodnenie je v evidence/bob-player-suffix-correction.json.

VYLÚČENÉ POLOŽKY
44 položiek so zhodnou cestou zostalo mimo dávky pre rozporné katalógové názvy,
poškodenú cestu alebo chýbajúce kompletné logo. Neoverené historické domény,
nepriradené upstream adresy a nezhodné cesty sa automaticky neprepisovali.

GRAFIKA A KONTROLA
Celé pôvodné grafiky vrátane fotografií, nápisov, farieb, pozadí a alfa kanála
sú iba pomerne zmenšené a vycentrované. Transparentný variant neodstraňuje plné
pozadie originálu. White a Black používajú pôvodné Warder šablóny overené SHA-256.
Overené sú všetky rozmery, RGBA, úplnosť deviatich variantov na referenciu,
kontrolné súčty a pixely šablón mimo vloženého podkladu. Pri čiastočne
priehľadných podkladoch sa overuje aj správne alfa zloženie.
Všetkých 1 323 PNG sa podarilo znovu vytvoriť s totožnými bajtmi.

NÁHĽADY A REPRODUKCIA
Sedem prehľadov podľa sietí ukazuje všetky pozadia pri 220×132. Devätnásť
detailných strán navyše ukazuje 50×30 v skutočnej veľkosti. Sú súčasťou ZIPu.
Úplné podklady, zmrazené stránky, pôvodné SVG, šablóny a renderer sú v tomto
ZIPe v priečinku reprodukcia/. GitHub obsahuje kontrolné záznamy a renderer;
veľké obrázky a zmrazené stránky sú zachované v tomto úplnom kontrolnom archíve.
Python 3.12, Pillow 13.0.0, libwebp 1.6.0. Z priečinka reprodukcia/ spustite:
python render_review.py --output /tmp/warder-radio-davka02 --verify
Picony sú v kontrola/, mapovanie v parovanie.csv a súčty v SHA256SUMS.txt.

Nová dávka čaká na vizuálne schválenie. Produkčné balíky, katalóg, IPK ani
prijímač sa nemenili. Živé prehrávanie a fyzický prijímač sa netestovali.
Ide o plugin Radio, nezávislý od satelitných piconov Vhannibal.
