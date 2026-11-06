"""Import frozen approved PNGs without rendering or changing existing approved bytes."""
import argparse
from collections import defaultdict
import gzip
import hashlib
import io
import json
from pathlib import Path
import zipfile
from PIL import Image
from prepare_country_packs import archive
from verify_batch import verify_archive,RESOLUTIONS,STYLES,REFERENCE

ROOT=Path(__file__).resolve().parents[2]
STAGE=ROOT/'picons/radio-world/staging/batch-34'
WORLD=ROOT/'picons/IPTV-SK-CZ/catalog/global/search/2ae88890a953c2f68d3f20352ad56a7390645bd3ce189573dd94e50c8a65abfe.json.gz'
BASE='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'
sha=lambda data:hashlib.sha256(data).hexdigest()

def payload(source):
    plan=json.loads((STAGE/'import-plan.json').read_text());assert sha(WORLD.read_bytes())==plan['catalogue_sha256']
    world={x['reference']:x for x in json.loads(gzip.decompress(WORLD.read_bytes()))}
    index=json.loads((ROOT/'picons/radio-world/staging/batch-32/countries.proposed.json').read_text())
    assert index['release_revision']=='849239b409f8d45aa35350061ff322288aaa3354' and len(index['countries'])==219
    countries={x['id']:x for x in index['countries']};incoming={};records={};held=[];verified=0
    variants={size+'/'+style for size in RESOLUTIONS for style in STYLES}
    for row in plan['entries']:
        ref,code=row['reference'],row['country'];assert REFERENCE.fullmatch(ref) and ref not in records
        assert set(row['renders'])==variants
        bodies={}
        for variant,e in row['renders'].items():
            body=(source/(e['sha256']+'.png')).read_bytes()
            assert sha(body)==e['sha256'] and len(body)==e['bytes']
            assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==e['git_blob']
            with Image.open(io.BytesIO(body)) as im:
                assert im.mode=='RGBA' and im.size==tuple(map(int,variant.split('/')[0].split('x')));im.verify()
            bodies[variant]=body;verified+=1
        records[ref]=row
        current=world.get(ref)
        assert current and code in countries
        assert all(current.get(k)==row['station'].get(k) for k in ('name','url','group'))
        assert countries[code]['name']==current['group'], 'HDF/group mismatch remains blocked'
        incoming[ref]=(code,bodies)
    assert len(records)==plan['references']==200 and verified==plan['pngs']==1800
    baselines={};old_images={};protected=0;duplicates=[]
    for code in {v[0] for v in incoming.values()}:
        mpath=ROOT/f'picons/IPTV-{code}/catalog/release.json';entry=countries[code]
        old_images[code]={}
        if entry['release'] is None:
            assert not mpath.exists();continue
        raw=mpath.read_bytes();assert sha(raw)==entry['release']['sha256'] and len(raw)==entry['release']['bytes']
        m=json.loads(raw);baselines[code]=m
        for size,styles in m['packages'].items():
            for style,e in styles.items():
                path=ROOT/f'picons/IPTV-{code}/packages'/e['url'].rsplit('/',1)[-1]
                verify_archive(path,e,tuple(map(int,size.split('x'))),style)
                with zipfile.ZipFile(path) as z:images={name:z.read(name) for name in e['files']}
                old_images[code][size+'/'+style]=images;protected+=len(images)
    for ref,(code,bodies) in list(incoming.items()):
        name=ref.replace(':','_')+'.png';collisions=[variant for variant in variants if name in old_images[code].get(variant,{})]
        if collisions:
            if len(collisions)==9 and all(old_images[code][v][name]==bodies[v] for v in collisions):duplicates.append(ref)
            else:held.append(dict(reference=ref,country=code,reason='Approved production PNG differs; retain existing bytes for all nine variants',conflicting_variants=[v for v in collisions if old_images[code][v][name]!=bodies[v]]))
            del incoming[ref]
    assert not duplicates and not held and len(incoming)==200
    by_country=defaultdict(dict)
    for ref,(code,bodies) in incoming.items():by_country[code][ref.replace(':','_')+'.png']=bodies
    report=dict(schema=1,status='working-candidate-not-published',batch=34,source_references=len(records),verified_source_pngs=verified,
                source_manifest_sha256=plan['historical_manifest_sha256'],catalogue_sha256=plan['catalogue_sha256'],
                no_rendering=True,protected_existing_pngs=protected,duplicate_references=duplicates,held=held,incoming_references=len(incoming),countries={})
    for code,rows in sorted(by_country.items()):
        report['countries'][code]=dict(collection='IPTV-'+code,name=countries[code]['name'],new_references=len(rows),catalogue_references=countries[code]['stations'],preserved_references=0,packages={})
        for size in RESOLUTIONS:
            for style in STYLES:
                variant=size+'/'+style;old=old_images[code].get(variant,{});images=dict(old)
                images.update({name:bodies[variant] for name,bodies in rows.items()})
                path=ROOT/f'picons/IPTV-{code}/packages/iptv-{code.lower()}-{style}-{size}.zip';path.parent.mkdir(parents=True,exist_ok=True)
                e=archive(path,images);assert all(e['files'][n]==sha(body) for n,body in old.items())
                verify_archive(path,e,tuple(map(int,size.split('x'))),style)
                assert e['bytes']<=64*1024*1024,'Country package exceeds unchanged receiver limits'
                report['countries'][code]['preserved_references']=len(old)
                report['countries'][code]['packages'].setdefault(size,{})[style]=e
    (STAGE/'candidate.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Imported',len(incoming),'exact approved references across',len(by_country),'countries; held',len(held),'duplicates',len(duplicates))

def manifests(commit):
    r=json.loads((STAGE/'candidate.json').read_text());assert len(commit)==40
    for code,country in r['countries'].items():
        collection='IPTV-'+code;m=dict(schema=1,status='verified',collection=collection,country=code,version='2026.11.06-history34',catalogue_stations=country['catalogue_references'],payload_commit=commit,packages={})
        for size,styles in country['packages'].items():
            m['packages'][size]={}
            for style,e in styles.items():
                path=f'picons/{collection}/packages/'+e['path'];raw=(ROOT/path).read_bytes();assert sha(raw)==e['sha256'] and len(raw)==e['bytes']
                m['packages'][size][style]=dict(resolution=size,url=BASE+commit+'/'+path,**{k:e[k] for k in ('bytes','sha256','files')})
        path=ROOT/f'picons/{collection}/catalog/release.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(m,indent=2)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['payload','manifests','downloader']);parser.add_argument('argument');args=parser.parse_args()
    if args.action=='payload':payload(Path(args.argument))
    elif args.action=='manifests':manifests(args.argument)
    else:
        import integrate_saved_batches as replay
        replay.STAGE=STAGE;replay.downloader(args.argument)
