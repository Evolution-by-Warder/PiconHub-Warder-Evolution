"""Fail-closed local finalization of unambiguous NEW service references.

Never writes to the Warder Master repository or overwrites existing output.
"""
from collections import defaultdict
from pathlib import Path
import hashlib
import os
import tempfile

STYLES = ('transparent', 'black', 'white')


def finalize_new_candidates(matches, qa_issues, work_root, final_root, *, image_class=None):
    """Copy only one-SHA NEW identities with three validated PNGs.

    Returns counters. Existing targets are never replaced, including when their
    bytes differ. Conflicting observations are skipped rather than ranked.
    """
    if image_class is None:
        from PIL import Image as image_class
    work_root, final_root = Path(work_root), Path(final_root)
    by_ref = defaultdict(set)
    eligible = {}
    blocked = set()
    for row in matches:
        ref = row.get('service_reference')
        sha = row.get('candidate_sha256')
        if not ref or not sha:
            continue
        by_ref[ref].add(sha)
        if row.get('classification') != 'NEW':
            blocked.add(ref)
        else:
            eligible[(ref, sha)] = row
    result = {'eligible': 0, 'copied': 0, 'already_present': 0,
              'conflicts': 0, 'qa_blocked': 0, 'invalid': 0}
    for ref, shas in sorted(by_ref.items()):
        if len(shas) != 1 or ref in blocked:
            result['conflicts'] += 1
            continue
        sha = next(iter(shas))
        if (ref, sha) not in eligible:
            continue
        if qa_issues.get(sha):
            result['qa_blocked'] += 1
            continue
        if not (len(ref.split('_')) == 10 and all(
                part and all(c in '0123456789abcdefABCDEF' for c in part)
                for part in ref.split('_'))):
            result['invalid'] += 1
            continue
        if len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
            result['invalid'] += 1
            continue
        source_dir = work_root / sha[:2] / sha
        sources = [source_dir / (style + '.png') for style in STYLES]
        try:
            for src in sources:
                with image_class.open(src) as image:
                    image.verify()
                with image_class.open(src) as image:
                    if image.size != (220, 132) or image.mode != 'RGBA':
                        raise ValueError('Invalid output PNG')
            result['eligible'] += 1
            # NEW-CANDIDATES is a local non-production deliverable, not an
            # approval or permission to publish into the Master Registry.
            targets = [final_root / 'NEW-CANDIDATES' / style / (ref + '.png')
                       for style in STYLES]
            if any(target.exists() for target in targets):
                if all(target.is_file() and
                       hashlib.sha256(target.read_bytes()).digest() ==
                       hashlib.sha256(src.read_bytes()).digest()
                       for target, src in zip(targets, sources)):
                    result['already_present'] += 1
                else:
                    result['conflicts'] += 1
                continue
            for target, src in zip(targets, sources):
                target.parent.mkdir(parents=True, exist_ok=True)
                # Exclusive creation prevents overwriting a concurrent result.
                with src.open('rb') as incoming, target.open('xb') as outgoing:
                    for block in iter(lambda: incoming.read(1024 * 1024), b''):
                        outgoing.write(block)
                result['copied'] += 1
        except (OSError, ValueError, SyntaxError):
            result['invalid'] += 1
    return result
