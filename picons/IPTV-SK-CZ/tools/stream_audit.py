#!/usr/bin/env python3
"""Bounded live stream checks; uncertain connections are not labelled dead."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import gzip
import hashlib
from http.client import HTTPException
import json
from pathlib import Path
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from station_identity import name_key
from global_radio import url_key


class Redirects(HTTPRedirectHandler):
    max_redirections = 5
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        url_key(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def audio_signature(data):
    return (data.startswith((b'ID3', b'OggS', b'fLaC')) or b'ftyp' in data[:16]
            or any(data[i] == 255 and data[i+1] & 0xe0 == 0xe0
                   for i in range(min(len(data)-1, 512))))


def probe(row, timeout=5):
    result = {'url': row['url'], 'checked_at': datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
    try:
        url_key(row['url'])
        request = Request(row['url'], headers={'User-Agent': 'WarderRadio/catalogue-validation',
                                              'Icy-MetaData': '0', 'Connection': 'close'})
        with build_opener(Redirects()).open(request, timeout=timeout) as response:
            final = response.geturl()
            url_key(final)
            data = response.read(1024)
            content = response.headers.get('Content-Type', '').lower().split(';')[0]
            icy_name = response.headers.get('icy-name', '').strip()
            result.update(final_url=final, http_status=response.status,
                          content_type=content, icy_name=icy_name,
                          sample_bytes=len(data), sample_sha256=hashlib.sha256(data).hexdigest())
            if response.status != 200 or not data:
                result['status'] = 'empty-or-incomplete'
            elif audio_signature(data) and (content.startswith('audio/') or content in
                                            ('application/ogg', 'application/octet-stream', 'video/mp4')):
                result['status'] = 'audio-confirmed'
            elif data.lstrip().startswith(b'#EXTM3U'):
                result['status'] = 'playlist-needs-review'
            else:
                result['status'] = 'non-audio-or-unrecognised'
    except HTTPError as error:
        result.update(status='http-error', http_status=error.code)
    except (URLError, OSError, ValueError, TimeoutError, HTTPException) as error:
        result.update(status='connection-unconfirmed', error=str(error)[:240])
    return result


def audit(rows, output, workers=32, timeout=5):
    """Two requests per host at most; schedule round-robin across hosts."""
    hosts = defaultdict(list)
    for row in rows:
        hosts[urlsplit(row['url']).hostname].append(row)
    ordered = []
    while hosts:
        for host in list(hosts):
            ordered.append(hosts[host].pop(0))
            if not hosts[host]:
                del hosts[host]
    gates = defaultdict(lambda: threading.Semaphore(2))
    def work(row):
        with gates[urlsplit(row['url']).hostname]:
            result=probe(row, timeout)
            hard=lambda r: r['status']=='non-audio-or-unrecognised' or r.get('http_status') in (404,410)
            if hard(result):
                first=result
                result=probe(row, timeout)
                result['confirmed_failure']=hard(result)
                result['first_status']=first['status']
            return result
    results = {}
    started = time.monotonic()
    def save():
        raw = json.dumps({'schema': 1, 'checks': results}, ensure_ascii=False, separators=(',', ':')).encode()
        temporary = output.with_suffix('.tmp')
        temporary.write_bytes(gzip.compress(raw, mtime=0))
        temporary.replace(output)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(work, row): row for row in ordered}
        for future in as_completed(futures):
            result = future.result()
            results[result['url']] = result
            if len(results) % 250 == 0:
                save()
                print(json.dumps({'completed':len(results),'total':len(rows),
                                  'seconds':round(time.monotonic()-started),
                                  'statuses':dict(Counter(r['status'] for r in results.values()))}), flush=True)
    save()
    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=32)
    parser.add_argument('--timeout', type=float, default=5)
    args = parser.parse_args()
    if not 1 <= args.workers <= 64 or not 1 <= args.timeout <= 15:
        parser.error('Invalid concurrency/timeout bound')
    rows = json.loads(gzip.decompress(args.input.read_bytes()))
    audit(rows, args.output, args.workers, args.timeout)
