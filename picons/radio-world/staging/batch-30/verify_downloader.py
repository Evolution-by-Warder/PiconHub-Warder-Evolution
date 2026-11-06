"""Replay staged batch bytes through the pinned Radio downloader, off production."""
import argparse
import copy
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile

parser=argparse.ArgumentParser()
parser.add_argument('radio',type=Path)
parser.add_argument('world',type=Path)
args=parser.parse_args()
sys.path.insert(0,str(args.radio/'src'))
from WarderRadio import picon_download as p
from WarderRadio.picon_catalogue import PiconCatalogue,INDEX_URL

root=Path(__file__).resolve().parent
manifest=json.loads((root/'manifest.json').read_text())
world={x['reference']:x for x in json.loads(gzip.decompress(args.world.read_bytes()))}
assert hashlib.sha256(args.world.read_bytes()).hexdigest()==manifest['catalogue_sha256']
for row in manifest['stations']:
    assert all(row[k]==world[row['reference']][k] for k in ('name','group','url'))
countries=sorted({x['country'] for x in manifest['stations']})
commit='a'*40
proof=[]
for style in p.STYLES:
    with tempfile.TemporaryDirectory() as tmp:
        index=copy.deepcopy(PiconCatalogue(tmp).document)
        routes={};requested=[]
        package=manifest['packages'][p.SIZE][style]
        body=(root/package['path']).read_bytes()
        for row in index['countries']:
            row.update(picons=0,status='unavailable',release=None)
            if row['id'] not in countries:continue
            collection=row['collection']
            entry=dict(package,resolution=p.SIZE,url=p.BASE+commit+'/picons/'+collection+'/packages/'+collection.lower()+'-'+style+'-220x132.zip')
            release={'schema':1,'status':'verified','collection':collection,'payload_commit':commit,'packages':{p.SIZE:{style:entry}}}
            raw=json.dumps(release).encode()
            url=p.BASE+commit+'/picons/'+collection+'/catalog/release.json'
            row.update(picons=sum(x['country']==row['id'] for x in manifest['stations']),status='partial',release={'url':url,'commit':commit,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)})
            routes[url]=raw;routes[entry['url']]=body
        routes[INDEX_URL]=json.dumps(index).encode()
        def opener(request,**kwargs):
            requested.append(request.full_url)
            return io.BytesIO(routes[request.full_url])
        def identities(directory,selected,task,opener):
            groups={x[2] for x in selected}
            return {r.replace(':','_')+'.png':x['name'] for r,x in world.items() if x['group'] in groups}
        settings=p.PiconSettings(tmp);settings.location=str(Path(tmp,'picons'));settings.countries=countries;settings.style=style
        Path(settings.location).mkdir()
        custom=Path(settings.location,manifest['stations'][0]['reference'].replace(':','_')+'.png');custom.write_bytes(b'user override')
        task=p.PiconTask();first=p.install(tmp,settings,task,opener,reference_loader=identities)
        assert first['failed']==0 and first['added']==len(manifest['stations'])-1 and first['preserved']==1,(first,task.drain())
        library=p.PiconLibrary(settings.location,style)
        assert all(library.lookup(x) for x in manifest['stations'])
        assert custom.read_bytes()==b'user override'
        requested.clear();repeat=p.install(tmp,settings,p.PiconTask(),opener,reference_loader=identities)
        assert repeat['unchanged']==first['added'] and not repeat['failed']
        assert not any(url.endswith('.zip') for url in requested)
        proof.append(dict(style=style,first=first,repeat=repeat,repeat_zip_requests=0,custom_preserved=True))
(root/'downloader-proof.json').write_text(json.dumps({'mode':'injected staging endpoints; real PNG ZIP bytes and pinned catalogue identities','radio_commit':'fe7fa6523e08ac0de466bba4e7ca831c246c6054','styles':proof,'receiver_hardware_tested':False},indent=2)+'\n')
print(json.dumps(proof))
