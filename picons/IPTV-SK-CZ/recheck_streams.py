"""Retry inconclusive selected streams with a slower, less bursty probe."""
from pathlib import Path
from urllib.request import Request,urlopen
from concurrent.futures import ThreadPoolExecutor,as_completed
import json,time,hashlib
R=Path(__file__).resolve().parent
rows=json.loads((R/'catalog/refreshed-stations.json').read_text())['stations']
cache=R/'research/stream-probes'
def path(u):return cache/(hashlib.sha256(u.encode()).hexdigest()+'.json')
def prior(u):return json.loads(path(u).read_text()) if path(u).exists() else {}
for record in json.loads((R/'catalog/sk-primary-recheck.json').read_text()):
 if record.get('audio_response'):
  record.update(checked_at=time.time(),stations=[record['name']]);path(record['url']).write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
tasks={r['stream_url']:r['name'] for r in rows if not prior(r['stream_url']).get('audio_response')}
def check(item):
 u,name=item;record=dict(url=u,stations=[name],checked_at=time.time(),audio_response=False);t=time.monotonic()
 try:
  with urlopen(Request(u,headers={'User-Agent':'Warder-Radio-Catalog/1.0','Icy-MetaData':'1','Connection':'close'}),timeout=12) as response:
   record.update(status=response.status,final_url=response.url,content_type=response.headers.get('Content-Type',''),icy_name=response.headers.get('icy-name',''))
   raw=response.read(1024);record.update(bytes_sampled=len(raw),audio_response=bool(raw) and (record['content_type'].startswith('audio/') or record['content_type'].startswith('application/ogg')))
 except Exception as error:record['error']=type(error).__name__+': '+str(error)
 record['elapsed']=round(time.monotonic()-t,2);path(u).write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');return record
print('Retrying inconclusive selected streams:',len(tasks),flush=True)
with ThreadPoolExecutor(max_workers=4) as pool:
 futures=[pool.submit(check,item) for item in tasks.items()]
 for i,f in enumerate(as_completed(futures),1):
  f.result()
  if i%25==0:print('Rechecked',i,flush=True)
records=[json.loads(p.read_text()) for p in cache.glob('*.json')]
(R/'catalog/stream-verification.json').write_text(json.dumps({'records':records},ensure_ascii=False,indent=2)+'\n')
print('Selected stations with audio response:',sum(prior(r['stream_url']).get('audio_response',False) for r in rows),flush=True)
