"""Read-only decoded-pixel evidence for grouped registry artwork reviews."""
import hashlib
from pathlib import Path
from PIL import Image


def candidate_pixel_digests(matches, output_root):
    """Compare transparent 220x132 RGBA pixels, never infer service identity."""
    shas = set()
    for row in matches:
        if not isinstance(row, dict) or row.get('classification') != 'REVIEW' or row.get('reason') != 'EXISTING_SERVICE_DIFFERENT_ART':
            continue
        sha = row.get('candidate_sha256')
        if isinstance(sha, str) and len(sha) == 64 and all(c in '0123456789abcdefABCDEF' for c in sha):
            shas.add(sha)
    result = {}
    root = Path(output_root)
    for sha in sorted(shas, key=str):
        if not isinstance(sha, str) or len(sha) != 64 or any(c not in '0123456789abcdefABCDEF' for c in sha):
            continue
        path = root / sha[:2] / sha / 'transparent.png'
        try:
            with Image.open(path) as image:
                rgba = image.convert('RGBA')
                if rgba.size != (220, 132):
                    continue
                result[sha] = hashlib.sha256(str(rgba.size).encode('ascii') + b'\0' + rgba.tobytes()).hexdigest()
        except (OSError, ValueError):
            continue
    return result


def master_artwork_pixel_digests(registry, master_root, cache_path):
    """Read-only service-scoped index of transparent Master pixels.

    Reuses the existing size/mtime pixel cache; never equates a matching
    picture with permission to overwrite or approve a service identity.
    """
    from collections import defaultdict
    import json
    from openatv_pixel_evidence import _cached
    from source_registry import atomic_json

    root = Path(master_root)
    cache_file = Path(cache_path)
    try:
        cache = json.loads(cache_file.read_text(encoding='utf-8'))
        if not isinstance(cache, dict):
            cache = {}
    except (OSError, ValueError):
        cache = {}
    result = defaultdict(set)
    base = root.resolve()
    services = registry.get('services') or {}
    if not isinstance(services, dict):
        services = {}
    for ref, entries in services.items():
        if not isinstance(entries, (list, tuple)):
            continue
        for entry in entries:
            if not isinstance(entry, dict) or entry.get('style') != 'transparent':
                continue
            try:
                path = (root / entry['path']).resolve(strict=True)
                if not path.is_relative_to(base) or not path.is_file():
                    continue
                digest = _cached(path, cache)
                if isinstance(digest, str) and len(digest) == 64 and all(c in '0123456789abcdef' for c in digest):
                    result[ref].add(digest)
            except (OSError, ValueError, KeyError, TypeError):
                continue
    atomic_json(cache_file, cache)
    return {ref: sorted(digests) for ref, digests in result.items()}


def attach_master_pixel_comparisons(queue, master_digests, candidate_digests):
    """Resolve only service-scoped exact Master RGBA matches; preserve audit items."""
    counts = {'PIXEL_EXACT_SAME_SERVICE_MASTER': 0,
              'NO_PIXEL_EXACT_SAME_SERVICE_MASTER': 0,
              'MASTER_PIXEL_EVIDENCE_UNAVAILABLE': 0}
    for item in queue.get('items', ()):
        if item.get('workstream') != 'ARTWORK_REVIEW' or item.get('decision') != 'PENDING':
            continue
        ref = item.get('candidate_identity')
        master = set(master_digests.get(ref) or ())
        master_bytes = sorted({entry.get('sha256').lower()
                               for entry in item.get('master_locations', [])
                               if isinstance(entry, dict) and entry.get('style') == 'transparent'
                               and isinstance(entry.get('sha256'), str)
                               and len(entry.get('sha256')) == 64})
        units = item.get('artwork_review_units') or ()
        for unit in units:
            unit['master_pixel_sha256'] = sorted(master)
            unit['master_sha256'] = master_bytes
            digest = unit.get('pixel_sha256')
            if not digest:
                sha = unit.get('representative_sha256')
                digest = candidate_digests.get(sha)
            if not master or not digest:
                status = 'MASTER_PIXEL_EVIDENCE_UNAVAILABLE'
            elif digest in master:
                status = 'PIXEL_EXACT_SAME_SERVICE_MASTER'
            else:
                status = 'NO_PIXEL_EXACT_SAME_SERVICE_MASTER'
            unit['master_pixel_comparison'] = status
            counts[status] += 1
        statuses = [unit.get('master_pixel_comparison') for unit in units]
        if statuses and all(status == 'PIXEL_EXACT_SAME_SERVICE_MASTER' for status in statuses):
            item['master_pixel_evidence'] = 'ALL_REVIEW_UNITS_EXACT_SAME_SERVICE_MASTER'
            # Pixel equality is evidence, not proof that the Master identity
            # and artwork were approved. The MASTER-FIRST coverage gate owns
            # the only safe skip path and requires explicit approval metadata.
        elif statuses and any(status == 'NO_PIXEL_EXACT_SAME_SERVICE_MASTER' for status in statuses):
            item['master_pixel_evidence'] = 'DIFFERENT_ARTWORK_PRESENT'
        else:
            item['master_pixel_evidence'] = 'INCOMPLETE_MASTER_PIXEL_EVIDENCE'
    # Keep the queue's workstream summary aligned with the pending-only UI.
    # The full item list/count remain intact for audit and historical review.
    if isinstance(queue.get('workstream_counts'), dict):
        for lane in queue['workstream_counts']:
            queue['workstream_counts'][lane] = sum(
                item.get('workstream') == lane and item.get('decision', 'PENDING') == 'PENDING'
                for item in queue.get('items', ()))
    return counts


def pixel_fingerprints_for_queue(queue, output_root):
    """Decode each unique rendered candidate once for item-level export."""
    shas = set()
    result = {}
    for item in (queue or {}).get('items', ()):
        if not isinstance(item, dict):
            continue
        for unit in item.get('artwork_review_units') or ():
            if not isinstance(unit, dict) or not isinstance(unit.get('pixel_sha256'), str):
                continue
            pixel = unit['pixel_sha256'].lower()
            for sha in [unit.get('representative_sha256')] + list(unit.get('duplicate_sha256') or []):
                if isinstance(sha, str) and len(sha) == 64:
                    result[sha.lower()] = pixel
        values = [item.get('sha256')]
        for field in ('source_evidence', 'variants'):
            for entry in item.get(field) or ():
                if isinstance(entry, dict):
                    values.append(entry.get('sha256'))
                    values.extend(entry.get('duplicate_sha256') or ())
        for unit in item.get('artwork_review_units') or ():
            if isinstance(unit, dict):
                values.append(unit.get('representative_sha256'))
                values.extend(unit.get('duplicate_sha256') or ())
        shas.update(value.lower() for value in values
                    if isinstance(value, str) and len(value) == 64
                    and all(c in '0123456789abcdefABCDEF' for c in value)
                    and value.lower() not in result)
    root = Path(output_root)
    for sha in sorted(shas):
        path = root / sha[:2] / sha / 'transparent.png'
        try:
            with Image.open(path) as image:
                rgba = image.convert('RGBA')
                if rgba.size != (220, 132):
                    continue
                result[sha] = hashlib.sha256(
                    str(rgba.size).encode('ascii') + b'\\0' + rgba.tobytes()
                ).hexdigest()
        except (OSError, ValueError):
            continue
    return result
