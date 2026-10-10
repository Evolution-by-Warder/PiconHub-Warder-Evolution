"""Read-only publication planning. Never performs git or network writes."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from source_registry import atomic_json

SERVICE_ID = re.compile(r'^[0-9a-fA-F]+(?:_[0-9a-fA-F]+){9,}$')
ALLOWED_VARIANTS = ('transparent', 'black', 'white')


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _load_exclusions(manifest_path, root):
    """Reject malformed, stale, or foreign exclusion manifests (fail closed)."""
    data = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    if not isinstance(data, dict) or data.get('schema') != 1:
        raise ValueError('Invalid publication exclusion manifest schema')
    shas = data.get('excluded_source_sha256')
    paths = data.get('excluded_variant_paths')
    if not isinstance(shas, list) or not isinstance(paths, list):
        raise ValueError('Missing publication exclusion entries')
    if data.get('blocking_count') != len(shas) or len(paths) != 3 * len(shas):
        raise ValueError('Inconsistent publication exclusion counts')
    expected = set()
    for sha in shas:
        if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{64}', sha):
            raise ValueError('Invalid excluded source SHA')
        for variant in ALLOWED_VARIANTS:
            expected.add(str(root / sha[:2] / sha / (variant + '.png')))
    if len(expected) != len(paths) or set(paths) != expected:
        raise ValueError('Publication exclusion paths do not match output root')
    return expected


def plan_publication(items, output_root, manifest_path, approved_ids=(), exclusion_manifest=None):
    """Create a candidate manifest, never publish or change production files.

    Approved review IDs only authorize inclusion in this *draft* manifest.
    GitHub publication requires a separate explicit action not implemented here.
    """
    root = Path(output_root).resolve(strict=True)
    # When exclusions are supplied, validate before producing any candidate.
    # A malformed or missing manifest is a hard failure, not a silent bypass.
    excluded = _load_exclusions(exclusion_manifest, root) if exclusion_manifest is not None else set()
    allowed = set(approved_ids)
    candidates, held = [], []
    seen = {}
    for item in items:
        review_id = item.get('review_id', '')
        service_id = item.get('service_id', '')
        variant = item.get('variant', '')
        source = item.get('path', '')
        reason = None
        if not isinstance(service_id, str) or not SERVICE_ID.fullmatch(service_id):
            reason = 'invalid_service_id'
        elif variant not in ALLOWED_VARIANTS:
            reason = 'invalid_variant'
        elif review_id not in allowed:
            reason = 'approval_required'
        elif not isinstance(source, str):
            reason = 'invalid_path'
        else:
            candidate = Path(source)
            try:
                resolved = (root / candidate).resolve(strict=True)
                if not resolved.is_relative_to(root) or not resolved.is_file() or resolved.suffix.lower() != '.png':
                    reason = 'unsafe_path'
            except (OSError, ValueError, RuntimeError):
                reason = 'missing_or_unsafe_path'
        if reason:
            held.append({'review_id': review_id, 'reason': reason})
            continue
        if str(resolved) in excluded:
            held.append({'review_id': review_id, 'reason': 'excluded_empty_source'})
            continue
        key = (service_id.lower(), variant)
        checksum = sha256_file(resolved)
        if key in seen:
            held.append({'review_id': review_id, 'reason': 'duplicate_identity_variant', 'conflicts_with': seen[key]})
            continue
        seen[key] = review_id
        candidates.append({'review_id': review_id, 'service_id': key[0], 'variant': variant,
                           'source': str(resolved.relative_to(root)), 'sha256': checksum,
                           'size': resolved.stat().st_size})
    manifest = {'schema': 1, 'publication_authorized': False, 'mode': 'DRAFT_ONLY',
                'candidate_count': len(candidates), 'held_count': len(held),
                'candidates': candidates, 'held': held}
    atomic_json(manifest_path, manifest)
    return manifest
