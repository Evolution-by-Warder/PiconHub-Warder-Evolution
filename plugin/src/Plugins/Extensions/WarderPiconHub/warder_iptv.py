"""Pinned IPTV SK/CZ artwork packages; no receiver-side image generation."""
import hashlib
import json
import pathlib
import re
import stat
import struct
import zipfile
from .radio_references import collect_picon_references
from . import warder_skin_sync as sync

REPOSITORY = 'Evolution-by-Warder/PiconHub-Warder-Evolution'
SELECTOR = 'IPTV-SK-CZ'
LABEL = 'IPTV rádiá SK/CZ'
MANIFEST_URL = 'https://raw.githubusercontent.com/' + REPOSITORY + '/main/picons/IPTV-SK-CZ/catalog/release.json'
_PINNED = re.compile(r'^https://raw\.githubusercontent\.com/' + re.escape(REPOSITORY) + r'/[0-9a-f]{40}/picons/IPTV-SK-CZ/packages/iptv-sk-cz-(?:transparent|white|black)-(?:50x30|220x132|400x240)\.zip$')
_SHA = re.compile(r'^[0-9a-f]{64}$')
_NAME = re.compile(r'(?:4097|5001|5002|8193)_0_(?:2|A)_(?:[0-9A-F]+_){6}[0-9A-F]+\.png')
RESOLUTIONS = ('50x30', '220x132', '400x240')
STYLES = ('transparent', 'white', 'black')


def trusted_url(url):
    return isinstance(url, str) and (url == MANIFEST_URL or bool(_PINNED.fullmatch(url)))


def reference_filename(name):
    return (isinstance(name, str) and bool(_NAME.fullmatch(name))
            and any(int(value, 16) for value in name[:-4].split('_')[3:]))


def read_manifest(opener):
    with opener(MANIFEST_URL) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError('IPTV catalogue exceeds size limit')
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get('schema') != 1 or data.get('status') != 'verified' or data.get('collection') != SELECTOR:
        raise ValueError('IPTV catalogue is not verified')
    packages = data.get('packages')
    if not isinstance(packages, dict) or set(packages) != set(RESOLUTIONS):
        raise ValueError('Incomplete IPTV resolutions')
    common = None
    for resolution in RESOLUTIONS:
        styles = packages[resolution]
        if not isinstance(styles, dict) or set(styles) != set(STYLES):
            raise ValueError('Incomplete IPTV styles')
        for style, package in styles.items():
            if not isinstance(package, dict) or package.get('resolution') != resolution:
                raise ValueError('Invalid IPTV resolution')
            url, digest = package.get('url'), package.get('sha256')
            if not isinstance(url, str) or not _PINNED.fullmatch(url) or not isinstance(digest, str) or not _SHA.fullmatch(digest):
                raise ValueError('Invalid IPTV package identity')
            if not url.endswith('/iptv-sk-cz-' + style + '-' + resolution + '.zip'):
                raise ValueError('IPTV style URL mismatch')
            if type(package.get('bytes')) is not int or not 0 < package['bytes'] <= 64 * 1024 * 1024:
                raise ValueError('Invalid IPTV package size')
            files = package.get('files')
            if not isinstance(files, dict) or not 0 < len(files) <= 10000:
                raise ValueError('Invalid IPTV file inventory')
            for name, checksum in files.items():
                if not reference_filename(name) or not isinstance(checksum, str) or not _SHA.fullmatch(checksum):
                    raise ValueError('Invalid IPTV image identity')
            if common is None:
                common = set(files)
            elif set(files) != common:
                raise ValueError('IPTV variants cover different references')
    return data


def bouquet_names(folder):
    result = set()
    for path in sorted(pathlib.Path(folder).glob('userbouquet.*.radio')):
        text = path.read_text(encoding='utf-8', errors='replace')
        result.update(ref + '.png' for ref in collect_picon_references(text) if reference_filename(ref + '.png'))
    return result


def plan(data, preferences, folder):
    if preferences['update_mode'] == sync.UPDATE_MODE_SYNC_TV:
        return None
    resolution, style = preferences['resolution'], preferences['style']
    if resolution not in RESOLUTIONS or style not in STYLES:
        raise ValueError('Unsupported IPTV artwork variant')
    package = data['packages'][resolution][style]
    names = set(package['files'])
    if preferences['update_mode'] == sync.UPDATE_MODE_SYNC_TV_RADIO:
        names &= bouquet_names(folder)
    if not names:
        return None
    # Only named, verified files may be overwritten; unrelated picons survive.
    queue = {'destination': preferences['destination'], 'positions': [],
             'mode': sync.UPDATE_MODE_INCREMENTAL, 'services': [], 'iptv_names': names}
    job = dict(package, selector_id=SELECTOR,
               parts=[{'url': package['url'], 'bytes': package['bytes'], 'sha256': package['sha256']}])
    return queue, job


def unpack(stage, path, job, cancel):
    expected, seen, wanted = job['files'], set(), stage.queue['iptv_names']
    size = tuple(map(int, job['resolution'].split('x')))
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) != len(expected) or sum(item.file_size for item in infos) > 128 * 1024 * 1024:
            raise ValueError('Invalid IPTV expanded inventory')
        for item in infos:
            cancel()
            name = item.filename
            if name not in expected or name in seen or not reference_filename(name) or stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError('Unsafe IPTV archive entry')
            seen.add(name)
            if not 0 < item.file_size <= 4 * 1024 * 1024:
                raise ValueError('Invalid IPTV image size')
            raw = archive.read(item)
            if (hashlib.sha256(raw).hexdigest() != expected[name] or len(raw) < 33
                    or raw[:8] != b'\x89PNG\r\n\x1a\n' or raw[12:16] != b'IHDR'
                    or struct.unpack('>II', raw[16:24]) != size):
                raise ValueError('Invalid IPTV PNG')
            if name in wanted:
                stage.hashes[name] = expected[name]
                stage.upstream.add(name)
                (stage.ready / name).write_bytes(raw)
        if seen != set(expected):
            raise ValueError('Incomplete IPTV archive')
