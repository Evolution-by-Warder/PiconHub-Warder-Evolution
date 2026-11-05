WARDER RADIO — ANTENNE BAYERN, KONTROLNÁ DÁVKA
5. november 2026

20 programových grafík, 21 existujúcich servisných referencií, 189 PNG.
180 rozdielnych grafických variantov; dve referencie 90er Eurodance majú
vo všetkých deviatich variantoch totožné PNG. Obe referencie zostávajú zachované.

Každá referencia má 50×30, 220×132 a 400×240 v štýloch Transparent, White, Black.
Použité sú celé oficiálne programové podklady vysielateľa v rozmere 600×600.
Farby, nápisy, obrázky, podložky a pomery sa nemenia. Podklad sa len pomerne
zmenší a vycentruje. Originálne Warder MASTER šablóny sú overené SHA-256.
Transparent znamená priehľadné plátno; plné pozadie originálu zostáva súčasťou loga.

PROGRAMY
2000er Hits, 2010er Hits, 80er Disco Hits, 90er Eurodance, 90er Party,
Après Ski, Bayerische Weihnacht, Bayern Sound, Halli Galli Gaudi, Happy Hits,
In the mix, Italo Hits, NDW, Nur die Musik, Party Hits, Pop XXL, Top 1000,
Workout Mix, CHILLOUT ANTENNE Bayern, ROCK ANTENNE Bayern.

ZDROJE A IDENTITA
Grafiky: https://www.antenne.de/webradio/
Programy a streamové trasy: https://www.antenne.de/programm/empfang/webradio
Presné URL, ich kontrolné súčty a servisné referencie sú v source-plan.json
a render-manifest.json. Naše označenie Top 100ü sa nemení; jeho existujúca
streamová cesta top-1000 sa zhoduje s oficiálnym programom Top 1000.

NEZARADENÉ DO TEJTO DÁVKY
Weihnachtslounge: názov naznačuje Vianoce, stream vedie na obyčajný Lounge.
Starý Chillout: staršie označenie a stream vyžadujú samostatné overenie identity.
Druhá položka Workout Mix: URL obsahuje chybné medzery a fragment.
Tieto tri existujúce položky sa neprepisujú ani nevymazávajú.

KONTROLA A REPRODUKCIA
Overené: pôvod a SHA-256 všetkých zdrojov, 21 presných referencií v katalógu,
všetkých 189 PNG a ich rozmery/alfa, zachovanie pôvodných farieb, pôvodné MASTER
šablóny a všetky ich pixely mimo loga. Opakované vytvorenie všetkých 189 PNG
vytvorilo totožné bajty. Nebolo testované živé prehrávanie ani fyzický prijímač.

Požadované prostredie: Python 3.12 a Pillow 13.0.0.
Z priečinka s týmto README spustite bez siete:
python render_review.py --output /tmp/warder-bayern-kontrola --verify

PNG sú v priečinku kontrola/ dodaného ZIPu. Tri obrázkové prehľady ukazujú
220×132 aj 50×30 v skutočnej veľkosti. V ZIPe je reprodukcia uložená v priečinku
reprodukcia/; overovací príkaz preto spustite odtiaľ.

Táto dávka čaká na presné vizuálne schválenie. Produkčné balíky, katalógy,
pôvodné picony, IPK a prijímač sa touto prípravou nemenia.
