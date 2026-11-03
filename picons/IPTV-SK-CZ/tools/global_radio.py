#!/usr/bin/env python3
"""Compile complete source snapshots into one auditable, country-sorted catalogue."""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse
import gzip
import hashlib
import ipaddress
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit

from laut_radio import station_key
from update_world_radio import parse, label_key, render_marker, replace

ROOT = Path(__file__).resolve().parents[1]
MAX_ROWS = 150000
MAX_MASTER = 128 * 1024 * 1024
MAX_BOUQUET = 32 * 1024 * 1024
UNKNOWN = 'Nezaradené'
ALIASES = {
    'slovensko':'SK','slovakia':'SK','slowakei':'SK',
    'cechy':'CZ','cesko':'CZ','czechia':'CZ','czech republic':'CZ','tschechien':'CZ',
    'deutschland':'DE','osterreich':'AT','schweiz':'CH','niederlande':'NL',
    'frankreich':'FR','polen':'PL','ungarn':'HU','italien':'IT','spanien':'ES',
    'portugal':'PT','belgien':'BE','danemark':'DK','schweden':'SE','norwegen':'NO',
    'finnland':'FI','island':'IS','irland':'IE','grossbritannien':'GB',
    'schottland':'GB','england':'GB','wales':'GB','turkei':'TR','turkey':'TR',
    'griechenland':'GR','rumanien':'RO','bulgarien':'BG','kroatien':'HR',
    'serbien':'RS','slowenien':'SI','ukraine':'UA','russland':'RU',
    'mexiko':'MX','brasilien':'BR','kanada':'CA','australien':'AU',
    'neuseeland':'NZ','sudafrika':'ZA','vereinigte staaten':'US','usa':'US',
}


def clean(value, maximum=240):
    return ''.join(c for c in str(value or '') if ord(c)>=32 and ord(c)!=127).strip()[:maximum]


def url_key(url):
    """Conservative stream identity: preserve protocol, query, mount and bitrate."""
    if not isinstance(url,str) or len(url)>4096 or any(c.isspace() or ord(c)<32 for c in url):
        raise ValueError('Invalid stream URL')
    p=urlsplit(url)
    if p.scheme not in ('http','https') or not p.hostname or p.username is not None or p.password is not None:
        raise ValueError('Unsupported stream URL')
    port=p.port
    host=p.hostname.lower()
    if host in ('localhost','localhost.localdomain') or host.endswith('.localhost'):
        raise ValueError('Local stream URL')
    try:
        if not ipaddress.ip_address(host).is_global: raise ValueError('Non-public stream URL')
    except ValueError as error:
        if str(error)=='Non-public stream URL': raise
    laut=station_key(url)
    if laut: return 'laut.fm:'+laut
    netloc=('['+host+']') if ':' in host else host
    if port is not None and (p.scheme,port) not in (('http',80),('https',443)):
        netloc+=':'+str(port)
    return urlunsplit((p.scheme,netloc,p.path or '/',p.query,''))


def tags(value):
    if isinstance(value,str): value=value.split(',')
    if not isinstance(value,list): return []
    return sorted({clean(v,80).casefold() for v in value if isinstance(v,str) and clean(v,80)})[:100]


def country_names(rows):
    names={}
    for row in rows:
        code=row.get('iso_3166_1') or row.get('countrycode')
        if isinstance(code,str) and re.fullmatch('[A-Z]{2}',code) and clean(row.get('name')):
            names[code]=clean(row['name'])
    if len(names)<150: raise ValueError('Incomplete country-code registry')
    names.update(SK='Slovensko',CZ='Čechy',US='United States',GB='United Kingdom',RU='Russia',
                 KR='South Korea',KP='North Korea',IR='Iran',BO='Bolivia',TZ='Tanzania',
                 VE='Venezuela',MD='Moldova',TW='Taiwan')
    return names


def source_rows(provider, rows, names):
    """Retain filtering metadata in the master, including unhealthy observations."""
    output=[]; rejected=Counter(); seen=set()
    for row in rows:
        try:
            if not isinstance(row,dict): raise ValueError('record')
            key=clean(row.get('stationuuid') if provider=='radio-browser' else row.get('name'),100)
            if not key or key in seen: raise ValueError('duplicate source identity')
            name=clean(row.get('name') if provider=='radio-browser' else row.get('display_name') or key)
            url=row.get('url') if provider=='radio-browser' else row.get('stream_url')
            url_key(url)
            if not name: raise ValueError('name')
            healthy=row.get('lastcheckok')==1 if provider=='radio-browser' else row.get('active') is True
            aliases=[url]
            resolved=row.get('url_resolved') if healthy and provider=='radio-browser' else None
            if resolved:
                try:
                    url_key(resolved)
                    if resolved not in aliases: aliases.append(resolved)
                except (ValueError,TypeError): pass
            code=row.get('countrycode') if provider=='radio-browser' else None
            code=code if code in names else None
            seen.add(key)
            bitrate=row.get('bitrate',0)
            output.append({'source_id':provider+':'+key,'name':name,'url':url,'aliases':aliases,
                'countrycode':code,'healthy':healthy,'genres':tags(row.get('tags') if provider=='radio-browser' else row.get('genres')),
                'languages':tags(row.get('language')),'bitrate':bitrate if isinstance(bitrate,int) and 0<=bitrate<=100000 else 0,
                'codec':clean(row.get('codec'),40),
                'favicon':clean(row.get('favicon') if provider=='radio-browser' else (row.get('images') or {}).get('station_640x640'),4096),
                'homepage':clean(row.get('homepage') or row.get('page_url'),4096),
                'location':clean(row.get('state') or row.get('location')),
                'lastcheck':clean(row.get('lastchecktime_iso8601'),60)})
        except (ValueError,TypeError,AttributeError): rejected['invalid_records']+=1
    if len(output)>MAX_ROWS: raise ValueError('Source row limit exceeded')
    return output,dict(rejected)


def baseline_rows(text, owned, names):
    protected={e.reference for e in parse(owned) if e.url}
    countries={label_key(v):k for k,v in names.items()};countries.update(ALIASES)
    rows=[];group=UNKNOWN
    for e in parse(text):
        if not e.url: group=e.name;continue
        url_key(e.url)
        rows.append({'source_id':'warder:'+e.reference,'reference':e.reference,'name':e.name,
            'url':e.url,'aliases':[e.url],'countrycode':countries.get(label_key(group)),
            'healthy':True,'genres':[],'languages':[],'bitrate':0,'codec':'',
            'group':group,'protected':e.reference in protected})
    if {r['reference'] for r in rows if r['protected']}!=protected:
        raise ValueError('Owned stations missing from baseline')
    return rows


def compile_catalogue(sources, names, owned, previous=()):
    rows=[r for source in sources.values() for r in source['rows']]
    if len(rows)>MAX_ROWS: raise ValueError('Master row limit exceeded')
    # Union by exact stream aliases, never by a station's display name.
    parents=list(range(len(rows))); aliases={};row_keys=[]
    def root(i):
        while parents[i]!=i:
            parents[i]=parents[parents[i]];i=parents[i]
        return i
    for i,row in enumerate(rows):
        keys={url_key(u) for u in row['aliases']}
        row_keys.append(keys)
        for key in keys:
            if key in aliases:
                a,b=root(i),root(aliases[key]);parents[a]=b
            else: aliases[key]=i
    clusters=defaultdict(list)
    for i in range(len(rows)): clusters[root(i)].append(i)
    old_alias={};old_source={}
    for item in previous:
        for url in item.get('aliases',[item['url']]):
            try: old_alias.setdefault(url_key(url),item)
            except ValueError: pass
        for key in item.get('source_ids',[]): old_source.setdefault(key,item)
    owned_entries=[e for e in parse(owned) if e.url]
    assigned={e.reference for e in owned_entries}
    reserved=assigned | {r['reference'] for r in rows if r.get('reference')} | {r['reference'] for r in previous}
    output=[];stats=Counter()
    for indices in clusters.values():
        members=[rows[i] for i in indices]
        keys=set().union(*(row_keys[i] for i in indices))
        protected=[r for r in members if r.get('protected')]
        baseline=[r for r in members if r['source_id'].startswith('warder:')]
        prior=next((old_alias[k] for k in sorted(keys) if k in old_alias),None)
        if prior is None:
            prior=next((old_source[r['source_id']] for r in members if r['source_id'] in old_source),None)
        # A failed check doesn't delete a previously distributed station.
        if not protected and not baseline and not prior and not any(r['healthy'] for r in members):
            stats['new_unhealthy_clusters_excluded']+=1;continue
        preferred=protected or baseline[:1]
        if not preferred:
            preferred=sorted(members,key=lambda r:(not r['healthy'],not r['source_id'].startswith('laut.fm:'),r['source_id']))[:1]
        codes={r['countrycode'] for r in members if r.get('countrycode') in names}
        code=next(iter(codes)) if len(codes)==1 else None
        if len(codes)>1: stats['country_conflicts']+=1
        unique_aliases=sorted({u for r in members for u in r['aliases']})
        genres=sorted({v for r in members for v in r.get('genres',[])})
        languages=sorted({v for r in members for v in r.get('languages',[])})
        for row in preferred:
            country=row.get('countrycode') if row.get('protected') else code
            reference=row.get('reference') or (prior or {}).get('reference')
            if not row.get('protected'):
                if reference in assigned: reference=None
                if not reference:
                    nonce=0
                    while True:
                        digest=hashlib.sha256(('global|'+min(keys)+'|'+str(nonce)).encode()).hexdigest()
                        reference=f'4097:0:2:{int(digest[:4],16) or 1:X}:{int(digest[4:8],16) or 1:X}:ED:0:0:0:0'
                        if reference not in assigned and reference not in reserved: break
                        nonce+=1
                assigned.add(reference)
            output.append({'id':hashlib.sha256(reference.encode()).hexdigest()[:24],
                'name':row['name'],'url':row['url'],'reference':reference,
                'group':names.get(country,UNKNOWN),'countrycode':country,
                'aliases':unique_aliases,'source_ids':sorted(r['source_id'] for r in members),
                'genres':genres,'languages':languages,'bitrate':row.get('bitrate',0),
                'codec':row.get('codec',''),
                'homepages':sorted({r['homepage'] for r in members if r.get('homepage')}),
                'favicons':sorted({r['favicon'] for r in members if r.get('favicon')}),
                'healthy':any(r['healthy'] for r in members),
                'protected':bool(row.get('protected'))})
        stats['duplicate_observations_merged']+=len(members)-len(preferred)
    by_ref={r['reference']:r for r in output}
    if len(by_ref)!=len(output): raise ValueError('Duplicate service reference')
    owned_rows=[by_ref[e.reference] for e in owned_entries]
    rest=sorted((r for r in output if not r['protected']),key=lambda r:(
        0 if r['countrycode']=='SK' else 1 if r['countrycode']=='CZ' else 3 if not r['countrycode'] else 2,
        label_key(r['group']),label_key(r['name']),r['reference']))
    # Preserve every owned identity/name/URL while placing each country in a
    # single section. The legacy compatible bouquet remains byte-for-byte intact.
    output=sorted(owned_rows+rest,key=lambda r:(0 if r['countrycode']=='SK' else 1 if r['countrycode']=='CZ' else 3 if not r['countrycode'] else 2,label_key(r['group']),label_key(r['name']),r['reference']))
    lines=['#NAME Warder Radio World\n'];group=None
    for row in output:
        if row['group']!=group:
            group=row['group'];lines.append(render_marker(group))
        lines.append('#SERVICE '+row['reference']+':'+row['url'].replace(':','%3a')+'\n#DESCRIPTION '+row['name']+'\n')
    bouquet=''.join(lines)
    if len(bouquet.encode())>MAX_BOUQUET:raise ValueError('Compiled bouquet exceeds size bound')
    stats.update(total_stations=len(output),countries=len({r['countrycode'] for r in output}-{None}),
                 unclassified=sum(r['countrycode'] is None for r in output))
    return output,bouquet,dict(stats)


def read_gzip(path,maximum=MAX_MASTER):
    with gzip.open(path,'rb') as f:data=f.read(maximum+1)
    if len(data)>maximum:raise ValueError('Master exceeds size bound')
    return json.loads(data)


def write_gzip(path,data):
    raw=json.dumps(data,ensure_ascii=False,separators=(',',':')).encode()
    if len(raw)>MAX_MASTER: raise ValueError('Master exceeds size bound')
    blob=gzip.compress(raw,mtime=0)
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists() or path.read_bytes()!=blob:
        temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_bytes(blob);temporary.replace(path)
    return {'bytes':len(blob),'decoded_bytes':len(raw),'sha256':hashlib.sha256(blob).hexdigest()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshots',type=Path,default=Path('catalogue-data'))
    parser.add_argument('--output',type=Path,default=ROOT/'catalog/global')
    parser.add_argument('--baseline',type=Path,default=ROOT/'bouquets/userbouquet.warder.radio')
    parser.add_argument('--owned',type=Path,default=ROOT/'bouquets/userbouquet.warder.sk-cz.radio')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    master_path=args.output/'world-radio-master.json.gz'
    old=read_gzip(master_path) if master_path.exists() else {}
    previous_path=args.output/'world-radio.json.gz'
    previous=read_gzip(previous_path) if previous_path.exists() else []
    registry=args.snapshots/'countries.json.gz'
    names=country_names(read_gzip(registry)) if registry.exists() else old.get('countries',{})
    if len(names)<150:raise ValueError('No complete country registry available')
    now=datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    sources={};status={};fetch_path=args.snapshots/'fetch-report.json'
    fetched=json.loads(fetch_path.read_text()) if fetch_path.exists() else {}
    for provider,filename in [('radio-browser','radio-browser'),('laut.fm','laut')]:
        path=args.snapshots/(filename+'.json.gz')
        if path.exists():
            records,rejected=source_rows(provider,read_gzip(path),names)
            minimum=10000 if provider=='radio-browser' else 5000
            prior_count=len(old.get('sources',{}).get(provider,{}).get('rows',[]))
            if len(records)<max(minimum,prior_count*.9):raise ValueError('Unexpected source shrink: '+provider)
            sources[provider]={'rows':records,'fetched_at':now}
            status[provider]={'status':'live','observations':len(records),**rejected,**fetched.get(provider,{})}
        elif provider in old.get('sources',{}):
            sources[provider]=old['sources'][provider]
            status[provider]={'status':'previous-data-retained','observations':len(sources[provider]['rows']),
                              'last_success':sources[provider].get('fetched_at'),
                              'error':fetched.get(provider,{}).get('error','Source snapshot unavailable')}
        else:raise ValueError('No initial snapshot for '+provider)
    owned=args.owned.read_text();baseline=args.baseline.read_text()
    sources['warder']={'rows':baseline_rows(baseline,owned,names),'fetched_at':now}
    items,bouquet,stats=compile_catalogue(sources,names,owned,previous)
    if previous and len(items)<len(previous)*.95:raise ValueError('Unexpected compiled catalogue shrink')
    master={'schema':1,'countries':names,'sources':sources}
    master_info=write_gzip(master_path,master)
    compiled_info=write_gzip(previous_path,items)
    receiver=[{k:r[k] for k in ('name','url','reference','group')} for r in items]
    receiver_info=write_gzip(args.output/'world-radio.receiver.json.gz',receiver)
    if len(receiver)>100000 or receiver_info['bytes']>8*1024*1024 or receiver_info['decoded_bytes']>32*1024*1024:
        raise ValueError('Receiver payload exceeds supported limits')
    replace(args.output/'userbouquet.warder.world.radio',bouquet)
    country_counts=Counter(r['group'] for r in items)
    country_index=[{'name':name,'countrycode':next((r['countrycode'] for r in items if r['group']==name),None),'stations':count} for name,count in country_counts.items()]
    replace(args.output/'countries.json',json.dumps(country_index,ensure_ascii=False,indent=2)+'\n')
    report={'schema':1,'built_at':now,'sources':status,'processing':stats,'master':master_info,
        'catalogue':compiled_info,'receiver':receiver_info,'bouquet_bytes':len(bouquet.encode()),
        'owned_sha256':hashlib.sha256(owned.encode()).hexdigest(),
        'validation':'Source-reported health only; no claim of box playback verification.',
        'source_policy':'Only supported directory exports are imported; other services remain candidates.'}
    replace(args.output/'build.json',json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
