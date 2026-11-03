"""Publish station identities, retaining stream variants and doubtful rows for review."""
from collections import Counter, defaultdict
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


def one_typo(a, b):
    if min(len(a), len(b)) < 10 or abs(len(a) - len(b)) > 1:
        return False
    if re.findall(r'\d+', a) != re.findall(r'\d+', b):
        return False
    # Only accidental repeated letters: never Classic/Classics, east/west,
    # channel numbers or arbitrary one-edit names.
    return a != b and re.sub(r'(.)\1+', r'\1', a) == re.sub(r'(.)\1+', r'\1', b)


def select_stations(rows, names, preferred_references=()):
    """Keep one evidenced station per country/name; quarantine unresolved homonyms."""
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
    typo_buckets = defaultdict(set)
    for i, row in enumerate(rows):
        country = row.get('countrycode')
        if not country or not keys[i]:
            continue
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
    review = []
    stats = Counter()

    def rank(i):
        r = rows[i]
        return (not r.get('protected'), not r.get('healthy'),
                r['reference'] not in preferred_references,
                not r['url'].startswith('https:'),
                -min(r.get('bitrate', 0), 512), r['reference'])

    for indices in clusters.values():
        canonical = min(indices, key=rank)
        item = dict(rows[canonical])
        # Keep all curated identities if two of them really occur in one cluster.
        protected = [i for i in indices if rows[i].get('protected')]
        if len(protected) > 1:
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
        item['healthy'] = any(rows[i].get('healthy') for i in indices)
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
                elif not item.get('healthy'):
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
    stats['input_station_rows'] = len(rows)
    stats['published_station_rows'] = len(published)
    if len(published) + len(review) + stats['station_variant_rows_merged'] != len(rows):
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
        reason=None
        if check.get('confirmed_failure'):
            reason='confirmed-unavailable-or-non-audio'
        final=check.get('final_url')
        if check.get('status')=='audio-confirmed' and final and url_key(final)!=url_key(row['url']):
            targets=endpoints.get(url_key(final),[])
            if targets and all(name_key(t['name'])!=name_key(row['name']) for t in targets):
                reason='redirects-to-another-station'
        if reason:
            alternatives=[v for v in row.get('stream_variants',[])
                          if checks.get(v['url'],{}).get('status')=='audio-confirmed'
                          and v['url']!=row['url']]
            if alternatives and reason=='confirmed-unavailable-or-non-audio':
                row=dict(row,url=alternatives[0]['url'])
                stats['verified_alternative_urls_selected']+=1
                reason=None
        if reason:
            review.append(dict(row,review_reason=reason,stream_check=check))
            stats[reason.replace('-','_')]+=1
        else:
            published.append(row)
            stats['audio_confirmed' if check.get('status')=='audio-confirmed' else 'live_check_unconfirmed']+=1
    return published,review,dict(stats)
