#!/usr/bin/env python3
"""Reproduce one approved laut.fm chunk with immutable Warder repo rendering.
Requires Pillow==13.0.0. Uses public pinned GitHub resources and frozen official
laut.fm image URLs; SHA256, exact byte length and Git blobSHA1 guard every input.
All nine expected output hashes are checked before staging files are written.
No authentication is created. Existing unequal files and ZIPs are never changed.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.parse
import urllib.request
import zipfile

import PIL
from PIL import Image

STAGE = 'picons/radio-world/staging/batch-42-laut-source'
SIZES = ('50x30', '220x132', '400x240')
STYLES = ('transparent', 'white', 'black')
VARIANTS = {size + '/' + style for size in SIZES for style in STYLES}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()


def valid_hash(value, length):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{' + str(length) + '}', value)


def validated(raw, resource):
    require(len(raw) == resource['bytes'], 'Input byte count mismatch')
    require(digest(raw) == resource['sha256'], 'Input SHA256 mismatch')
    require(blob(raw) == resource['git_blob'], 'Input Git blobSHA1 mismatch')
    return raw


def load(resource, url, cache, extension, official):
    require(valid_hash(resource['sha256'], 64) and valid_hash(resource['git_blob'], 40), 'Unpinned input')
    require(0 < resource['bytes'] <= 16 * 1024 * 1024, 'Unexpected input size')
    if cache:
        path = cache / (resource['sha256'] + extension)
        if path.exists():
            return validated(path.read_bytes(), resource)
    expected_host = 'assets.laut.fm' if official else 'raw.githubusercontent.com'
    require(urllib.parse.urlsplit(url).scheme == 'https' and urllib.parse.urlsplit(url).hostname == expected_host, 'Unexpected input origin')
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': '*/*'})
    with urllib.request.urlopen(request, timeout=60) as response:
        require(urllib.parse.urlsplit(response.url).hostname == expected_host, 'Unexpected input redirect')
        raw = response.read(resource['bytes'] + 1)
    return validated(raw, resource)


def put_immutable(path, raw):
    if path.exists():
        require(path.is_file() and path.read_bytes() == raw, 'Refusing to overwrite unequal existing file: ' + str(path))
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as handle:
            handle.write(raw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--source-cache', type=Path, help='Optional read-only frozen .img input cache')
    parser.add_argument('--resource-cache', type=Path, help='Optional read-only pinned SHA256.blob repo resource cache')
    args = parser.parse_args()
    require(PIL.__version__ == '13.0.0', 'Install the pinned Pillow==13.0.0 to reproduce the approved PNG bytes')
    raw_plan = args.plan.read_bytes()
    plan = json.loads(raw_plan)
    require(plan['schema'] == 1 and plan['repository'] == 'Evolution-by-Warder/PiconHub-Warder-Evolution', 'Unexpected plan schema/repository')
    require(plan['stage'] == STAGE and 1 <= plan['references'] <= 100, 'Unexpected destination/chunk scope')
    require(plan['must_not_admit_indices'] == [558], 'Missing source-hold protection')
    rows = plan['expected_selection']['entries']
    require(len(rows) == plan['references'] and len({r['ref'] for r in rows}) == len(rows), 'Invalid reference inventory')
    require(not any(r['index'] == 558 for r in rows), 'Held source558 must never enter output')
    require(all(r['source_commit'] is None and r['asset_root'] == STAGE + '/verified-assets' for r in rows), 'Expected unpinned working selection')
    expected = {}
    for row in rows:
        require(set(row['variants']) == VARIANTS, 'Each reference must have9expectedvariants')
        require(set(row['final_visual_approval']['reviewed_variants']) == VARIANTS and row['final_visual_approval']['decision'] == 'approve', 'Final nine-variant visual approval missing')
        for key, value in row['variants'].items():
            require(len(value) == 3 and valid_hash(value[0], 64) and valid_hash(value[2], 40), 'Unpinned output hash')
            expected[(row['ref'], key)] = value
    require(len(expected) == plan['png_instances'] == len(rows) * 9, 'Output instance count mismatch')
    require(len({v[0] for v in expected.values()}) == plan['unique_pngs'], 'Unique output count mismatch')
    require(set(plan['resources']) == {'renderer', 'verifier', 'white', 'black', 'catalogue'}, 'Invalid immutable repo resources')
    tasks = []
    for name, resource in plan['resources'].items():
        require(valid_hash(resource['commit'], 40), 'Repo input must pin a full commit')
        path = Path(resource['path'])
        require(not path.is_absolute() and '..' not in path.parts, 'Unsafe pinned path')
        url = 'https://raw.githubusercontent.com/' + plan['repository'] + '/' + resource['commit'] + '/' + urllib.parse.quote(resource['path'], safe='/')
        tasks.append((('repo', name), resource, url, args.resource_cache, '.blob', False))
    for source_sha, resource in plan['originals'].items():
        require(resource['sha256'] == source_sha, 'Original inventory key mismatch')
        tasks.append((('source', source_sha), resource, resource['url'], args.source_cache, '.img', True))
    print('Loading', len(tasks), 'frozen inputs for chunk', plan['chunk'], flush=True)
    with ThreadPoolExecutor(max_workers=8) as pool:
        loaded = list(pool.map(lambda task: (task[0], load(*task[1:])), tasks))
    loaded = dict(loaded)
    originals = {key: loaded[('source', key)] for key in plan['originals']}
    resources = {key: loaded[('repo', key)] for key in plan['resources']}
    outputs = {}
    with tempfile.TemporaryDirectory(prefix='warder-laut42-') as temporary:
        batch = Path(temporary)
        (batch / 'originals').mkdir()
        (batch / 'masters').mkdir()
        for source_sha, inventory in plan['render_sources']['source_inventory'].items():
            require(inventory['path'] == 'originals/' + source_sha + '.img', 'Unexpected local original path')
            require(inventory['sha256'] == source_sha and inventory['bytes'] == len(originals[source_sha]), 'Render source mismatch')
            (batch / inventory['path']).write_bytes(originals[source_sha])
        require(plan['render_sources']['catalogue_sha256'] == digest(resources['catalogue']), 'Catalogue mismatch')
        for style in ('white', 'black'):
            require(plan['render_sources']['master_sha256'][style] == digest(resources[style]), 'Immutable MASTER mismatch')
            (batch / 'masters' / (style + '.png')).write_bytes(resources[style])
        (batch / 'render_verified_batch.py').write_bytes(resources['renderer'])
        (batch / 'verify_batch.py').write_bytes(resources['verifier'])
        (batch / 'world.json.gz').write_bytes(resources['catalogue'])
        (batch / 'sources.json').write_text(json.dumps(plan['render_sources'], indent=2, ensure_ascii=False) + '\n')
        print('Running unchanged pinned repo renderer/verifier', flush=True)
        subprocess.run([os.sys.executable, str(batch / 'render_verified_batch.py'), str(batch), str(batch / 'world.json.gz'), str(batch / 'masters')], check=True)
        manifest = json.loads((batch / 'manifest.json').read_bytes())
        for size in SIZES:
            for style in STYLES:
                package = manifest['packages'][size][style]
                with zipfile.ZipFile(batch / package['path']) as archive:
                    require(archive.testzip() is None and len(archive.namelist()) == len(rows), 'Temporary renderer archive inventory mismatch')
                    for row in rows:
                        name = row['ref'].replace(':', '_') + '.png'
                        raw = archive.read(name)
                        sha, count, git_blob = expected[(row['ref'], size + '/' + style)]
                        require(digest(raw) == sha and len(raw) == count and blob(raw) == git_blob, 'PNG differs from the approved local output: ' + row['ref'] + ' ' + size + '/' + style)
                        with Image.open(io.BytesIO(raw), formats=['PNG']) as image:
                            require(image.mode == 'RGBA' and image.size == tuple(map(int, size.split('x'))), 'PNG format/geometry mismatch')
                            image.verify()
                        if sha in outputs:
                            require(outputs[sha] == raw, 'Output SHA collision')
                        outputs[sha] = raw
    require(len(outputs) == plan['unique_pngs'], 'Unexpected deduplicated output count')
    destination = args.output_root.resolve() / STAGE
    writes = {destination / 'verified-assets' / (sha + '.png'): raw for sha, raw in outputs.items()}
    writes.update({destination / 'originals' / (sha + '.img'): raw for sha, raw in originals.items()})
    writes[destination / 'plans' / ('producer-plan-' + str(plan['chunk']).zfill(3) + '.json')] = raw_plan
    selection_raw = (json.dumps(plan['expected_selection'], indent=2, ensure_ascii=False) + '\n').encode()
    writes[destination / ('selection-chunk-' + str(plan['chunk']).zfill(3) + '.json')] = selection_raw
    proof = {'schema': 1, 'status': 'pass', 'chunk': plan['chunk'], 'references': len(rows), 'png_instances': len(expected),
             'unique_pngs': len(outputs), 'originals': len(originals), 'plan_sha256': digest(raw_plan),
             'runtime': {'pillow': PIL.__version__}, 'all_nine_output_sha256_bytes_gitblob_match_local_approved': True,
             'original_bytes_preserved': True, 'source_commit': None, 'must_not_admit_indices': [558],
             'resources': plan['resources'], 'original_inventory': plan['originals'],
             'output_files': {sha + '.png': {'sha256': sha, 'bytes': len(raw), 'git_blob': blob(raw)} for sha, raw in sorted(outputs.items())}}
    writes[destination / ('reproduction-proof-chunk-' + str(plan['chunk']).zfill(3) + '.json')] = (json.dumps(proof, indent=2, ensure_ascii=False) + '\n').encode()
    # Preflight all existing paths before writing any new destination files.
    for path, raw in writes.items():
        if path.exists():
            require(path.is_file() and path.read_bytes() == raw, 'Refusing to change existing destination: ' + str(path))
    for path, raw in writes.items():
        put_immutable(path, raw)
    print('PASS:', len(rows), 'references;', len(expected), 'PNG instances;', len(outputs), 'unique PNGs;', len(originals), 'byte-preserved originals at', destination, flush=True)


if __name__ == '__main__':
    main()
