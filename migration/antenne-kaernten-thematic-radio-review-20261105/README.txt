WARDER · ANTENNE KÄRNTEN · KONTROLNÁ DÁVKA PRE PLUGIN RADIO
5. november 2026

4 programové grafiky, 4 existujúce servisné referencie, 36 piconov PNG.
Každá referencia: 50×30, 220×132, 400×240; Transparent, White, Black.

PROGRAMY
Austro Hits, 80er Pop, Partyhitmix a Sunrise.

ZDROJE
https://kaernten.antenne.at/player/streams
https://cms.kaernten.antenne.at/api/globals/streams
https://steiermark.antenne.at/player/streams
https://cms.steiermark.antenne.at/api/globals/streams
Programové názvy, streamové adresy aj obrazy sú z oficiálnych CMS vysielateľa.
Zdrojové odpovede a stránky sú zachované v reprodukcia/evidence/.
Všetky štyri adresy majú zhodný názov hostiteľa a presnú programovú cestu
v pôvodnom katalógu aj v oficiálnom CMS. Rozdiel HTTP/HTTPS pri Partyhitmix
a Sunrise sa zaznamenal; pôvodné adresy a referencie katalógu sa neprepisovali.

REGIONÁLNA GRAFIKA
V CMS Kärnten aj Steiermark sú pri týchto programoch rovnaké streamové adresy,
ale regionálne označené obrázky. Pre kontrolnú dávku je zvolená grafika Kärnten.
Tri zodpovedajúce katalógové názvy výslovne uvádzajú Kärnten. Austro Hits má
v katalógu všeobecný názov Antenne Austro Hits. Tu je použitá podoba Kärnten;
nejde o tvrdenie, že spoločný stream je vysielaný výhradne pre tento región.

ZDROJOVÉ OBRÁZKY
Všetky prijaté podklady sú úplné WebP 1024×1024. Pri 80er Pop, Partyhitmix
a Sunrise sa počet prijatých bajtov líši od údaja filesize v CMS. Príčina
tohto rozdielu nebola potvrdená. Skutočné rozmery, prijaté počty bajtov aj
SHA-256 sa zaznamenali samostatne; pôvodné údaje CMS zostali zachované.
Kontrola a reprodukcia používajú presne uložené prijaté podklady.

ÚPRAVY A KONTROLA
Celé podklady vrátane fotografií, nápisov, farieb a pôvodných pozadí sú iba
pomerne zmenšené a vycentrované. Pozadie zdroja sa neodstraňovalo. Transparentný
variant zachováva plné pozadie obrazu a priehľadné vonkajšie plátno.
Warder White a Black šablóny sú pôvodné a overené SHA-256.
V základnom rozmere sa overuje každý pixel celého zmenšeného obrazu aj všetky
pixely šablóny mimo neho. Každá referencia má všetkých deväť variantov.
Všetkých 36 PNG má správne rozmery a RGBA. Opakované vytvorenie dalo totožné bajty.

REPRODUKCIA
Python 3.12, Pillow 13.0.0, libwebp 1.6.0.
Z priečinka reprodukcia/ spustite:
python render_review.py --output /tmp/warder-antenne-at-kontrola --verify
Picony sú v kontrola/, mapovanie v parovanie.csv, súčty v SHA256SUMS.txt.
Náhľad zobrazuje všetky pozadia a 50×30 v skutočnej veľkosti.

Nová dávka čaká na vizuálne schválenie. Produkčné balíky, katalóg, IPK a prijímač
sa nemenili. Živé prehrávanie ani fyzický prijímač sa netestovali.
Ide o picony pre plugin Radio, nezávislé od satelitných piconov Vhannibal.
