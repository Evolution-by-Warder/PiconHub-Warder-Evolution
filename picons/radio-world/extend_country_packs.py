"""Combine verified radio batches with staged country packs, preserving every old PNG."""
import argparse
from collections import defaultdict
import gzip
import json
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile

from prepare_country_packs import archive
from verify_batch import RESOLUTIONS, STYLES, require, sha256, verify, verify_archive

ROOT = Path(__file__).resolve().parent
BASE = 'https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'
BASELINE = 'fe6a52a41b9b359bdf842d8b194830d4c0718e16'
BASE_COUNTRIES = ('AR', 'DE', 'GB', 'SE', 'UA', 'US')


def prepare(checkout, world_path, batches, output):
    require(not output.exists(), 'Output already exists')
    raw = world_path.read_bytes()
    world = json.loads(gzip.decompress(raw))
    catalogue = {row['reference']: row for row in world}
    require(len(catalogue) == len(world), 'Duplicate catalogue reference')
    countries = {row['id']: row for row in json.loads((ROOT / 'coverage.json').read_bytes())['groups']
                 if row['kind'] == 'country'}
    plans = []
    stations = {}
    names = defaultdict(set)
    for batch in batches:
        verify(batch)
        plan = json.loads((batch / 'manifest.json').read_bytes())
        require(sha256(raw) == plan['catalogue_sha256'], 'Catalogue hash mismatch')
        plans.append(plan)
        for station in plan['stations']:
            ref, code = station['reference'], station['country']
            require(ref not in stations, 'Duplicate incoming reference across batches: ' + ref)
            row = catalogue[ref]
            require(code in countries and countries[code]['name'] == row['group'], 'Country mismatch')
            require(all(row[k] == station[k] for k in ('name', 'url', 'group')), 'Station identity mismatch')
            stations[ref] = station
            names[code].add(ref.replace(':', '_') + '.png')
    manifests = {}
    for code in set(names):
        path = checkout / f'picons/IPTV-{code}/catalog/release.json'
        if path.exists():
            if code in BASE_COUNTRIES:
                pinned = subprocess.check_output(['git', '-C', str(checkout), 'show',
                    BASELINE + f':picons/IPTV-{code}/catalog/release.json'])
                require(path.read_bytes() == pinned, 'Baseline manifest differs from pinned commit')
            value = json.loads(path.read_bytes())
            require(value['status'] == 'verified' and value['collection'] == f'IPTV-{code}', 'Invalid baseline')
            manifests[code] = value
    report = dict(schema=2, status='staging', batches=[p['batch'] for p in plans],
                  baseline_commit=BASELINE, catalogue_commit=plans[0]['catalogue_commit'],
                  catalogue_sha256=sha256(raw), incoming_references=len(stations), countries={})
    for code in sorted(set(names)):
        require(re.fullmatch('[A-Z]{2}', code) and code in countries, 'Invalid country code')
        report['countries'][code] = dict(collection=f'IPTV-{code}', name=countries[code]['name'],
            new_references=len(names[code]), catalogue_references=countries[code]['catalogue_rows'],
            preserved_references=0, packages={})
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as scratch:
        root = Path(scratch) / 'candidate'
        for resolution in RESOLUTIONS:
            size = tuple(map(int, resolution.split('x')))
            for style in STYLES:
                incoming = {}
                for batch, plan in zip(batches, plans):
                    entry = plan['packages'][resolution][style]
                    for part in entry.get('parts', [entry]):
                        with zipfile.ZipFile(batch / part['path']) as package:
                            for name in part['files']:
                                require(name not in incoming, 'Repeated staged PNG')
                                incoming[name] = package.read(name)
                for code, country in report['countries'].items():
                    images = {}
                    previous = None
                    if code in manifests:
                        previous = manifests[code]['packages'][resolution][style]
                        baseline = checkout / f'picons/IPTV-{code}/packages' / previous['url'].rsplit('/', 1)[-1]
                        verify_archive(baseline, previous, size, style)
                        with zipfile.ZipFile(baseline) as package:
                            images = {name: package.read(name) for name in previous['files']}
                        require(not set(images) & names[code], 'Reference is already staged: ' + code)
                        country['preserved_references'] = len(images)
                    images.update({name: incoming[name] for name in names[code]})
                    path = root / f'picons/IPTV-{code}/packages/iptv-{code.lower()}-{style}-{resolution}.zip'
                    path.parent.mkdir(parents=True, exist_ok=True)
                    entry = archive(path, images)
                    verify_archive(path, entry, size, style)
                    if previous:
                        require(all(entry['files'][n] == h for n, h in previous['files'].items()), 'Baseline PNG changed')
                    country['packages'].setdefault(resolution, {})[style] = entry
        (root / 'candidate.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        root.rename(output)
    return report


def manifests(candidate, revision, checkout):
    require(re.fullmatch('[a-f0-9]{40}', revision), 'Expected immutable payload SHA')
    report = json.loads((candidate / 'candidate.json').read_bytes())
    for code, country in report['countries'].items():
        collection = f'IPTV-{code}'
        manifest = dict(schema=1, status='verified', collection=collection, country=code,
            version='2026.11.06-batches-' + '-'.join(map(str, report['batches'])),
            catalogue_stations=country['catalogue_references'], payload_commit=revision, packages={})
        for resolution, styles in country['packages'].items():
            manifest['packages'][resolution] = {}
            for style, entry in styles.items():
                path = Path('picons') / collection / 'packages' / entry['path']
                raw = (checkout / path).read_bytes()
                require(sha256(raw) == entry['sha256'] and len(raw) == entry['bytes'], 'Payload changed')
                manifest['packages'][resolution][style] = dict(resolution=resolution,
                    url=BASE + revision + '/' + path.as_posix(),
                    **{k: entry[k] for k in ('bytes', 'sha256', 'files')})
        target = checkout / f'picons/{collection}/catalog/release.json'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='action', required=True)
    build = subs.add_parser('build')
    build.add_argument('checkout', type=Path)
    build.add_argument('world', type=Path)
    build.add_argument('output', type=Path)
    build.add_argument('batches', nargs='+', type=Path)
    pin = subs.add_parser('manifests')
    pin.add_argument('candidate', type=Path)
    pin.add_argument('revision')
    pin.add_argument('checkout', type=Path)
    args = parser.parse_args()
    if args.action == 'build':
        report = prepare(args.checkout, args.world, args.batches, args.output)
        print('Prepared', len(report['countries']), 'countries with', report['incoming_references'], 'incoming references')
    else:
        manifests(args.candidate, args.revision, args.checkout)
