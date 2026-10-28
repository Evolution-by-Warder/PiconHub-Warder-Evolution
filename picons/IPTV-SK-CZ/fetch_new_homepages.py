from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
from urllib.request import Request,urlopen
from concurrent.futures import ThreadPoolExecutor,as_completed
import json,hashlib,gzip,io
R=Path(__file__).resolve().parent
scope={'__file__':str(R/'fetch_pages.py')};exec((R/'fetch_pages.py').read_text().split('rows=json.loads')[0],scope);Page=scope['Page']
old=json.loads((R/'research/pages.json').read_text());known={r['url']:r for r in old}
rows=json.loads((R/'catalog/refreshed-stations.json').read_text())['stations'];urls={r['homepage'] for r in rows if r.get('homepage') and urlsplit(r['homepage']).hostname not in (None,'http')};urls-=set(known)
folder=R/'research/pages';folder.mkdir(exist_ok=True)
def fetch(url):
 p=folder/(hashlib.sha256(url.encode()).hexdigest()[:20]+'.html');record={'url':url,'file':str(p.relative_to(R))}
 try:
  if p.exists():raw=p.read_bytes();final=url
  else:
   with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0','Accept-Encoding':'identity'}),timeout=6) as response:raw=response.read(2*1024*1024+1);final=response.url
   if len(raw)>2*1024*1024:raise ValueError('Homepage size limit')
  if raw.startswith(b'\x1f\x8b'):
   with gzip.GzipFile(fileobj=io.BytesIO(raw)) as source:raw=source.read(8*1024*1024+1)
   if len(raw)>8*1024*1024:raise ValueError('Expanded homepage size limit')
  p.write_bytes(raw);page=Page();page.feed(raw.decode('utf-8','replace'));record.update(final_url=final,title=page.title,images=page.images,links=[x for x in page.links if any(w in (x['href']+' '+x['text']).lower() for w in ('logo','logotyp','.svg','.zip'))])
 except Exception as e:record['error']=type(e).__name__+': '+str(e)
 return record
print('New homepages',len(urls),flush=True)
with ThreadPoolExecutor(max_workers=6) as pool:
 fs=[pool.submit(fetch,url) for url in sorted(urls)];new=[]
 for f in as_completed(fs):
  row=f.result();new.append(row)
  (R/'research/homepage-progress.json').write_text(json.dumps(new,ensure_ascii=False))
  if len(new)%25==0:print('Processed',len(new),'retrieved',sum('error' not in r for r in new),flush=True)
(R/'research/pages.json').write_text(json.dumps(old+new,ensure_ascii=False,indent=2)+'\n');print('Finished',len(new),'retrieved',sum('error' not in r for r in new),flush=True)
