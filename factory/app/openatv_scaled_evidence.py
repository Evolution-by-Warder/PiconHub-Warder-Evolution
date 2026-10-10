"""Scale-tolerant *candidate evidence*, never verified service identity.

Uses two independently resized alpha-trimmed RGBA signatures. Exact matches
at both resolutions are required; ambiguous references are retained as such.
"""
from collections import Counter, defaultdict
from pathlib import Path
import hashlib
from PIL import Image


def signature(path):
    with Image.open(path) as im:
        rgba = im.convert('RGBA')
        alpha = rgba.getchannel('A')
        bbox = alpha.point(lambda a: 255 if a >= 240 else 0).getbbox()
        if not bbox:
            return None
        crop = rgba.crop(bbox)
        w, h = crop.size
        if min(w, h) < 12 or max(w, h) < 24:
            return None
        # Very different aspect ratios must never collapse into one square logo.
        aspect = round(w / h, 2)
        # Preserve aspect ratio and use two independent sample grids.
        signatures = []
        for longest in (48, 96):
            dims = (max(1, round(longest*w/max(w,h))), max(1, round(longest*h/max(w,h))))
            sample = crop.resize(dims, Image.Resampling.NEAREST)
            raw = bytearray(sample.tobytes())
            for i in range(0, len(raw), 4):
                if raw[i+3] == 0:
                    raw[i:i+3] = b'\0\0\0'
            signatures.append(hashlib.sha256(str(dims).encode()+raw).hexdigest())
        return (aspect, *signatures)


def attach_scaled_evidence(matches, registry, master_root):
    root = Path(master_root).resolve()
    index = defaultdict(set)
    counts = Counter()
    for ref, entries in registry.get('services', {}).items():
        for entry in entries:
            if entry.get('style') != 'transparent':
                continue
            try:
                p = (root / entry['path']).resolve(strict=True)
                if p.is_relative_to(root) and p.is_file():
                    sig = signature(p)
                    if sig: index[sig].add(ref)
            except (OSError, ValueError, KeyError):
                counts['master_unreadable'] += 1
    for row in matches:
        src = str(row.get('candidate_source', ''))
        parts = src.replace('\\', '/').lower().split('/')
        if row.get('classification') != 'UNMAPPED' or 'openatv8' not in parts or 'source-ingest' not in parts:
            continue
        if (row.get('artwork_evidence') or {}).get('possible_master_service_references'):
            continue
        try:
            sig = signature(src)
        except (OSError, ValueError):
            counts['candidate_unreadable'] += 1
            continue
        refs = sorted(index.get(sig, ())) if sig else []
        if not refs:
            counts['NO_SCALE_EXACT_MATCH'] += 1
            continue
        status = 'SCALE_EXACT_SINGLE_MASTER_REF' if len(refs) == 1 else 'SCALE_EXACT_MULTIPLE_MASTER_REFS'
        row['artwork_evidence'] = {'status': status, 'possible_master_service_references': refs,
            'identity_verified': False, 'evidence_type': 'DUAL_RESOLUTION_NEAREST_SCALE_EXACT'}
        counts[status] += 1
    return dict(counts)
