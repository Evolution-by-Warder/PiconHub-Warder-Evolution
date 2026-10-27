# -*- coding: utf-8 -*-
"""Extract Enigma2 picon basenames from bouquet service entries.

Service references have ten hexadecimal identity fields, followed optionally
by an IPTV URL. The URL must never become part of a filename. This module
does not guess DAB ensemble IDs or equate unrelated regional stations.
"""
import re

_HEX = re.compile(r'^[0-9A-Fa-f]+$')
# These are known service-reference *type* strings (decimal spelling).
# 1 is a valid DVB service and must NOT be rejected.
_NON_PLAYABLE_TYPES = ('0', '4', '64', '128', '256', '512')
# The second field is flags; 0 means a normal service entry.
_STREAM_TYPES = ('4097', '5001', '5002', '8193')


def picon_reference(service_line):
    """Return a picon basename or None for a non-service/unsupported line."""
    line = service_line.strip()
    if not line.startswith('#SERVICE '):
        return None
    fields = line[len('#SERVICE '):].strip().split(':', 10)
    if len(fields) < 10 or not all(_HEX.match(x) for x in fields[:10]):
        return None
    if fields[0] in _NON_PLAYABLE_TYPES or int(fields[1], 16) != 0:
        return None
    # Stream URLs can follow the first ten fields, and are deliberately ignored.
    # Reject entries where the tenth field is not followed by a delimiter.
    if len(fields) == 10 and not line.endswith(':'):
        return None
    return '_'.join(x.upper() for x in fields[:10])


def collect_picon_references(contents):
    """Collect sorted, unique picon basenames for playable bouquet services."""
    return sorted(set(filter(None, (picon_reference(line)
                                   for line in contents.splitlines()))))
