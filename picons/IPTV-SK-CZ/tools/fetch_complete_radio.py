"""Download complete public directory snapshots for offline catalogue compilation."""
import gzip, json, time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode

OUT=Path('catalogue-data'); OUT.mkdir(exist_ok=True)

def get(url, maximum=100*1024*1024):
    req=Request(url,headers={'User-Agent':'Warder-radio-catalogue/2 (+https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution)','Accept':'application/json','Accept-Encoding':'gzip'})
    with urlopen(req,timeout=60) as response:
        raw=response.read(maximum+1)
        if len(raw)>maximum: raise ValueError('Response exceeds size limit')
        if response.headers.get('Content-Encoding')=='gzip':
            import io
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as f: raw=f.read(maximum+1)
        if len(raw)>maximum: raise ValueError('Decoded response exceeds size limit')
    return json.loads(raw)

def save(name,data):
    blob=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode()
    (OUT/(name+'.json.gz')).write_bytes(gzip.compress(blob,mtime=0))
    print(name,len(data) if isinstance(data,list) else list(data),len(blob),flush=True)

report={}
for host in ['de1.api.radio-browser.info','de2.api.radio-browser.info','nl1.api.radio-browser.info']:
    try:
        start=time.monotonic()
        rows=get('https://'+host+'/json/stations?limit=100000&hidebroken=false&order=uuid')
        if not isinstance(rows,list) or not 10000<len(rows)<100000: raise ValueError('Incomplete directory')
        countries=get('https://'+host+'/json/countries')
        save('radio-browser',rows);save('countries',countries)
        report['radio-browser']={'server':host,'rows':len(rows),'seconds':round(time.monotonic()-start,2)}
        break
    except Exception as error:
        print('mirror failed',host,str(error)[:200],flush=True)
else: raise RuntimeError('No complete Radio Browser snapshot')
rows=[]; offset=0; total=None; pages=0
while True:
    page=get('https://api.laut.fm/stations?'+urlencode({'limit':1000,'offset':offset}),8*1024*1024)
    if not isinstance(page,dict) or page.get('offset')!=offset or not isinstance(page.get('items'),list): raise ValueError('Invalid laut page')
    total=page['total'] if total is None else total
    if total!=page['total'] or not 0<total<=30000: raise ValueError('Directory changed during pagination; retry next run')
    rows.extend(page['items']);pages+=1
    print('laut.fm page',pages,'rows',len(rows),'total',total,flush=True)
    nxt=page.get('next_offset')
    if nxt is None: break
    if nxt!=offset+len(page['items']) or nxt<=offset or pages>30: raise ValueError('Invalid pagination')
    offset=nxt
    time.sleep(.15)
if len(rows)!=total or len({r['name'] for r in rows})!=total: raise ValueError('Incomplete or unstable laut snapshot')
save('laut',rows)
report['laut.fm']={'rows':len(rows),'pages':pages,'active':sum(r.get('active') is True for r in rows)}
(OUT/'fetch-report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
