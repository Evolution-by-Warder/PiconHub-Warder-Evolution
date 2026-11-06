"""Prepare batch 23 country packages without publishing it."""
import argparse
from collections import defaultdict
import gzip
import io
import json
from pathlib import Path
import tempfile
import zipfile

from verify_batch import RESOLUTIONS, STYLES, require, sha256, verify, verify_archive

RADIO_ROOT = Path(__file__).resolve().parent


def read_json(path):
    return json.loads(path.read_bytes())


def archive(output, images):
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as target:
        for name, data in sorted(images.items()):
            info = zipfile.ZipInfo(name)
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            target.writestr(info, data)
    data = output.read_bytes()
    return {
        'path': output.name,
        'bytes': len(data),
        'sha256': sha256(data),
        'files': {name: sha256(data) for name, data in sorted(images.items())},
    }


def prepare(batch, world_path, de_manifest_path, de_packages, output):
    verify(batch)
    manifest = read_json(batch / 'manifest.json')
    world = world_path.read_bytes()
    require(sha256(world) == manifest['catalogue_sha256'], 'Catalogue snapshot differs from the batch')
    catalogue = json.loads(gzip.decompress(world))
    by_reference = {row['reference']: row for row in catalogue}
    require(len(catalogue) == len(by_reference), 'Duplicate catalogue reference')
    countries = {row['id']: row for row in read_json(RADIO_ROOT / 'coverage.json')['groups']}
    by_country = defaultdict(set)
    for station in manifest['stations']:
        row = by_reference[station['reference']]
        country = station['country']
        require(row['group'] == countries[country]['name'] and row['url'] == station['url']
                and row['name'] == station['name'], f'Catalogue identity mismatch for {station["reference"]}')
        by_country[country].add(station['reference'].replace(':', '_') + '.png')

    de_manifest = read_json(de_manifest_path)
    require(de_manifest['status'] == 'verified' and de_manifest['collection'] == 'IPTV-DE',
            'A verified Germany release is required')
    package_sets = {}
    for country, names in sorted(by_country.items()):
        package_sets[country] = {
            'collection': f'IPTV-{country}', 'new_references': len(names),
            'catalogue_references': countries[country]['catalogue_rows'], 'packages': {},
        }
    previous_names = set(de_manifest['packages']['220x132']['black']['files'])
    require(not previous_names & by_country['DE'], 'German reference already exists in the verified baseline')

    require(not output.exists(), f'Output already exists: {output}')
    with tempfile.TemporaryDirectory(dir=output.parent) as scratch:
        root = Path(scratch) / 'candidate'
        for resolution in RESOLUTIONS:
            size = tuple(map(int, resolution.split('x')))
            for style in STYLES:
                staged = manifest['packages'][resolution][style]
                incoming = {}
                for part in staged.get('parts', [staged]):
                    with zipfile.ZipFile(batch / part['path']) as package:
                        incoming.update({name: package.read(name) for name in part['files']})
                previous = de_manifest['packages'][resolution][style]
                expected = f'iptv-de-{style}-{resolution}.zip'
                require(previous['url'].rsplit('/', 1)[-1] == expected, 'Unexpected baseline package path')
                baseline = de_packages / expected
                require(verify_archive(baseline, previous, size, style) == previous_names,
                        f'Inconsistent German inventory in {expected}')
                with zipfile.ZipFile(baseline) as package:
                    old_images = {name: package.read(name) for name in previous_names}

                for country, names in by_country.items():
                    candidate = package_sets[country]
                    images = {name: incoming[name] for name in names}
                    if country == 'DE':
                        images.update(old_images)
                    folder = root / 'picons' / candidate['collection'] / 'packages'
                    folder.mkdir(parents=True, exist_ok=True)
                    output_zip = folder / f'iptv-{country.lower()}-{style}-{resolution}.zip'
                    entry = archive(output_zip, images)
                    require(verify_archive(output_zip, entry, size, style) == set(images),
                            f'Generated inventory differs for {output_zip.name}')
                    if country == 'DE':
                        require(all(entry['files'][name] == digest for name, digest in previous['files'].items()),
                                f'An existing German PNG changed in {output_zip.name}')
                    candidate['packages'].setdefault(resolution, {})[style] = entry

        report = {
            'schema': 1, 'status': 'staging', 'batch': manifest['batch'],
            'catalogue_commit': manifest['catalogue_commit'], 'catalogue_sha256': manifest['catalogue_sha256'],
            'germany_base_payload_commit': de_manifest['payload_commit'],
            'germany_base_manifest_sha256': sha256(de_manifest_path.read_bytes()),
            'germany_existing_references_preserved': len(previous_names), 'countries': package_sets,
        }
        (root / 'candidate.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        root.rename(output)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('batch', 'world', 'de_manifest', 'de_packages', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    report = prepare(args.batch, args.world, args.de_manifest, args.de_packages, args.output)
    print(f'Prepared {len(report["countries"])} countries and preserved '
          f'{report["germany_existing_references_preserved"]} German references in all nine variants.')
