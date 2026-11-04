"""Publish station identities, retaining stream variants and doubtful rows for review."""
from collections import Counter, defaultdict
from datetime import datetime,timezone
import re
import unicodedata
from urllib.parse import parse_qsl, urlsplit

TRACKING = {'aw_0_req.gdpr', 'aw_0_1st.playerid', 'utm_source', 'utm_medium',
            'utm_campaign', 'ref', 'referrer'}
VANITY_TLDS = {'fm', 'am', 'tv', 'me', 'io', 'ai', 'co', 'cc', 'nu', 'ws',
               'tk', 'gg', 'sh', 'to'}
QUALITY = re.compile(r'\s*[\[(]\s*(?:(?:mp3|aac\+?|ogg|opus|flac|hls|hd|hq|lq)|'
                     r'\d{2,4}\s*(?:k(?:b(?:it)?)?p?s?))\s*[\])]\s*$', re.I)
ENCODING = r'(?:mp3|aac\+?|ogg(?:\+meta)?|opus|flac|hls)'
QUALITY_GROUP = re.compile(r'\s*[\[(]([^\[\]()]+)[\])]\s*$')
QUALITY_WORDS = re.compile(r'(?:(?:mp3|aac|ogg|meta|opus|flac|hls|stream|high|low|quality|mobile|hd|hq|sd|lq|non|ssl|k|kb|kbps|kbit|bit|s)|\d{2,4}|[\s+/,\-])+\Z')
TRAILING_ENCODING = re.compile(r'\s+\d{2,4}\s*(?:kbps|kbit/s|kb/s|k)\s*'+ENCODING+r'\s*$')
PLACEHOLDER_NAMES = {'test','teststation','teststream','demo','undefined','unknown',
                     'noname','stationname','yourradioname','stream','offline','deleted','donotuse'}


def name_key(name):
    """Ignore typography and explicit encoding labels, retaining language and subchannels."""
    name = unicodedata.normalize('NFKD', name.casefold())
    name = ''.join(c for c in name if not unicodedata.combining(c))
    while True:
        old=name
        name=QUALITY.sub('',name)
        group=QUALITY_GROUP.search(name)
        if group and QUALITY_WORDS.fullmatch(group[1].strip()):
            name=name[:group.start()]
        name=TRAILING_ENCODING.sub('',name)
        if name==old:
            break
    # Directory headings often prepend the Slovak public-service channel index.
    # Keep regional/programme suffixes; only the redundant index is removed.
    name=re.sub(r'^sro\s*\d{1,2}\s*[:\-]?\s*(?=radio\b)', '', name)
    compact=''.join(c for c in name if c.isalnum())
    if compact.startswith('radio') and len(compact)>8:
        compact=compact[5:]
    # Do not transliterate other scripts to an empty ASCII identity.
    return compact


def homepage_key(url):
    try:
        p = urlsplit(url)
        if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
            return None
        return (p.hostname.lower().removeprefix('www.'), p.path.rstrip('/'))
    except ValueError:
        return None


def transport_key(url):
    p = urlsplit(url)
    # Only transport/known tracking differences disappear; channel queries remain.
    port = p.port if p.port not in (None, 80, 443) else None
    query = tuple(sorted((k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
                         if k.casefold() not in TRACKING))
    return (p.hostname.lower(), port, p.path or '/', query)


# Editorial evidence outranks a legacy endpoint that still serves audio.
# STVR programme concept 2025, p. 25: Pyramida ended on 2025-02-28.
PYRAMIDA_RETIREMENT = {
    'effective_date': '2025-02-28',
    'source': 'https://www.stvr.org/download.pl?ID=31453&hash=dwSLRbHysLAXglOCE0FdLRE5JM9bnPYQ',
    'page': 25,
}


def stvr_programme(url):
    """Explicit old/current broadcaster resources; never infer RSI from a label."""
    p=urlsplit(url)
    if ((p.hostname=='live.slovakradio.sk' and p.port in (None,80,443,8000)) or
            (p.hostname=='icecast.stv.livebox.sk' and p.port in (None,80,443))):
        path=p.path.casefold()
        if path=='/patria_128.mp3':return 'patria',transport_key(url)[3]
        if re.fullmatch(r'/(?:pyramida|klasika)_(?:128|256)\.mp3',path):
            return 'retired-pyramida',transport_key(url)[3]
    return None


def retirement_evidence(row):
    if row.get('countrycode')!='SK':return None
    if name_key(row['name']) in {'pyramida','rtvsradiopyramida','stvrradiopyramida'}:
        return PYRAMIDA_RETIREMENT
    if any((p:=stvr_programme(u)) and p[0]=='retired-pyramida'
           for u in row.get('aliases',[row['url']])):
        return PYRAMIDA_RETIREMENT
    return None


def one_typo(a, b):
    if min(len(a), len(b)) < 10 or abs(len(a) - len(b)) > 1:
        return False
    if re.findall(r'\d+', a) != re.findall(r'\d+', b):
        return False
    # Only accidental repeated letters: never Classic/Classics, east/west,
    # channel numbers or arbitrary one-edit names.
    return a != b and re.sub(r'(.)\1+', r'\1', a) == re.sub(r'(.)\1+', r'\1', b)


LANGUAGE_SITES={'en','eng','english','cz','cs','cesky','czech','de','deutsch','german',
                'fr','francais','french','es','espanol','spanish','ru','russian',
                'it','italian','pt','portuguese','pl','polish','sk','slovak'}
GENERIC_MOUNTS={'live','stream','radio','listen','index','master','audio','broadcast',
                'playlist','rock','jazz','pop','news','main','station','channel','default',
                'play','mp3','aac','aacp','ogg','opus','flac','hls','low','high','hi','lo'}


def programme_mount(row,url):
    """Encoding profiles share a programme; station/channel numbers do not."""
    p=urlsplit(url);host=p.hostname.lower()
    family='play.cz' if re.fullmatch(r'(?:icecast|ice)\d*\.play\.cz',host) else host
    path=p.path
    stem=re.sub(r'\.(?:mp3|aacp?|ogg|opus|flac|m3u8?|pls)$','',path,flags=re.I)
    if stem==path:return None
    suffix=re.search(r'(?:[_-](?:mp3|aacp?|ogg|opus|flac))?[_-](24|32|48|56|64|96|128|160|192|256|320|512|high|low|hi|lo|hq|lq)$',stem,re.I)
    if suffix and not (suffix[1].isdigit() and suffix[1] in re.findall(r'\d+',name_key(row['name']))):
        stem=stem[:suffix.start()]
    elif family=='play.cz':
        suffix=re.search(r'(24|32|48|56|64|96|128|160|192|256|320|512)$',stem)
        if suffix and suffix[1] not in re.findall(r'\d+',name_key(row['name'])):
            stem=stem[:suffix.start()]
    stem=re.sub(r'[_-](?:mp3|aacp?|ogg|opus|flac)$','',stem,flags=re.I)
    token=stem.rsplit('/',1)[-1]
    if len(token)<3 or not any(c.isalpha() for c in token) or token.casefold() in GENERIC_MOUNTS:
        return None
    port=p.port if p.port not in (None,80,443) else None
    query=transport_key(url)[3]
    # A shared leaf such as /programme-a/play.mp3 vs /programme-b/play.mp3
    # is not a shared programme: retain the entire identifying path.
    return (family,port,stem,query),stem,query


def language_site(url):
    key=homepage_key(url)
    if not key:return None
    host,path=key
    if len(host.split('.'))>=3 and host.split('.')[0] in LANGUAGE_SITES:
        host=host.split('.',1)[1]
    if path.strip('/') in LANGUAGE_SITES:path=''
    return host,path


def select_stations(rows, names, preferred_references=()):
    """Keep one evidenced station per country/name; quarantine unresolved homonyms."""
    input_count=len(rows)
    retired=[dict(r,review_reason='confirmed-retired-programme',
                  retirement_evidence=retirement_evidence(r))
             for r in rows if retirement_evidence(r)]
    rows=[r for r in rows if not retirement_evidence(r)]
    parents = list(range(len(rows)))
    preferred_references=set(preferred_references)
    keys = [name_key(r['name']) for r in rows]
    homes = [{k for u in r.get('homepages', []) if (k := homepage_key(u))} for r in rows]
    streams = [{transport_key(u) for u in r.get('aliases', [r['url']])} for r in rows]

    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    def join(a, b):
        a, b = root(a), root(b)
        if a != b:
            parents[max(a, b)] = min(a, b)

    evidence = {}
    programmes={};site_programmes=defaultdict(list)
    typo_buckets = defaultdict(set)
    for i, row in enumerate(rows):
        country = row.get('countrycode')
        if not country or not keys[i]:
            continue
        # Same audio resource across HTTP/HTTPS or encoding/node profiles is
        # stronger evidence than translated/old display labels.
        for value in streams[i]:
            key=(country,'transport',value)
            if key in programmes:join(i,programmes[key])
            else:programmes[key]=i
        for url in row.get('aliases',[row['url']]):
            broadcaster=stvr_programme(url)
            if country=='SK' and broadcaster and broadcaster[0]=='patria':
                key=(country,'broadcaster',broadcaster)
                if key in programmes:join(i,programmes[key])
                else:programmes[key]=i
        for url in row.get('aliases',[row['url']]):
            programme=programme_mount(row,url)
            if not programme:continue
            resource,programme_path,query=programme
            key=(country,'programme',resource)
            if key in programmes:join(i,programmes[key])
            else:programmes[key]=i
            for home in row.get('homepages',[]):
                site=language_site(home)
                if not site:continue
                key=(country,site,programme_path,resource[1],query)
                for other in site_programmes[key]:
                    a=set(row.get('languages',[]));b=set(rows[other].get('languages',[]))
                    if not a or not b or a & b:join(i,other)
                site_programmes[key].append(i)
        for kind, values in (('homepage', homes[i]), ('stream', streams[i])):
            for value in values:
                key = (country, keys[i], kind, value)
                if key in evidence:
                    join(i, evidence[key])
                else:
                    evidence[key] = i
        for host, path in homes[i]:
            typo_buckets[(country, 'homepage', host, path)].add(i)
        for host, port, path, query in streams[i]:
            typo_buckets[(country, 'server', host, port)].add(i)

    # Single-character misspellings need shared station/site/server evidence.
    # Large shared hosting servers are never fuzzy matched.
    for candidates in typo_buckets.values():
        if len(candidates) > 32:
            continue
        candidates = sorted(candidates)
        for n, a in enumerate(candidates):
            for b in candidates[n + 1:]:
                if keys[a] != keys[b] and one_typo(keys[a], keys[b]):
                    join(a, b)

    clusters = defaultdict(list)
    for i in range(len(rows)):
        clusters[root(i)].append(i)
    selected = []
    review = retired
    stats = Counter(confirmed_retired_programme=len(retired))

    def rank(i):
        r = rows[i]
        return (not r.get('protected'), not r.get('healthy'),
                not r['url'].startswith('https:'),
                -min(r.get('bitrate', 0), 512), r['name'].casefold(),r['url'],r['reference'])

    for indices in clusters.values():
        canonical = min(indices, key=rank)
        item = dict(rows[canonical])
        if not item.get('protected'):
            existing=[i for i in indices if rows[i]['reference'] in preferred_references]
            if existing:
                identity=min(existing,key=lambda i:rows[i]['reference'])
                item['reference']=rows[identity]['reference'];item['id']=rows[identity]['id']
        # Keep all curated identities if two of them really occur in one cluster.
        protected = [i for i in indices if rows[i].get('protected')]
        if len(protected) > 1 and any(rows[i].get('countrycode')=='SK' for i in protected):
            selected.extend(dict(rows[i]) for i in protected)
            others = [i for i in indices if i not in protected]
            review.extend(dict(rows[i], review_reason='multiple-curated-identities') for i in others)
            stats['ambiguous_rows_withheld'] += len(others)
            continue
        for field in ('aliases', 'source_ids', 'genres', 'languages', 'homepages', 'favicons'):
            item[field] = sorted({v for i in indices for v in rows[i].get(field, [])})
        item['stream_variants'] = sorted(
            {r['url']: {k: r.get(k) for k in ('url', 'bitrate', 'codec', 'healthy')}
             for i in indices for r in [rows[i]]}.values(), key=lambda r: r['url'])
        item['merged_references'] = sorted({rows[i]['reference'] for i in indices} - {item['reference']})
        item['name_aliases']=sorted({name for i in indices for name in
                                    [rows[i]['name']]+rows[i].get('name_aliases',[])})
        item['healthy'] = any(rows[i].get('healthy') for i in indices)
        item['known_working']=any(rows[i].get('known_working') for i in indices)
        item['failure_days']=sorted({d for i in indices for d in rows[i].get('failure_days',[])})
        item['last_audio_at']=max((rows[i].get('last_audio_at') or '' for i in indices),default='') or None
        item['first_failure_at']=min((rows[i]['first_failure_at'] for i in indices
                                      if rows[i].get('first_failure_at')),default=None)
        item['last_failure_at']=max((rows[i]['last_failure_at'] for i in indices
                                     if rows[i].get('last_failure_at')),default=None)
        stats['station_variant_rows_merged'] += len(indices) - 1
        selected.append(item)

    by_name = defaultdict(list)
    for item in selected:
        by_name[(item.get('countrycode'), name_key(item['name']))].append(item)
    published = []
    country_codes = {c.lower() for c in names} - VANITY_TLDS
    for same_name in by_name.values():
        for item in same_name:
            reason = None
            if not item.get('protected'):
                if not item.get('countrycode'):
                    reason = 'unknown-or-conflicting-country'
                elif not item.get('healthy') and not item.get('known_working'):
                    reason = 'source-reports-unavailable'
                elif not name_key(item['name']) or not any(homepage_key(u) for u in item.get('homepages', [])):
                    reason = 'missing-station-evidence'
                elif ''.join(c for c in item['name'].casefold() if c.isalnum()) in PLACEHOLDER_NAMES:
                    reason = 'placeholder-or-test-entry'
                elif (urlsplit(item['url']).hostname == 'stream.bauermedia.sk'
                      and any(homepage_key(u) and homepage_key(u)[0] == 'rayo.sk'
                              for u in item.get('homepages', []))):
                    # Receiver reports thematic entries playing another channel.
                    # A community URL returning audio cannot prove its programme.
                    # Curated main channels are unaffected; restore a thematic
                    # channel only after a broadcaster mapping is established.
                    reason = 'broadcaster-channel-identity-unconfirmed'
                elif len(same_name) > 1:
                    reason = 'unresolved-same-name-identities'
                else:
                    home_tlds = {k[0].rsplit('.', 1)[-1] for u in item['homepages']
                                 if (k := homepage_key(u))}
                    stream_tlds = {urlsplit(u).hostname.rsplit('.', 1)[-1]
                                   for u in item['aliases']}
                    corroborated = (home_tlds & stream_tlds & country_codes)
                    if corroborated and item['countrycode'].lower() not in corroborated:
                        reason = 'country-evidence-needs-review'
            if reason:
                review.append(dict(item, review_reason=reason))
                stats[reason.replace('-', '_')] += 1
            else:
                published.append(item)
    published.sort(key=lambda r: (0 if r['countrycode'] == 'SK' else 1 if r['countrycode'] == 'CZ'
                                 else 3 if not r['countrycode'] else 2,
                                 r['group'].casefold(), name_key(r['name']), r['reference']))
    stats['review_rows'] = len(review)
    stats['input_station_rows'] = input_count
    stats['published_station_rows'] = len(published)
    if len(published) + len(review) + stats['station_variant_rows_merged'] != input_count:
        raise ValueError('Station selection accounting mismatch')
    return published, review, dict(stats)


def apply_stream_checks(rows, checks):
    """Apply corroborated failures/other-station redirects, never delete on a timeout."""
    from global_radio import url_key
    endpoints=defaultdict(list)
    for row in rows:
        for url in row.get('aliases',[row['url']]):
            endpoints[url_key(url)].append(row)
    published=[];review=[];stats=Counter()
    for row in rows:
        check=checks.get(row['url'],{})
        if row.get('protected') and row.get('countrycode')=='SK':
            # The owner confirmed this original list is working. A remote probe
            # must neither remove these stations nor rewrite their stream URLs.
            item=dict(row,known_working=True,live_status='audio-confirmed' if check.get('status')=='audio-confirmed'
                      else 'original-station-retained-during-outage')
            published.append(item)
            stats['original_slovak_stations_preserved']+=1
            stats['audio_confirmed' if check.get('status')=='audio-confirmed'
                  else 'known_stations_retained_during_outage']+=1
            continue
        reason=None
        if check.get('confirmed_failure'):
            reason='confirmed-unavailable-or-non-audio'
        elif check.get('status')!='audio-confirmed':
            # Preserve the observation/master and saved favourites, while the
            # user-facing country catalogue requires actual audio evidence.
            # A timeout/playlist/access restriction is review, never "dead".
            reason='live-audio-not-confirmed'
        final=check.get('final_url')
        if check.get('status')=='audio-confirmed' and final and url_key(final)!=url_key(row['url']):
            targets=endpoints.get(url_key(final),[])
            if targets and all(name_key(t['name'])!=name_key(row['name']) for t in targets):
                reason='redirects-to-another-station'
        if reason:
            alternatives=[v for v in row.get('stream_variants',[])
                          if checks.get(v['url'],{}).get('status')=='audio-confirmed'
                          and v['url']!=row['url']]
            if alternatives and reason in ('confirmed-unavailable-or-non-audio','live-audio-not-confirmed'):
                row=dict(row,url=alternatives[0]['url'])
                check=checks[row['url']]
                stats['verified_alternative_urls_selected']+=1
                reason=None
        if reason in ('live-audio-not-confirmed','confirmed-unavailable-or-non-audio') and (
                row.get('known_working') or row.get('protected')):
            row=dict(row,known_working=True)
            days=set(row.get('failure_days',[]))
            observed=None
            try:
                observed=datetime.fromisoformat(check['checked_at'].replace('Z','+00:00'))
            except (KeyError,ValueError,TypeError):pass
            # A deferred check or regional access restriction is not evidence
            # of a retired station. Cached retries on one date count once.
            if (observed is not None and check.get('requested',True)
                    and check.get('http_status') not in (401,403)
                    and check.get('status') not in ('playlist-needs-review','host-check-unconfirmed','audit-budget-unconfirmed')):
                days.add(observed.date().isoformat())
                row['first_failure_at']=row.get('first_failure_at') or observed.isoformat()
                row['last_failure_at']=max(row.get('last_failure_at') or '',observed.isoformat())
            row['failure_days']=sorted(days)[-30:]
            persistent=False
            try:
                first=datetime.fromisoformat((row.get('first_failure_at') or '').replace('Z','+00:00'))
                last=datetime.fromisoformat((row.get('last_failure_at') or '').replace('Z','+00:00'))
                persistent=len(days)>=3 and (last-first).total_seconds()>=48*3600
            except (KeyError,ValueError,TypeError):pass
            if not persistent:
                published.append(dict(row,live_status='known-station-retained-during-outage'))
                stats['known_stations_retained_during_outage']+=1
                continue
            reason='persistent-unavailability'
        if reason:
            review.append(dict(row,review_reason=reason,stream_check=check))
            stats[reason.replace('-','_')]+=1
        else:
            published.append(dict(row,known_working=True,live_status='audio-confirmed',
                                  last_audio_at=check.get('checked_at') or row.get('last_audio_at'),
                                  first_failure_at=None,last_failure_at=None,failure_days=[]))
            stats['audio_confirmed' if check.get('status')=='audio-confirmed' else 'live_check_unconfirmed']+=1
    return published,review,dict(stats)
