WARDER · RADIO FLAMINGO · KONTROLNÁ DÁVKA PRE PLUGIN RADIO
5. november 2026

6 programov, 6 existujúcich servisných referencií, 54 piconov PNG.
Každá referencia: 50×30, 220×132, 400×240; Transparent, White, Black.

PROGRAMY
Radio Flamingo Christkindl, Plus Golden Hits, Hoamat, Plus Kultschlager,
Partyschlager a Plus Volksmusik.

ZDROJE A IDENTITA
https://www.radioflamingo.at/player/streams
https://cms.radioflamingo.at/api/globals/streams
Každá úplná streamová adresa presne súhlasí s existujúcou položkou katalógu.
Názov, adresa a vlastná grafika pochádzajú vždy z rovnakého programového záznamu
v oficiálnom CMS vysielateľa. Odpoveď CMS aj stránka sú zachované v reprodukcia/evidence/.
Originálne WebP podklady 4000×4000 boli prevzaté v plnom rozlíšení a overené
aj oproti rozmerom a počtu bajtov zverejneným vysielateľom.

ÚPRAVY
Celé podklady vrátane vlastných pozadí, nápisov a farieb sú pomerne zmenšené
a vycentrované. Pozadie zdrojov sa neodstraňovalo. Transparentný variant má
priehľadné vonkajšie plátno a zachováva plné pozadie originálneho loga.
Warder White a Black šablóny sú pôvodné a overené podľa SHA-256.

HLAVNÝ PROGRAM ZOSTÁVA NA PREVERENIE
Katalóg má Radio Flamingo na starej doméne live.antenne.at/rf, zatiaľ čo aktuálny
oficiálny prehrávač uvádza live.radioflamingo.at/rf. Pri overení HEAD v tomto
prostredí obe adresy vrátili HTTP 502. To nedokazuje, že rádio nefunguje.
Rovnocennosť adries ani prehrávanie sa tým nepotvrdili, preto hlavný program
nie je súčasťou tejto dávky a existujúci katalóg zostal zachovaný.

OVERENIE A REPRODUKCIA
Všetkých 54 piconov je RGBA a v správnych rozmeroch. Overené sú referencie,
deväť variantov každej stanice, zdrojové a výsledné kontrolné súčty. V základnom
rozmere je overený každý pixel celého zmenšeného podkladu aj všetky pixely
šablóny mimo podkladu. Opakované vytvorenie dalo totožné bajty všetkých PNG.
Python 3.12, Pillow 13.0.0, libwebp 1.6.0.
Z priečinka reprodukcia/ spustite:
python render_review.py --output /tmp/warder-flamingo-kontrola --verify

Picony sú v kontrola/, presné párovanie v parovanie.csv a kontrolné súčty
v SHA256SUMS.txt. Náhľad zobrazuje všetky tri pozadia aj 50×30 v skutočnej veľkosti.

Nová dávka čaká na vizuálne schválenie. Ide o picony pre plugin Radio.
Produkčné balíky, katalóg, IPK a prijímač sa nemenili. Živé prehrávanie ani
fyzický prijímač sa netestovali. Dávka je nezávislá od satelitných piconov Vhannibal.
