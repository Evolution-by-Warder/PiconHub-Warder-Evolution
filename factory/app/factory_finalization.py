"""Fail-closed local finalization of unambiguous NEW service references.

Never writes to the Warder Master repository or overwrites existing output.
"""
from collections import defaultdict
from pathlib import Path
import hashlib
import os
import tempfile

STYLES = ('transparent', 'black', 'white')


def _digest(path):
    checksum = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(block)
    return checksum.digest()


def _stat_signature(st):
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def _copy_verified_exclusive(source, target, expected):
    """Stage, hash, fsync and atomically publish one file without overwriting."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix='.warder-factory-', suffix='.partial',
                                     dir=str(target.parent))
    temp_path = Path(temp_name)
    checksum = hashlib.sha256()
    try:
        with os.fdopen(fd, 'wb') as outgoing, Path(source).open('rb') as incoming:
            before = _stat_signature(os.fstat(incoming.fileno()))
            for block in iter(lambda: incoming.read(1024 * 1024), b''):
                checksum.update(block)
                outgoing.write(block)
            outgoing.flush()
            os.fsync(outgoing.fileno())
            after = _stat_signature(os.fstat(incoming.fileno()))
        if before != after:
            raise OSError('Work asset changed while copying')
        if checksum.digest() != expected:
            raise OSError('Source SHA-256 changed after QA')
        # Hard-link publication is atomic and fails if a destination already
        # exists. This keeps interrupted copies out of the visible output set.
        os.link(temp_path, target)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
    return checksum.digest()


def _evidence_digest(evidence, path):
    if not isinstance(evidence, dict):
        return None
    try:
        expected = evidence.get('sha256')
        recorded_stat = tuple(evidence.get('stat', ()))
        current_stat = _stat_signature(Path(path).stat())
        if (not isinstance(expected, str) or len(expected) != 64 or
                any(c not in '0123456789abcdef' for c in expected) or
                recorded_stat != current_stat):
            return None
        return bytes.fromhex(expected)
    except (OSError, TypeError, ValueError):
        return None


def finalize_new_candidates(matches, qa_issues, work_root, final_root, *,
                             verified_shas=None, verified_signatures=None,
                             image_class=None):
    """Copy only one-SHA NEW identities with three QA-verified PNGs.

    QA evidence can avoid a second decode/hash pass only when all file stats
    still match the successful QA snapshot. Every copied byte is SHA-256
    checked during staging before an atomic, no-overwrite publication.
    """
    if image_class is None:
        from PIL import Image as image_class
    work_root, final_root = Path(work_root), Path(final_root)
    verified_shas = set(verified_shas or ())
    verified_signatures = verified_signatures or {}
    source_digest_cache = {}
    digest_cache_hits = 0
    digest_cache_misses = 0

    def source_digest(path):
        nonlocal digest_cache_hits, digest_cache_misses
        path = Path(path)
        before = path.stat()
        signature = _stat_signature(before)
        key = (str(path.resolve()), signature)
        cached = source_digest_cache.get(key)
        if cached is not None:
            digest_cache_hits += 1
            return cached
        value = _digest(path)
        after_signature = _stat_signature(path.stat())
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
        if sha not in verified_shas or qa_issues.get(sha):
            result['qa_blocked'] += 1
            continue
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
            evidence = verified_signatures.get(sha, {})
            source_digests = []
            trusted = len(evidence) == 3
            if trusted:
                for style, src in zip(STYLES, sources):
                    digest = _evidence_digest(evidence.get(style), src)
                    if digest is None:
                        trusted = False
                        break
                    source_digests.append(digest)
            if not trusted:
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
                for target, src, expected in zip(targets, sources, source_digests):
                    _copy_verified_exclusive(src, target, expected)
                    created.append(target)
                result['copied'] += len(created)
            except (OSError, FileExistsError):
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
