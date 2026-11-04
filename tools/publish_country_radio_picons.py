"""Build and publish independent, reviewed Warder IPTV radio country archives."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from urllib.request import urlopen
import zipfile
from PIL import Image

REPO='Evolution-by-Warder/PiconHub-Warder-Evolution'
COUNTRIES=('AT','DE','HU','PL')
SHA=lambda raw:hashlib.sha256(raw).hexdigest()


def git(*args):
    for attempt in range(3):
        try:return subprocess.check_output(['git',*args],text=True).strip()
        except subprocess.CalledProcessError:
            if args[0]!='push' or attempt==2:raise
            time.sleep(3)


def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def png(image):
    out=io.BytesIO();image.save(out,format='PNG');return out.getvalue()


def archive(files):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as target:
        for name,raw in sorted(files.items()):
            entry=zipfile.ZipInfo(name,(1980,1,1,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED;entry.external_attr=(stat.S_IFREG|0o644)<<16;target.writestr(entry,raw)
    return out.getvalue()


def runtime():
    # Native planner module is independent of Enigma2; skip the GUI package initializer.
    from types import ModuleType
    folder=Path('plugin/src/Plugins/Extensions/WarderPiconHub').resolve()
    name='country_picon_verifier'
    if name+'.warder_iptv' in sys.modules:return sys.modules[name+'.warder_iptv']
    package=ModuleType(name);package.__path__=[str(folder)];sys.modules[name]=package
    spec=importlib.util.spec_from_file_location(name+'.warder_iptv',folder/'warder_iptv.py')
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module


def build(country,revision,approved_folder=None):
    root=Path('picons/IPTV-'+country);plan=json.loads((root/'plan.json').read_text());iptv=runtime()
    assert plan['collection']=='IPTV-'+country
    masters={}
    for style,digest in plan['master_sha256'].items():
        raw=Path('plugin/artwork/templates/picons',style+'-sablona.png').read_bytes();assert SHA(raw)==digest
        masters[style]=Image.open(io.BytesIO(raw)).convert('RGBA')
    dab={}
    for style,entry in (plan.get('approved_dab_packages') or {}).items():
        if approved_folder:raw=(approved_folder/('dab-'+style+'-220x132.zip')).read_bytes()
        else:
            with urlopen(entry['url'],timeout=30) as response:raw=response.read(entry['bytes']+1)
        assert len(raw)==entry['bytes'] and SHA(raw)==entry['sha256'];dab[style]=zipfile.ZipFile(io.BytesIO(raw))
    prepared={(size,style):{} for size in iptv.RESOLUTIONS for style in iptv.STYLES}
    for artwork in plan['artwork']:
        if 'frozen_review_assets' in artwork:
            # Owner-approved exact Warder PNG bytes. No rasterisation,
            # colour repair or second resizing: preserve approved output.
            source = (root / artwork['path']).read_bytes()
            assert SHA(source) == artwork['sha256'], 'Owner-approved source file changed'
            for resolution in iptv.RESOLUTIONS:
                for style in iptv.STYLES:
                    path = root / artwork['frozen_review_assets'][resolution][style]
                    body = path.read_bytes()
                    assert SHA(body) == artwork['render_sha256'][resolution][style], 'Approved Warder PNG changed'
                    with Image.open(io.BytesIO(body)) as image:
                        assert image.format == 'PNG' and image.mode == 'RGBA'
                        assert image.size == tuple(map(int, resolution.split('x')))
                        image.verify()
                    for station in artwork['stations']:
                        assert station['country'] == country
                        name = station['target']
                        assert iptv.reference_filename(name) and name not in prepared[(resolution,style)]
                        prepared[(resolution,style)][name] = body
            continue
        if 'approved_dab_filename' not in artwork:
            raw=(root/artwork['path']).read_bytes();assert SHA(raw)==artwork['sha256'];original=Image.open(io.BytesIO(raw)).convert('RGBA')
            for flag,colour in [('light_panel','white'),('dark_panel','black')]:
                if artwork.get(flag):panel=Image.new('RGBA',(original.width+16,original.height+16),colour);panel.alpha_composite(original,(8,8));original=panel
            original.thumbnail((192,104),Image.Resampling.LANCZOS)
        for style in iptv.STYLES:
            if 'approved_dab_filename' in artwork:
                name=artwork['approved_dab_filename'];raw=dab[style].read(name);assert SHA(raw)==plan['approved_dab_packages'][style]['files'][name]
                image=Image.open(io.BytesIO(raw)).convert('RGBA')
            else:
                image=masters[style].copy() if style!='transparent' else Image.new('RGBA',(220,132));image.alpha_composite(original,((220-original.width)//2,(132-original.height)//2))
            for resolution in iptv.RESOLUTIONS:
                size=tuple(map(int,resolution.split('x')));body=png(image if size==image.size else image.resize(size,Image.Resampling.LANCZOS))
                assert SHA(body)==artwork['render_sha256'][resolution][style],'Reviewed image changed'
                for station in artwork['stations']:
                    assert station['country']==country
                    name=station['target'];assert iptv.reference_filename(name) and name not in prepared[(resolution,style)]
                    prepared[(resolution,style)][name]=body
    manifest=dict(schema=1,status='verified',collection=plan['collection'],country=country,country_name=plan['country_name'],version=plan['version'],stations=plan['covered_stations'],catalogue_stations=plan['catalogue_stations'],reference_files_per_variant=plan['reference_files_per_variant'],packages={})
    packages={}
    for (resolution,style),files in prepared.items():
        assert len(files)==manifest['reference_files_per_variant'];body=archive(files);name=plan['collection'].lower()+'-'+style+'-'+resolution+'.zip';packages[name]=body
        assert len(body)<=64*1024*1024
        manifest['packages'].setdefault(resolution,{})[style]=dict(resolution=resolution,url='https://raw.githubusercontent.com/'+REPO+'/'+revision+'/'+str(root/'packages'/name),bytes=len(body),sha256=SHA(body),files={n:SHA(b) for n,b in sorted(files.items())})
    return root,plan,manifest,packages


def verify_receiver(manifest,packages):
    iptv=runtime();parsed=iptv.read_manifest(lambda u:io.BytesIO(json.dumps(manifest).encode()),manifest['collection'])
    for resolution,styles in parsed['packages'].items():
        for style,entry in styles.items():
            with tempfile.TemporaryDirectory() as folder:
                target=Path(folder,'picons');target.mkdir();(target/'unrelated.png').write_bytes(b'keep')
                prefs=dict(update_mode=iptv.sync.UPDATE_MODE_INCREMENTAL,style=style,resolution=resolution,destination=str(target))
                queue,job=iptv.plan(parsed,prefs,folder);assert job['selector_id']==manifest['collection']
                stage=SimpleNamespace(queue=queue,ready=target,hashes={},upstream=set());path=Path(folder,'package.zip');path.write_bytes(packages[entry['url'].rsplit('/',1)[-1]])
                iptv.unpack(stage,path,job,lambda:None)
                assert stage.hashes==entry['files'] and (target/'unrelated.png').read_bytes()==b'keep'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=Path('/tmp/country-radio-picons'));parser.add_argument('--approved-dab-folder',type=Path);parser.add_argument('--publish',action='store_true');args=parser.parse_args()
    baseline=json.loads(Path('tools/country-radio-publication.json').read_text())['baseline']
    revision=os.environ.get('GITHUB_SHA',baseline);results=[build(country,revision,args.approved_dab_folder) for country in COUNTRIES]
    summary=[]
    for root,plan,manifest,packages in results:
        verify_receiver(manifest,packages)
        for name,raw in packages.items():path=args.output/root/'packages'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        write_json(args.output/root/'catalog/release.json',manifest)
        summary.append(dict(country=plan['country_name'],stations=plan['covered_stations'],total=plan['catalogue_stations'],references=plan['reference_files_per_variant'],variants=9))
    print(json.dumps(summary),flush=True)
    if not args.publish:return
    assert os.environ['GITHUB_REF_NAME']=='radio/country-picons-20261104-1'
    assert git('ls-remote','origin','refs/heads/main').split()[0]==baseline,'Main advanced; publication stopped'
    git('config','user.name','Warder radio automation');git('config','user.email','warder-radio@users.noreply.github.com')
    payload_paths=[]
    for root,plan,manifest,packages in results:
        for name,raw in packages.items():path=root/'packages'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw);payload_paths.append(str(path))
    git('add',*payload_paths);git('commit','-m','Publish separate Austria Germany Hungary Poland IPTV radio picon archives')
    payload=git('rev-parse','HEAD');git('push','origin','HEAD:refs/heads/radio/country-picons-20261104-1')
    tasks=[]
    for root,plan,manifest,packages in results:
        for styles in manifest['packages'].values():
            for entry in styles.values():entry['url']=entry['url'].replace(revision,payload);tasks.append(entry)
        manifest['payload_commit']=payload
    def public(entry):
        with urlopen(entry['url'],timeout=30) as response:raw=response.read(entry['bytes']+1)
        assert len(raw)==entry['bytes'] and SHA(raw)==entry['sha256']
        with zipfile.ZipFile(io.BytesIO(raw)) as z:assert {n:SHA(z.read(n)) for n in z.namelist()}==entry['files']
    list(ThreadPoolExecutor(4).map(public,tasks))
    final=[]
    for root,plan,manifest,packages in results:
        verify_receiver(manifest,packages);write_json(root/'catalog/release.json',manifest);final.append(str(root/'catalog/release.json'))
        readme=root/'README.md';readme.write_text('# IPTV radios '+plan['country_name']+'\n\nIndependent Warder country collection. Current reviewed batch: '+str(plan['covered_stations'])+' of '+str(plan['catalogue_stations'])+' catalogue stations, '+str(plan['reference_files_per_variant'])+' references in every variant. Coverage is partial.\n\n50×30, 220×132, 400×240; transparent, white, black. Original Warder masters and approved station artwork. See [provenance](plan.json) and [remaining stations](coverage.json).\n')
        final.append(str(readme))
    report=Path('reports/country-radio-picons-20261104.json');write_json(report,dict(status='verified',payload_commit=payload,countries=summary,public_archives_verified=36,receiver_engine_verified=True,physical_receiver_tested=False));final.append(str(report))
    git('add',*final);git('commit','-m','Activate four independent verified country picon collections [skip ci]');git('push','origin','HEAD:refs/heads/radio/country-picons-20261104-1')
    assert git('ls-remote','origin','refs/heads/main').split()[0]==baseline,'Main advanced before activation'
    git('push','--force-with-lease=refs/heads/main:'+baseline,'origin','HEAD:refs/heads/main')
    print('Activated country packages:',git('rev-parse','HEAD'),flush=True)


if __name__=='__main__':main()
