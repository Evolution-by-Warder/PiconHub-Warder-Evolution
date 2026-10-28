"""Verify a small owner-approved delta, preserve all older picons, publish atomically."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request,urlopen
import csv,hashlib,io,json,os,re,stat,subprocess,time,zipfile
from PIL import Image
ROOT=Path('picons/IPTV-SK-CZ')
REPO='Evolution-by-Warder/PiconHub-Warder-Evolution'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],text=True).strip()
def head():return git('ls-remote','origin','refs/heads/main').split()[0]
def write(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
def read(url,entry):
    assert url.startswith('https://raw.githubusercontent.com/'+REPO+'/')
    for attempt in range(3):
        try:
            with urlopen(Request(url,headers={'User-Agent':'Warder-owner-artwork-publication'}),timeout=30) as response:raw=response.read(entry['bytes']+1)
            assert len(raw)==entry['bytes'] and sha(raw)==entry['sha256'],url
            return raw
        except OSError:
            if attempt==2:raise
            time.sleep(2)
def main():
    update=json.loads((ROOT/'catalog/owner-artwork-update.json').read_text())
    assert head()==update['expected_main_sha'],'Production advanced; do not overwrite it'
    branch=os.environ['GITHUB_REF_NAME'];assert branch.startswith('radio/owner-artwork-')
    base=json.loads((ROOT/'catalog/release.json').read_text())
    stations=json.loads((ROOT/'catalog/stations.json').read_text())['stations']
    additions=update['stations'];assert len({r['identity_key'] for r in additions})==len(additions)
    for row in additions:
        match=next(r for r in stations if r['country']==row['country'] and r['identity_key']==row['identity_key'])
        assert row['picon_filename']==match['picon_filename'] and row['reference_aliases']==match.get('reference_aliases',[])
        source=row['source_file'];assert source['path'].startswith('sources/owner-supplied/') and '..' not in Path(source['path']).parts
        raw=(ROOT/source['path']).read_bytes();assert len(raw)==source['bytes'] and sha(raw)==source['sha256']
    raw=(ROOT/'owner-artwork-delta.zip').read_bytes();assert sha(raw)==update['delta_sha256']
    replacement={}
    with zipfile.ZipFile(io.BytesIO(raw)) as delta:
        assert set(delta.namelist())==set(update['files']) and len(delta.namelist())==len(update['files'])
        for name in delta.namelist():
            resolution,style,filename=name.split('/')
            assert resolution in ('50x30','220x132','400x240') and style in ('transparent','white','black')
            assert filename in {r['picon_filename'] for r in additions}
            png=delta.read(name);assert sha(png)==update['files'][name]
            with Image.open(io.BytesIO(png)) as image:assert image.size==tuple(map(int,resolution.split('x')));image.verify()
            replacement.setdefault((resolution,style),{})[filename]=png
    assert len(replacement)==9
    tasks=[(resolution,style,entry) for resolution,styles in base['packages'].items() for style,entry in styles.items()]
    with ThreadPoolExecutor(max_workers=3) as pool:downloads=list(pool.map(lambda task:read(task[2]['url'],task[2]),tasks))
    packages={};common=None
    for (resolution,style,entry),raw in zip(tasks,downloads):
        with zipfile.ZipFile(io.BytesIO(raw)) as original:
            assert len(original.namelist())==len(entry['files']) and set(original.namelist())==set(entry['files'])
            files={name:original.read(name) for name in original.namelist()}
        assert all(sha(png)==entry['files'][name] for name,png in files.items())
        assert not set(files).intersection(replacement[(resolution,style)]),'This publication adds missing artwork only'
        files.update(replacement[(resolution,style)])
        if common is None:common=set(files)
        assert set(files)==common
        target=ROOT/'packages'/('iptv-sk-cz-'+style+'-'+resolution+'.zip');target.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as output:
            for name,png in sorted(files.items()):
                assert re.fullmatch(r'(4097|5001|5002|8193)_0_(2|A)_([0-9A-F]+_){6}[0-9A-F]+\.png',name)
                info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=(stat.S_IFREG|0o644)<<16;output.writestr(info,png)
        raw=target.read_bytes();packages.setdefault(resolution,{})[style]={'resolution':resolution,'bytes':len(raw),'sha256':sha(raw),'files':{name:sha(png) for name,png in sorted(files.items())}}
    (ROOT/'owner-artwork-delta.zip').unlink()
    git('config','user.name','Warder release automation');git('config','user.email','warder-release@users.noreply.github.com')
    git('add',str(ROOT/'packages'),str(ROOT/'owner-artwork-delta.zip'));git('commit','-m','Add owner-approved radio artwork to all nine verified archives')
    payload=git('rev-parse','HEAD');git('push','origin','HEAD:refs/heads/'+branch)
    jobs=[]
    for resolution,styles in packages.items():
        for style,entry in styles.items():
            entry['url']='https://raw.githubusercontent.com/'+REPO+'/'+payload+'/'+str(ROOT/'packages'/('iptv-sk-cz-'+style+'-'+resolution+'.zip'));jobs.append((entry['url'],entry))
    with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(lambda item:read(*item),jobs))
    count=len(additions);base.update(version=update['version'],picon_stations=base['picon_stations']+count,missing_artwork=base['missing_artwork']-count,reference_files_per_variant=len(common),payload_commit=payload,packages=packages)
    write(ROOT/'catalog/release.json',base)
    missing=ROOT/'catalog/missing-artwork.csv';rows=list(csv.reader(io.StringIO(missing.read_text(encoding='utf-8-sig'))));targets={(r['country'],r['name']) for r in additions}
    remaining=[row for row in rows if tuple(row[:2]) not in targets];assert len(rows)-len(remaining)==count
    with missing.open('w',encoding='utf-8-sig',newline='') as output:csv.writer(output).writerows(remaining)
    followup=json.loads((ROOT/'catalog/followup-sources.json').read_text());followup['rows'].extend(additions);write(ROOT/'catalog/followup-sources.json',followup)
    readme=ROOT/'README.md';text=readme.read_text();text=text.replace('Picony pokrývajú %d položiek, %d súborov'%(base['picon_stations']-count,base['reference_files_per_variant']-len(replacement[('220x132','transparent')])), 'Picony pokrývajú %d položiek, %d súborov'%(base['picon_stations'],base['reference_files_per_variant']));text=text.replace('Zvyšných %d položiek'%(base['missing_artwork']+count),'Zvyšných %d položiek'%base['missing_artwork']);text+='\nDoplnený originál od vlastníka: '+', '.join(r['name'] for r in additions)+'. Všetkých deväť variantov používa dodaný podklad bez zmeny farieb a písma. [Overenie publikácie](catalog/owner-artwork-publication.json).\n';readme.write_text(text)
    proof={'status':'verified','version':update['version'],'payload_commit':payload,'picon_stations':base['picon_stations'],'missing_artwork':base['missing_artwork'],'references_per_variant':len(common),'all_nine_public_archives_verified':True,'previous_picons_preserved_byte_for_byte':True,'new_station_keys':[r['identity_key'] for r in additions]};write(ROOT/'catalog/owner-artwork-publication.json',proof)
    git('add',str(ROOT/'catalog'),str(ROOT/'README.md'));git('commit','-m','Activate verified owner-supplied radio artwork in the shared catalogue')
    git('push','origin','HEAD:refs/heads/'+branch)
    # A sparse depth-one checkout may not know main's old commit locally;
    # fetch the ancestry before the client's non-forced fast-forward check.
    git('fetch','--no-tags','--deepen=10','origin',branch,'main')
    assert head()==update['expected_main_sha'],'Production advanced before activation'
    git('push','origin','HEAD:refs/heads/main')
    print(json.dumps(proof))
if __name__=='__main__':main()
