#!/usr/bin/env python3
"""Build and validate the DAB preview catalog from a receiver mapping CSV.

No network calls, no logos downloaded, and no production installation.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parents[1] / 'plugin' / 'src' / 'Plugins' / 'Extensions' / 'WarderPiconHub'))
from radio_references import picon_filename_is_reference


def build_catalog(csv_file, preview_dir):
    with csv_file.open('r', encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError('Empty receiver mapping')
    records = []
    seen = set()
    for row in rows:
        name = row['picon_filename'].strip()
        station = row['station'].strip()
        bouquet = row['bouquet'].strip()
        if not station or not bouquet or not picon_filename_is_reference(name):
            raise ValueError('Invalid receiver mapping row')
        if name in seen:
            raise ValueError('Duplicate reference: %s' % name)
        seen.add(name)
        variants = {}
        for variant in ('transparent', 'white', 'black'):
            path = preview_dir / variant / name
            if not path.is_file():
                raise ValueError('Missing preview: %s' % path)
            variants[variant] = hashlib.sha256(path.read_bytes()).hexdigest()
        records.append({
            'station': station,
            'bouquet': bouquet,
            'picon_filename': name,
            'preview_sha256': variants,
            'logo_verified': False,
            'approved_master_v9': False,
        })
    return {
        'schema_version': 1,
        'status': 'preview_only',
        'station_count': len(set(row['station'] for row in records)),
        'reference_count': len(records),
        'records': sorted(records, key=lambda item: item['picon_filename']),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mapping', type=Path, required=True)
    parser.add_argument('--preview', type=Path, default=ROOT / 'preview')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    catalog = build_catalog(args.mapping, args.preview)
    args.output.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('%s stations / %s references (PREVIEW ONLY)' %
          (catalog['station_count'], catalog['reference_count']))


if __name__ == '__main__':
    main()
