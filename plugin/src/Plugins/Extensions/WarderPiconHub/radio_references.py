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
# Service-type strings are retained verbatim because Enigma2 references use
# decimal-looking spellings (e.g. 4097), unlike hex-encoded identity fields.
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
    # Generic IPTV entries with all-zero IDs share the same filename stem.
    # Never assign one station's logo to every such stream. A separate
    # name/URL-aware mapping must handle these entries.
    if fields[0] in _STREAM_TYPES and all(int(x, 16) == 0 for x in fields[3:10]):
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


def analyze_bouquet(contents):
    """Summarize matching without storing private stream URLs or credentials.

    This read-only diagnostic reports counts and accepted picon references.
    It does not download images, modify bouquets, or infer station identities.
    """
    references = set()
    skipped = 0
    service_count = 0
    for line in contents.splitlines():
        if not line.strip().startswith('#SERVICE '):
            continue
        service_count += 1
        ref = picon_reference(line)
        if ref is None:
            skipped += 1
        else:
            references.add(ref)
    return {
        'service_entries': service_count,
        'accepted_unique': len(references),
        'skipped_entries': skipped,
        'references': sorted(references),
    }


def picon_filename_is_reference(filename):
    """Check the basename of a PNG without treating station-name icons as IDs."""
    if not filename.lower().endswith('.png'):
        return False
    stem = filename[:-4]
    fields = stem.split('_')
    return (len(fields) == 10
            and all(_HEX.match(field) for field in fields)
            and fields[0] not in _NON_PLAYABLE_TYPES
            and int(fields[1], 16) == 0)
