"""Publish the four explicitly approved radio sheets; preserve all older PNGs.

Developer/Actions tooling only. All pixel bytes come from the reviewed artifact;
no Pillow version, image rendering or source fetching can alter approved logos.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request,urlopen
from types import ModuleType,SimpleNamespace
import argparse,csv,hashlib,importlib,io,json,os,re,stat,subprocess,sys,tempfile,time,zipfile
from PIL import Image

ROOT=Path('picons/IPTV-SK-CZ')
REPO='Evolution-by-Warder/PiconHub-Warder-Evolution'
PLAN=ROOT/'catalog/radio-logos-publication-plan-20261030.json'
BRANCH='radio/publish-reviewed-logos-20261030'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],text=True).strip()
def head():return git('ls-remote','origin','refs/heads/main').split()[0]
def write(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def checked(path,digest,size=None):
    raw=path.read_bytes();assert sha(raw)==digest,path
    assert size is None or len(raw)==size,path
    return raw

def read(url,entry):
    assert re.fullmatch(r'https://raw\.githubusercontent\.com/'+REPO+r'/[0-9a-f]{40}/picons/IPTV-SK-CZ/packages/iptv-sk-cz-(transparent|white|black)-(50x30|220x132|400x240)\.zip',url),url
    for attempt in range(3):
        try:
            with urlopen(Request(url,headers={'User-Agent':'Warder-approved-radio-artwork','Cache-Control':'no-cache'}),timeout=45) as response:raw=response.read(entry['bytes']+1)
            assert len(raw)==entry['bytes'] and sha(raw)==entry['sha256'],url
            return raw
        except OSError:
            if attempt==2:raise
            time.sleep(2)

def prepare():
    update=json.loads(PLAN.read_text())
    assert head()==update['expected_main_sha'],'Main advanced before publication; do not overwrite.'
    raw=checked(ROOT/'catalog/release.json',update['baseline_catalogue_sha256']);base=json.loads(raw)
    approval=json.loads(checked(ROOT/update['approval_path'],update['approval_sha256']))
    frozen=json.loads(checked(ROOT/update['plan_path'],update['plan_sha256']))
    assert approval['status']=='USER_APPROVED' and approval['source_graphics']==26 and approval['station_entries']==30
    assert approval['plan_sha256']==update['plan_sha256']
    assert {p['filename'] for p in approval['approved_previews']}=={f'Warder-radio-loga-{i}.png' for i in range(1,5)}
    assert approval['approved_slugs']==[r['slug'] for r in frozen['artwork']]
    assert approval['approved_station_keys']==[key for r in frozen['artwork'] for key in r['identity_keys']]
    assert set(approval['approved_station_keys'])=={r['identity_key'] for r in update['stations']}
    catalogue=json.loads((ROOT/'catalog/stations.json').read_text())['stations'];catalogue={r['identity_key']:r for r in catalogue}
    expected={};sources=ROOT/'sources/radio-logos-20261030'
    for art in frozen['artwork']:
        checked(sources/art['original_path'],art['source_sha256'])
        checked(sources/art['canonical_path'],art['canonical_sha256'])
        for key in art['identity_keys']:
            row=next(r for r in update['stations'] if r['identity_key']==key)
            station=catalogue[key]
            for field in ('country','name','picon_filename','reference_aliases'):assert row[field]==station.get(field,[])
            assert row['source_file']['path'].startswith('sources/radio-logos-20261030/originals/')
            checked(ROOT/row['source_file']['path'],row['source_file']['sha256'],row['source_file']['bytes'])
            for variant,meta in art['outputs'].items():expected[variant+'/'+row['picon_filename']]=meta['sha256']
    assert len(expected)==270 and expected==update['files']
    buffer=bytearray()
    for part in update['parts']:
        assert re.fullmatch(r'packages/staging/radio-logos-20261030/approved-pngs\.part\d{3}',part['path'])
        buffer.extend(checked(ROOT/part['path'],part['sha256'],part['bytes']))
    assert len(buffer)==update['delta_bytes'] and sha(buffer)==update['delta_sha256']
    replacement={}
    with zipfile.ZipFile(io.BytesIO(buffer)) as archive:
        assert len(archive.namelist())==270 and set(archive.namelist())==set(expected)
        assert archive.testzip() is None
        for info in archive.infolist():
            res,style,filename=info.filename.split('/')
            assert not stat.S_ISLNK(info.external_attr>>16)
            assert re.fullmatch(r'(4097|5001|5002|8193)_0_(2|A)_([0-9A-F]+_){6}[0-9A-F]+\.png',filename)
            raw=archive.read(info);assert sha(raw)==expected[info.filename]
            with Image.open(io.BytesIO(raw)) as image:
                assert image.size==tuple(map(int,res.split('x'))) and image.mode=='RGBA';image.verify()
            replacement.setdefault((res,style),{})[filename]=raw
    assert len(replacement)==9 and all(len(files)==30 for files in replacement.values())
    tasks=[(res,style,entry) for res,styles in base['packages'].items() for style,entry in styles.items()]
    with ThreadPoolExecutor(max_workers=3) as pool:downloads=list(pool.map(lambda t:read(t[2]['url'],t[2]),tasks))
    packages={};blobs={};common=None
    for (res,style,entry),raw in zip(tasks,downloads):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            assert len(archive.namelist())==len(entry['files']) and set(archive.namelist())==set(entry['files'])
            assert archive.testzip() is None
            files={name:archive.read(name) for name in archive.namelist()}
        assert all(sha(raw)==entry['files'][name] for name,raw in files.items())
        assert not set(files).intersection(replacement[(res,style)]),'Only missing picons may be added.'
        old=dict(files);files.update(replacement[(res,style)])
        assert all(files[name]==raw for name,raw in old.items())
        if common is None:common=set(files)
        assert set(files)==common and len(files)==294
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            for name,png in sorted(files.items()):
                info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=(stat.S_IFREG|0o644)<<16;archive.writestr(info,png)
        raw=output.getvalue();blobs[(res,style)]=raw
        packages.setdefault(res,{})[style]={'resolution':res,'bytes':len(raw),'sha256':sha(raw),'files':{name:sha(png) for name,png in sorted(files.items())}}
    assert base['picon_stations']==248 and base['missing_artwork']==73 and base['reference_files_per_variant']==264
    return update,base,approval,packages,blobs

def check_engine(data,blobs):
    # Import the unchanged receiver engine without Enigma2; only UI-owned enum
    # constants are supplied locally. Manifest parsing/PNG staging is real code.
    package='warder_publication_check';path=Path('plugin/src/Plugins/Extensions/WarderPiconHub').resolve()
    pkg=ModuleType(package);pkg.__path__=[str(path)];sys.modules[package]=pkg
    sync=ModuleType(package+'.warder_skin_sync');sync.UPDATE_MODE_SYNC_TV='sync_tv';sync.UPDATE_MODE_SYNC_TV_RADIO='sync_tv_radio';sync.UPDATE_MODE_INCREMENTAL='incremental';sys.modules[sync.__name__]=sync
    iptv=importlib.import_module(package+'.warder_iptv')
    verified=iptv.read_manifest(lambda url:io.BytesIO(json.dumps(data).encode()))
    with tempfile.TemporaryDirectory(prefix='warder-approved-radio-') as temp:
        folder=Path(temp)
        for res,styles in data['packages'].items():
            for style,entry in styles.items():
                ready=folder/(res+'-'+style);ready.mkdir();unrelated=ready/'personal-user-picon.png';unrelated.write_bytes(b'keep-exact')
                prefs={'update_mode':'incremental','resolution':res,'style':style,'destination':str(ready)}
                queue,job=iptv.plan(verified,prefs,str(folder));assert len(queue['iptv_names'])==294
                archive=folder/(res+'-'+style+'.zip');archive.write_bytes(blobs[(res,style)])
                stage=SimpleNamespace(queue=queue,ready=ready,hashes={},upstream=set())
                iptv.unpack(stage,archive,job,lambda:None)
                assert len(stage.hashes)==294 and stage.upstream==set(entry['files'])
                assert unrelated.read_bytes()==b'keep-exact'
                assert all(sha((ready/name).read_bytes())==digest for name,digest in entry['files'].items())
    return {'receiver_engine':'warder_iptv.py','variants_installed':9,'files_per_variant':294,'unrelated_picon_preserved':True,'physical_receiver_test':False}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify-only',action='store_true');args=parser.parse_args()
    update,base,approval,packages,blobs=prepare()
    provisional=dict(base,version=update['version'],picon_stations=278,missing_artwork=43,reference_files_per_variant=294,packages=packages)
    for res,styles in packages.items():
        for style,entry in styles.items():entry['url']='https://raw.githubusercontent.com/'+REPO+'/'+update['expected_main_sha']+'/'+str(ROOT/'packages'/('iptv-sk-cz-'+style+'-'+res+'.zip'))
    engine=check_engine(provisional,blobs)
    if args.verify_only:
        print(json.dumps({'status':'preflight-passed','approved_graphics':26,'new_stations':30,'packages':9,'protected_old_files_per_variant':264,'receiver_engine':engine}));return
    assert os.environ.get('GITHUB_REF_NAME')==BRANCH
    protected={p:git('rev-parse',update['expected_main_sha']+':'+p) for p in update['protected_paths']}
    assert all(git('rev-parse','HEAD:'+p)==digest for p,digest in protected.items())
    assert head()==update['expected_main_sha'],'Main advanced before staging.'
    targets=[]
    for (res,style),raw in blobs.items():
        p=ROOT/'packages'/('iptv-sk-cz-'+style+'-'+res+'.zip');p.write_bytes(raw);targets.append(str(p))
    for part in update['parts']:(ROOT/part['path']).unlink()
    git('config','user.name','Warder release automation');git('config','user.email','warder-release@users.noreply.github.com')
    git('add',*targets,*[str(ROOT/p['path']) for p in update['parts']]);git('commit','-m','Add 30 approved missing radio picons to all nine immutable archives')
    payload=git('rev-parse','HEAD');git('push','origin','HEAD:refs/heads/'+BRANCH)
    jobs=[]
    for res,styles in packages.items():
        for style,entry in styles.items():
            entry['url']='https://raw.githubusercontent.com/'+REPO+'/'+payload+'/'+str(ROOT/'packages'/('iptv-sk-cz-'+style+'-'+res+'.zip'));jobs.append((entry['url'],entry))
    with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(lambda item:read(*item),jobs))
    base.update(version=update['version'],picon_stations=278,missing_artwork=43,reference_files_per_variant=294,payload_commit=payload,packages=packages)
    engine=check_engine(base,blobs)
    write(ROOT/'catalog/release.json',base)
    missing=ROOT/'catalog/missing-artwork.csv';rows=list(csv.reader(io.StringIO(missing.read_text(encoding='utf-8-sig'))));keys={(r['country'],r['name']) for r in update['stations']};remaining=[r for r in rows if tuple(r[:2]) not in keys];assert len(rows)-len(remaining)==30
    with missing.open('w',encoding='utf-8-sig',newline='') as f:csv.writer(f).writerows(remaining)
    followup_path=ROOT/'catalog/followup-sources.json';followup=json.loads(followup_path.read_text());followup['rows'].extend(update['stations']);write(followup_path,followup)
    readme=ROOT/'README.md';text=readme.read_text();assert 'Picony pokrývajú 248 položiek, 264 súborov' in text and 'Zvyšných 73 položiek' in text
    text=text.replace('Picony pokrývajú 248 položiek, 264 súborov','Picony pokrývajú 278 položiek, 294 súborov').replace('Zvyšných 73 položiek','Zvyšných 43 položiek')
    text+='\nDoplnenie 30. októbra 2026: majiteľ schválil všetky štyri ukážky — 26 grafických predlôh pre 30 chýbajúcich položiek. Všetkých deväť archívov obsahuje rovnaké referencie. Staršie picony zostali byte za bytom zachované. [Schválenie](catalog/radio-logos-approval-20261030.json), [overenie publikácie](catalog/radio-logos-publication-20261030.json). Obnovte IPTV rádiá SK/CZ v PiconHube alebo FullHDGlass; nový IPK netreba.\n';readme.write_text(text)
    proof={'schema':1,'status':'verified','version':update['version'],'payload_commit':payload,'approved_preview_sheets':4,'source_graphics':26,'new_station_entries':30,'picon_stations':278,'missing_artwork':43,'reference_files_per_variant':294,'all_nine_public_archives_verified':True,'all_270_approved_png_bytes_preserved':True,'all_264_previous_pngs_preserved_per_variant':True,'approval_sha256':update['approval_sha256'],'receiver_engine':engine,'protected_git_trees':protected,'temporary_staging_parts_removed':True}
    write(ROOT/'catalog/radio-logos-publication-20261030.json',proof)
    git('add',str(ROOT/'catalog'),str(readme));git('commit','-m','Activate 278 verified SK/CZ radio picons shared by PiconHub and FullHDGlass [skip ci]')
    activated=git('rev-parse','HEAD');git('push','origin','HEAD:refs/heads/'+BRANCH)
    git('fetch','--no-tags','--filter=blob:none','--deepen=10','origin',BRANCH,'main')
    assert head()==update['expected_main_sha'],'Main advanced before activation.'
    assert all(git('rev-parse','HEAD:'+p)==digest for p,digest in protected.items())
    git('push','origin','HEAD:refs/heads/main')
    assert head()==activated
    with urlopen(Request('https://raw.githubusercontent.com/'+REPO+'/'+activated+'/'+str(ROOT/'catalog/release.json'),headers={'User-Agent':'Warder-approved-radio-check'}),timeout=30) as r:live=r.read(2000000)
    assert sha(live)==sha((ROOT/'catalog/release.json').read_bytes())
    print(json.dumps(dict(proof,activation_commit=activated),ensure_ascii=False))

if __name__=='__main__':main()
