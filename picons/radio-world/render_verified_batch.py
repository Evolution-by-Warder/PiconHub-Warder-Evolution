"""Render the verified batch originals into the Warder Radio master variants."""
import argparse
import gzip
import io
import json
from pathlib import Path
import zipfile

from PIL import Image

from verify_batch import RESOLUTIONS, STYLES, require, sha256, verify


def render(batch, world_path, masters_path):
    plan = json.loads((batch / 'sources.json').read_bytes())
    world = world_path.read_bytes()
    require(sha256(world) == plan['catalogue_sha256'], 'Radio catalogue hash changed')
    catalogue = {row['reference']: row for row in json.loads(gzip.decompress(world))}
    originals = {}
    for digest, original in plan['source_inventory'].items():
        raw = (batch / original['path']).read_bytes()
        require(len(raw) == original['bytes'] and sha256(raw) == digest, 'Original image changed')
        with Image.open(io.BytesIO(raw)) as image:
            mark = image.convert('RGBA')
        mark.thumbnail((192, 104), Image.Resampling.LANCZOS)
        require(mark.getbbox(), 'Empty station mark')
        originals[digest] = mark
    masters = {'transparent': Image.new('RGBA', (220, 132))}
    for style, digest in plan['master_sha256'].items():
        raw = (masters_path / (style + '.png')).read_bytes()
        require(sha256(raw) == digest, 'Warder master changed')
        with Image.open(io.BytesIO(raw)) as image:
            masters[style] = image.convert('RGBA')
    for station in plan['stations']:
        expected = catalogue[station['reference']]
        require(all(expected[key] == station[key] for key in ('name', 'url', 'group')),
                f'Catalogue mismatch for {station["reference"]}')
    packages = {}
    for resolution in RESOLUTIONS:
        size = tuple(map(int, resolution.split('x')))
        packages[resolution] = {}
        for style in STYLES:
            path = batch / f'radio-batch{plan["batch"]}-{style}-{resolution}.zip'
            member_hashes = {}
            with zipfile.ZipFile(path, 'w') as package:
                for station in plan['stations']:
                    key = station.get('black_source', station['source']) if style == 'black' else station['source']
                    mark = originals[key]
                    image = masters[style].copy()
                    position = ((220 - mark.width) // 2, (132 - mark.height) // 2)
                    if style == 'transparent':
                        image.paste(mark, position)
                    else:
                        image.alpha_composite(mark, position)
                    if size != image.size:
                        image = image.resize(size, Image.Resampling.LANCZOS)
                    buffer = io.BytesIO()
                    image.save(buffer, format='PNG', optimize=True)
                    data = buffer.getvalue()
                    name = station['reference'].replace(':', '_') + '.png'
                    member_hashes[name] = sha256(data)
                    info = zipfile.ZipInfo(name)
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o100644 << 16
                    package.writestr(info, data)
            body = path.read_bytes()
            packages[resolution][style] = {
                'path': path.name, 'bytes': len(body), 'sha256': sha256(body), 'files': member_hashes,
            }
    (batch / 'manifest.json').write_text(json.dumps(dict(plan, status='staging', packages=packages),
                                                    ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Verified {verify(batch)} station references across nine variants')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('batch', type=Path)
    parser.add_argument('world', type=Path)
    parser.add_argument('masters', type=Path)
    args = parser.parse_args()
    render(args.batch, args.world, args.masters)
