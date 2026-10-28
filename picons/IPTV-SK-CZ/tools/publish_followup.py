"""Add reviewed logos to all existing immutable packages, then advance the catalogue."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen
import hashlib
import io
import json
import re
import stat
import subprocess
import zipfile
from PIL import Image

ROOT=Path('picons/IPTV-SK-CZ')
REPO='Evolution-by-Warder/PiconHub-Warder-Evolution'
BRANCH='radio/iptv-sk-cz-publish'
EXPECTED='d0a513519ab24418d6220122ff963d29134321b6'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],text=True).strip()
def head(branch):return git('ls-remote','origin','refs/heads/'+branch).split()[0]
def read(url,entry):
    assert url.startswith('https://raw.githubusercontent.com/'+REPO+'/')
    with urlopen(Request(url,headers={'User-Agent':'Warder-logo-followup'}),timeout=60) as response:raw=response.read(entry['bytes']+1)
    assert len(raw)==entry['bytes'] and sha(raw)==entry['sha256'],url
    return raw

def main():
    assert head('main')==EXPECTED,'Production advanced'
    base=json.loads((ROOT/'catalog/release.json').read_text())
    coverage=json.loads((ROOT/'catalog/followup-coverage.json').read_text())
    index=json.loads((ROOT/'catalog/followup-delta-index.json').read_text())
    replacement={}
    with zipfile.ZipFile(ROOT/'followup-delta.zip') as archive:
        assert len(archive.namelist())==len(index) and set(archive.namelist())==set(index)
        for entry in archive.infolist():
            name=entry.filename
            assert '..' not in Path(name).parts and not Path(name).is_absolute() and not stat.S_ISLNK(entry.external_attr>>16)
            raw=archive.read(entry);assert sha(raw)==index[name]
            if name.startswith('picons/'):
                _,resolution,style,filename=name.split('/')
                assert resolution in ('50x30','220x132','400x240') and style in ('transparent','white','black')
                assert re.fullmatch(r'(4097|5001|5002|8193)_0_(2|A)_([0-9A-F]+_){6}[0-9A-F]+\.png',filename)
                replacement.setdefault((resolution,style),{})[filename]=raw
            else:
                assert name.startswith('source-artwork/sources/') and Path(name).suffix.lower() in ('.png','.webp','.svg','.jpg','.jpeg','.gif')
                target=ROOT/name.removeprefix('source-artwork/');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    tasks=[(res,sty,entry) for res,styles in base['packages'].items() for sty,entry in styles.items()]
    with ThreadPoolExecutor(max_workers=5) as pool:downloads=list(pool.map(lambda task:read(task[2]['url'],task[2]),tasks))
    common=None;updated={}
    for (resolution,style,entry),raw in zip(tasks,downloads):
        with zipfile.ZipFile(io.BytesIO(raw)) as original:
            assert set(original.namelist())==set(entry['files']) and len(original.namelist())==len(entry['files'])
            files={name:original.read(name) for name in original.namelist()}
        assert all(sha(raw)==entry['files'][name] for name,raw in files.items())
        files.update(replacement[(resolution,style)])
        if common is None:common=set(files)
        assert set(files)==common and len(files)==coverage['png_files']//9
        path=ROOT/'packages'/('iptv-sk-cz-'+style+'-'+resolution+'.zip')
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as output:
            for name,png in sorted(files.items()):
                with Image.open(io.BytesIO(png)) as image:
                    assert image.size==tuple(map(int,resolution.split('x')));image.verify()
                info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=(stat.S_IFREG|0o644)<<16;output.writestr(info,png)
        raw=path.read_bytes();updated.setdefault(resolution,{})[style]={'resolution':resolution,'bytes':len(raw),'sha256':sha(raw),'files':{name:sha(png) for name,png in sorted(files.items())}}
    (ROOT/'followup-delta.zip').unlink()
    git('config','user.name','Warder release automation');git('config','user.email','warder-release@users.noreply.github.com')
    git('add',str(ROOT));git('commit','-m','Add reviewed official radio artwork to all nine immutable packages')
    revision=git('rev-parse','HEAD');git('push','origin','HEAD:refs/heads/'+BRANCH)
    jobs=[]
    for resolution,styles in updated.items():
        for style,entry in styles.items():
            entry['url']='https://raw.githubusercontent.com/'+REPO+'/'+revision+'/'+str(ROOT/'packages'/('iptv-sk-cz-'+style+'-'+resolution+'.zip'))
            jobs.append((entry['url'],entry))
    with ThreadPoolExecutor(max_workers=5) as pool:list(pool.map(lambda item:read(*item),jobs))
    base.update(version='2026.10.28-r2',stations=coverage['stations'],picon_stations=coverage['picon_stations'],missing_artwork=coverage['missing'],reference_files_per_variant=len(common),payload_commit=revision,packages=updated)
    (ROOT/'catalog/release.json').write_text(json.dumps(base,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'catalog/followup-publication.json').write_text(json.dumps({'status':'verified','payload_commit':revision,'picon_stations':coverage['picon_stations'],'missing_artwork':coverage['missing'],'references_per_variant':len(common),'all_nine_public_archives_verified':True,'existing_unselected_pngs_preserved':True},indent=2)+'\n')
    git('add',str(ROOT/'catalog'));git('commit','-m','Activate verified radio artwork follow-up in the shared catalogue');git('push','origin','HEAD:refs/heads/'+BRANCH)
    assert head('main')==EXPECTED,'Production advanced before activation'
    git('fetch','--no-tags','--depth=1','origin','main:refs/remotes/origin/main')
    git('push','origin','HEAD:refs/heads/main')
    print('Verified and activated',coverage['picon_stations'],'station entries;',len(common),'references per variant')

if __name__=='__main__':main()
