"""Collect publisher-hosted candidate originals; never approve or publish picons."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent / 'staging/batch-30'


def fetch(url, maximum):
    with urlopen(Request(url, headers={'User-Agent': 'WarderRadio-source-audit/30'}), timeout=20) as response:
        body = response.read(maximum + 1)
        if len(body) > maximum:
            raise ValueError('Response too large')
        return body


def collect(station):
    slug = urlsplit(station['url']).path.strip('/')
    result = {'station': station, 'api_url': 'https://api.laut.fm/station/' + slug}
    try:
        raw = fetch(result['api_url'], 1024 * 1024)
        meta = json.loads(raw)
        result.update(api_sha256=hashlib.sha256(raw).hexdigest(), metadata=meta)
        (ROOT / 'evidence' / (slug + '.json')).write_bytes(raw)
        image = meta.get('images', {}).get('station_640') or meta.get('images', {}).get('station')
        if image:
            body = fetch(image, 2 * 1024 * 1024)
            digest = hashlib.sha256(body).hexdigest()
            (ROOT / 'originals' / (digest + '.img')).write_bytes(body)
            result.update(image_url=image, sha256=digest, bytes=len(body))
    except Exception as exc:
        result['error'] = type(exc).__name__ + ': ' + str(exc)
    return result


if __name__ == '__main__':
    plan = json.loads((ROOT / 'candidate-plan.json').read_text())
    for folder in ('evidence', 'originals'):
        (ROOT / folder).mkdir(exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(collect, plan['candidates']))
    (ROOT / 'discovery.json').write_text(json.dumps({'status': 'unreviewed-candidates', 'results': results},
                                                ensure_ascii=False, indent=2) + '\n')
    print('Collected', sum('sha256' in row for row in results), 'candidate originals; identity review pending')
