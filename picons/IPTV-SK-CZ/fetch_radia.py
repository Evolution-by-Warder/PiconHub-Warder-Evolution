from pathlib import Path
from urllib.request import Request,urlopen
from concurrent.futures import ThreadPoolExecutor
import json,re
R=Path(__file__).resolve().parent
D=R/'research'
def get(page):
 p=D/f'radia-page-{page}.html'
 if not p.exists():
  with urlopen(Request(f'https://radia.cz/radia?page={page}',headers={'User-Agent':'Mozilla/5.0'}),timeout=15) as response:p.write_bytes(response.read(3*1024*1024))
 s=p.read_text();match=re.search(r'window\.__qc__=(\{.*?\});',s,re.S);d=json.loads(match[1]);result=[]
 for q in d['queries']:
  data=q['state'].get('data')
  if isinstance(data,dict) and 'result' in data:result.extend(x for x in data['result'] if 'logo' in x)
 return result
with ThreadPoolExecutor(max_workers=4) as pool:rows=[r for rs in pool.map(get,range(1,9)) for r in rs]
rows=list({r['id']:r for r in rows}.values());(D/'radia-stations.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');print('Radia metadata',len(rows))
