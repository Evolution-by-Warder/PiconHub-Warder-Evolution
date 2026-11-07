"""Package exact saved Radio PNGs without rendering or changing approved bytes."""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import io
import json
import re
from pathlib import Path
import struct
import subprocess
import sys
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo
from PIL import Image

BASE = 'https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'
LIMIT = 64 * 1024 * 1024
STYLES = ('transparent','white','black')
SIZES = ('50x30','220x132','400x240')
STAGE = None
CONFIG = None

def sha(data):
    return hashlib.sha256(data).hexdigest()

def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False)+'\n').encode()

def get(entry):
    from urllib.request import urlopen
    from urllib.error import URLError
    import time
    url=entry['url']
    assert url.startswith(BASE)
    for attempt in range(3):
        try:
            with urlopen(url,timeout=30) as response:
                raw=response.read(entry['bytes']+1)
            assert len(raw)==entry['bytes'] and sha(raw)==entry['sha256'],url
            return raw
        except (URLError, TimeoutError):
            if attempt==2:
                raise
            time.sleep(2**attempt)

def unzip(entry):
    with ZipFile(io.BytesIO(get(entry))) as z:
        assert len(z.infolist())==len(entry['files']) and set(z.namelist())==entry['files'].keys()
        images={name:z.read(name) for name in entry['files']}
    assert all(sha(body)==entry['files'][name] for name,body in images.items())
    return images

def load_sources(selection, root):
    by_commit=defaultdict(set)
    for row in selection:
        by_commit[row['source_commit']].update(row['asset_root']+'/'+e['path'] for e in row['variants'].values())
    blobs=sorted({v['git_blob'] for row in selection for v in row['variants'].values()})
    subprocess.run(['git','fetch','--no-tags','--no-write-fetch-head','--filter=blob:none',
                    '--no-recurse-submodules','origin','--stdin'],
                    input=('\n'.join(blobs)+'\n').encode(),check=True)
    for commit, paths in by_commit.items():
        subprocess.run(['git','fetch','--depth=1','--filter=blob:none','--no-tags','origin',commit],check=True)
        checkout=root/commit
        checkout.mkdir(parents=True)
        arch=subprocess.Popen(['git','archive',commit,'--',*sorted(paths)],stdout=subprocess.PIPE)
        unpack=subprocess.run(['tar','-xf','-','-C',str(checkout)],stdin=arch.stdout)
        arch.stdout.close()
        assert arch.wait()==unpack.returncode==0

def package(task):
    code,size,style,old,rows,source,dest=task
    items=unzip(old) if old else {}
    prior={name:sha(body) for name,body in items.items()}
    for row in rows:
        e=row['variants'][size+'/'+style]
        name=row['ref'].replace(':','_')+'.png'
        assert name not in items
        data=(source/row['source_commit']/row['asset_root']/e['path']).read_bytes()
        assert (len(data),sha(data))==(e['bytes'],e['sha256'])
        assert hashlib.sha1(f'blob {len(data)}\0'.encode()+data).hexdigest()==e['git_blob']
        assert data[:16]==b'\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR'
        assert struct.unpack('>II',data[16:24])==tuple(map(int,size.split('x'))) and data[25]==6
        with Image.open(io.BytesIO(data)) as image:
            assert image.format=='PNG' and image.mode=='RGBA' and image.size==tuple(map(int,size.split('x')))
            image.verify()
        items[name]=data
    filename=re.compile(r'(?:4097|5001|5002)_0_2_(?:[A-Fa-f0-9]+_){6}[A-Fa-f0-9]+\.png')
    assert all(filename.fullmatch(name) for name in items)
    if size=='220x132':
        assert all(57<=len(body)<=2*1024*1024 for body in items.values())
        assert sum(map(len,items.values()))<=128*1024*1024
    path=f'picons/IPTV-{code}/packages/iptv-{code.lower()}-{style}-{size}.zip'
    target=dest/path
    target.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(target,'w') as archive:
        for name,body in sorted(items.items()):
            i=ZipInfo(name,(1980,1,1,0,0,0))
            i.external_attr=0o100644 << 16
            archive.writestr(i,body,compress_type=ZIP_DEFLATED,compresslevel=9)
    raw=target.read_bytes()
    assert len(raw)<=LIMIT
    files={name:sha(body) for name,body in sorted(items.items())}
    assert prior.items()<=files.items()
    with ZipFile(io.BytesIO(raw)) as z:
        assert len(z.infolist())==len(files) and set(z.namelist())==files.keys()
        assert all(sha(z.read(name))==digest for name,digest in files.items())
    return code,size,style,dict(resolution=size,path=path,bytes=len(raw),sha256=sha(raw),files=files),len(prior)

def build(temporary, snapshot):
    selection_raw=(STAGE/CONFIG.get('selection_filename','selection.json')).read_bytes()
    if 'selection_sha256' in CONFIG:
        assert sha(selection_raw)==CONFIG['selection_sha256']
    if CONFIG.get('selection_filename','').endswith('.gz'):
        import gzip
        selection_raw=gzip.decompress(selection_raw)
    selection=json.loads(selection_raw)['entries']
    assert len(selection)==len({r['ref'] for r in selection})==CONFIG['references']
    for row in selection:
        row['variants']={k:dict(sha256=d,bytes=n,git_blob=b,path=f'verified-assets/{d}.png')
                         for k,(d,n,b) in row['variants'].items()}
    by_country=defaultdict(list)
    for row in selection:
        by_country[row['country']].append(row)
    import gzip
    world_raw=get(CONFIG['world'])
    world={r['reference']:r for r in json.loads(gzip.decompress(world_raw))}
    baseline=json.loads(get(CONFIG['baseline_index']))
    catalogue={r['id']:r for r in baseline['countries']}
    held=set(CONFIG['held_references'])
    for row in selection:
        assert row['ref'] not in held and row['country'] in catalogue
        current=world[row['ref']]
        assert current['group']==catalogue[row['country']]['name']
        assert all(current[k]==row['station'][k] for k in ('name','url','group'))
    source=temporary/'sources'
    load_sources(selection,source)
    manifests, tasks, protected={}, [], 0
    for row in json.loads(get(CONFIG['baseline_index']))['countries']:
        code=row['id']
        if code not in by_country:
            continue
        old=json.loads(get(row['release'])) if row['release'] else None
        manifests[code]=dict(schema=1,status='verified',collection=row['collection'],country=code,
                             version='2026.11.07-history'+str(CONFIG['batch']),catalogue_stations=row['stations'],packages={})
        for size in SIZES:
            for style in sorted(STYLES):
                base=old['packages'][size][style] if old else None
                tasks.append((code,size,style,base,by_country[code],source,snapshot))
    assert len(tasks)==9*len(by_country)
    with ThreadPoolExecutor(max_workers=8) as pool:
        for code,size,style,entry,count in pool.map(package,tasks):
            manifests[code]['packages'].setdefault(size,{})[style]=entry
            protected+=count
    (temporary/'packages.json').write_bytes(encoded(dict(
        preserved_pngs=protected, countries=manifests, additions={c:len(v) for c,v in by_country.items()})))

def manifests(temporary,snapshot,payload):
    report=json.loads((temporary/'packages.json').read_bytes())
    for manifest in report['countries'].values():
        manifest['payload_commit']=payload
        for styles in manifest['packages'].values():
            for e in styles.values():
                e['url']=BASE+payload+'/'+e.pop('path')
        path=snapshot/'picons'/manifest['collection']/'catalog'/'release.json'
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(encoded(manifest))

def index(temporary,snapshot,payload,revision):
    result=json.loads(get(CONFIG['baseline_index']))
    report=json.loads((temporary/'packages.json').read_bytes())
    for row in result['countries']:
        count=report['additions'].get(row['id'])
        if not count:
            continue
        path=f'picons/{row["collection"]}/catalog/release.json'
        raw=(snapshot/path).read_bytes()
        row['picons']+=count
        assert row['picons']<=row['stations']
        row['status']='complete' if row['picons']==row['stations'] else 'partial'
        row['release']=dict(commit=revision,url=BASE+revision+'/'+path,bytes=len(raw),sha256=sha(raw))
        assert get(row['release'])==raw
    assert len(result['countries'])==219
    assert sum(r['picons'] for r in result['countries'])==CONFIG['expected_coverage']
    (STAGE/'countries.proposed.json').write_bytes(encoded(result))
    (STAGE/'proof.json').write_bytes(encoded(dict(
        schema=1,payload_commit=payload,manifest_commit=revision,references=CONFIG['references'],pngs=9*CONFIG['references'],packages=9*len(report['countries']),
        country_count=len(report['countries']),preserved_pngs=report['preserved_pngs'],additions=report['additions'])))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('configuration',type=Path)
    parser.add_argument('mode',choices=['build','manifests','index'])
    parser.add_argument('temporary',type=Path)
    parser.add_argument('snapshot',type=Path)
    parser.add_argument('revisions',nargs='*')
    args=parser.parse_args()
    CONFIG=json.loads(args.configuration.read_bytes())
    STAGE=args.configuration.parent
    globals()[args.mode](args.temporary,args.snapshot,*args.revisions)

