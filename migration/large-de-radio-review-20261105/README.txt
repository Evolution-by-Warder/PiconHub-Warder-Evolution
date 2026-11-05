WARDER · VEĽKÁ RÁDIOVÁ DÁVKA · PLUGIN RADIO
5. november 2026

115 programových grafík, 120 existujúcich referencií, 1 080 piconov PNG.
Každá referencia: 50×30, 220×132, 400×240; Transparent, White, Black.
Niektoré formáty toho istého programu majú samostatnú referenciu.
Preto je tu 1 035 odlišných grafických variantov v 1 080 pomenovaných PNG.

ROZSAH
RADIO BOB!: 35 programových grafík, 40 referencií, 360 PNG.
ON Radio: 56 programových grafík, 56 referencií, 504 PNG.
1A Radio: 24 programových grafík, 24 referencií, 216 PNG.

OFICIÁLNE ZDROJE
https://streams.radiobob.de/
https://www.0nradio.com/
https://www.1aradio.com/
RADIO BOB!: logo, názov, cesta programu, kodek a bitrate sú v rovnakom bloku
oficiálneho streamového indexu. Zachované sú pôvodné katalógové názvy aj URL.
ON a 1A: programový kľúč súhlasí v názve hostiteľa, názve katalógového súboru,
oficiálnej programovej dlaždici a JSON prehrávača. JSON niekedy uvádza príponu
_web pred koncovkou audio súboru. To je zaznamenané pri identite programu;
nepreukazuje to rovnocennosť audio endpointov ani úspešné prehrávanie.
Názvy z dlaždice a JSON sa kontrolujú po zjednotení medzier a interpunkcie.
Pôvodné odpovede zostávajú uložené nezmenené. Dvanásť z nich má bajty Latin-1;
použité dekódovanie je výslovne zaznamenané, bez zásahu do zdrojových bajtov.
Podklady ON a 1A majú 600×600 a pochádzajú z adresára logos na doméne vysielateľa.
Názov súboru je odvodený z jeho programovej dlaždice a výsledné obrazy boli
vizuálne porovnané s programovými názvami. Nepoužívajú sa logá cudzích katalógov.
1A Radio na radionetz.de sa nezamieňa so sieťou 1A-Webradio.de.

VYLÚČENÉ POLOŽKY
36 ďalších referencií zostáva samostatne zdokumentovaných: 32 kombinácií formátu
a bitrate nie je v aktuálnom indexe RADIO BOB!, dve položky majú rozporný alebo
všeobecný názov či poškodenú URL, jedna programová cesta chýba a jeden názov
1A nezodpovedá aktuálnej dlaždici. Tieto položky sa touto dávkou neprepisovali.
Úplný zoznam a dôvody sú v reprodukcia/source-plan.json v časti excluded.

GRAFIKA A KONTROLA
Zdrojové obrazy 600×600 sú zachované celé vrátane pôvodných farieb, textu,
fotografií, pozadí aj pôvodného alfa kanála. Len sa pomerne zmenšili a vycentrovali.
Transparentný variant neodstraňuje plné pozadie originálu. White a Black
používajú pôvodné Warder šablóny overené podľa SHA-256.
V základnom rozmere sa overuje zachovanie celého zmenšeného obrazu a jeho alfa
kanála, správne vloženie do šablóny a všetky pixely šablóny mimo obrazu.
Pri čiastočne priehľadných origináloch sa kontroluje aj správne alfa zloženie.
Všetkých 1 080 PNG má správne rozmery a RGBA. Každá referencia má deväť variantov.
Opakované vytvorenie dalo totožné bajty všetkých PNG.

NÁHĽADY
Tri rodinné prehľady BOB, ON a 1A ukazujú všetky tri pozadia v rozmere 220×132.
Sedemnásť detailných strán ukazuje navyše aj 50×30 v skutočnej veľkosti.
Všetky náhľady sú súčasťou tohto ZIPu.

REPRODUKCIA BEZ SIETE
Úplné zdrojové obrazy, zmrazené stránky, odpovede prehrávačov, šablóny a renderer
sú v priečinku reprodukcia/ tohto kontrolného ZIPu. Na presnú reprodukciu použite
tento priečinok z archívu. GitHub obsahuje záznamy, kontrolné súčty a renderer;
veľké zdrojové obrazy a všetky náhľady sa uchovávajú v tomto úplnom ZIPe.
Python 3.12, Pillow 13.0.0, libwebp 1.6.0.
Z priečinka reprodukcia/ spustite:
python render_review.py --output /tmp/warder-large-de-kontrola --verify
Picony sú v kontrola/, mapovanie v parovanie.csv a súčty v SHA256SUMS.txt.

Táto nová dávka čaká na vizuálne schválenie. Produkčné balíky, katalóg, IPK
a prijímač sa nemenili. Živé prehrávanie ani fyzický prijímač sa netestovali.
Ide o picony pre plugin Radio, nezávislé od satelitných piconov Vhannibal.
