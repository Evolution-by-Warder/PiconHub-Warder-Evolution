"""Build all catalogue countries; availability comes only from pinned radio releases."""
import argparse
from collections import defaultdict
import gzip
import json
from pathlib import Path
import re
import subprocess

from verify_batch import require, sha256

BASE = 'https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'
WORLD = 'picons/IPTV-SK-CZ/catalog/global/search/2ae88890a953c2f68d3f20352ad56a7390645bd3ce189573dd94e50c8a65abfe.json.gz'


def build(checkout, revision):
    require(re.fullmatch('[a-f0-9]{40}', revision), 'Expected immutable release-manifest revision')
    def read(path):
        return subprocess.check_output(['git', '-C', str(checkout), 'show', revision + ':' + path])
    country_manifest = json.loads(read('picons/IPTV-SK-CZ/catalog/global/country-manifest.json'))
    raw_world = read(WORLD)
    require(sha256(raw_world) == Path(WORLD).name.split('.')[0], 'Catalogue snapshot changed')
    by_group = defaultdict(set)
    for station in json.loads(gzip.decompress(raw_world)):
        by_group[station['group']].add(station['reference'].replace(':', '_') + '.png')
    tree = set(subprocess.check_output(['git', '-C', str(checkout), 'ls-tree', '-r', '--name-only', revision, 'picons']).decode().splitlines())
    releases = {}
    countries = []
    for country in country_manifest['countries']:
        if country['kind'] != 'country':
            continue
        code = country['id']
        require(re.fullmatch('[A-Z]{2}', code), 'Invalid country code')
        collection = 'IPTV-SK-CZ' if code in ('SK', 'CZ') else 'IPTV-' + code
        path = 'picons/' + collection + '/catalog/release.json'
        if path not in releases and path in tree:
            raw = read(path)
            manifest = json.loads(raw)
            require(manifest['schema'] == 1 and manifest['status'] == 'verified'
                    and manifest['collection'] == collection, 'Invalid radio release')
            variants = manifest['packages']['220x132']
            require(set(variants) == {'transparent', 'white', 'black'}, 'Missing 220x132 background')
            inventories = [set(variants[style]['files']) for style in ('transparent', 'white', 'black')]
            require(all(names == inventories[0] for names in inventories), 'Background inventories differ')
            releases[path] = (inventories[0], dict(commit=revision, url=BASE + revision + '/' + path,
                                                  bytes=len(raw), sha256=sha256(raw)))
        expected = by_group[country['name']]
        require(len(expected) == country['stations'], 'Country catalogue count mismatch')
        covered = len(expected & releases[path][0]) if path in releases else 0
        countries.append(dict(id=code, name=country['name'], collection=collection,
            stations=len(expected), picons=covered,
            status='unavailable' if not covered else 'complete' if covered == len(expected) else 'partial',
            release=releases[path][1] if covered else None))
    return dict(schema=1, kind='warder-radio-picons', resolution='220x132',
        catalogue_revision=country_manifest['revision'], catalogue_sha256=sha256(raw_world),
        release_revision=revision, countries=countries)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('revision')
    parser.add_argument('output', type=Path)
    parser.add_argument('--checkout', type=Path, default=Path.cwd())
    args = parser.parse_args()
    value = build(args.checkout, args.revision)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    print('Indexed', len(value['countries']), 'countries;',
          sum(row['status'] != 'unavailable' for row in value['countries']), 'downloadable')
