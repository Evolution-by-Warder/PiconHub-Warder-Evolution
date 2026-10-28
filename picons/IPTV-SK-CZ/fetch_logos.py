from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,gzip
R=Path(__file__).resolve().parent
rows=json.loads((R/'catalog/refreshed-artwork-sources.json').read_text())['rows'];tasks={r['logo']['url']:r['logo'] for r in rows if r['logo']}
folder=R/'sources';folder.mkdir(exist_ok=True)
known=json.loads((R/'catalog/downloaded-logos.json').read_text()) if (R/'catalog/downloaded-logos.json').exists() else {}
def get(item):
 url,spec=item
 if url in known and known[url].get('path'):
  saved=R/known[url]['path']
  if saved.exists() and hashlib.sha256(saved.read_bytes()).hexdigest()==known[url].get('sha256'):
   return url,dict(known[url],**spec)
 if spec.get('source_type')=='inline-svg':
  record=known[url];assert hashlib.sha256((R/record['path']).read_bytes()).hexdigest()==record['sha256'];return url,record
 key=hashlib.sha256(url.encode()).hexdigest()[:24];suffix=Path(urlsplit(url).path).suffix.lower() or '.img';target=folder/(key+suffix);record=dict(spec)
 try:
  if not target.exists():
   with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=8) as response:data=response.read(4*1024*1024+1)
   if data.startswith(b'\x1f\x8b'):data=gzip.decompress(data)
   if len(data)>4*1024*1024:raise ValueError('Logo size limit')
   target.write_bytes(data)
  data=target.read_bytes();record.update(path=str(target.relative_to(R)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
 except Exception as e:record['error']=type(e).__name__+': '+str(e)
 return url,record
with ThreadPoolExecutor(max_workers=6) as pool:result=dict(pool.map(get,tasks.items()));known.update(result)
(R/'catalog/downloaded-logos.json').write_text(json.dumps(known,ensure_ascii=False,indent=2)+'\n');print('Downloaded',sum('path' in r for r in result.values()),'of',len(result),flush=True)
