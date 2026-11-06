"""Verify a staged Warder Radio batch against its checked-in manifest."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

from PIL import Image

RESOLUTIONS = ('50x30', '220x132', '400x240')
STYLES = ('transparent', 'white', 'black')
REFERENCE = re.compile(r'(?:4097|5001|5002):0:2:(?:[0-9A-Fa-f]+:){6}[0-9A-Fa-f]+')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def verify(directory):
    manifest = json.loads((directory / 'manifest.json').read_bytes())
    require(manifest['schema'] == 1 and manifest['status'] == 'staging', 'Unknown staging schema')
    refs = [station['reference'] for station in manifest['stations']]
    require(refs and len(set(refs)) == len(refs), 'Empty or duplicate station inventory')
    require(all(REFERENCE.fullmatch(ref) for ref in refs), 'Invalid radio service reference')
    expected = {ref.replace(':', '_') + '.png' for ref in refs}
    packages = manifest['packages']
    require(set(packages) == set(RESOLUTIONS), 'Invalid resolution inventory')
    for resolution in RESOLUTIONS:
        size = tuple(map(int, resolution.split('x')))
        require(set(packages[resolution]) == set(STYLES), f'Invalid styles for {resolution}')
        for style in STYLES:
            entry = packages[resolution][style]
            stem = f'radio-batch{manifest["batch"]}-{style}-{resolution}'
            parts = entry.get('parts', [entry])
            require(isinstance(parts, list) and parts, f'Invalid package parts for {stem}')
            seen = set()
            for index, part in enumerate(parts, 1):
                name = f'{stem}-part{index:02d}.zip' if 'parts' in entry else f'{stem}.zip'
                require(part['path'] == name, f'Invalid archive path for {name}')
                members = verify_archive(directory / name, part, size, style)
                require(not seen & members, f'Duplicate archive member across parts for {name}')
                seen.update(members)
            require(seen == expected, f'Incorrect station inventory for {stem}')
    return len(expected)


def verify_archive(path, entry, size, style):
    name = path.name
    body = path.read_bytes()
    require(len(body) == entry['bytes'] and sha256(body) == entry['sha256'], f'Archive digest mismatch for {name}')
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        members = archive.namelist()
        require(len(members) == len(set(members)) and set(members) == set(entry['files']),
                f'Invalid archive inventory for {name}')
        for member in members:
            data = archive.read(member)
            require(sha256(data) == entry['files'][member], f'Member digest mismatch for {name}/{member}')
            with Image.open(io.BytesIO(data), formats=['PNG']) as image:
                require(image.mode == 'RGBA' and image.size == size, f'Invalid PNG format for {name}/{member}')
                image.verify()
            with Image.open(io.BytesIO(data), formats=['PNG']) as image:
                image.load()
                if style == 'transparent':
                    alpha = image.getchannel('A')
                    require(alpha.getpixel((0, 0)) == 0 and alpha.getextrema()[1] > 0,
                            f'Invalid transparent canvas for {name}/{member}')
    return set(members)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    stations = verify(parser.parse_args().directory)
    print(f'Verified {stations} radio references and {stations * 9} PNGs across 9 variants.')
