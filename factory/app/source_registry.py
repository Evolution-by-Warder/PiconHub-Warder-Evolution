"""Fail-closed source policy and atomic checkpoints for Warder Factory."""
from __future__ import annotations
import hashlib
import json
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse

ALLOWED_REPOS = frozenset({
    'Evolution-by-Warder/PiconHub-Warder-Evolution',
    'Evolution-by-Warder/FullHDGlass-Warder-Evolution',
    'Evolution-by-Warder/Glass-System-Utility-Warder-Evolution',
})

class SourceRejected(ValueError):
    pass

def validate_github_archive(url: str, repo: str, branch: str = 'warder-master-production') -> str:
    """Only accept HTTPS GitHub API archive URLs for explicitly approved repositories."""
    if repo not in ALLOWED_REPOS:
        raise SourceRejected('Unapproved repository')
    if not branch or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-' for c in branch):
        raise SourceRejected('Invalid branch')
    parsed = urlparse(url)
    expected = f'/repos/{repo}/zipball/{branch}'
    if (parsed.scheme != 'https' or parsed.netloc != 'api.github.com' or
            parsed.path != expected or parsed.query or parsed.fragment or
            parsed.username or parsed.password):
        raise SourceRejected('Archive URL does not match approved source')
    return url

def atomic_json(path: Path, data: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.checkpoint-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

def source_fingerprint(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()

def checkpoint_source(path: Path, repo: str, branch: str, archive: bytes) -> dict:
    if repo not in ALLOWED_REPOS:
        raise SourceRejected('Unapproved repository')
    if len(archive) == 0 or len(archive) > 450_000_000:
        raise SourceRejected('Archive size outside safety limits')
    state = {'repository': repo, 'branch': branch, 'sha256': source_fingerprint(archive), 'bytes': len(archive)}
    atomic_json(path, state)
    return state
