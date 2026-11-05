WARDER RADIO – VEĽKÁ DÁVKA 04 – laut.fm
Dátum: 2026-11-05

164 celých pôvodných grafík; 164 referencií; 1476 PNG.
Každá referencia: 50×30, 220×132, 400×240 × transparent / white / black.
Toto je kontrolná dávka pre plugin Radio. Čaká na vizuálne schválenie.

Podklady sú publikované v oficiálnom registri laut.fm a zachované celé, s pôvodnými farbami, pozadím a priehľadnosťou. Zhoduje sa názov stanice, jej identifikátor a cesta streamu. Jediná osobitná normalizácia katalógového názvu odstraňuje prefix „laut.fm -“, medzery, diakritiku a interpunkciu. Nejasné identity, všeobecné predvolené podklady a vizuálne nevhodné profilové obrázky sú odložené; dôvody sú zapísané v source-plan.json.

Produkčné balíky, katalógy a pôvodné Warder šablóny sa nemenia. Predchádzajúce schválené referencie sa neprepisujú ani nezapočítavajú. Táto dávka nerieši Vhannibalove satelitné picony. Prehrávanie zvuku ani skúška v prijímači neboli vykonané.

kontrola/: všetkých 1476 PNG podľa veľkosti a pozadia.
Warder_Radio_Davka04_*.png: celkové a podrobné vizuálne kontroly.
parovanie.csv: presné párovanie katalógovej referencie s podkladom.
SHA256SUMS.txt: kontrolné súčty všetkých piconov.
reprodukcia/: celé pôvodné podklady, nemenné registre, šablóny a offline renderer.
Pre presné overenie: Python 3.12, Pillow 13.0.0, libwebp 1.6.0:
python reprodukcia/render_review.py --output /tmp/warder-radio-recheck --verify

V Gite sú kontrolné záznamy, registre, súčty a renderer. Celé obrazové zdroje sú v tomto ZIP.
