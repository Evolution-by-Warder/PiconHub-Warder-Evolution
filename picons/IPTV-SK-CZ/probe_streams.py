"""Bounded audio-header probes; never read an unbounded live stream."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor,as_completed
import json,time,hashlib
R=Path(__file__).resolve().parent
doc=json.loads((R/'catalog/refresh-candidate.json').read_text());tasks={}
for r in doc['existing']:
 for u in [r['stream_url'],r.get('candidate_stream')]:
  if u:tasks.setdefault(u,[]).append(r['name'])
for r in doc['additions']:tasks.setdefault(r['stream_url'],[]).append(r['name'])
for r in json.loads((R/'catalog/refreshed-stations.json').read_text())['stations']:
 tasks.setdefault(r['stream_url'],[]).append(r['name'])
cache=R/'research/stream-probes';cache.mkdir(exist_ok=True)
def probe(item):
 u,names=item;p=cache/(hashlib.sha256(u.encode()).hexdigest()+'.json')
 if p.exists():return json.loads(p.read_text())
 start=time.monotonic();result={'url':u,'stations':sorted(set(names)),'checked_at':time.time()}
 try:
  req=Request(u,headers={'User-Agent':'Warder-Radio-Catalog/1.0','Icy-MetaData':'1','Connection':'close'})
  with urlopen(req,timeout=4) as response:
   ct=response.headers.get('Content-Type','')
   result.update(status=response.status,final_url=response.url,content_type=ct,icy_name=response.headers.get('icy-name',''))
   raw=response.read(1024)
   result.update(bytes_sampled=len(raw),audio_response=bool(raw) and (ct.lower().startswith('audio/') or ct.lower().startswith('application/ogg')))
 except Exception as e:result.update(error=type(e).__name__+': '+str(e),audio_response=False)
 result['elapsed']=round(time.monotonic()-start,2);p.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');return result
print('Streams to check',len(tasks),flush=True)
with ThreadPoolExecutor(max_workers=12) as pool:
 futures=[pool.submit(probe,item) for item in tasks.items()]
 records=[]
 for f in as_completed(futures):
  records.append(f.result())
  if len(records)%40==0:print('Checked',len(records),'audio responses',sum(r['audio_response'] for r in records),flush=True)
(R/'catalog/stream-verification.json').write_text(json.dumps({'records':records},ensure_ascii=False,indent=2)+'\n');print('Finished',len(records),'audio responses',sum(r['audio_response'] for r in records),flush=True)
