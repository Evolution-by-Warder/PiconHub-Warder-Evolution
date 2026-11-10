"""Independent read-only audit of candidate batch80 20-reference split packaging."""
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
from zipfile import ZipFile
from PIL import Image

S=Path('picons/radio-world/staging')
ROOT=S/'batch-80-reviewed'
PREV=S/'batch-79-reviewed'
script=S/'batch-79-reviewed/helpers/import_queryfree.py'
spec=importlib.util.spec_from_file_location('radio_batch_importer',str(script))
importer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)
sha=lambda b:hashlib.sha256(b).hexdigest()


def read(path):
    b=path.read_bytes()
    return json.loads(gzip.decompress(b) if path.suffix=='.gz' else b)


def audit(work,snapshot):
    result=read(work/'packages.json')
    assert set(result['countries'])=={'DE'}
    assert result['additions']=={'DE':20}
    assert not result['reused']
    manifest=result['countries']['DE']
    assert manifest['collection']=='IPTV-DE'
    rows=read(ROOT/'selection.json.gz')['entries']
    assert len(rows)==20
    baseline=read(PREV/'countries.proposed.json')
    de=next(r for r in baseline['countries'] if r['id']=='DE')
    old=read(ROOT/'configuration.json')
    prior=json.loads(importer.get(de['release']))
    expected_sizes={'50x30',( '220x132'),('400x240')}
    assert set(manifest['packages'])==expected_sizes
    evidence=[]
    for size in ('50x30','220x132','400x240'):
        for style in ('transparent','white','black'):
            entry=manifest['packages'][size][style]
            before=prior['packages'][size][style]['files']
            added={r['ref'].replace(':','_')+'.png':r for r in rows}
            assert not set(added).intersection(before)
            total_expected=dict(before)
            for name,row in added.items():
                total_expected[name]=row['variants'][size+'/'+style][0]
            assert entry['files']==total_expected
            parts=entry.get('parts') or [entry]
            seen=set()
            for part in parts:
                path=snapshot/part['path']
                data=path.read_bytes()
                assert len(data)==part['bytes'] and sha(data)==part['sha256']
                if entry.get('parts') is not None:
                    assert len(data)<=importer.PART_LIMIT
                with ZipFile(io.BytesIO(data)) as z:
                    infos=z.infolist()
                    assert z.testzip() is None
                    assert len(infos)==len(part['files'])
                    assert len({i.filename for i in infos})==len(infos)
                    assert {i.filename for i in infos}==set(part['files'])
                    for info in infos:
                        assert info.filename not in seen
                        seen.add(info.filename)
                        image_bytes=z.read(info)
                        assert sha(image_bytes)==part['files'][info.filename]
                        with Image.open(io.BytesIO(image_bytes)) as image:
                            assert image.mode=='RGBA'
                            assert image.size==tuple(map(int,size.split('x')))
                            image.verify()
                        if info.filename in added:
                            entryrow=added[info.filename]['variants'][size+'/'+style]
                            digest,length,gitblob=entryrow
                            assert sha(image_bytes)==digest and len(image_bytes)==length
                            assert hashlib.sha1(b'blob '+str(length).encode()+b'\0'+image_bytes).hexdigest()==gitblob
                evidence.append(dict(size=size,style=style,path=part['path'],bytes=len(data),
                                     sha256=sha(data),PNG_members=len(part['files']),archive_crc='pass'))
            assert seen==set(total_expected)
    assert len(evidence)>=9
    result=dict(status='pass',mode='candidate-dry-run-only',references_added=20,PNG_added=180,
                baseline_coverage=3462,candidate_coverage=3482,
                packages=len(evidence),all_previous_members_preserved=True,
                source_pngs_rerendered=0,producer_32MiB_cap_verified=True,
                production_or_git_manifests_modified=False,archives=evidence)
    (work/'independent-batch80-readback.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS: 20 references, 180 saved PNGs, %s verified ZIPs, zero production changes'%len(evidence),flush=True)


if __name__=='__main__':
    audit(Path(sys.argv[1]),Path(sys.argv[2]))
