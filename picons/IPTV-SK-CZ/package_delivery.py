from pathlib import Path
import json,hashlib,zipfile,io,csv
from PIL import Image
R=Path(__file__).resolve().parent;out=R/'delivery';out.mkdir(exist_ok=True)
rows=json.loads((R/'catalog/refreshed-artwork-sources.json').read_text())['rows'];lookup={r['picon_filename']:r for r in rows};report=json.loads((R/'catalog/preview-review.json').read_text());included=[];missing=[]
for r in report['records']:
 source=lookup[r['picon_filename']];valid=len(r.get('files',{}))==9 and r['status']!='SOURCE_ERROR' and source['identity_key'] not in ('lifetrance','freeravecz')
 if valid:
  for variant,spec in r['files'].items():
   raw=(R/spec['path']).read_bytes()
   if hashlib.sha256(raw).hexdigest()!=spec['sha256']:valid=False;break
   with Image.open(io.BytesIO(raw)) as im:
    if im.size!=tuple(map(int,variant.split('/')[0].split('x'))):valid=False;break
    im.verify()
 if valid:included.append(r)
 else:missing.append((r['country'],r['name'],'Chýba vhodný overený podklad alebo obrázok neprešiel kontrolou'))
probe={r['url']:r for r in json.loads((R/'catalog/stream-verification.json').read_text())['records']};sampled=sum(probe.get(r['stream_url'],{}).get('audio_response',False) for r in rows)
notes=f'''Warder IPTV rádiá SK/CZ — 28. 10. 2026\n\nBouquet: {len(rows)} položiek, 88 SK a 233 CZ. Pri {sampled} vybraných adresách skúška vrátila zvukové dáta. Ostatné nemajú úplné potvrdenie. Timeout neznamená zánik stanice.\n\nPicony: {len(included)} položiek, deväť variantov: 50x30, 220x132, 400x240; transparent, white, black. PNG prešli kontrolou SHA256, formátu a rozmerov. Chýbajúce podklady sú v chybajuce-picony.csv. Nevhodné obrázky nie sú nahradené vymyslenými logami.\n\nPOUŽITIE\nZ priečinka picony vyber iba jednu kombináciu rozlíšenia a štýlu. PNG z nej skopíruj priamo do priečinka picon nastaveného v skine, napríklad /media/hdd/picon/. Nesúvisiace existujúce súbory nemaž. Nekopíruj všetky varianty naraz.\n\nuserbouquet.warder.sk-cz.radio je samostatný SK/CZ bouquet pre import správcom bouquetov. userbouquet.warder.radio je celý pôvodný bouquet s upravenými SK/CZ sekciami; ostatné krajiny zostávajú nezmenené. Pred nahradením pôvodného rovnomenného súboru si urob zálohu.\n\nSTAV APLIKÁCIÍ\nPonuka IPTV je zapracovaná v pracovných vetvách PiconHubu a FullHDGlass radio/iptv-sk-cz-refresh. Prešli kontroly Python 3.9 a 3.14. Produkčné IPK a automatické aktualizácie s touto ponukou ešte NIE SÚ vydané. Toto je odovzdaný balík súborov, nie vydaná aktualizácia aplikácií.\n'''
text=io.StringIO();w=csv.writer(text);w.writerow(('Krajina','Stanica','Dôvod'));w.writerows(missing)
archive=out/'Warder-IPTV-SK-CZ.zip';hashes=[];names=set()
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for r in included:
  source=lookup[r['picon_filename']]
  for variant,spec in r['files'].items():
   raw=(R/spec['path']).read_bytes();filenames=[r['picon_filename']]+[a.replace(':','_')+'.png' for a in source.get('reference_aliases',[])]
   for name in filenames:
    path='picony/'+variant+'/'+name
    if path in names:continue
    names.add(path);z.writestr(path,raw);hashes.append(hashlib.sha256(raw).hexdigest()+'  '+path)
 z.writestr('PRECITAJ-MA.txt',notes);z.writestr('chybajuce-picony.csv','\ufeff'+text.getvalue());z.writestr('SHA256SUMS.txt','\n'.join(hashes)+'\n')
 for name in ('userbouquet.warder.sk-cz.radio','userbouquet.warder.radio'):z.write(R/'output'/name,name)
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
summary=dict(path=str(archive),bytes=archive.stat().st_size,stations=len(rows),audio_sampled=sampled,picon_stations=len(included),missing=len(missing),png_files=len(names),sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
(out/'delivery-summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
