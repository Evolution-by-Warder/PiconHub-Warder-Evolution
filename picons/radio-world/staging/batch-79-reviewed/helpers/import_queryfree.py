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

sys.path.insert(0, str(Path.cwd()/'picons/radio-world/tools'))

BASE = 'https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'
LIMIT = 64 * 1024 * 1024  # Existing immutable single-ZIP limit.
PART_LIMIT = 32 * 1024 * 1024
PART_TARGET = 24 * 1024 * 1024  # Bound part sizes before compression.
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
    """Read legacy or multipart country packages without changing PNG bytes."""
    images={}
    parts=entry.get('parts') or [entry]
    for part in parts:
        with ZipFile(io.BytesIO(get(part))) as z:
            assert len(z.infolist())==len(part['files'])
            assert len(set(z.namelist()))==len(part['files'])
            assert set(z.namelist())==set(part['files'])
            for name,digest in part['files'].items():
                assert name not in images
                body=z.read(name)
                assert sha(body)==digest
                images[name]=body
    assert set(images)==set(entry['files'])
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

def _zip_bytes(images):
    out=io.BytesIO()
    with ZipFile(out,'w') as archive:
        for name,body in images:
            i=ZipInfo(name,(1980,1,1,0,0,0))
            i.external_attr=0o100644 << 16
            archive.writestr(i,body,compress_type=ZIP_DEFLATED,compresslevel=9)
    raw=out.getvalue()
    with ZipFile(io.BytesIO(raw)) as z:
        assert len(z.infolist())==len(images)
        assert len(set(z.namelist()))==len(images)
        assert set(z.namelist())==set(n for n,_body in images)
        assert all(sha(z.read(name))==sha(body) for name,body in images)
    return raw


def write_packages(code,size,style,items,dest,target_bytes=PART_TARGET):
    """Produce immutable <=32 MiB parts or an old-style single ZIP.

    Part boundaries are deterministic; each file occurs exactly once.  Every
    published part is independently read back and verified.
    """
    assert isinstance(items,dict) and items
    assert 4096 <= target_bytes <= PART_TARGET
    ordered=sorted(items.items())
    filename=f'iptv-{code.lower()}-{style}-{size}'
    root=f'picons/IPTV-{code}/packages/'
    inventory={name:sha(body) for name,body in ordered}
    estimated=sum(len(body)+len(name.encode('utf-8'))+192 for name,body in ordered)
    if estimated <= target_bytes:
        raw=_zip_bytes(ordered)
        if len(raw)<=LIMIT:
            path=root+filename+'.zip'
            target=dest/path
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(raw)
            assert target.read_bytes()==raw
            return dict(resolution=size,path=path,bytes=len(raw),sha256=sha(raw),files=inventory)
    groups=[]
    current=[]
    count=0
    for name,body in ordered:
        cost=len(body)+len(name.encode('utf-8'))+192
        assert cost<=target_bytes, 'Oversized single picon for fixed part limit'
        if current and count+cost>target_bytes:
            groups.append(current)
            current=[]
            count=0
        current.append((name,body))
        count+=cost
    if current:
        groups.append(current)
    assert 2<=len(groups)<=128, 'Unexpected multipart count'
    parts=[]
    seen=set()
    for number,group in enumerate(groups,1):
        path=root+filename+f'-part{number:02d}.zip'
        raw=_zip_bytes(group)
        assert 0<len(raw)<=PART_LIMIT, 'Multipart ZIP exceeds safe 32MiB limit'
        target=dest/path
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(raw)
        assert target.read_bytes()==raw
        files={name:sha(body) for name,body in group}
        assert not seen.intersection(files)
        seen.update(files)
        parts.append(dict(path=path,bytes=len(raw),sha256=sha(raw),files=files))
    assert seen==set(inventory)
    return dict(resolution=size,files=inventory,parts=parts)


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
    descriptor=write_packages(code,size,style,items,dest)
    assert prior.items()<=descriptor['files'].items()
    return code,size,style,descriptor,len(prior)

def build(temporary, snapshot):
    selection_raw=(STAGE/CONFIG.get('selection_filename','selection.json')).read_bytes()
    if 'selection_sha256' in CONFIG:
        assert sha(selection_raw)==CONFIG['selection_sha256']
    if CONFIG.get('selection_filename','').endswith('.gz'):
        import gzip
        selection_raw=gzip.decompress(selection_raw)
    selection=json.loads(selection_raw)['entries']
    assert len(selection)==len({r['ref'] for r in selection})==CONFIG['references']
    if CONFIG.get('visual_ledger_filename'):
        from visual_gate import read,validate_selection
        validate_selection(selection,read(STAGE/CONFIG['visual_ledger_filename']))
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
        assert all(current[k]==row['station'][k] for k in ('name','group'))
        assert sha(current['url'].encode()) == row['provenance']['catalog_url_sha256']['new']
        assert current['url'].split('?')[0] == row['station']['url']
        assert '?' not in row['station']['url']
    source=temporary/'sources'
    load_sources(selection,source)
    manifests, tasks, protected={}, [], 0
    reused={}
    reuse_rows={row['id']:row for row in json.loads(get(CONFIG['reuse_index']))['countries']} if CONFIG.get('reuse_index') else {}
    for row in json.loads(get(CONFIG['baseline_index']))['countries']:
        code=row['id']
        if code not in by_country:
            continue
        old=json.loads(get(row['release'])) if row['release'] else None
        reuse_row=reuse_rows.get(code)
        if reuse_row and reuse_row['release']:
            candidate=json.loads(get(reuse_row['release']))
            matches=True
            for size in SIZES:
                for style in STYLES:
                    before=old['packages'][size][style]['files'] if old else {}
                    expected=dict(before)
                    expected.update({entry['ref'].replace(':','_')+'.png':entry['variants'][size+'/'+style]['sha256']
                                     for entry in by_country[code]})
                    if candidate['packages'][size][style]['files']!=expected:
                        matches=False
            if matches:
                reused[code]=reuse_row['release']
                continue
        manifests[code]=dict(schema=1,status='verified',collection=row['collection'],country=code,
                             version='2026.11.07-history'+str(CONFIG['batch']),catalogue_stations=row['stations'],packages={})
        for size in SIZES:
            for style in sorted(STYLES):
                base=old['packages'][size][style] if old else None
                tasks.append((code,size,style,base,by_country[code],source,snapshot))
    assert len(tasks)==9*(len(by_country)-len(reused))
    with ThreadPoolExecutor(max_workers=8) as pool:
        for code,size,style,entry,count in pool.map(package,tasks):
            manifests[code]['packages'].setdefault(size,{})[style]=entry
            protected+=count
    (temporary/'packages.json').write_bytes(encoded(dict(
        preserved_pngs_in_new_archives=protected, countries=manifests, reused=reused, additions={c:len(v) for c,v in by_country.items()})))

def manifests(temporary,snapshot,payload):
    report=json.loads((temporary/'packages.json').read_bytes())
    for manifest in report['countries'].values():
        manifest['payload_commit']=payload
        for styles in manifest['packages'].values():
            for e in styles.values():
                for part in e.get('parts') or [e]:
                    part['url']=BASE+payload+'/'+part.pop('path')
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
        row['picons']+=count
        if row['id'] in report['reused']:
            row['status']='complete' if row['picons']==row['stations'] else 'partial'
            row['release']=report['reused'][row['id']]
            get(row['release'])
            continue
        path=f'picons/{row["collection"]}/catalog/release.json'
        raw=(snapshot/path).read_bytes()
        assert row['picons']<=row['stations']
        row['status']='complete' if row['picons']==row['stations'] else 'partial'
        row['release']=dict(commit=revision,url=BASE+revision+'/'+path,bytes=len(raw),sha256=sha(raw))
        assert get(row['release'])==raw
    assert len(result['countries'])==219
    assert sum(r['picons'] for r in result['countries'])==CONFIG['expected_coverage']
    (STAGE/'countries.proposed.json').write_bytes(encoded(result))
    (STAGE/'proof.json').write_bytes(encoded(dict(
        schema=1,payload_commit=payload,manifest_commit=revision,references=CONFIG['references'],pngs=9*CONFIG['references'],
        packages=sum(len(entry.get('parts') or [entry]) for country in report['countries'].values()
                     for styles in country['packages'].values() for entry in styles.values()),
        country_count=len(report['additions']),new_archives_countries=len(report['countries']),
        reused_package_countries=report['reused'],preserved_pngs_in_new_archives=report['preserved_pngs_in_new_archives'],
        additions=report['additions'])))

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
