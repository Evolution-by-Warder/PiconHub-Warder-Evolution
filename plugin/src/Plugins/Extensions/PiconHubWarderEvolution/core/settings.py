# -*- coding: utf-8 -*-
from __future__ import print_function

import json
import os
import tempfile

from ..constants import CONFIG_FILE, DEFAULT_TARGET_DIR

DEFAULTS = {
    'schema': 1,
    'target_dir': DEFAULT_TARGET_DIR,
    'satellite': '23.5e',
    'provider': 'skylink',
    'style': 'transparent',
    'mode': 'bouquets_tv',
    'remove_orphans': False,
}


def _safe_load(path):
    try:
        with open(path, 'r') as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def normalize(data):
    result = dict(DEFAULTS)
    if isinstance(data, dict):
        result.update(data)
    result['schema'] = 1
    result['target_dir'] = str(result.get('target_dir') or DEFAULT_TARGET_DIR).strip()
    for key in ('satellite', 'provider', 'style', 'mode'):
        result[key] = str(result.get(key) or DEFAULTS[key]).strip()
    result['remove_orphans'] = bool(result.get('remove_orphans'))
    return result


def load(path=CONFIG_FILE):
    return normalize(_safe_load(path))


def save(data, path=CONFIG_FILE):
    data = normalize(data)
    directory = os.path.dirname(path) or '.'
    if not os.path.isdir(directory):
        os.makedirs(directory)
    fd, temp_path = tempfile.mkstemp(prefix='.piconhub-', suffix='.json', dir=directory)
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write('\n')
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except Exception:
                pass
        try:
            os.chmod(temp_path, 0o600)
        except Exception:
            pass
        try:
            os.replace(temp_path, path)
        except AttributeError:
            if os.path.exists(path):
                os.remove(path)
            os.rename(temp_path, path)
    except Exception:
        try:
            os.remove(temp_path)
        except Exception:
            pass
        raise
    return data
