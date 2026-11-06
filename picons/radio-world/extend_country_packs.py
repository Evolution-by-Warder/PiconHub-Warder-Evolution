"""Extend the verified batch 23 country packages with batches 24 and 25."""
import argparse
from collections import defaultdict
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import zipfile

from prepare_country_packs import archive
from verify_batch import RESOLUTIONS, STYLES, require, sha256, verify, verify_archive

COUNTRIES = {'AR', 'DE', 'GB', 'US'}
BASE_PAYLOAD = '1707bdf858c9f831515d2be89d9d115280af8f6d'


def load(path):
    return json.loads(path.read_bytes())


def extend(checkout, world_path, output):
    radio = checkout / 'picons/radio-world'
    world = world_path.read_bytes()
    rows = {row['reference']: row for row in json.loads(gzip.decompress(world))}
    groups = {row['id']: row['name'] for row in load(radio / 'coverage.json')['groups']}
    additions = defaultdict(set)
    batches = {}
    for number in (24, 25):
        directory = radio / 'staging' / f'batch-{number}'
        verify(directory)
        batch = load(directory / 'manifest.json')
        require(batch['batch'] == number and batch['catalogue_sha256'] == sha256(world),
                'Incorrect batch or catalogue snapshot')
        batches[number] = directory, batch
        for station in batch['stations']:
            ref, code = station['reference'], station['country']
            row = rows[ref]
            require(code in COUNTRIES and row['group'] == groups[code]
                    and all(row[key] == station[key] for key in ('name', 'url', 'group')),
                    f'Catalogue identity differs for {ref}')
            filename = ref.replace(':', '_') + '.png'
            require(filename not in additions[code], f'Duplicate staged reference {ref}')
            additions[code].add(filename)
    require(set(additions) == COUNTRIES, 'Missing candidate country')

    require(not output.exists(), f'Output already exists: {output}')
    with TemporaryDirectory(dir=output.parent) as temp:
        root = Path(temp) / 'candidate'
        countries = {}
        for code, added in sorted(additions.items()):
            collection = f'IPTV-{code}'
            folder = Path('picons') / collection
            baseline = load(checkout / folder / 'catalog/release.json')
            require(baseline['collection'] == collection and baseline['status'] == 'verified'
                    and baseline['payload_commit'] == BASE_PAYLOAD, f'Unexpected baseline for {collection}')
            packages = {}
            old_names = set(baseline['packages']['220x132']['black']['files'])
            require(not added & old_names, f'Existing picon would be replaced in {collection}')
            destination = root / folder / 'packages'
            destination.mkdir(parents=True)
            for resolution in RESOLUTIONS:
                size = tuple(map(int, resolution.split('x')))
                packages[resolution] = {}
                for style in STYLES:
                    entry = baseline['packages'][resolution][style]
                    name = f'iptv-{code.lower()}-{style}-{resolution}.zip'
                    path = checkout / folder / 'packages' / name
                    require(verify_archive(path, entry, size, style) == old_names,
                            f'Inconsistent existing inventory in {name}')
                    with zipfile.ZipFile(path) as source:
                        images = {member: source.read(member) for member in old_names}
                    for directory, batch in batches.values():
                        staged = batch['packages'][resolution][style]
                        for part in staged.get('parts', [staged]):
                            with zipfile.ZipFile(directory / part['path']) as source:
                                images.update({member: source.read(member) for member in added & part['files'].keys()})
                    path = destination / name
                    result = archive(path, images)
                    require(verify_archive(path, result, size, style) == old_names | added,
                            f'Output inventory differs in {name}')
                    require(all(result['files'][member] == digest for member, digest in entry['files'].items()),
                            f'Existing PNG changed in {name}')
                    packages[resolution][style] = result
            countries[code] = {
                'collection': collection, 'new_references': len(added),
                'preserved_references': len(old_names),
                'catalogue_references': baseline['catalogue_stations'], 'packages': packages,
            }
        report = {'schema': 1, 'status': 'staging', 'batch': 25,
                  'catalogue_sha256': sha256(world), 'base_payload': BASE_PAYLOAD, 'countries': countries}
        (root / 'candidate.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        root.rename(output)
    for code, country in countries.items():
        print(code, 'preserved', country['preserved_references'], 'added', country['new_references'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ('checkout', 'world', 'output'):
        parser.add_argument(argument, type=Path)
    args = parser.parse_args()
    extend(args.checkout, args.world, args.output)
