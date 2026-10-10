"""Explicit, fail-closed local finalization of an already-reviewed picon triplet.

APPROVED_FOR_REVIEW is *not* final approval. No GitHub writes or source deletion.
"""
from pathlib import Path
import hashlib
import json
from PIL import Image
from warder_storage_policy import StoragePolicy


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def finalize_triplet(root, identity, variants, *, approval, expected_sha256):
    """Promote black/white only with explicit final approval and pinned hashes.

    Transparent original is never rewritten. Existing final assets are not silently
    replaced. Returns finalized paths; no cleanup occurs until a later verified pass.
    """
    if approval != 'FINAL_QA_APPROVED':
        raise PermissionError('Final QA approval required (review approval is insufficient)')
    store = StoragePolicy(root)
    store._validate(identity)
    if set(variants) != {'black', 'white'} or set(expected_sha256) != {'black', 'white'}:
        raise ValueError('Both derivative variants and both expected hashes required')
    validated = {}
    for variant in ('black', 'white'):
        source = Path(variants[variant]).resolve(strict=True)
        expected = expected_sha256[variant]
        if not isinstance(expected, str) or len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
            raise ValueError('Invalid SHA-256')
        # Only assets in canonical work store can be promoted.
        if not source.is_relative_to(store.work.resolve()):
            raise ValueError('Source outside canonical work store')
        with Image.open(source) as image:
            image.verify()
        with Image.open(source) as image:
            if image.size != (220, 132):
                raise ValueError('Unexpected picon dimensions')
        if sha256(source) != expected:
            raise ValueError('Work asset changed since QA')
        dest = store.path(identity, variant, approved=True)
        if dest.exists() and sha256(dest) != expected:
            raise FileExistsError('Different final asset already exists: ' + str(dest))
        validated[variant] = source
    # Publish as one local operation: never overwrite a different approved file.
    # Roll back only paths created by this call if a later variant fails.
    results = {}
    created = []
    try:
        for variant, source in validated.items():
            dest = store.path(identity, variant, approved=True)
            existed = dest.exists()
            if existed:
                if sha256(dest) != expected_sha256[variant]:
                    raise FileExistsError('Final asset changed during QA: ' + str(dest))
            else:
                dest = store.publish_local(identity, variant, source, qa_approved=True)
                created.append(dest)
            if sha256(dest) != expected_sha256[variant]:
                raise IOError('Final integrity check failed')
            results[variant] = str(dest)
    except Exception:
        for dest in reversed(created):
            # Do not delete a file that has been replaced since our publication.
            variant = dest.parent.name
            if dest.exists() and sha256(dest) == expected_sha256[variant]:
                dest.unlink()
        raise
    return results
