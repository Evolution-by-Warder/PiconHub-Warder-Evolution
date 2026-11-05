"""Freeze newly completed Radio picons without replacing approved checkpoints."""
import concurrent.futures
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
import threading
import time
import zipfile
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from PIL import Image

ROOT=Path(__file__).resolve().parent
SNAPSHOT='4cd57cba2e72384b5c3d2793e8d6f562fe851fbe'
CATALOGUE='e90a1fe3a2734b555f48f343284f9103530180fb'
REPO='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'
REMOTE=REPO+SNAPSHOT+'/migration/radio-fast-logo-production-20261105/'
PINS={'white':'c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589',
      'black':'61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe'}
SIZES={'50x30':(50,30),'220x132':(220,132),'400x240':(400,240)}
BASELINE=ROOT/os.environ.get('RADIO_BASELINE','recovery')
ROWS=json.loads((ROOT/os.environ.get('RADIO_NEW_READY','new-fast-ready.json')).read_text())
DEST=ROOT/'verified-supplement';DEST.mkdir(exist_ok=True)
CACHE=ROOT/'snapshot-files';CACHE.mkdir(exist_ok=True)
LOCAL=threading.local()
SHA=lambda b:hashlib.sha256(b).hexdigest()


def download(task):
    path,url,digest,expected=task
    if not hasattr(LOCAL,'session'):
        LOCAL.session=requests.Session()
        LOCAL.session.headers['User-Agent']='Warder-Radio-Checkpoint/1.0'
    if path.exists():
        body=path.read_bytes()
        if (digest is None or SHA(body)==digest) and (expected is None or len(body)==expected):
            return path
    error=None
    for attempt in range(4):
        try:
            with LOCAL.session.get(url,timeout=(10,40),stream=True) as response:
                response.raise_for_status()
                chunks=[];length=0
                for chunk in response.iter_content(65536):
                    length+=len(chunk)
                    if length>8*1024*1024:raise ValueError('oversized source')
                    chunks.append(chunk)
            body=b''.join(chunks)
            if digest is not None and SHA(body)!=digest:raise ValueError('SHA256 mismatch')
            if expected is not None and len(body)!=expected:raise ValueError('size mismatch')
            path.parent.mkdir(parents=True,exist_ok=True)
            fd,tmp=tempfile.mkstemp(prefix='.download-',dir=path.parent)
            try:
                with os.fdopen(fd,'wb') as stream:stream.write(body)
                os.replace(tmp,path)
            finally:
                if os.path.exists(tmp):os.unlink(tmp)
            return path
        except Exception as exc:
            error=exc
            if attempt<3:time.sleep(attempt+1)
    raise RuntimeError(str(path)+': '+str(error))


def source_task(relative,digest=None,expected=None,origin=None):
    pure=PurePosixPath(relative)
    if pure.is_absolute() or '..' in pure.parts:raise ValueError('unsafe evidence path')
    return CACHE/relative,(origin or REMOTE)+relative,digest,expected


def write_json(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def main():
    tasks={}
    references=set()
    for row in ROWS:
        reference=row['reference']
        origin=REPO+row.get('asset_snapshot',SNAPSHOT)+'/'+row.get('asset_root','migration/radio-fast-logo-production-20261105')+'/'
        if not re.fullmatch(r'(4097|5001|5002):0:2:(?:[A-Fa-f0-9]+:){6}[A-Fa-f0-9]+',reference):
            raise ValueError('invalid radio identity')
        if reference in references:raise ValueError('duplicate reference')
        references.add(reference)
        expected={size+'/'+style for size in SIZES for style in ('transparent','white','black')}
        if set(row['renders'])!=expected:raise ValueError('incomplete nine-variant set')
        for item in row['renders'].values():
            task=source_task(item['path'],item['sha256'],item['bytes'],origin);tasks[str(task[0])]=task
        source=row['source'];task=source_task(source['path'],source['sha256'],source['bytes'],origin)
        tasks[str(task[0])]=task
        raster=source.get('frozen_svg_raster')
        if raster:
            task=source_task(raster['path'],raster['sha256'],origin=origin);tasks[str(task[0])]=task
        page=row['page'];task=source_task(page['path'],page.get('sha256') if page['path'].endswith('.html') else None,origin=origin)
        tasks[str(task[0])]=task
    for style,pin in PINS.items():
        path=CACHE/'templates'/(style+'.png')
        tasks[str(path)]=(path,REPO+CATALOGUE+'/plugin/artwork/templates/picons/'+style+'-sablona.png',pin,None)
    print('Downloading/verifying',len(tasks),'unique assets/evidence files for',len(ROWS),'new references',flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        for number,path in enumerate(pool.map(download,tasks.values()),1):
            if number%100==0 or number==len(tasks):
                write_json(DEST/'download-progress.json',{'complete':False,'verified_files':number,'total_files':len(tasks)})
                print('Verified files',number,'/',len(tasks),flush=True)
    masters={'transparent':Image.new('RGBA',(220,132))}
    for style in PINS:
        masters[style]=Image.open(CACHE/'templates'/(style+'.png')).convert('RGBA')
    for number,row in enumerate(ROWS,1):
        source=row['source'];raster=source.get('frozen_svg_raster')
        original=Image.open(CACHE/(raster['path'] if raster else source['path'])).convert('RGBA')
        original.thumbnail((192,104),Image.Resampling.LANCZOS)
        pos=((220-original.width)//2,(132-original.height)//2)
        for style,background in masters.items():
            canvas=background.copy()
            if style=='transparent':canvas.paste(original,pos)
            else:canvas.alpha_composite(original,pos)
            for size,dimensions in SIZES.items():
                target=canvas if size=='220x132' else canvas.resize(dimensions,Image.Resampling.LANCZOS)
                asset=row['renders'][size+'/'+style]
                with Image.open(CACHE/asset['path']) as check:check.verify()
                with Image.open(CACHE/asset['path']) as image:
                    if image.mode!='RGBA' or image.size!=dimensions or image.tobytes()!=target.tobytes():
                        raise ValueError('master/logo pixel comparison failed: '+row['reference']+' '+size+'/'+style)
        if number%25==0:print('Nine-variant master/logo verification',number,'/',len(ROWS),flush=True)
    stamp=datetime.now(ZoneInfo('Europe/Bratislava')).strftime('%Y%m%d_%H%M%S')
    tag='Doplnok_'+stamp
    package=DEST/('Warder_Radio_'+tag+'_'+str(len(ROWS))+'_ref_'+str(len(ROWS)*9)+'_PNG.zip')
    with zipfile.ZipFile(package,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for row in ROWS:
            filename=row['reference'].replace(':','_')+'.png'
            for variant,asset in sorted(row['renders'].items()):
                archive.write(CACHE/asset['path'],variant+'/'+filename)
        archive.writestr('new-ready-manifest.json',json.dumps(ROWS,ensure_ascii=False,indent=2)+'\n')
    with zipfile.ZipFile(package) as archive:
        if archive.testzip() is not None:raise ValueError('corrupt output ZIP')
        if len([n for n in archive.namelist() if n.endswith('.png')])!=len(ROWS)*9:raise ValueError('output inventory mismatch')
    baseline=json.loads((BASELINE/'complete-ready-manifest.json').read_text())
    ready={row['reference'] for row in baseline}
    if ready&references:raise ValueError('supplement would replace approved picons')
    combined=list(baseline)
    for row in ROWS:
        combined.append({'country':row.get('country','WORLD'),'reference':row['reference'],
            'origins':['git/'+row.get('asset_snapshot',SNAPSHOT)],'asset_root':row.get('asset_root','migration/radio-fast-logo-production-20261105'),'renders':row['renders'],'station':{k:row[k] for k in ('name','url','reference','group','country') if k in row},
            'status':'ready_verified_owner_approved','asset_batch':tag,'source':row['source'],'page':row['page'],'verification':row['verification']})
    manifest=DEST/'complete-ready-manifest.json';write_json(manifest,combined)
    write_json(DEST/'ready-references.json',sorted(ready|references))
    summary={'complete':True,'baseline_references':len(baseline),'new_references':len(ROWS),'new_pngs':len(ROWS)*9,
             'combined_references':len(combined),'combined_pngs':len(combined)*9,'countries':dict(Counter(row['group'] for row in ROWS)),
             'source_snapshots':sorted({row.get('asset_snapshot',SNAPSHOT) for row in ROWS}),'package':package.name,'sha256':SHA(package.read_bytes()),'bytes':package.stat().st_size,
             'verified_master_pixels':True,'approved_baseline_modified':False,'production_changed':False,'tag':tag}
    write_json(DEST/'summary.json',summary)
    recovery=DEST/('Warder_Radio_'+tag+'_originaly_stav_a_obnova.zip')
    with zipfile.ZipFile(recovery,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name in ('summary.json','complete-ready-manifest.json','ready-references.json'):
            archive.write(DEST/name,name)
        archive.write(ROOT/'next-source-decisions-complete.json','source-decisions-complete.json')
        for name in ('review_missing_country_logos.py','coverage-next.json'):
            archive.write(ROOT/name,name)
        for name in ('assistant-review-input.json','assistant-review-decisions.json'):
            archive.write(ROOT/'missing-source-files'/name,name)
        archive.writestr('new-ready-manifest.json',json.dumps(ROWS,ensure_ascii=False,indent=2)+'\n')
        for name in ('deduplication-vs15.json','deduplication-vs16.json'):
            if (ROOT/name).exists():archive.write(ROOT/name,name)
        archive.write(Path(__file__),'save_verified_supplement.py')
        for path in sorted({task[0] for task in tasks.values()}):
            if path.is_file() and path.parent.name!='verified-assets':archive.write(path,path.relative_to(CACHE))
    with zipfile.ZipFile(recovery) as archive:
        if archive.testzip() is not None:raise ValueError('corrupt recovery ZIP')
    summary.update(recovery_file=recovery.name,recovery_sha256=SHA(recovery.read_bytes()),recovery_bytes=recovery.stat().st_size)
    write_json(DEST/'saved-result.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
