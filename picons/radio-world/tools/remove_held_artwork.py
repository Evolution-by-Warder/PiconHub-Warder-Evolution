"""Remove newly imported rejected artwork while preserving all baseline PNGs."""
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import io,json,sys
from pathlib import Path
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
sys.path.insert(0,str(Path(__file__).parent))
from saved_artwork_import import get,unzip,sha,encoded,LIMIT,STYLES,SIZES

CONFIG=None
STAGE=None

def package(task):
    code,size,style,entry,names,snapshot=task
    images=unzip(entry)
    assert names<=images.keys()
    images={name:body for name,body in images.items() if name not in names}
    assert images
    path=f'picons/IPTV-{code}/packages/iptv-{code.lower()}-{style}-{size}.zip'
    target=snapshot/path
    target.parent.mkdir(parents=True,exist_ok=True)
    with ZipFile(target,'w') as archive:
        for name,body in sorted(images.items()):
            item=ZipInfo(name,(1980,1,1,0,0,0));item.external_attr=0o100644 << 16
            archive.writestr(item,body,compress_type=ZIP_DEFLATED,compresslevel=9)
    raw=target.read_bytes()
    assert len(raw)<=LIMIT
    if size=='220x132':
        assert sum(map(len,images.values()))<=128*1024*1024
        assert all(57<=len(body)<=2*1024*1024 for body in images.values())
    files={name:sha(body) for name,body in images.items()}
    assert all(entry['files'][name]==digest for name,digest in files.items())
    with ZipFile(io.BytesIO(raw)) as archive:
        assert len(archive.infolist())==len(files)
        assert all(sha(archive.read(name))==digest for name,digest in files.items())
    return code,size,style,dict(resolution=size,path=path,bytes=len(raw),sha256=sha(raw),files=files)

def build(temporary,snapshot):
    rows={r['id']:r for r in json.loads(get(CONFIG['baseline_index']))['countries']}
    protected={r['id']:r for r in json.loads(get(CONFIG['protected_index']))['countries']}
    revoked=defaultdict(set)
    for row in CONFIG['revoked']:
        revoked[row['country']].add(row['ref'].replace(':','_')+'.png')
    assert sum(map(len,revoked.values()))==CONFIG['revoked_count']
    tasks=[];manifests={};unavailable=[]
    for code,names in revoked.items():
        current=json.loads(get(rows[code]['release']))
        baseline=json.loads(get(protected[code]['release'])) if protected[code]['release'] else None
        inventories=[set(entry['files']) for styles in current['packages'].values() for entry in styles.values()]
        assert len(inventories)==9 and all(inventory==inventories[0] for inventory in inventories)
        if inventories[0]==names:
            assert baseline is None and rows[code]['picons']==len(names)
            unavailable.append(code)
            continue
        manifests[code]=dict(current,version=CONFIG['version'],packages={})
        for size,styles in current['packages'].items():
            for style,entry in styles.items():
                assert names<=entry['files'].keys()
                if baseline:
                    old=baseline['packages'][size][style]['files']
                    assert not names & old.keys()
                    assert old.items()<=entry['files'].items()
                tasks.append((code,size,style,entry,names,snapshot))
    with ThreadPoolExecutor(max_workers=8) as pool:
        for code,size,style,entry in pool.map(package,tasks):
            manifests[code]['packages'].setdefault(size,{})[style]=entry
    (temporary/'packages.json').write_bytes(encoded(dict(countries=manifests,unavailable=unavailable,additions={c:-len(v) for c,v in revoked.items()})))

def manifests(temporary,snapshot,payload):
    report=json.loads((temporary/'packages.json').read_bytes())
    for manifest in report['countries'].values():
        manifest['payload_commit']=payload
        for styles in manifest['packages'].values():
            for entry in styles.values():
                entry['url']=CONFIG['base_url']+payload+'/'+entry.pop('path')
        path=snapshot/'picons'/manifest['collection']/'catalog/release.json'
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(encoded(manifest))

def index(temporary,snapshot,payload,revision):
    result=json.loads(get(CONFIG['baseline_index']))
    report=json.loads((temporary/'packages.json').read_bytes())
    for row in result['countries']:
        if row['id'] not in report['additions']:continue
        row['picons']+=report['additions'][row['id']]
        assert row['picons']>=0
        if row['picons']==0:
            assert row['id'] in report['unavailable']
            row['status']='unavailable'
            row['release']=None
            continue
        path=f'picons/{row["collection"]}/catalog/release.json';raw=(snapshot/path).read_bytes()
        row['status']='complete' if row['picons']==row['stations'] else 'partial'
        row['release']=dict(commit=revision,url=CONFIG['base_url']+revision+'/'+path,bytes=len(raw),sha256=sha(raw))
        assert get(row['release'])==raw
    assert sum(r['picons'] for r in result['countries'])==CONFIG['expected_coverage']
    (STAGE/'countries.proposed.json').write_bytes(encoded(result))
    (STAGE/'proof.json').write_bytes(encoded(dict(schema=1,payload_commit=payload,manifest_commit=revision,
        accepted_new_references=CONFIG['accepted_new_references'],revoked=CONFIG['revoked'],packages=9*len(report['countries']),additions=report['additions'])))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('configuration',type=Path)
    parser.add_argument('mode',choices=['build','manifests','index']);parser.add_argument('temporary',type=Path)
    parser.add_argument('snapshot',type=Path);parser.add_argument('revisions',nargs='*')
    args=parser.parse_args();CONFIG=json.loads(args.configuration.read_bytes());STAGE=args.configuration.parent
    globals()[args.mode](args.temporary,args.snapshot,*args.revisions)
