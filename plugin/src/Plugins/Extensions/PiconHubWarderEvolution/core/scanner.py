# -*- coding: utf-8 -*-
from __future__ import print_function

import glob
import hashlib
import os
import re

PICON_NAME_RE = re.compile(r'^[0-9A-F]+_0_[0-9A-F_]+\.png$', re.I)


def git_blob_sha1(path, chunk_size=256 * 1024):
    size = os.path.getsize(path)
    digest = hashlib.sha1()
    digest.update(('blob %d\0' % size).encode('ascii'))
    with open(path, 'rb') as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def service_line_to_picon(line):
    if not line.startswith('#SERVICE'):
        return None
    try:
        ref = line.split(None, 1)[1].strip()
    except Exception:
        return None
    fields = ref.split(':')
    if len(fields) < 10 or fields[1] != '0':
        return None
    first = fields[:10]
    if not all(re.match(r'^[0-9A-Fa-f]+$', item or '') for item in first):
        return None
    return '_'.join(first).upper() + '.png'


def scan_bouquets(include_radio=False, config_dir='/etc/enigma2'):
    patterns = [os.path.join(config_dir, 'userbouquet*.tv')]
    if include_radio:
        patterns.append(os.path.join(config_dir, 'userbouquet*.radio'))
    names = set()
    for pattern in patterns:
        for filename in glob.glob(pattern):
            try:
                with open(filename, 'r') as handle:
                    for line in handle:
                        name = service_line_to_picon(line.strip())
                        if name:
                            names.add(name)
            except (IOError, OSError, UnicodeError):
                continue
    return names


def local_picons(target_dir):
    found = {}
    if not os.path.isdir(target_dir):
        return found
    try:
        names = os.listdir(target_dir)
    except OSError:
        return found
    for name in names:
        if PICON_NAME_RE.match(name):
            path = os.path.join(target_dir, name)
            if os.path.isfile(path):
                found[name.lower()] = path
    return found
