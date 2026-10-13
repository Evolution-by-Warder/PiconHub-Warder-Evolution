"""Fail-closed local finalization of unambiguous NEW service references.

Never writes to the Warder Master repository or overwrites existing output.
"""
from collections import defaultdict
from pathlib import Path
import hashlib

STYLES = ('transparent', 'black', 'white')


def _digest(path):
    checksum = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(block)
    return checksum.digest()


def finalize_new_candidates(matches, qa_issues, work_root, final_root, *, verified_shas=None, image_class=None):
    """Copy only one-SHA NEW identities with three validated PNGs.

    Returns counters. Existing targets are never replaced, including when their
    bytes differ. Conflicting observations are skipped rather than ranked.
    """
    if image_class is None:
        from PIL import Image as image_class
    work_root, final_root = Path(work_root), Path(final_root)
    verified_shas = set(verified_shas or ())
    source_digest_cache = {}
    digest_cache_hits = 0
    digest_cache_misses = 0

    def source_digest(path):
        nonlocal digest_cache_hits, digest_cache_misses
        path = Path(path)
        before = path.stat()
        signature = (before.st_dev, before.st_ino, before.st_size,
                     before.st_mtime_ns, before.st_ctime_ns)
        key = (str(path.resolve()), signature)
        cached = source_digest_cache.get(key)
        if cached is not None:
            digest_cache_hits += 1
            return cached
        value = _digest(path)
        after = path.stat()
        after_signature = (after.st_dev, after.st_ino, after.st_size,
                           after.st_mtime_ns, after.st_ctime_ns)
        if after_signature != signature:
            raise OSError('Work asset changed while hashing')
        source_digest_cache[key] = value
        digest_cache_misses += 1
        return value

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
              'conflicts': 0, 'identity_conflicts': 0,
              'existing_target_conflicts': 0, 'candidates_ready_to_copy': 0,
              'copy_failures': 0, 'qa_blocked': 0, 'invalid': 0}
    for ref, shas in sorted(by_ref.items()):
        if len(shas) != 1 or ref in blocked:
            result['conflicts'] += 1
            result['identity_conflicts'] += 1
            continue
        sha = next(iter(shas))
        if (ref, sha) not in eligible:
            continue
        # A missing QA result is not a successful QA result.
        if sha not in verified_shas:
            result['qa_blocked'] += 1
            continue
        if qa_issues.get(sha):
            result['qa_blocked'] += 1
            continue
        # The source is immutable by content hash; reject stale/mismatched
        # source identities even when the rendered files still look valid.
        if len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha):
            result['invalid'] += 1
            continue
        if not (len(ref.split('_')) == 10 and all(
                part and all(c in '0123456789abcdefABCDEF' for c in part)
                for part in ref.split('_'))):
            result['invalid'] += 1
            continue
        source_dir = work_root / sha[:2] / sha
        sources = [source_dir / (style + '.png') for style in STYLES]
        try:
            source_digests = []
            for src in sources:
                with image_class.open(src) as image:
                    image.verify()
                with image_class.open(src) as image:
                    if image.size != (220, 132) or image.mode != 'RGBA':
                        raise ValueError('Invalid output PNG')
                    image.load()
                source_digests.append(source_digest(src))
            result['eligible'] += 1
            # NEW-CANDIDATES is a local non-production deliverable, not an
            # approval or permission to publish into the Master Registry.
            targets = [final_root / 'NEW-CANDIDATES' / style / (ref + '.png')
                       for style in STYLES]
            if any(target.exists() for target in targets):
                if all(target.is_file() and
                       _digest(target) == expected
                       for target, expected in zip(targets, source_digests)):
                    result['already_present'] += 1
                else:
                    result['conflicts'] += 1
                    result['existing_target_conflicts'] += 1
                continue
            result['candidates_ready_to_copy'] += 1
            created = []
            try:
                for target, src in zip(targets, sources):
                    target.parent.mkdir(parents=True, exist_ok=True)
                    # Exclusive creation refuses to overwrite existing output.
                    with src.open('rb') as incoming, target.open('xb') as outgoing:
                        created.append(target)
                        for block in iter(lambda: incoming.read(1024 * 1024), b''):
                            outgoing.write(block)
                for target, expected in zip(targets, source_digests):
                    if _digest(target) != expected:
                        raise OSError('Copied PNG checksum mismatch')
                result['copied'] += len(created)
            except OSError:
                result['copy_failures'] += 1
                for target in reversed(created):
                    try:
                        target.unlink()
                    except OSError:
                        pass
                continue
        except (OSError, ValueError, SyntaxError):
            result['invalid'] += 1
    result['source_digest_cache_hits'] = digest_cache_hits
    result['source_digest_cache_misses'] = digest_cache_misses
    return result
