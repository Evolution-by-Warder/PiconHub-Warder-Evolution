# -*- coding: utf-8 -*-
from __future__ import print_function

"""Self-update engine for PiconHub-Warder-Evolution.

The update source is the canonical Warder channel in this repository:
`plugin/update/manifest.json` and `plugin/update/packages/`.
No legacy Chocholousek/s3n0 update endpoint is contacted.
"""

import hashlib
import os
import re
import shutil
import subprocess

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

from ..constants import (
    PLUGIN_VERSION, UPDATE_MANIFEST_URL, UPDATE_PACKAGE_ROOT, UPDATE_TMP_DIR,
)
from .errors import IntegrityError, NetworkError
from .http import download_atomic, fetch_json


_VERSION_RE = re.compile(r'^\s*(\d+(?:\.\d+)*)(?:[-_.]?([A-Za-z]+)(\d*)?)?\s*$')
_PRE_RANK = {
    'dev': 0,
    'alpha': 10, 'a': 10,
    'beta': 20, 'b': 20,
    'rc': 30,
}


def _version_key(value):
    """Return a stable ordering where prereleases sort below final releases."""
    text = str(value or '').strip().lower()
    match = _VERSION_RE.match(text)
    if not match:
        return ((0,), -100, 0, text)
    numbers = tuple(int(x) for x in match.group(1).split('.'))
    label = (match.group(2) or '').lower()
    serial = int(match.group(3) or 0)
    rank = 100 if not label else _PRE_RANK.get(label, 40)
    return (numbers, rank, serial, label)


def is_newer(remote, local=PLUGIN_VERSION):
    return _version_key(remote) > _version_key(local)


def update_channel():
    return UPDATE_MANIFEST_URL


def automatic_update_supported():
    return True


def _trusted_package_url(url):
    """Only allow HTTPS packages from the canonical Warder package path."""
    parsed = urlparse(str(url or '').strip())
    expected = urlparse(UPDATE_PACKAGE_ROOT + '/')
    if parsed.scheme != 'https':
        return False
    if parsed.netloc.lower() != expected.netloc.lower():
        return False
    return parsed.path.startswith(expected.path)


def fetch_manifest(timeout=15, retries=2):
    data = fetch_json(UPDATE_MANIFEST_URL, timeout=timeout, retries=retries)
    if not isinstance(data, dict):
        raise NetworkError('Invalid plugin update manifest')
    if int(data.get('schema', 0) or 0) != 1:
        raise NetworkError('Unsupported plugin update manifest schema')
    return data


def check_for_update(timeout=15, retries=2):
    manifest = fetch_manifest(timeout=timeout, retries=retries)
    enabled = bool(manifest.get('enabled', False))
    remote = str(manifest.get('version') or '').strip()
    package_url = str(manifest.get('package_url') or '').strip()

    result = {
        'enabled': enabled,
        'current_version': PLUGIN_VERSION,
        'version': remote,
        'available': False,
        'package_url': package_url,
        'sha256': str(manifest.get('sha256') or '').strip().lower(),
        'size': manifest.get('size'),
        'notes': str(manifest.get('notes') or '').strip(),
        'restart_gui': bool(manifest.get('restart_gui', True)),
    }

    if not enabled or not remote:
        return result
    if not _trusted_package_url(package_url):
        raise NetworkError('Update manifest contains an untrusted package URL')
    if not result['sha256'] or len(result['sha256']) != 64:
        raise IntegrityError('Update manifest is missing a valid SHA-256')

    result['available'] = is_newer(remote, PLUGIN_VERSION)
    return result


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        while True:
            block = handle.read(256 * 1024)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest().lower()


def _clean_update_dir():
    try:
        if os.path.isdir(UPDATE_TMP_DIR):
            shutil.rmtree(UPDATE_TMP_DIR)
    except Exception:
        pass
    if not os.path.isdir(UPDATE_TMP_DIR):
        os.makedirs(UPDATE_TMP_DIR)


def download_update(info, timeout=30, retries=2):
    if not info or not info.get('available'):
        raise ValueError('No plugin update is available')
    url = str(info.get('package_url') or '')
    if not _trusted_package_url(url):
        raise NetworkError('Untrusted plugin update package URL')

    _clean_update_dir()
    filename = os.path.basename(urlparse(url).path)
    if not filename or not (filename.endswith('.ipk') or filename.endswith('.deb')):
        raise NetworkError('Unsupported plugin update package type')
    target = os.path.join(UPDATE_TMP_DIR, filename)

    download_atomic(url, target, expected_size=info.get('size'),
                    timeout=timeout, retries=retries)
    actual = _sha256(target)
    expected = str(info.get('sha256') or '').lower()
    if actual != expected:
        try:
            os.remove(target)
        except Exception:
            pass
        raise IntegrityError('Plugin update SHA-256 mismatch')
    return target


def install_package(path):
    """Install a verified package and fail on any package-manager error."""
    path = os.path.abspath(path)
    if not path.startswith(os.path.abspath(UPDATE_TMP_DIR) + os.sep):
        raise ValueError('Refusing package outside update directory')
    if not os.path.isfile(path):
        raise IOError('Update package not found: %s' % path)

    if path.endswith('.ipk'):
        commands = [
            ['opkg', 'install', '--force-reinstall', path],
            ['opkg', 'install', path],
        ]
    elif path.endswith('.deb'):
        commands = [['dpkg', '-i', path]]
    else:
        raise ValueError('Unsupported update package type')

    last_output = ''
    for command in commands:
        try:
            proc = subprocess.Popen(command, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
            output = proc.communicate()[0]
            if not isinstance(output, str):
                output = output.decode('utf-8', 'replace')
            last_output = output.strip()
            if proc.returncode == 0:
                return last_output
        except OSError as exc:
            last_output = str(exc)
    raise RuntimeError('Plugin installation failed: %s' % last_output)


def install_update(info, timeout=30, retries=2):
    package = download_update(info, timeout=timeout, retries=retries)
    output = install_package(package)
    return {
        'version': info.get('version'),
        'package': package,
        'output': output,
        'restart_gui': bool(info.get('restart_gui', True)),
    }
