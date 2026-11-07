#!/usr/bin/env python3
"""Reproduce the approved18x9 repair PNGs from pinned public GitHub objects.

Requires Python3 and Pillow. No credentials are created or read by this script.
Example on the existing authorized Actions checkout:
  python path/to/reproduce_on_github.py --plan path/to/reproduce-plan.json --output-root .

The unchanged repo renderer creates temporary utility ZIPs inside TemporaryDirectory;
only162SHA-named PNGs are copied to the explicit staging destination. Existing source
files, existing ZIPs and unequal existing destination files are never overwritten.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile
import zipfile
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

DESTINATION = 'picons/radio-world/staging/batch-40-replay-repair/verified-assets'
HEX40 = re.compile(r'[0-9a-f]{40}\Z')
HEX64 = re.compile(r'[0-9a-f]{64}\Z')
RESOLUTIONS = {'50x30', '220x132', '400x240'}
STYLES = {'transparent', 'white', 'black'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()


def git(repo, *args, input=None, check=True):
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_NO_LAZY_FETCH='1')
    result = subprocess.run(['git', '-C', str(repo), *args], input=input,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if check and result.returncode:
        raise RuntimeError('git ' + ' '.join(args[:3]) + ': ' + result.stderr.decode(errors='replace')[-2000:])
    return result


def validate_resource(resource):
    require(HEX40.fullmatch(resource['commit']) and HEX40.fullmatch(resource['git_blob']), 'Unpinned Git input')
    require(HEX64.fullmatch(resource['sha256']) and resource['bytes'] > 0, 'Invalid digest or byte count')
    path = PurePosixPath(resource['path'])
    require(not path.is_absolute() and '..' not in path.parts and '\\' not in resource['path'], 'Unsafe Git path')


def read_resource(repo, resource):
    line = git(repo, 'ls-tree', resource['commit'], '--', resource['path']).stdout.decode().strip()
    require(line and line.split()[1:3] == ['blob', resource['git_blob']], 'Pinned path/blob mismatch: ' + resource['path'])
    raw = git(repo, 'cat-file', 'blob', resource['git_blob']).stdout
    require(len(raw) == resource['bytes'] and sha256(raw) == resource['sha256'], 'Pinned SHA256/size mismatch: ' + resource['path'])
    require(git_blob(raw) == resource['git_blob'], 'Git object digest mismatch')
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=Path(__file__).with_name('reproduce-plan.json'))
    parser.add_argument('--output-root', type=Path, required=True)
    parser.add_argument('--object-cache', type=Path, help='Optional read-only local Git repository/object cache; public pinned raw URLs supply missing objects')
    parser.add_argument('--offline', action='store_true', help='Fail on any missing object instead of fetching')
    args = parser.parse_args()
    plan_raw = args.plan.read_bytes()
    plan = json.loads(plan_raw)
    require(plan['schema'] == 1 and plan['repository'] == 'Evolution-by-Warder/PiconHub-Warder-Evolution', 'Unexpected plan repository/schema')
    require(plan['destination'] == DESTINATION and plan['references'] == 18 and plan['pngs'] == 162, 'Unexpected repair scope')
    require(sha256((json.dumps(plan['expected_selection'], indent=2, ensure_ascii=False) + '\n').encode()) == plan['expected_selection_sha256'], 'Approved selection digest mismatch')
    selected = plan['expected_selection']['entries']
    require(len(selected) == 18 and len({r['ref'] for r in selected}) == 18, 'Reference inventory mismatch')
    require(set(plan['resources']) == {'renderer', 'verifier', 'white', 'black', 'catalogue'}, 'Unexpected resource inventory')
    require(len(plan['originals']) == 18, 'Original inventory mismatch')
    resources = list(plan['resources'].values()) + list(plan['originals'].values())
    for resource in resources:
        validate_resource(resource)
    expected = {}
    for row in selected:
        require(set(row['variants']) == {r + '/' + s for r in RESOLUTIONS for s in STYLES}, 'Expected9variants')
        for key, value in row['variants'].items():
            require(len(value) == 3 and HEX64.fullmatch(value[0]) and HEX40.fullmatch(value[2]), 'Invalid output expectation')
            expected[(row['ref'], key)] = value
    require(len(expected) == 162 and len({v[0] for v in expected.values()}) == 162, 'Expected 162 unique output PNGs')
    require(plan['render_sources']['catalogue_sha256'] == plan['resources']['catalogue']['sha256'], 'Catalogue plan mismatch')
    with tempfile.TemporaryDirectory(prefix='warder-replay18-') as temp:
        scratch = Path(temp)
        def load(resource):
            if args.object_cache:
                repo = args.object_cache.resolve()
                exists = git(repo, 'cat-file', '-e', resource['git_blob'], check=False).returncode == 0
                if exists:
                    return read_resource(repo, resource)
            require(not args.offline, 'Pinned resource absent from offline cache: ' + resource['path'])
            url = ('https://raw.githubusercontent.com/' + plan['repository'] + '/' +
                   resource['commit'] + '/' + urllib.parse.quote(resource['path'], safe='/'))
            with urllib.request.urlopen(url, timeout=60) as response:
                raw = response.read(resource['bytes'] + 1)
            require(len(raw) == resource['bytes'] and sha256(raw) == resource['sha256'] and
                    git_blob(raw) == resource['git_blob'], 'Pinned public raw SHA256/bytes/blob mismatch: ' + url)
            return raw
        print('Loading 23 explicitly pinned GitHub resources', flush=True)
        with ThreadPoolExecutor(max_workers=6) as pool:
            loaded = list(pool.map(load, resources))
        by_blob = {resource['git_blob']: raw for resource, raw in zip(resources, loaded)}
        pinned = {key: by_blob[resource['git_blob']] for key, resource in plan['resources'].items()}
        originals = {digest: by_blob[resource['git_blob']] for digest, resource in plan['originals'].items()}
        require(all(sha256(raw) == digest for digest, raw in originals.items()), 'Original map mismatch')
        batch = scratch / 'render'
        batch.mkdir()
        (batch / 'masters').mkdir()
        for key, filename in [('renderer', 'render_verified_batch.py'), ('verifier', 'verify_batch.py'), ('catalogue', 'world.json.gz')]:
            (batch / filename).write_bytes(pinned[key])
        for style in ['white', 'black']:
            require(sha256(pinned[style]) == plan['render_sources']['master_sha256'][style], 'MASTER mismatch')
            (batch / 'masters' / (style + '.png')).write_bytes(pinned[style])
        for digest, resource in plan['render_sources']['source_inventory'].items():
            relative = PurePosixPath(resource['path'])
            require(len(relative.parts) == 1 and relative.name == digest + '.png', 'Unsafe original local path')
            require(resource['sha256'] == digest and len(originals[digest]) == resource['bytes'], 'Original plan mismatch')
            (batch / relative.name).write_bytes(originals[digest])
        (batch / 'sources.json').write_text(json.dumps(plan['render_sources'], ensure_ascii=False, indent=2) + '\n')
        print('Running unchanged pinned renderer and verifier', flush=True)
        subprocess.run([os.sys.executable, str(batch / 'render_verified_batch.py'), str(batch), str(batch / 'world.json.gz'), str(batch / 'masters')], check=True)
        manifest = json.loads((batch / 'manifest.json').read_bytes())
        outputs = {}
        for resolution in sorted(RESOLUTIONS):
            for style in sorted(STYLES):
                package = manifest['packages'][resolution][style]
                with zipfile.ZipFile(batch / package['path']) as archive:
                    require(archive.testzip() is None and len(archive.namelist()) == 18, 'Temporary renderer archive mismatch')
                    for row in selected:
                        key = resolution + '/' + style
                        name = row['ref'].replace(':', '_') + '.png'
                        raw = archive.read(name)
                        digest, size, blob = expected[(row['ref'], key)]
                        require(len(raw) == size and sha256(raw) == digest and git_blob(raw) == blob, 'Output differs from approved local PNG: ' + row['ref'] + ' ' + key)
                        with Image.open(io.BytesIO(raw), formats=['PNG']) as im:
                            require(im.mode == 'RGBA' and im.size == tuple(map(int, resolution.split('x'))), 'PNG geometry/mode mismatch')
                            im.verify()
                        outputs[digest] = raw
        require(len(outputs) == 162, 'Output count mismatch')
        destination = args.output_root.resolve() / DESTINATION
        destination.mkdir(parents=True, exist_ok=True)
        for digest, raw in outputs.items():
            path = destination / (digest + '.png')
            if path.exists():
                require(path.read_bytes() == raw, 'Refusing to overwrite different existing output: ' + str(path))
        for digest, raw in outputs.items():
            path = destination / (digest + '.png')
            if not path.exists():
                with path.open('xb') as handle:
                    handle.write(raw)
        proof = {'schema': 1, 'status': 'pass', 'references': 18, 'pngs': 162, 'plan_sha256': sha256(plan_raw),
                 'all_output_sha256_bytes_git_blobs_match_approved_local_pngs': True,
                 'resources': plan['resources'], 'originals': plan['originals'],
                 'expected_selection': plan['expected_selection'], 'destination': DESTINATION,
                 'files': {h + '.png': {'sha256': h, 'bytes': len(raw), 'git_blob': git_blob(raw)} for h, raw in sorted(outputs.items())}}
        proof_path = destination.parent / 'reproduction-proof.json'
        proof_raw = (json.dumps(proof, indent=2, ensure_ascii=False) + '\n').encode()
        if proof_path.exists():
            require(proof_path.read_bytes() == proof_raw, 'Refusing to overwrite different existing proof')
        else:
            with proof_path.open('xb') as handle:
                handle.write(proof_raw)
        print('PASS: 162/162 approved PNG digests reproduced at', destination, flush=True)


if __name__ == '__main__':
    main()
