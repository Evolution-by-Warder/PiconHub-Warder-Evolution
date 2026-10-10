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
    for ref, entries in (registry.get('services') or {}).items():
        for entry in entries:
            if not isinstance(entry, dict) or entry.get('style') != 'transparent':
                continue
            try:
                path = (root / entry['path']).resolve(strict=True)
                if not path.is_relative_to(base) or not path.is_file():
                    continue
                result[ref].add(_cached(path, cache))
            except (OSError, ValueError, KeyError, TypeError):
                continue
    atomic_json(cache_file, cache)
    return {ref: sorted(digests) for ref, digests in result.items()}


def attach_master_pixel_comparisons(queue, master_digests, candidate_digests):
    """Annotate pending artwork tasks; do not change decisions or task counts."""
    counts = {'PIXEL_EXACT_SAME_SERVICE_MASTER': 0,
              'NO_PIXEL_EXACT_SAME_SERVICE_MASTER': 0,
              'MASTER_PIXEL_EVIDENCE_UNAVAILABLE': 0}
    for item in queue.get('items', ()):
        if item.get('workstream') != 'ARTWORK_REVIEW' or item.get('decision') != 'PENDING':
            continue
        ref = item.get('candidate_identity')
        master = set(master_digests.get(ref) or ())
        for unit in item.get('artwork_review_units') or ():
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
    return counts
