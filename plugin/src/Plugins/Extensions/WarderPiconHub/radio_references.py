# -*- coding: utf-8 -*-
"""Conservative Enigma2 bouquet service-reference extraction.

Only the first ten numeric service-reference fields form a picon basename.
Stream URLs after those fields are not part of the basename. Directory and
marker entries are excluded. No guessed DAB identifier translations.
"""
import re

_HEX = re.compile(r'^[0-9A-Fa-f]+$')
_NON_PLAYABLE = {0, 1, 4, 64, 128, 256, 512}


def picon_reference(service_line):
    """Return a picon basename, or None for non-service/unsupported lines."""
    line = service_line.strip()
    if not line.startswith('#SERVICE '):
        return None
    reference = line[9:].strip()
    fields = reference.split(':', 10)
    if len(fields) < 10 or not all(_HEX.fullmatch(x or '') for x in fields[:10]):
        return None
    values = [int(x, 16) for x in fields[:10]]
    if values[0] in _NON_PLAYABLE:
        return None
    # Reject bouquet references and directory/marker flags.
    if values[1] != 0 or values[0] == 0:
        return None
    return '_'.join(format(v, 'X') for v in values)


def collect_picon_references(contents):
    """Collect unique playable service references from one or more bouquets."""
    found = set()
    for line in contents.splitlines():
        name = picon_reference(line)
        if name:
            found.add(name)
    return sorted(found)
