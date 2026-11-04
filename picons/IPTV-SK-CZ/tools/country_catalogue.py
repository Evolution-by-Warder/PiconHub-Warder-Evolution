"""Content-addressed country packages; the full receiver endpoint stays compatible."""
from collections import defaultdict
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / 'catalog/global'


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def write(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_bytes() != body:
        temporary = path.with_suffix(path.suffix + '.tmp')
        temporary.write_bytes(body)
        temporary.replace(path)


def export_packages(rows, countries, output):
    if not isinstance(rows, list) or not 100 <= len(rows) <= 100000:
        raise ValueError('Incomplete receiver catalogue')
    groups = defaultdict(list)
    references = set()
    for row in rows:
        if row['reference'] in references:
            raise ValueError('Duplicate receiver reference')
        references.add(row['reference'])
        groups[row['group']].append(row)
    entries = []
    used = set()

    def package(items, code, name, kind, directory):
        raw = encoded(items)
        # Python 3.9-3.12 may expose zlib's host OS byte with mtime=0;
        # normalize it to the Python 3.14 value for portable package versions.
        blob = bytearray(gzip.compress(raw, mtime=0))
        blob[9] = 255
        blob = bytes(blob)
        digest = hashlib.sha256(blob).hexdigest()
        path = directory + '/' + digest + '.json.gz'
        if len(blob) > 8 * 1024 * 1024 or len(raw) > 32 * 1024 * 1024:
            raise ValueError('Country package exceeds receiver bounds')
        write(output / path, blob)
        return dict(id=code, name=name, kind=kind, stations=len(items), path=path,
                    version=digest, sha256=digest, bytes=len(blob), decoded_bytes=len(raw),
                    decoded_sha256=hashlib.sha256(raw).hexdigest())

    for country in countries:
        name = country['name']
        code = 'SOURCE' if country.get('original_source_view') else country.get('countrycode') or 'UNCLASSIFIED'
        if not re.fullmatch(r'[A-Z]{2}|SOURCE|UNCLASSIFIED', code) or code in used:
            raise ValueError('Invalid or duplicate country identity')
        used.add(code)
        items = groups.pop(name, [])
        if not items or len(items) != country['stations']:
            raise ValueError('Country index count mismatch')
        entries.append(package(items, code, name, 'source' if code == 'SOURCE' else 'country',
                               'countries/' + code))
    if groups or sum(e['stations'] for e in entries) != len(rows):
        raise ValueError('Country package accounting mismatch')
    search = package(rows, 'WORLD', 'All groups', 'search', 'search')
    body = dict(schema=1, countries=entries, search=search)
    body['revision'] = hashlib.sha256(encoded(body)).hexdigest()
    write(output / 'country-manifest.json', encoded(body))
    return body


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT)
    args = parser.parse_args()
    with gzip.open(args.output / 'world-radio.receiver.json.gz', 'rt') as stream:
        rows = json.load(stream)
    countries = json.loads((args.output / 'countries.json').read_text())
    manifest = export_packages(rows, countries, args.output)
    print(json.dumps(dict(countries=len(manifest['countries']), revision=manifest['revision'],
                         stations=len(rows), manifest_bytes=(args.output / 'country-manifest.json').stat().st_size)))


if __name__ == '__main__':
    main()
