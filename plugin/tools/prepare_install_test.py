#!/usr/bin/env python3
"""Prepare an isolated RC package without modifying any published feed."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.35'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version',default=VERSION,choices=('0.1.35','0.1.36','0.1.37'))
    version=parser.parse_args().version
    feed = ROOT/'update/stable.json'
    before = hashlib.sha256(feed.read_bytes()).hexdigest()
    (ROOT/'src/Plugins/Extensions/WarderPiconHub/version.txt').write_text(version+'\n')
    path = ROOT/'project.json'
    value = json.loads(path.read_text())
    value['development_version'] = version
    path.write_text(json.dumps(value,indent=2)+'\n')
    (ROOT/'update/RELEASE-NOTES.i18n.json').write_bytes((ROOT/('design/install-test/notes-'+version+'.json')).read_bytes())
    (ROOT/'update/RELEASE-NOTES.md').write_bytes((ROOT/('design/install-test/RELEASE-NOTES-'+version+'.md')).read_bytes())
    assert hashlib.sha256(feed.read_bytes()).hexdigest()==before
    folder = ROOT/'build'
    folder.mkdir(exist_ok=True)
    (folder/'install-test-feed-isolation.json').write_text(json.dumps({'stable_feed_sha256':before,'version':version},indent=2)+'\n')
    print('Prepared '+version+'; stable feed unchanged')


if __name__ == '__main__':
    main()
