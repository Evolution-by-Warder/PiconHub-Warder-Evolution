# -*- coding: utf-8 -*-
"""Conservative extraction of picon references from Enigma2 bouquet entries.

Use the first ten hexadecimal service-reference fields, not stream URLs.
Preserve original hexadecimal field spelling except case, as Enigma2 picon
filenames can contain leading zeroes. No speculative DAB identifier mapping.
"""
import re

_HEX = re.compile(r'^[0-9A-Fa-f]+$')
_NON_PLAYABLE = (0, 1, 4, 64, 128, 256, 512)


def picon_reference(service_line):
    """Return the reference filename stem, or None for unsupported entries."""
    line = service_line.strip()
    if not line.startswith('#SERVICE '):
        return None
    fields = line[len('#SERVICE '):].strip().split(':', 10)
    if len(fields) < 10 or not all(_HEX.match(x) for x in fields[:10]):
        return None
    values = [int(x, 16) for x in fields[:10]]
    if values[0] in _NON_PLAYABLE or values[1] != 0:
        return None
    return '_'.join(x.upper() for x in fields[:10])


def collect_picon_references(contents):
    """Return sorted unique references for playable bouquet entries."""
    found = set()
    for line in contents.splitlines():
        name = picon_reference(line)
        if name:
            found.add(name)
    return sorted(found)
