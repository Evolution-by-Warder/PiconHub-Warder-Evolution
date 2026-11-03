"""Bounded public laut.fm station metadata; no country guesses or stream probing."""
from dataclasses import dataclass
import json
import re
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

API = 'https://api.laut.fm'
SLUG = re.compile(r'^[a-z0-9_-]{1,100}$')
MAX_RESPONSE = 4 * 1024 * 1024
MAX_TOTAL = 12 * 1024 * 1024
DISCOVERY_LIMIT = 1000


@dataclass(frozen=True)
class Station:
    name: str
    display_name: str
    stream_url: str


def station_key(url):
    """Deduplicate provider aliases across http/https and stream host variants."""
    try:
        if not isinstance(url, str) or len(url) > 4096 or any(c.isspace() or ord(c) < 32 for c in url):
            return None
        parts = urlsplit(url)
        host = (parts.hostname or '').lower()
        name = parts.path.strip('/')
        if (parts.scheme not in ('http', 'https') or parts.username or parts.password
                or parts.port not in (None, 80, 443) or not SLUG.fullmatch(name)):
            return None
        if host == 'stream.laut.fm' or host == name + '.stream.laut.fm':
            return name
    except (ValueError, TypeError):
        pass
    return None


def stations(rows):
    if not isinstance(rows, list):
        raise ValueError('Invalid laut.fm station list')
    result = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('active'), bool):
            raise ValueError('Invalid laut.fm station record')
        if not row['active']:
            continue
        name, url = row.get('name'), row.get('stream_url')
        if not isinstance(name, str) or station_key(url) != name:
            raise ValueError('laut.fm station and stream identity differ')
        label = row.get('display_name') or name
        if not isinstance(label, str) or any(ord(c) < 32 for c in label):
            raise ValueError('Invalid laut.fm station label')
        label = label.strip()[:220] or name
        item = Station(name, label, url)
        if name in result and result[name] != item:
            raise ValueError('Conflicting laut.fm station records')
        result[name] = item
    return result


def download(known, discovery_limit=DISCOVERY_LIMIT, opener=urlopen, clock=time.monotonic):
    """Refresh known stations, then discover at most 1000 additional candidates."""
    if not isinstance(discovery_limit, int) or not 0 <= discovery_limit <= DISCOVERY_LIMIT:
        raise ValueError('Invalid laut.fm discovery limit')
    names = sorted(set(known))
    if len(names) > 18000 or any(not isinstance(n, str) or not SLUG.fullmatch(n) for n in names):
        raise ValueError('Invalid known laut.fm station names')
    deadline, used, requests = clock() + 90, 0, 0

    def get(path):
        nonlocal used, requests
        remaining = deadline - clock()
        if remaining <= 0:
            raise TimeoutError('laut.fm metadata deadline exceeded')
        request = Request(API + path, headers={'User-Agent': 'Warder-radio-catalogue/1',
                                              'Accept': 'application/json'})
        with opener(request, timeout=min(15, remaining)) as response:
            target = urlsplit(getattr(response, 'url', request.full_url))
            if target.scheme != 'https' or target.hostname != 'api.laut.fm' or target.port not in (None, 443):
                raise ValueError('Unexpected laut.fm metadata redirect')
            raw = response.read(MAX_RESPONSE + 1)
        used += len(raw); requests += 1
        if not raw or len(raw) > MAX_RESPONSE or used > MAX_TOTAL or clock() > deadline:
            raise ValueError('laut.fm metadata size/time limit exceeded')
        return json.loads(raw.decode('utf-8'))

    result = {}
    for offset in range(0, len(names), 50):
        batch = names[offset:offset + 50]
        rows = get('/stations/' + ','.join(batch))
        if not isinstance(rows, list) or len(rows) > len(batch):
            raise ValueError('Invalid laut.fm requested-station response')
        parsed = stations(rows)
        if not set(parsed).issubset(batch):
            raise ValueError('Unexpected station in laut.fm requested batch')
        result.update(parsed)
    discovered = 0
    if discovery_limit:
        page = get('/stations?limit=%d&offset=0' % discovery_limit)
        if (not isinstance(page, dict) or page.get('offset') != 0
                or not isinstance(page.get('total'), int) or page['total'] < 0
                or not isinstance(page.get('items'), list)
                or len(page['items']) > discovery_limit or len(page['items']) > page['total']):
            raise ValueError('Invalid laut.fm discovery page')
        parsed = stations(page['items'])
        discovered = len(set(parsed) - set(result))
        for name, item in parsed.items():
            result.setdefault(name, item)  # The explicit station response takes precedence.
    return result, {'status': 'live', 'requests': requests, 'bytes': used,
                    'known_requested': len(names), 'discovery_candidates': discovered,
                    'discovery_limit': discovery_limit, 'country_filter': False}
