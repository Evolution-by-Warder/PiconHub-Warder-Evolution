"""Combine verified country ZIPs without altering any existing image."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import re
import time
from urllib.error import URLError
from urllib.request import urlopen
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

BASE = 'https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'
STAGE = Path('picons/radio-world/staging/batch-34')
CANDIDATE = '9897e3e262e18aaacf89d7ed95ee398cff7164b7'
INDEX_PATH = 'picons/radio-world/catalog/countries.json'
SIZE = '220x132'
STYLES = {'black', 'transparent', 'white'}
LIMIT = 64 * 1024 * 1024

def sha(data):
    return hashlib.sha256(data).hexdigest()

def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()

def fetch(url, size, digest=None):
    if not url.startswith(BASE):
        raise ValueError(url)
    for attempt in range(3):
        try:
            with urlopen(url, timeout=25) as response:
                raw = response.read(size + 1)
            assert len(raw) <= size and (digest is None or (len(raw) == size and sha(raw) == digest)), url
            return raw
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)

def get(entry):
    return fetch(entry['url'],entry['bytes'],entry['sha256'])

def unzip(entry):
    with ZipFile(io.BytesIO(get(entry))) as archive:
        assert len(archive.infolist()) == len(entry['files']) and set(archive.namelist()) == entry['files'].keys()
        files = {name: archive.read(name) for name in entry['files']}
    assert all(sha(body) == entry['files'][name] for name, body in files.items())
    return files

def package(task):
    code, size, style, old, incoming, allowed, destination = task
    existing = unzip(old)
    new = unzip(incoming)
    assert allowed <= new.keys() and not (allowed & existing.keys())
    combined = dict(existing)
    combined.update({name: new[name] for name in allowed})
    path = Path(f'picons/IPTV-{code}/packages/iptv-{code.lower()}-{style}-{size}.zip')
    target = destination / path
    target.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(target,'w') as archive:
        for name, body in sorted(combined.items()):
            item = ZipInfo(name, (1980,1,1,0,0,0))
            item.external_attr = 0o100644 << 16
            archive.writestr(item, body, compress_type=ZIP_DEFLATED, compresslevel=9)
    raw = target.read_bytes()
    assert len(raw) <= LIMIT
    files = {name:sha(body) for name, body in sorted(combined.items())}
    assert old['files'].items() <= files.items()
    with ZipFile(io.BytesIO(raw)) as archive:
        assert len(archive.infolist()) == len(files) and set(archive.namelist()) == files.keys()
        assert all(sha(archive.read(n)) == digest for n,digest in files.items())
    return code, size, style, dict(resolution=size, path=str(path), bytes=len(raw), sha256=sha(raw), files=files)

def build(destination, intermediate):
    report = json.loads((STAGE/'production-reconciliation.json').read_bytes())
    prod = json.loads(fetch(BASE+report['production_base']+'/'+INDEX_PATH, 512*1024))
    candidate = json.loads(fetch(BASE+CANDIDATE+'/'+str(STAGE/'countries.proposed.json'), 512*1024))
    plan = json.loads(fetch(BASE+CANDIDATE+'/'+str(STAGE/'import-plan.json'), 1024*1024))
    by_id = {row['id']:row for row in candidate['countries']}
    selected = {row['id']:row for row in prod['countries'] if row['id'] in report['deferred']}
    allowed = {code:set() for code in selected}
    for e in plan['entries']:
        if e['country'] in allowed:
            name=e['reference'].replace(':','_')+'.png'
            assert re.fullmatch(r'(?:4097|5001|5002)_0_2_(?:[A-Fa-f0-9]+_){6}[A-Fa-f0-9]+\.png',name)
            allowed[e['country']].add(name)
    held = {row['reference'].replace(':','_')+'.png' for row in json.loads(Path('picons/radio-world/staging/batch-33/held-hdf-references.json').read_bytes())['entries']}
    manifests={}
    tasks=[]
    for code, row in selected.items():
        assert len(allowed[code])==report['deferred'][code]['references'] and not held & allowed[code]
        existing, incoming = (json.loads(get(r['release'])) for r in (row,by_id[code]))
        assert existing['collection']==incoming['collection']==row['collection']
        manifests[code]=dict(schema=1,status='verified',collection=row['collection'],country=code,version='2026.11.06-history34-union',catalogue_stations=row['stations'],packages={})
        for size, styles in existing['packages'].items():
            assert set(styles)==STYLES
            for style, old in styles.items():
                tasks.append((code,size,style,old,incoming['packages'][size][style],allowed[code],destination))
    assert len(tasks)==117 and sum(map(len,allowed.values()))==43
    with ThreadPoolExecutor(max_workers=8) as pool:
        for code,size,style,entry in pool.map(package,tasks):
            manifests[code]['packages'].setdefault(size,{})[style]=entry
    intermediate.write_bytes(encoded({code:dict(manifest=m,references=len(allowed[code])) for code,m in manifests.items()}))

def pin(intermediate, revision):
    index=json.loads((STAGE/'countries.production-safe.json').read_bytes())
    unions=json.loads(intermediate.read_bytes())
    proof={}
    for row in index['countries']:
        code=row['id']
        if code not in unions:
            continue
        info=unions[code]
        manifest=info['manifest']
        manifest['payload_commit']=revision
        for styles in manifest['packages'].values():
            for e in styles.values():
                e['url']=BASE+revision+'/'+e.pop('path')
        path=f'picons/{row["collection"]}/catalog/release.json'
        target=STAGE/'union-manifests'/f'{code}.json'
        target.parent.mkdir(parents=True,exist_ok=True)
        raw=encoded(manifest)
        target.write_bytes(raw)
        # Release URL is pinned to the canonical manifest in the next phase.
        proof[code]=dict(new_references=info['references'],manifest_path=path,bytes=len(raw),sha256=sha(raw))
    (STAGE/'union-proof.json').write_bytes(encoded(dict(payload_commit=revision,countries=proof)))

def final_index(revision):
    index=json.loads((STAGE/'countries.production-safe.json').read_bytes())
    proof=json.loads((STAGE/'union-proof.json').read_bytes())
    for row in index['countries']:
        info=proof['countries'].get(row['id'])
        if info is None:
            continue
        row['picons']+=info['new_references']
        assert row['picons']<=row['stations']
        row['status']='complete' if row['picons']==row['stations'] else 'partial'
        path=info['manifest_path']
        row['release']=dict(commit=revision,url=BASE+revision+'/'+path,bytes=info['bytes'],sha256=info['sha256'])
        assert get(row['release'])==(STAGE/'union-manifests'/f"{row['id']}.json").read_bytes()
    assert len(index['countries'])==219 and sum(bool(r['release']) for r in index['countries'])==79
    assert sum(r['picons'] for r in index['countries'])==1284
    proof['manifest_commit']=revision
    (STAGE/'union-proof.json').write_bytes(encoded(proof))
    (STAGE/'countries.full-candidate.json').write_bytes(encoded(index))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['build','pin','index'])
    parser.add_argument('intermediate',type=Path)
    parser.add_argument('target')
    args=parser.parse_args()
    if args.mode=='build':
        build(Path(args.target),args.intermediate)
    elif args.mode=='pin':
        pin(args.intermediate,args.target)
    else:
        final_index(args.target)
