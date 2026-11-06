"""Place verified Radio ZIPs and their SHA-pinned downloader manifests in a checkout."""
import argparse
import json
from pathlib import Path
import re
import shutil

from verify_batch import require, sha256

BATCH_COUNTRIES = {
    23: {'AR', 'DE', 'GB', 'SE', 'UA', 'US'},
    25: {'AR', 'DE', 'GB', 'US'},
}
BASE = 'https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'


def prepare(candidate, checkout, revision):
    report = json.loads((candidate / 'candidate.json').read_bytes())
    batch = report['batch']
    require(report['schema'] == 1 and report['status'] == 'staging'
            and set(report['countries']) == BATCH_COUNTRIES.get(batch), 'Unexpected Radio candidate')
    require(revision == 'payload' or re.fullmatch(r'[a-f0-9]{40}', revision), 'Expected a payload commit SHA')
    for code, country in sorted(report['countries'].items()):
        collection = f'IPTV-{code}'
        root = Path('picons') / collection
        manifest = {
            'schema': 1, 'status': 'verified', 'collection': collection, 'country': code,
            'version': f'2026.11.06-batch{batch}', 'catalogue_stations': country['catalogue_references'],
            'payload_commit': revision, 'packages': {},
        }
        for size, variants in country['packages'].items():
            manifest['packages'][size] = {}
            for style, entry in variants.items():
                name = f'iptv-{code.lower()}-{style}-{size}.zip'
                require(name == entry['path'], 'Unexpected package name')
                path = root / 'packages' / name
                source = candidate / path
                destination = checkout / path
                data = (source if revision == 'payload' else destination).read_bytes()
                require(len(data) == entry['bytes'] and sha256(data) == entry['sha256'],
                        f'Package differs from candidate inventory: {name}')
                if revision == 'payload':
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, destination)
                else:
                    manifest['packages'][size][style] = {
                        'resolution': size, 'url': BASE + revision + '/' + path.as_posix(),
                        **{key: entry[key] for key in ('bytes', 'sha256', 'files')},
                    }
        if revision != 'payload':
            output = checkout / root / 'catalog/release.json'
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('revision', help='payload to copy ZIPs, or the commit containing those ZIPs')
    parser.add_argument('--checkout', type=Path, default=Path.cwd())
    args = parser.parse_args()
    prepare(args.candidate, args.checkout, args.revision)
