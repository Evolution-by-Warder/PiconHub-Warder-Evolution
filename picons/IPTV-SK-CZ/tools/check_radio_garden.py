"""Read-only verification of public Radio Garden endpoints; no catalogue changes."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

BASE = 'https://radio.garden'
MAX_BYTES = 4 * 1024 * 1024
ID = re.compile(r'^[A-Za-z0-9_-]{1,80}$')
deadline = time.monotonic() + 120

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

opener = build_opener(NoRedirect)

def request(url, method='GET', json_body=True):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError('Source check deadline reached')
    req = Request(url, method=method, headers={
        'User-Agent':'Warder-radio-source-check/1',
        'Accept':'application/json' if json_body else '*/*'})
    try:
        response = opener.open(req, timeout=min(15, remaining))
    except HTTPError as error:
        if error.code not in (301,302,303,307,308):
            error.close()
            raise
        response = error
    with response:
        status = response.status
        headers = dict(response.headers.items())
        raw = response.read(MAX_BYTES+1) if json_body else b''
    if len(raw)>MAX_BYTES:
        raise ValueError('Public response exceeds size limit')
    if json_body and status != 200:
        raise ValueError('Unexpected JSON status %s' % status)
    return status, headers, raw

def get(path):
    _, _, raw = request(BASE + path)
    return json.loads(raw), raw

def country(value):
    return value.get('title','') if isinstance(value,dict) else value if isinstance(value,str) else ''

def refs(document):
    stack, found, visited = [document], {}, 0
    while stack and visited < 30000:
        node = stack.pop(); visited += 1
        if isinstance(node,list):
            stack.extend(reversed(node))
        elif isinstance(node,dict):
            href = node.get('href') or node.get('url')
            if isinstance(href,str):
                match=re.fullmatch(r'/listen/[^/]+/([A-Za-z0-9_-]+)',href)
                if match:
                    found.setdefault(match.group(1),str(node.get('title',''))[:200])
            stack.extend(reversed(list(node.values())))
    return list(found.items())

def resolve(identifier):
    url = BASE + '/api/ara/content/listen/' + identifier + '/channel.mp3'
    for _ in range(3):
        status, headers, _ = request(url, method='HEAD', json_body=False)
        location = next((v for k,v in headers.items() if k.lower()=='location'),None)
        if not location:
            return {'status':status,'redirect':False,'content_type':next((v for k,v in headers.items() if k.lower()=='content-type'),None)}
        target = urlsplit(urljoin(url,location))
        if target.scheme not in ('http','https') or not target.hostname or target.username or target.password:
            raise ValueError('Invalid stream redirect')
        if target.hostname == 'radio.garden':
            url = urljoin(url,location)
            continue
        # Stop at the published redirect: do not contact third-party audio servers.
        return {'status':status,'redirect':True,'stream_scheme':target.scheme,
                'stream_host':target.hostname,'stream_path':target.path,
                'has_query':bool(target.query),'location_sha256':hashlib.sha256(location.encode()).hexdigest()}
    raise ValueError('Too many same-site redirects')

report = {'schema':1,'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'api_base':BASE+'/api','places':{},'samples':[],
          'scope':'Public index and two cities; up to four station HEAD redirects. No audio downloaded, no production list changed.'}
try:
    status, headers, _ = request('http://radio.garden/api/ara/content/places',method='HEAD',json_body=False)
    report['http_probe']={'status':status,'location':next((v for k,v in headers.items() if k.lower()=='location'),None)}
except Exception as error:
    report['http_probe']={'error':str(error)[:250]}
try:
    index, raw = get('/api/ara/content/places')
    places = index.get('data',{}).get('list')
    if not isinstance(places,list) or not places:
        raise ValueError('Places shape differs from OpenAPI')
    labels = sorted({country(p.get('country')) for p in places if isinstance(p,dict)}-{''})
    report['places']={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),
                      'api_version':index.get('apiVersion'),'places':len(places),
                      'country_labels':len(labels),'sample_country_labels':labels[:12],
                      'keys':list(places[0])}
    for nation, preferred in [('Slovakia','Bratislava'),('Germany','Berlin')]:
        options=[p for p in places if country(p.get('country'))==nation and ID.fullmatch(str(p.get('id','')))]
        if not options:
            continue
        place=next((p for p in options if p.get('title','').casefold()==preferred.casefold()),options[0])
        sample={'place_id':place['id'],'place':place.get('title'),'country':nation,'channels':[]}
        try:
            page, _ = get('/api/ara/content/page/'+place['id']+'/channels')
            channels=refs(page)
            sample['channel_references']=len(channels)
            for identifier,title in channels[:2]:
                item={'id':identifier,'title_from_place':title}
                try:
                    metadata, _ = get('/api/ara/content/channel/'+identifier)
                    data=metadata.get('data',{})
                    item.update(title=data.get('title'),country=country(data.get('country')),
                                place=data.get('place'),metadata_keys=list(data),
                                redirect=resolve(identifier))
                except Exception as error:
                    item['error']=str(error)[:250]
                sample['channels'].append(item)
        except Exception as error:
            sample['error']=str(error)[:250]
        report['samples'].append(sample)
except Exception as error:
    report['places']['error']=str(error)[:250]
report['resolved_redirects']=sum(bool(ch.get('redirect',{}).get('redirect')) for sample in report['samples'] for ch in sample['channels'])
report['passed']=bool(report['places'].get('places') and report['resolved_redirects'])
Path('radio-garden-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(0 if report['passed'] else 1)
