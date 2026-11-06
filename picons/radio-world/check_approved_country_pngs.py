"""Reject changes to approved PNG bytes before staging Radio country packs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile


def check(checkout, baseline, countries):
    checked = 0
    for country in countries:
        root = f'picons/IPTV-{country}'
        manifest = json.loads(subprocess.check_output([
            'git', '-C', str(checkout), 'show', baseline + ':' + root + '/catalog/release.json',
        ]))
        for styles in manifest['packages'].values():
            for entry in styles.values():
                path = checkout / root / 'packages' / entry['url'].rsplit('/', 1)[-1]
                with zipfile.ZipFile(path) as archive:
                    names = archive.namelist()
                    if len(names) != len(set(names)):
                        raise ValueError(f'Duplicate entry in {path}')
                    for name, expected in entry['files'].items():
                        if hashlib.sha256(archive.read(name)).hexdigest() != expected:
                            raise ValueError(f'Approved PNG changed: {path}/{name}')
                        checked += 1
    print(f'Verified {checked} approved PNG members against {baseline}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkout', type=Path)
    parser.add_argument('baseline')
    parser.add_argument('countries', nargs='+')
    args = parser.parse_args()
    check(args.checkout, args.baseline, args.countries)
