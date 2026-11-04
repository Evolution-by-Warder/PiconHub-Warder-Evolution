"""Apply the owner's exact Star The Mix removal without refreshing unrelated stations."""
import csv
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
from urllib.parse import unquote

from country_catalogue import export_packages, encoded
from update_world_radio import owner_removed, parse

SHA = lambda raw: hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def write_gzip(path, value):
    raw=encoded(value)
    blob=bytearray(gzip.compress(raw, mtime=0));blob[9]=255;blob=bytes(blob)
    path.write_bytes(blob)
    return dict(bytes=len(blob), decoded_bytes=len(raw), sha256=SHA(blob))


def remove_bouquet(text):
    # Inspect the targeted identity while preserving unrelated raw source bytes.
    lines=text.splitlines(keepends=True);out=[lines[0]];removed=0;i=1
    while i<len(lines):
        if (lines[i].startswith('#SERVICE ') and i+1<len(lines)
                and lines[i+1].startswith('#DESCRIPTION ')):
            fields=lines[i][9:].strip().split(':',10)
            row=dict(reference=':'.join(fields[:10]),name=lines[i+1][13:].strip(),
                     url=unquote(fields[10]) if len(fields)==11 else '')
            if owner_removed(row):
                removed+=1;i+=2;continue
        out.append(lines[i]);i+=1
    return ''.join(out),removed


def apply(root):
    root=Path(root);plan=json.loads((root/'sources/warder-radio-20261104-r5/plan.json').read_text())
    for relative,digest in plan['data_base_sha256'].items():
        assert SHA((root/relative).read_bytes())==digest, 'Catalogue baseline changed: '+relative
    changed=[];counts={};global_root=root/'catalog/global'
    for relative in ['bouquets/userbouquet.warder.sk-cz.radio','bouquets/userbouquet.warder.radio',
                     'catalog/source-radio.radio','catalog/global/userbouquet.warder.world.radio']:
        path=root/relative;before=path.read_text();after,n=remove_bouquet(before)
        assert n==(2 if relative.endswith('userbouquet.warder.world.radio') else 1),(relative,n)
        path.write_text(after);changed.append(relative);counts[relative]=n
    before_owned=json.loads((root/'catalog/stations.json').read_text())
    before_owned['stations']=[r for r in before_owned['stations'] if not owner_removed(r)]
    assert len(before_owned['stations'])==320
    # The legacy missing-artwork name list also serves old bouquet consumers.
    for key,value in before_owned.items():
        if isinstance(value,list) and value and isinstance(value[0],str):
            before_owned[key]=[v for v in value if v!='Star The Mix']
    before_owned['output_bouquet_sha256']=SHA((root/'bouquets/userbouquet.warder.sk-cz.radio').read_bytes())
    write_json(root/'catalog/stations.json',before_owned);changed.append('catalog/stations.json')
    missing=root/'catalog/missing-artwork.csv'
    with missing.open(encoding='utf-8-sig',newline='') as stream:rows=list(csv.reader(stream))
    rows=rows[:1]+[r for r in rows[1:] if r[1]!='Star The Mix']
    with missing.open('w',encoding='utf-8-sig',newline='') as stream:csv.writer(stream).writerows(rows)
    changed.append('catalog/missing-artwork.csv')
    stats={};before_rows={};after_rows={}
    for name in ['world-radio','world-radio.receiver','world-radio.review']:
        path=global_root/(name+'.json.gz');before=json.loads(gzip.decompress(path.read_bytes()))
        after=[r for r in before if not owner_removed(r)]
        expected={'world-radio':1,'world-radio.receiver':2,'world-radio.review':0}[name]
        assert len(before)-len(after)==expected,(name,len(before)-len(after))
        assert after==[r for r in before if not owner_removed(r)]
        before_rows[name]=before;after_rows[name]=after
        if expected:stats[name]=write_gzip(path,after);changed.append('catalog/global/'+path.name)
    path=global_root/'world-radio-master.json.gz';master=json.loads(gzip.decompress(path.read_bytes()));removed_master=0
    for source in master['sources'].values():
        rows=source['rows'];source['rows']=[r for r in rows if not owner_removed(r)];removed_master+=len(rows)-len(source['rows'])
    assert removed_master==1
    stats['master']=write_gzip(path,master);changed.append('catalog/global/'+path.name)
    countries=json.loads((global_root/'countries.json').read_text())
    for row in countries:
        if row.get('countrycode')=='CZ' or row.get('original_source_view'):
            row['stations']-=1
    assert next(r for r in countries if r.get('countrycode')=='CZ')['stations']==249
    write_json(global_root/'countries.json',countries);changed.append('catalog/global/countries.json')
    old_manifest=json.loads((global_root/'country-manifest.json').read_text())
    receiver=after_rows['world-radio.receiver']
    # Reuse all immutable country packages outside the two affected groups.
    # New files are emitted only for CZ, SOURCE, and the global search index.
    with tempfile.TemporaryDirectory() as tmp:
        generated=export_packages(receiver,countries,Path(tmp))
        replacements={r['id']:r for r in generated['countries'] if r['id'] in {'CZ','SOURCE'}}
        manifest=dict(schema=1,countries=[replacements.get(r['id'],r) for r in old_manifest['countries']],search=generated['search'])
        manifest['revision']=SHA(encoded(manifest))
        for row in list(replacements.values())+[manifest['search']]:
            relative='catalog/global/'+row['path'];target=root/relative;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes((Path(tmp)/row['path']).read_bytes());changed.append(relative)
        (global_root/'country-manifest.json').write_bytes(encoded(manifest));changed.append('catalog/global/country-manifest.json')
    assert all(row==old for row,old in zip(manifest['countries'],old_manifest['countries']) if row['id'] not in {'CZ','SOURCE'})
    report=json.loads((global_root/'build.json').read_text())
    report['built_at']=plan['prepared_at']
    report['master']=stats['master'];report['catalogue']=stats['world-radio'];report['receiver']=stats['world-radio.receiver']
    processing=report['processing'];processing['total_stations']=35560;processing['published_station_rows']=35560
    processing['known_stations_retained_during_outage']-=1;processing['input_station_rows']-=1
    processing['owner_requested_station_removals']=1
    if report.get('last_live_published_stations')==35561:report['last_live_published_stations']=35560
    report['receiver_rows']=40903;report['bouquet_bytes']=(global_root/'userbouquet.warder.world.radio').stat().st_size
    report['owned_sha256']=SHA((root/'bouquets/userbouquet.warder.sk-cz.radio').read_bytes())
    report['source_list']['stations']=5343;report['source_list']['source_sha256']=SHA((root/'catalog/source-radio.radio').read_bytes())
    report['source_list']['policy']='Original source names, URLs and order, excluding explicit owner removals.'
    report['country_packages_revision']=manifest['revision'];report['owner_update']=dict(date='2026-11-04',removed='Star The Mix',reason='Owner reports station does not work and requests removal; no new network availability claim.')
    write_json(global_root/'build.json',report);changed.append('catalog/global/build.json')
    world=root/'catalog/world-radio-update.json';report=json.loads(world.read_text());report['owned_stations']['CZ']-=1;report['total_stations']-=1
    for key,relative in [('owned_sha256','bouquets/userbouquet.warder.sk-cz.radio'),('source_sha256','catalog/source-radio.radio'),('bouquet_sha256','bouquets/userbouquet.warder.radio')]:report[key]=SHA((root/relative).read_bytes())
    report['owner_requested_station_removals']=['Star The Mix'];write_json(world,report);changed.append('catalog/world-radio-update.json')
    proof=dict(schema=1,request_date='2026-11-04',owner_requested_removal='Star The Mix',reference='4097:0:2:B929:9DC5:EC:0:0:0:0',
        removed_from_receiver_views=2,removed_from_main_country_catalogue=1,removed_from_master=removed_master,
        before_stations=35561,after_stations=35560,before_receiver_rows=40905,after_receiver_rows=40903,
        unchanged_receiver_rows_preserved=True,unaffected_country_packages_preserved=True,
        country_packages_revision=manifest['revision'],changed_files=changed,
        note='Content-addressed historical packages remain immutable for existing cached manifests; current manifests and every active catalogue exclude the station. Source import guards prevent its reappearance.')
    write_json(root/'catalog/owner-radio-update-20261104.json',proof);changed.append('catalog/owner-radio-update-20261104.json')
    return changed,proof
