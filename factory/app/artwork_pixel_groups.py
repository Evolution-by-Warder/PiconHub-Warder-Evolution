"""Read-only decoded-pixel evidence for grouped registry artwork reviews."""
import hashlib
from pathlib import Path
from PIL import Image


def candidate_pixel_digests(matches, output_root):
    """Compare transparent 220x132 RGBA pixels, never infer service identity."""
    shas = {row.get('candidate_sha256') for row in matches
            if row.get('classification') == 'REVIEW'
            and row.get('reason') == 'EXISTING_SERVICE_DIFFERENT_ART'
            and row.get('candidate_sha256')}
    result = {}
    root = Path(output_root)
    for sha in sorted(shas):
        if not isinstance(sha, str) or len(sha) != 64 or any(c not in '0123456789abcdefABCDEF' for c in sha):
            continue
        path = root / sha[:2] / sha / 'transparent.png'
        try:
            with Image.open(path) as image:
                rgba = image.convert('RGBA')
                if rgba.size != (220, 132):
                    continue
                result[sha] = hashlib.sha256(rgba.tobytes()).hexdigest()
        except (OSError, ValueError):
            continue
    return result
