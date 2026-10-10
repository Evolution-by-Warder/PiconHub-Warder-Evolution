"""Conservative normalized artwork evidence; never establishes service identity.

Only a crisp alpha-bounded logo is compared. Bilinear/interpolated images and
low-detail/blank graphics are deliberately not matched.
"""
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image, ImageChops


def signature(path):
    with Image.open(path) as im:
        rgba = im.convert('RGBA')
        alpha = rgba.getchannel('A')
        bbox = alpha.point(lambda v: 255 if v >= 240 else 0).getbbox()
        if not bbox:
            return None
        crop = rgba.crop(bbox)
        if crop.width < 12 or crop.height < 8:
            return None
        # No resampling: only geometrically identical visible artwork is linked.
        # Ignore fully transparent padding and its arbitrary RGB values.
        pixels = bytearray(crop.tobytes())
        for i in range(0, len(pixels), 4):
            if pixels[i+3] == 0:
                pixels[i:i+3] = b'\0\0\0'
        import hashlib
        return hashlib.sha256(f'{crop.width}x{crop.height}:'.encode()+pixels).hexdigest()


def attach_normalized_evidence(matches, registry, master_root):
    """Apply trim-exact evidence only to OpenATV rows without prior evidence."""
    root = Path(master_root).resolve()
    index = defaultdict(set)
    counts = Counter()
    for ref, entries in registry.get('services', {}).items():
        for entry in entries:
            if entry.get('style') != 'transparent':
                continue
            try:
                p = (root / entry['path']).resolve(strict=True)
                if not p.is_relative_to(root) or not p.is_file():
                    continue
                sig = signature(p)
                if sig:
                    index[sig].add(ref)
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
            refs = sorted(index.get(sig, ())) if sig else []
        except (OSError, ValueError):
            counts['candidate_unreadable'] += 1
            continue
        if len(refs) == 1:
            status = 'TRIM_EXACT_SINGLE_MASTER_REF'
        elif len(refs) > 1:
            status = 'TRIM_EXACT_MULTIPLE_MASTER_REFS'
        else:
            status = 'NO_TRIM_EXACT_MATCH'
        if refs:
            row['artwork_evidence'] = {'status':status, 'possible_master_service_references':refs,
                'identity_verified':False, 'evidence_type':'ALPHA_TRIM_PIXEL_EXACT'}
        counts[status] += 1
    return dict(counts)
