from pathlib import Path
import json,gzip,io
R=Path(__file__).resolve().parent
code=(R/'fetch_pages.py').read_text().split('rows=json.loads')[0];scope={'__file__':str(R/'fetch_pages.py')};exec(code,scope);Page=scope['Page']
fixed=[]
for p in (R/'research').rglob('*.html'):
 raw=p.read_bytes()
 if raw.startswith(b'\x1f\x8b'):
  with gzip.GzipFile(fileobj=io.BytesIO(raw)) as source:out=source.read(8*1024*1024+1)
  if len(out)>8*1024*1024:continue
  p.write_bytes(out);fixed.append(str(p.relative_to(R)))
records=json.loads((R/'research/pages.json').read_text())
for r in records:
 p=R/r['file'] if r.get('file') else None
 if p and p.exists() and 'error' not in r:
  page=Page();page.feed(p.read_text(errors='replace'));r.update(title=page.title,images=page.images,links=[x for x in page.links if any(w in (x['href']+' '+x['text']).lower() for w in ('logo','logotyp','.svg','.zip'))])
(R/'research/pages.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
print('Normalized compressed pages',len(fixed),fixed)
for r in records:
 if any(x in r['url'] for x in ['casrock','subfm','countryradio','radiohana','krokodyl','proglas']):print(r['url'],r.get('title'),[i for i in r.get('images',[]) if 'logo' in str(i).lower()][:3])
