import json,csv,io,zipfile,urllib.request
from pathlib import Path
from PIL import Image
R=Path(__file__).resolve().parent;d=json.loads((R/'comparison.json').read_text());diag=json.loads((R/'pixel-diagnostics.json').read_text());ref=d['skin_commit'];root='https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/'+ref+'/assets/warder/downloads/picons/channels/';doc=json.load(urllib.request.urlopen(root+'manifest.json',timeout=30));meta={p['filename']:p for p in doc['parts']};tv5=[]
for p in doc['packages']:
 if p['selector_id'] not in ('CANALPLUS_SK','CANALPLUS_CZ') or p['resolution']!='220x132':continue
 raw=b''.join((R/'parts'/meta[u.rsplit('/',1)[-1]]['sha256']).read_bytes() for u in p['parts'])
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  im=Image.open(io.BytesIO(z.read('1_0_1_1B03_3FE_1_C00000_0_0_0.png'))).convert('RGBA');colours=im.getcolors(40000)
  tv5.append({'selector':p['selector_id'],'style':p['family'].removeprefix('channel-'),'colour_count':len(colours),'constant_colour':list(colours[0][1]) if len(colours)==1 else None})
labels={'1816_C82_3_EB':'Mezzo','18ED_3F4_1_C0':'CGTN','18EF_3F4_1_C0':'CGTN Français','1F50_CA1_3_EB':'Story4 (older graphic/reference)','1_40B_1_C0':'SES logo / demo identity not verified','36EB_C8C_3_EB':'CS Horror (separate legacy reference)','3E_5_85_C0':'EWTN','1B03_3FE_1_C0':'TV5MONDE','36EA_C8C_3_EB':'CS Film / CS Horror combined graphic in Canal+','5318_C96_3_EB':'TV8 / televízia osem','1F4B_CA1_3_EB':'Canal+ Sport 2','3C30_C90_3_EB':'Sport 1','164F_42C_1_C0':'CGTN','1651_42C_1_C0':'CGTN Français','3355_45B_1_C0':'EWTN','17EB_C82_3_EB':'Story4'}
findings={'snapshot':ref,'labels_are_from_package_graphics_not_a_verified_current_channel_lineup':True,'labels':labels,'tv5_pixel_check':tv5,'coverage_issue':{'CANALPLUS_SK_missing_transparent_and_white':['1F4B_CA1_3_EB','3C30_C90_3_EB']},'no_audit_asset_changes':True}
(R/'named-findings.json').write_text(json.dumps(findings,ensure_ascii=False,indent=2)+'\n')
allkeys=sorted(set().union(*(set(v) for v in d['all_records'].values())))
with (R/'service-differences.csv').open('w',newline='') as f:
 cols=['service_identity','label_from_graphic']+[sel+'_'+style for sel in ('SKYLINK','CANALPLUS_SK','CANALPLUS_CZ') for style in ('transparent','white','black')];w=csv.writer(f);w.writerow(cols)
 for key in allkeys:w.writerow([key,labels.get(key,'')]+['yes' if key in d['all_records'][sel+'/'+style] else 'no' for sel in ('SKYLINK','CANALPLUS_SK','CANALPLUS_CZ') for style in ('transparent','white','black')])
text='''# Skylink a Canal+ SK/CZ — porovnanie skutočných balíkov

Stav po doplnení deviatich rádiových referencií do oboch Canal+ sád, 27. október 2026. Nemenný zdroj katalógu: `17ac58f68dc2016b161790781d6532d859f30c98`. Všetkých deväť porovnávaných ZIPov aj ich časti boli overené podľa veľkosti a SHA256. Audit nič neodstránil ani nezmenil v piconových balíkoch.

## Počty v spoločnom rozmere 220×132

| Balík | Transparent | Biele | Čierne |
|---|---:|---:|---:|
| Skylink | 257 | 257 | 257 |
| Canal+ SK | 238 | 238 | 240 |
| Canal+ CZ | 243 | 243 | 243 |

Počty sú PNG súbory, nie zaručené počty staníc. Po zlúčení technických aliasov má Skylink 255 identít služieb; Canal+ SK 234 (Transparent/Biele) alebo 236 (Čierne); Canal+ CZ 239. Referencie sa porovnávajú podľa SID, TSID, ONID a orbitálneho namespace, aby sa rozdiel typu služby SD/HD nepovažoval automaticky za ďalšiu stanicu.

Skylink obsahuje zmiešané slovenské aj české picony. Oproti Canal+ SK má 38 ďalších identít v Transparent/Biele a 36 v Čiernom; oproti Canal+ CZ ich má 33. Veľká časť týchto rozdielov je obsiahnutá v druhej krajinskej sade. Úplný výpis je v service-differences.csv a na obrázkoch `canalplus_sk-skylink-only-*` / `canalplus_cz-skylink-only-*`.

## Sedem referencií mimo spojenej množiny oboch Canal+ sád

| Identita v Skylinku | Nápis/značka na picone | Zistenie |
|---|---|---|
| 1816_C82_3_EB | Mezzo | Táto konkrétna referencia v Canal+ sadách nie je. |
| 18ED_3F4_1_C0 | CGTN | Rovnaký obrázok je v oboch Canal+ pod 164F_42C_1_C0. |
| 18EF_3F4_1_C0 | CGTN Français | Rovnaký obrázok je v oboch Canal+ pod 1651_42C_1_C0. |
| 1F50_CA1_3_EB | Story4 | Canal+ má značku Story4 aj pod 17EB_C82_3_EB, s inou grafikou. |
| 1_40B_1_C0 | SES | Logo SES; presný názov testovacej služby sa z obrázka nepotvrdzuje. |
| 36EB_C8C_3_EB | CS Horror | Samostatná stará referencia nie je v Canal+. Značka CS Horror je aj v spojenej picone CS Film/CS Horror na 36EA_C8C_3_EB. |
| 3E_5_85_C0 | EWTN | Rovnaký obrázok je v oboch Canal+ pod 3355_45B_1_C0. |

Sedem rozdielnych referencií preto nepredstavuje sedem preukázateľne chýbajúcich staníc. Tabuľka popisuje obsah obrázkov a súborov, nie dnešnú obchodnú ponuku ani stav satelitného vysielania.

![Skylink: sedem referencií mimo oboch Canal+ sád](skylink-only-transparent.png)

## Zistené chyby a rozdiely grafiky

1. **TV5MONDE je v oboch Canal+ sadách chybná.** Transparentný PNG pre 1B03_3FE_1_C0 má celú alfu nulovú. Pixelová kontrola bieleho a čierneho prevedenia je presne zapísaná v named-findings.json; nejde o rozdielne oprávnenia stanice. Skylink má viditeľné logo.
2. **Canal+ SK nemá jednotné pokrytie farieb.** Canal+ Sport 2 (1F4B_CA1_3_EB) a Sport 1 (3C30_C90_3_EB) sú v Čiernom, ale chýbajú v Transparent/Biele. V Canal+ CZ sú vo všetkých troch prevedeniach.
3. **Rámčeky bielych a čiernych piconov sa výrazne odlišujú.** Pri testovaní štyroch rohov so schváleným MASTER podkladom sedí v Skylinku 251/257 čiernych a 252/257 bielych obrázkov. V Canal+ SK je to 29/240 a 21/238, v Canal+ CZ 28/243 a 22/243. Na kontrolovaných príkladoch majú mnohé Canal+ picony orezaný pravý/spodný rám. Neshoda rohov sama osebe nie je dôkaz nesprávneho loga; presná metodika je v pixel-diagnostics.json.
4. **Pri spoločných transparentných referenciách sú rozdielne iba tri obrázky:** TV5MONDE, CS Film (Skylink má samostatné CS Film, Canal+ novšiu schválenú spoločnú CS Film/CS Horror) a TV8/televízia osem (Skylink má starú grafiku TV8, Canal+ aktuálny schválený obrázok osem). Tieto rozdiely sa nemajú mechanicky vracať na staré logá.

![Spoločné transparentné referencie: Skylink vľavo, Canal+ vpravo](transparent-differences.png)

![Príklady čiernych piconov: Skylink vľavo, Canal+ SK vpravo](canalplus_sk-different-01.png)

## Súbory a reprodukcia

- comparison.json: každá referencia a SHA256 pôvodného PNG aj viditeľných pixelov.
- pixel-diagnostics.json: prázdne PNG a rohy oproti schváleným MASTER podkladom.
- named-findings.json: konkrétne názvy prečítané z porovnávaných piconov a pixelová kontrola TV5MONDE.
- service-differences.csv: úplná prítomnosť identít vo všetkých deviatich ZIPoch.
- compare.py, details.py, pixel_diagnostics.py, write_report.py: reprodukcia nad nemenným verejným katalógom; Pillow je potrebný iba na počítači vykonávajúcom audit.

V tomto porovnaní sa žiadne staré stanice ani picony nevyraďovali. Chyby TV5MONDE, nejednotné farebné pokrytie dvoch športových staníc a rámčeky sú zaznamenané ako nálezy; audit ich nevydáva za už opravené.
'''
(R/'README.md').write_text(text)
print('TV5 checks:',json.dumps(tv5));print('Audit report, inventory and findings saved.')
