"""Exact-reference DAB packages; no guessed identities or preview downloads."""
import hashlib,json,pathlib,re,stat,struct,zipfile
from .radio_references import collect_picon_references,picon_filename_is_reference
from . import warder_skin_sync as sync

REPOSITORY='Evolution-by-Warder/PiconHub-Warder-Evolution'
MANIFEST_URL='https://raw.githubusercontent.com/'+REPOSITORY+'/main/picons/DAB/catalog/release.json'
_PINNED=re.compile(r'^https://raw\.githubusercontent\.com/'+re.escape(REPOSITORY)+r'/[0-9a-f]{40}/picons/DAB/packages/[a-z0-9-]+\.zip$')
_SHA=re.compile(r'^[0-9a-f]{64}$')

def trusted_url(url):return isinstance(url,str) and (url==MANIFEST_URL or bool(_PINNED.fullmatch(url)))

def read_manifest(opener):
    with opener(MANIFEST_URL) as response:raw=response.read(2*1024*1024+1)
    if len(raw)>2*1024*1024:raise ValueError('DAB catalog exceeds size limit')
    data=json.loads(raw)
    if not isinstance(data,dict):raise ValueError('Invalid DAB catalog document')
    if data.get('schema')!=1 or data.get('status')!='verified':raise ValueError('DAB catalog is not approved')
    if not isinstance(data.get('packages'),dict):raise ValueError('Invalid DAB packages')
    if set(data.get('packages',{}))!={'transparent','white','black'}:raise ValueError('Incomplete DAB style catalog')
    for style,package in data['packages'].items():
        if not isinstance(package,dict):raise ValueError('Invalid DAB package record')
        if style not in ('transparent','white','black') or package.get('resolution')!='220x132':raise ValueError('Unsupported DAB package')
        if not isinstance(package.get('url'),str) or not isinstance(package.get('sha256'),str) or not _PINNED.fullmatch(package['url']) or not _SHA.fullmatch(package['sha256']):raise ValueError('Invalid DAB package identity')
        if type(package.get('bytes')) is not int or not 0<package['bytes']<=32*1024*1024:raise ValueError('Invalid DAB package size')
        records=package.get('files',{})
        if not isinstance(records,dict) or not records or len(records)>10000:raise ValueError('Invalid DAB file count')
        for name,digest in records.items():
            if not picon_filename_is_reference(name) or name!=name.upper()[:-4]+'.png' or not isinstance(digest,str) or not _SHA.fullmatch(digest):raise ValueError('Invalid DAB file identity')
    return data

def bouquet_names(folder):
    names=set()
    # Generated DAB bouquets need not be linked from bouquets.radio yet.
    for path in sorted(pathlib.Path(folder).glob('userbouquet.*.radio')):
        names.update(ref+'.png' for ref in collect_picon_references(path.read_text(encoding='utf-8',errors='replace')))
    return names

def plan(data,prefs,folder):
    if prefs['update_mode']==sync.UPDATE_MODE_SYNC_TV:return None
    package=data.get('packages',{}).get(prefs['style'])
    if package is None:raise ValueError('DAB style has no verified package')
    if prefs['resolution']!='220x132':raise ValueError('DAB picons currently require 220x132')
    names=set(package['files'])
    if prefs['update_mode']==sync.UPDATE_MODE_SYNC_TV_RADIO:
        wanted=bouquet_names(folder);names&=wanted
    else:
        positions={sync.position_token(p) for p in prefs.get('positions',[])}
        if not prefs.get('dab_only'):names={n for n in names if sync.service_orbital_position(n[:-4]) in positions}
    if not names:return None
    queue={'destination':prefs['destination'],'positions':[],'mode':sync.UPDATE_MODE_INCREMENTAL,
           'services':[],'dab_names':names}
    job=dict(package,selector_id='DAB',parts=[{'url':package['url'],'bytes':package['bytes'],'sha256':package['sha256']}])
    return queue,job

def unpack(stage,path,job,cancel):
    expected=job['files'];seen=set();wanted=stage.queue['dab_names']
    with zipfile.ZipFile(path) as archive:
        infos=archive.infolist()
        if sum(i.file_size for i in infos)>128*1024*1024:raise ValueError('DAB expanded package exceeds size limit')
        if len(infos)!=len(expected):raise ValueError('DAB package file count mismatch')
        for item in infos:
            cancel();name=item.filename
            if name not in expected or name in seen or '/' in name or '\\' in name or stat.S_ISLNK(item.external_attr>>16):raise ValueError('Unsafe DAB archive entry')
            seen.add(name)
            if not 0<item.file_size<=2*1024*1024:raise ValueError('DAB image exceeds size limit')
            raw=archive.read(item)
            if hashlib.sha256(raw).hexdigest()!=expected[name] or raw[:8]!=b'\x89PNG\r\n\x1a\n' or len(raw)<24 or raw[12:16]!=b'IHDR' or struct.unpack('>II',raw[16:24])!=(220,132):raise ValueError('Invalid DAB PNG')
            if name in wanted:
                stage.hashes[name]=expected[name];stage.upstream.add(name);(stage.ready/name).write_bytes(raw)
    if seen!=set(expected):raise ValueError('Incomplete DAB package')
