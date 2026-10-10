"""Provider-neutral, fail-closed remote source inventory.

Endpoints must be verified and supplied by a source adapter; no guessed URLs.
This module never mutates originals or publishes anything.
"""
import hashlib
import json
import os
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

MAX_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_ARCHIVE_BYTES = 450 * 1024 * 1024
PEERS = frozenset(('vhannibal', 'openatv8', 'chocholousek'))


class SourceError(ValueError):
    pass


def validate_manifest(data):
    if not isinstance(data, dict) or data.get('schema') != 1:
        raise SourceError('Unsupported source manifest')
    entries = data.get('sources')
    if not isinstance(entries, list) or not entries:
        raise SourceError('Missing sources')
    keys = set()
    for item in entries:
        if not isinstance(item, dict):
            raise SourceError('Invalid source')
        key = item.get('key')
        if key not in PEERS or key in keys:
            raise SourceError('Unknown or duplicate source')
        keys.add(key)
        if item.get('priority') is not None:
            raise SourceError('Peer sources cannot be prioritized')
        url = item.get('url')
        if not isinstance(url, str):
            raise SourceError('Missing verified endpoint')
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
            raise SourceError('Unsafe endpoint')
        if not isinstance(item.get('sha256'), str) or len(item['sha256']) != 64 or any(c not in '0123456789abcdef' for c in item['sha256']):
            raise SourceError('Missing or invalid archive SHA-256')
        if not isinstance(item.get('version'), str) or not item['version'].strip():
            raise SourceError('Missing source version')
    return entries


def plan_downloads(manifest, state):
    """Return only changed source entries, independent of input ordering."""
    entries = validate_manifest(manifest)
    state = state if isinstance(state, dict) else {}
    return sorted((e for e in entries if state.get(e['key']) != e['sha256']), key=lambda e: e['key'])


def stream_verified_archive(url, sha256, target, allowed_hosts, opener=None, max_bytes=MAX_ARCHIVE_BYTES):
    """Bounded, hash-verified atomic download. Redirects must remain on approved hosts."""
    parsed = urllib.parse.urlsplit(url)
    allowed_hosts = frozenset(allowed_hosts)
    if parsed.scheme != 'https' or parsed.hostname not in allowed_hosts:
        raise SourceError('Unapproved download host')
    opener = opener or urllib.request.urlopen
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.warder-', suffix='.partial', dir=target.parent)
    size = 0
    digest = hashlib.sha256()
    try:
        with os.fdopen(fd, 'wb') as out:
            request = urllib.request.Request(url, headers={'User-Agent': 'WarderPiconFactory/1'})
            with opener(request, timeout=45) as response:
                final = urllib.parse.urlsplit(response.geturl())
                if final.scheme != 'https' or final.hostname not in allowed_hosts:
                    raise SourceError('Redirect to unapproved host')
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > max_bytes:
                        raise SourceError('Download exceeds size limit')
                    digest.update(chunk)
                    out.write(chunk)
            out.flush()
            os.fsync(out.fileno())
        if digest.hexdigest() != sha256:
            raise SourceError('Archive SHA-256 mismatch')
        os.replace(temporary, target)
        return {'bytes': size, 'sha256': sha256}
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def commit_source_state(path, previous, source, verified_sha256):
    """Only call after archive verification and successful processing."""
    if source['sha256'] != verified_sha256:
        raise SourceError('Cannot checkpoint unverified source')
    state = dict(previous)
    state[source['key']] = verified_sha256
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.source-state-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as file:
            json.dump(state, file, sort_keys=True)
            file.flush()
            os.fsync(file.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return state
