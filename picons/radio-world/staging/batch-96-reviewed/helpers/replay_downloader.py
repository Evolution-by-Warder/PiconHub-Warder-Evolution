#!/usr/bin/env python3
"""Replay the unchanged stable Radio downloader against a candidate country index."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


STABLE_COMMIT = 'fe573248f3d9e0a8d21acf5696f44b4c02e6fdb7'
BASE = 'https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'


def digest(body):
    return hashlib.sha256(body).hexdigest()


class HttpCache:
    def __init__(self, directory, user_agent):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.user_agent = user_agent
        self.downloaded = set()

    def get(self, url, maximum, expected_size=None, expected_digest=None):
        if not url.startswith(BASE):
            raise ValueError('Unexpected URL ' + url)
        path = self.directory / digest(url.encode())
        if path.is_file():
            body = path.read_bytes()
        else:
            for attempt in range(3):
                try:
                    request = Request(url, headers={'User-Agent': self.user_agent})
                    with urlopen(request, timeout=25) as response:
                        body = response.read(maximum + 1)
                    break
                except (URLError, TimeoutError):
                    if attempt == 2:
                        raise
                    time.sleep(2 ** attempt)
            self.downloaded.add(url)
        if len(body) > maximum:
            raise ValueError('Download exceeds limit ' + url)
        if expected_size is not None and len(body) != expected_size:
            raise ValueError('Download size mismatch ' + url)
        if expected_digest is not None and digest(body) != expected_digest:
            raise ValueError('Download SHA-256 mismatch ' + url)
        if not path.is_file():
            temporary = path.with_suffix('.tmp')
            temporary.write_bytes(body)
            os.replace(temporary, path)
        return body

    def entry(self, entry):
        return self.get(entry['url'], entry['bytes'], entry['bytes'], entry['sha256'])

    def preload(self, entries, workers):
        unique = {entry['url']: entry for entry in entries}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(self.entry, unique.values()))


def run(args):
    stable_repo = args.radio.resolve()
    source_changes = subprocess.check_output([
        'git', '-C', str(stable_repo), 'diff', STABLE_COMMIT, '--', 'src',
    ])
    if source_changes:
        raise ValueError('Radio source differs from the pinned multipart PR21 commit')
    sys.path.insert(0, str(stable_repo / 'src'))
    from WarderRadio import VERSION
    from WarderRadio import picon_download as downloader
    from WarderRadio.country_catalogue import CountryCatalogue, BASE as COUNTRY_BASE
    from WarderRadio.model import Store
    from WarderRadio.picon_catalogue import INDEX_URL, validate_index, verify_release

    if VERSION != '0.1.9.3':
        raise ValueError('Unexpected Radio version ' + VERSION)
    raw_index = args.index.read_bytes()
    document = validate_index(json.loads(raw_index))
    by_code = {row['id']: row for row in document['countries']}
    codes = list(dict.fromkeys(args.countries))
    if codes == ['all-available']:
        codes = [code for code, row in by_code.items() if row['release']]
    if not codes or any(code not in by_code or not by_code[code]['release'] for code in codes):
        raise ValueError('Select available countries from the candidate index')
    rows = [by_code[code] for code in codes]
    by_collection = {row['collection']: row for row in rows}
    cache = HttpCache(args.cache, 'WarderRadio/' + VERSION)
    cache.preload([row['release'] for row in by_collection.values()], args.workers)
    manifests = {
        collection: verify_release(cache.entry(row['release']), row['release'])
        for collection, row in by_collection.items()
    }
    with tempfile.TemporaryDirectory(prefix='warder-catalogue-') as directory:
        catalogue = CountryCatalogue(directory)
        country_entries = [catalogue.entry(row['name']) for row in rows]
    if any(entry is None for entry in country_entries):
        raise ValueError('Country absent from stable Radio catalogue')
    cache.preload([
        dict(url=COUNTRY_BASE + entry['path'], bytes=entry['bytes'], sha256=entry['sha256'])
        for entry in country_entries
    ], args.workers)
    country_names = {}
    for row, entry in zip(rows, country_entries):
        raw_country = cache.get(COUNTRY_BASE + entry['path'], entry['bytes'],
                                entry['bytes'], entry['sha256'])
        items = catalogue.unpack(raw_country, entry)
        country_names[row['id']] = {item['reference'].replace(':', '_') + '.png'
                                   for item in items if item.get('reference')}
    package_entries = []
    for style in downloader.STYLES:
        entries = [downloader.descriptor(manifest, collection, style)
                   for collection, manifest in manifests.items()]
        for row in rows:
            entry = downloader.descriptor(manifests[row['collection']], row['collection'], style)
            if len(country_names[row['id']] & entry['files'].keys()) != row['picons']:
                raise ValueError('Country coverage differs from catalogue identities ' + row['id'])
        flat = [part for entry in entries for part in (entry.get('parts') or [entry])]
        cache.preload(flat, args.workers)
        package_entries.extend(flat)
        print('Verified public ZIPs', style, len(entries), flush=True)

    reports = []
    for style in downloader.STYLES:
        requests = []

        def opener(request, **kwargs):
            url = request.full_url
            requests.append(url)
            if url == INDEX_URL:
                return io.BytesIO(raw_index)
            return io.BytesIO(cache.get(url, downloader.MAX_PACKAGE))

        with tempfile.TemporaryDirectory(prefix='warder-downloader-') as directory:
            store = Store(directory)
            store.history = [dict(name='User radio', url='https://example.org/radio',
                                  reference='4097:0:2:1:2:3:0:0:0:0', group='Custom')]
            store.favourites = list(store.history)
            store.save()
            saved_store = Path(store.path).read_bytes()
            settings = downloader.PiconSettings(directory)
            settings.location = str(Path(directory) / 'picons')
            settings.countries, settings.style = codes, style
            settings.save()
            saved_settings = Path(settings.path).read_bytes()
            country_choices = [country for country in downloader.COUNTRIES if country[0] in codes]
            wanted = downloader.references(directory, country_choices, downloader.PiconTask(), opener)
            expected = {}
            collection_names = {}
            for collection, manifest in manifests.items():
                entry = downloader.descriptor(manifest, collection, style)
                names = set(entry['files']) & set(wanted)
                if not names:
                    raise ValueError('Selected country collection has no matching references ' + collection)
                collection_names[collection] = names
                for name in names:
                    old = expected.get(name)
                    if old is not None and old != entry['files'][name]:
                        raise ValueError('Conflicting service reference across selected countries ' + name)
                    expected[name] = entry['files'][name]
            if len(expected) != sum(row['picons'] for row in rows):
                raise ValueError('Index coverage differs from actual catalogue identities')
            # Put the override in the largest collection so one-item selections still work.
            largest = max(collection_names.values(), key=len)
            custom_name = sorted(largest)[0]
            custom = Path(settings.location) / custom_name
            custom.parent.mkdir()
            custom_body = b'user-owned picon sentinel'
            custom.write_bytes(custom_body)
            del expected[custom_name]
            expected_archives = sum(bool(set(part['files']) & set(expected)) for manifest in manifests.values() for entry in [downloader.descriptor(manifest, manifest['collection'], style)] for part in (entry.get('parts') or [entry]))
            requests.clear()
            task = downloader.PiconTask()
            first = downloader.install(directory, settings, task, opener)
            if (first['failed'] or first['added'] != len(expected) or first['preserved'] != 1
                    or first['updated'] or first['unchanged']):
                raise AssertionError((first, task.drain()[-20:]))
            archives = sum(url.endswith('.zip') for url in requests)
            if archives != expected_archives:
                raise AssertionError((archives, expected_archives))
            library = downloader.PiconLibrary(settings.location, settings.style, settings.legacy_location)
            if library.files != expected:
                raise AssertionError('Installed PNG inventory differs from pinned manifests')
            for value in set(expected.values()):
                if digest((Path(library.directory) / (value + '.png')).read_bytes()) != value:
                    raise AssertionError('Installed PNG digest mismatch')
            requests.clear()
            repeated = downloader.install(directory, settings, downloader.PiconTask(), opener)
            if (repeated['failed'] or repeated['added'] or repeated['updated']
                    or repeated['unchanged'] != len(expected) or repeated['preserved'] != 1):
                raise AssertionError(repeated)
            repeated_archives = sum(url.endswith('.zip') for url in requests)
            if repeated_archives or custom.read_bytes() != custom_body:
                raise AssertionError('Repeat downloaded archives or changed user picon')
            if Path(store.path).read_bytes() != saved_store or Path(settings.path).read_bytes() != saved_settings:
                raise AssertionError('Downloader changed saved user data')
            report = dict(style=style, first=first, repeat=repeated, archives=archives,
                          repeat_zip_requests=repeated_archives,
                          exact_installed_png_hashes=len(expected), user_data_preserved=True)
            reports.append(report)
            print(json.dumps(report), flush=True)

    proof = dict(schema=1, radio_version=VERSION, radio_commit=STABLE_COMMIT,
                 mode='pinned PR21 downloader replay with actual immutable public GitHub packages, including multipart and legacy descriptors',
                 index_sha256=digest(raw_index), country_count=len(codes), selected_countries=codes,
                 index_country_count=len(document['countries']),
                 selected_catalogue_references=sum(row['picons'] for row in rows),
                 public_zip_urls_verified=len({entry['url'] for entry in package_entries}),
                 uncached_http_downloads=len(cache.downloaded), resolution=downloader.SIZE,
                 styles=reports, hardware_tested=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(proof, indent=2, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', required=True, type=Path)
    parser.add_argument('--countries', required=True, nargs='+', help='Country codes or all-available')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--radio', required=True, type=Path)
    parser.add_argument('--cache', type=Path, default=Path('tools-check/http-cache'))
    parser.add_argument('--workers', type=int, default=12)
    run(parser.parse_args())
