#!/usr/bin/env python3
"""Stage approved DAB picons into an Enigma2 picon directory.

Developer utility; dry-run by default. Never installs preview placeholders.
"""
import argparse
from pathlib import Path
import shutil
import sys
import struct

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'plugin' / 'src' / 'Plugins' / 'Extensions' / 'WarderPiconHub'))
from radio_references import picon_filename_is_reference


def validate_png(path):
    """Reject non-PNG payloads and unexpected image dimensions."""
    with path.open('rb') as stream:
        header = stream.read(24)
    if len(header) < 24 or header[:8] != b'\x89PNG\r\n\x1a\n' or header[12:16] != b'IHDR':
        raise ValueError('Not a valid PNG header: %s' % path)
    width, height = struct.unpack('>II', header[16:24])
    if (width, height) != (220, 132):
        raise ValueError('Unexpected PNG dimensions %sx%s: %s' % (width, height, path))


def plan(source, destination):
    if not source.is_dir():
        raise ValueError('Verified source directory is missing: %s' % source)
    result = []
    for png in sorted(source.glob('*.png')):
        if not picon_filename_is_reference(png.name):
            raise ValueError('Invalid picon filename: %s' % png.name)
        validate_png(png)
        result.append((png, destination / png.name))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', required=True, help='Enigma2 picon directory')
    parser.add_argument('--apply', action='store_true', help='Copy approved files (default: dry run)')
    parser.add_argument('--overwrite', action='store_true', help='Replace existing files (requires --apply)')
    args = parser.parse_args()
    if args.overwrite and not args.apply:
        parser.error('--overwrite requires --apply')
    source = Path(__file__).resolve().parent / 'verified'
    destination = Path(args.destination).expanduser()
    entries = plan(source, destination)
    if not entries:
        print('No approved DAB picons in verified/. Nothing to install.')
        return 0
    if args.apply:
        destination.mkdir(parents=True, exist_ok=True)
    for src, dst in entries:
        if dst.exists() and not args.overwrite:
            print('SKIP existing: %s' % dst)
            continue
        print('%s %s -> %s' % ('COPY' if args.apply else 'DRY-RUN', src.name, dst))
        if args.apply:
            shutil.copy2(str(src), str(dst))
    return 0


if __name__ == '__main__':
    sys.exit(main())
