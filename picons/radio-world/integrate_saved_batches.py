"""Stage exact approved Radio PNG bytes; never render or publish production."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
from urllib.request import Request,urlopen
import zipfile

from prepare_country_packs import archive
from verify_batch import verify, verify_archive, RESOLUTIONS, STYLES

ROOT=Path(__file__).resolve().parents[2]
BASE='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'
WORLD='picons/IPTV-SK-CZ/catalog/global/search/2ae88890a953c2f68d3f20352ad56a7390645bd3ce189573dd94e50c8a65abfe.json.gz'
STAGE=ROOT/'picons/radio-world/staging/batch-32'
EXPECTED={29:'b393399ee9caf1dd202ee9d67d543d4c56cfc4e3df504e45cbf54006b3eedf9f',30:'48ca8f06da03295caeec9df85bbc9946eeb43699a3295533027700fcae7688ed',31:'c322a4c032f2f90e07bbd10edff16cf3f36fd69246129b9be8c73159316e98c2'}
sha=lambda data:hashlib.sha256(data).hexdigest()

def payload():
    raw=(ROOT/WORLD).read_bytes();assert sha(raw)==Path(WORLD).name.split('.')[0]
    world={x['reference']:x for x in json.loads(gzip.decompress(raw))}
    index=json.loads((ROOT/'picons/radio-world/catalog/countries.json').read_bytes())
    assert len(index['countries'])==219
    countries={x['id']:x for x in index['countries']}
    batches=[];incoming={};refs={}
    for number,digest in EXPECTED.items():
        folder=ROOT/f'picons/radio-world/staging/batch-{number}'
        assert sha((folder/'manifest.json').read_bytes())==digest
        verify(folder);m=json.loads((folder/'manifest.json').read_bytes());batches.append((folder,m))
        for station in m['stations']:
            ref,code=station['reference'],station['country'];assert ref not in refs
            assert all(station[k]==world[ref][k] for k in ('name','group','url'))
            assert countries[code]['name']==world[ref]['group'];refs[ref]=station
            incoming.setdefault(code,set()).add(ref.replace(':','_')+'.png')
    report=dict(schema=1,status='working-candidate-not-published',baseline_commit='648c52b5cc69038bd1b6a1d7ad5b5514c308458d',
                source_batches=EXPECTED,catalogue_sha256=sha(raw),incoming_references=len(refs),countries={},stations=list(refs.values()))
    baselines={}
    for code in incoming:
        path=ROOT/f'picons/IPTV-{code}/catalog/release.json';entry=countries[code]
        if entry['release'] is not None:
            raw=path.read_bytes();assert sha(raw)==entry['release']['sha256'] and len(raw)==entry['release']['bytes']
            baselines[code]=json.loads(raw)
        else:assert not path.exists()
        report['countries'][code]=dict(collection='IPTV-'+code,name=entry['name'],new_references=len(incoming[code]),catalogue_references=entry['stations'],preserved_references=0,packages={})
    for size in RESOLUTIONS:
        for style in STYLES:
            new={}
            for folder,m in batches:
                entry=m['packages'][size][style]
                for part in entry.get('parts',[entry]):
                    with zipfile.ZipFile(folder/part['path']) as z:
                        for name,digest in part['files'].items():
                            raw=z.read(name);assert sha(raw)==digest and name not in new;new[name]=raw
            for code,names in incoming.items():
                images={};previous=None
                if code in baselines:
                    previous=baselines[code]['packages'][size][style]
                    p=ROOT/f'picons/IPTV-{code}/packages'/previous['url'].rsplit('/',1)[-1]
                    verify_archive(p,previous,tuple(map(int,size.split('x'))),style)
                    with zipfile.ZipFile(p) as z:images={name:z.read(name) for name in previous['files']}
                    assert not set(images)&names,'Incoming reference already exists in approved baseline'
                    report['countries'][code]['preserved_references']=len(images)
                images.update({name:new[name] for name in names})
                path=ROOT/f'picons/IPTV-{code}/packages/iptv-{code.lower()}-{style}-{size}.zip';path.parent.mkdir(parents=True,exist_ok=True)
                entry=archive(path,images);verify_archive(path,entry,tuple(map(int,size.split('x'))),style)
                if previous:assert all(entry['files'][name]==digest for name,digest in previous['files'].items())
                assert entry['bytes']<=64*1024*1024
                report['countries'][code]['packages'].setdefault(size,{})[style]=entry
    STAGE.mkdir(parents=True,exist_ok=True)
    (STAGE/'candidate.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Prepared',len(refs),'exact saved references in',sorted(incoming))

def manifests(commit):
    r=json.loads((STAGE/'candidate.json').read_text());assert len(commit)==40
    for code,country in r['countries'].items():
        collection='IPTV-'+code;m=dict(schema=1,status='verified',collection=collection,country=code,version='2026.11.06-batches29-31',catalogue_stations=country['catalogue_references'],payload_commit=commit,packages={})
        for size,styles in country['packages'].items():
            m['packages'][size]={}
            for style,e in styles.items():
                path=f'picons/{collection}/packages/'+e['path'];raw=(ROOT/path).read_bytes()
                assert sha(raw)==e['sha256'] and len(raw)==e['bytes']
                m['packages'][size][style]=dict(resolution=size,url=BASE+commit+'/'+path,**{k:e[k] for k in ('bytes','sha256','files')})
        path=ROOT/f'picons/{collection}/catalog/release.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(m,indent=2)+'\n')

def downloader(radio):
    import sys
    sys.path.insert(0,str(Path(radio)/'src'))
    from WarderRadio import picon_download as p
    from WarderRadio.model import Store
    from WarderRadio.picon_catalogue import INDEX_URL,validate_index
    document=validate_index(json.loads((STAGE/'countries.proposed.json').read_text()));codes=sorted(json.loads((STAGE/'candidate.json').read_text())['countries'])
    reports=[];cache={}
    for style in p.STYLES:
        requests=[]
        def opener(req,**kwargs):
            url=req.full_url;requests.append(url)
            if url==INDEX_URL:return io.BytesIO(json.dumps(document).encode())
            if url not in cache:
                with urlopen(req,**kwargs) as response:cache[url]=response.read(64*1024*1024+1)
            return io.BytesIO(cache[url])
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(tmp);store.history=[{'name':'User radio','url':'https://example.org/radio','reference':'4097:0:2:1:2:3:0:0:0:0','group':'Custom'}];store.favourites=list(store.history);store.save();saved=Path(store.path).read_bytes()
            settings=p.PiconSettings(tmp);settings.location=str(Path(tmp)/'picons');settings.countries=codes;settings.style=style;settings.save();settings_raw=Path(settings.path).read_bytes()
            wanted=p.references(tmp,[x for x in p.COUNTRIES if x[0] in codes],p.PiconTask(),opener)
            covered=set()
            for row in document['countries']:
                if row['id'] not in codes:continue
                release=json.loads(opener(Request(row['release']['url']),timeout=30).read());covered|=set(release['packages'][p.SIZE][style]['files'])&set(wanted)
            custom=Path(settings.location)/sorted(covered)[0];custom.parent.mkdir();custom.write_bytes(b'user-owned PNG sentinel')
            requests.clear();first=p.install(tmp,settings,p.PiconTask(),opener)
            assert first['failed']==0 and first['added']==len(covered)-1 and first['preserved']==1,first
            archives=sum(url.endswith('.zip') for url in requests);assert archives==len(codes)
            assert custom.read_bytes()==b'user-owned PNG sentinel' and Path(store.path).read_bytes()==saved and Path(settings.path).read_bytes()==settings_raw
            requests.clear();repeat=p.install(tmp,settings,p.PiconTask(),opener);assert not repeat['failed'] and repeat['unchanged']==first['added']
            assert not any(url.endswith('.zip') for url in requests)
            reports.append(dict(style=style,first=first,repeat=repeat,archives=archives,repeat_zip_requests=0,user_data_preserved=True))
    (STAGE/'downloader-proof.json').write_text(json.dumps(dict(radio_commit='b7384bfdb55621beaf183ca6d40e9dedacaecdb9',mode='proposed index injection; real immutable GitHub manifests and ZIP downloads',countries=codes,styles=reports,hardware_tested=False),indent=2)+'\n')
    print(json.dumps(reports))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['payload','manifests','downloader']);parser.add_argument('argument',nargs='?');args=parser.parse_args()
    if args.action=='payload':payload()
    elif args.action=='manifests':manifests(args.argument)
    else:downloader(args.argument)
