#!/usr/bin/env python3
"""Read complete supported directory exports; each failed source retains its cache."""
import argparse
import gzip
import io
import json
from pathlib import Path
import time
from urllib.request import Request,urlopen
from urllib.parse import urlencode,urlsplit

MIRRORS=('de1.api.radio-browser.info','de2.api.radio-browser.info','nl1.api.radio-browser.info')
MAX_RESPONSE=128*1024*1024


def get(url, maximum=MAX_RESPONSE, opener=urlopen):
    req=Request(url,headers={'User-Agent':'Warder-radio-catalogue/2 (+https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution)',
                            'Accept':'application/json','Accept-Encoding':'gzip'})
    with opener(req,timeout=60) as response:
        target=urlsplit(getattr(response,'url',url))
        if target.scheme!='https' or target.hostname!=urlsplit(url).hostname:
            raise ValueError('Unexpected directory redirect')
        raw=response.read(maximum+1)
        if len(raw)>maximum:raise ValueError('Response exceeds size limit')
        if response.headers.get('Content-Encoding')=='gzip':
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as f:raw=f.read(maximum+1)
        if len(raw)>maximum:raise ValueError('Decoded response exceeds size limit')
    return json.loads(raw)


def radio_browser(getter=get):
    errors=[]
    for host in MIRRORS:
        try:
            start=time.monotonic()
            rows=getter('https://'+host+'/json/stations?limit=100000&hidebroken=false&order=url')
            if not isinstance(rows,list) or not 10000<len(rows)<100000:
                raise ValueError('Incomplete or capped directory')
            keys=[r.get('stationuuid') for r in rows if isinstance(r,dict)]
            if len(keys)!=len(rows) or len(set(keys))!=len(rows) or not all(keys):
                raise ValueError('Invalid/duplicate directory identities')
            countries=getter('https://'+host+'/json/countries')
            if not isinstance(countries,list) or len(countries)<150:raise ValueError('Incomplete countries')
            return rows,countries,{'server':host,'rows':len(rows),'seconds':round(time.monotonic()-start,2)}
        except Exception as error:errors.append(host+': '+str(error)[:180])
    raise RuntimeError('; '.join(errors))


def laut(getter=get, pause=time.sleep):
    # The public pages are not a transaction and can repeat names as their
    # ranking changes. Reconcile them with the authoritative name inventory.
    names=getter('https://api.laut.fm/station_names',2*1024*1024)
    if (not isinstance(names,list) or not 5000<len(names)<=30000
            or any(not isinstance(n,str) or not __import__('re').fullmatch('[a-z0-9_-]{1,100}',n) for n in names)
            or len(set(names))!=len(names)):
        raise ValueError('Invalid laut.fm name inventory')
    inventory=set(names); records={};offset=0;pages=0;duplicate_rows=0
    while True:
        page=getter('https://api.laut.fm/stations?'+urlencode({'limit':1000,'offset':offset}),8*1024*1024)
        if not isinstance(page,dict) or page.get('offset')!=offset or not isinstance(page.get('items'),list):
            raise ValueError('Invalid laut.fm page')
        total=page.get('total')
        if not isinstance(total,int) or not 0<total<=30000:raise ValueError('Invalid laut.fm total')
        for row in page['items']:
            if not isinstance(row,dict) or not isinstance(row.get('name'),str):raise ValueError('Invalid laut.fm record')
            if row['name'] in records:duplicate_rows+=1
            if row['name'] in inventory:records[row['name']]=row
        pages+=1;nxt=page.get('next_offset')
        if nxt is None:break
        if len(page['items'])>1000 or nxt!=offset+len(page['items']) or nxt<=offset or pages>30:
            raise ValueError('Invalid laut.fm pagination')
        offset=nxt;pause(.2)
    missing=sorted(inventory-set(records));requests=pages+1
    for start in range(0,len(missing),100):
        batch=missing[start:start+100]
        rows=getter('https://api.laut.fm/stations/'+','.join(batch),8*1024*1024);requests+=1
        if not isinstance(rows,list) or len(rows)>len(batch):raise ValueError('Invalid laut.fm name batch')
        for row in rows:
            if row.get('name') not in batch:raise ValueError('Unexpected laut.fm batch identity')
            records[row['name']]=row
        pause(.2)
    # A name without metadata is retained in the diagnostic inventory. The
    # compiler also retains its previous snapshot if a later fetch fails.
    absent=sorted(inventory-set(records))
    if len(absent)>max(5,len(inventory)*.01):raise ValueError('Incomplete laut.fm named lookup')
    rows=[records[k] for k in sorted(records)]
    return rows,{'rows':len(rows),'inventory':len(inventory),'pages':pages,'requests':requests,
                 'page_duplicates':duplicate_rows,'named_recoveries':len(missing)-len(absent),
                 'unavailable_names':absent,'active':sum(r.get('active') is True for r in rows)}


def save(path,data):
    raw=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode()
    if len(raw)>MAX_RESPONSE:raise ValueError('Snapshot exceeds size bound')
    temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_bytes(gzip.compress(raw,mtime=0));temporary.replace(path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path('catalogue-data'))
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    # No leftover temporary source file may masquerade as a successful fresh fetch.
    for filename in ('radio-browser.json.gz','countries.json.gz','laut.json.gz'):
        (args.output/filename).unlink(missing_ok=True)
    report={}
    try:
        rows,countries,info=radio_browser()
        save(args.output/'radio-browser.json.gz',rows);save(args.output/'countries.json.gz',countries)
        report['radio-browser']={'status':'live',**info}
    except Exception as error:report['radio-browser']={'status':'failed','error':str(error)[:600]}
    print(json.dumps({'radio-browser':report['radio-browser']}),flush=True)
    try:
        rows,info=laut();save(args.output/'laut.json.gz',rows)
        report['laut.fm']={'status':'live',**info}
    except Exception as error:report['laut.fm']={'status':'failed','error':str(error)[:600]}
    (args.output/'fetch-report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__':main()
