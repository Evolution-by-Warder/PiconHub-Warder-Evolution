"""Conservative pixel-exact (not perceptual) evidence for OpenATV artwork.

PNG metadata, compression and encoding may differ while decoded RGBA pixels are
identical. Such a match is still only artwork evidence, never service identity.
"""
from collections import defaultdict, Counter
from pathlib import Path
import hashlib
import json
from PIL import Image
from source_registry import atomic_json


def _digest(path):
    with Image.open(path) as im:
        rgba = im.convert('RGBA')
        return hashlib.sha256(str(rgba.size).encode('ascii') + b'\0' + rgba.tobytes()).hexdigest()


def _cached(path, cache):
    path = Path(path)
    stat = path.stat()
    key = str(path.resolve())
    old = cache.get(key)
    if isinstance(old, dict) and old.get('size') == stat.st_size and old.get('mtime_ns') == stat.st_mtime_ns:
        digest = old.get('pixel_sha256')
        if isinstance(digest, str) and len(digest) == 64 and all(c in '0123456789abcdef' for c in digest):
            return digest
        # A malformed cache record is not evidence; decode the PNG again.
    digest = _digest(path)
    cache[key] = {'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns, 'pixel_sha256': digest}
    return digest


def attach_pixel_evidence(matches, registry, master_root, cache_path):
    """Link only pixel-identical OpenATV files to a unique Master transparent ref.

    Existing byte-exact evidence wins; ambiguous matches never become linked.
    Failed or missing images remain unmapped and are counted, not guessed.
    """
    cache_path = Path(cache_path)
    try:
        cache = json.loads(cache_path.read_text(encoding='utf-8'))
        if not isinstance(cache, dict): cache = {}
    except (OSError, ValueError):
        cache = {}
    master_index = defaultdict(set)
    counts = Counter()
    root = Path(master_root)
    for ref, entries in registry.get('services', {}).items():
        for entry in entries:
            if entry.get('style') != 'transparent':
                continue
            try:
                p = (root / entry['path']).resolve(strict=True)
                if not p.is_relative_to(root.resolve()) or not p.is_file():
                    continue
                digest = _cached(p, cache)
                master_index[digest].add(ref)
            except (OSError, ValueError, KeyError):
                counts['master_read_failures'] += 1
    from registry_triage import origin_of
    candidate_pixels = {}
    for row in matches:
        source = str(row.get('candidate_source', ''))
        if row.get('classification') != 'UNMAPPED' or origin_of(source) != 'openatv8':
            continue
        if (row.get('artwork_evidence') or {}).get('possible_master_service_references'):
            continue
        try:
            source_sha = row.get('candidate_sha256')
            if isinstance(source_sha, str) and len(source_sha) == 64 and all(c in '0123456789abcdef' for c in source_sha):
                pixel_digest = candidate_pixels.get(source_sha)
                if pixel_digest is None:
                    pixel_digest = _cached(source, cache)
                    candidate_pixels[source_sha] = pixel_digest
            else:
                pixel_digest = _cached(source, cache)
            refs = sorted(master_index.get(pixel_digest, ()))
        except (OSError, ValueError):
            counts['candidate_read_failures'] += 1
            continue
        if len(refs) == 1:
            status = 'PIXEL_EXACT_SINGLE_MASTER_REF'
        elif refs:
            status = 'PIXEL_EXACT_MULTIPLE_MASTER_REFS'
        else:
            status = 'NO_PIXEL_EXACT_MASTER_ARTWORK'
        row['artwork_evidence'] = {'status': status, 'possible_master_service_references': refs,
                                   'identity_verified': False, 'evidence_type': 'DECODED_RGBA_PIXEL_SHA256'}
        counts[status] += 1
    atomic_json(cache_path, cache)
    return dict(counts)
