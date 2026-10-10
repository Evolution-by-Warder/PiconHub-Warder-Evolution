"""Bounded, read-only discovery of approved Factory GitHub releases.

The Enigma2 plugin and Factory share a repository but NOT a release stream.
No update is installed without a separately verified manifest and package.
"""
import json
import re
import urllib.request

REPO = 'Evolution-by-Warder/PiconHub-Warder-Evolution'
API = 'https://api.github.com/repos/' + REPO + '/releases?per_page=30'
VERSION = re.compile(r'^factory-v(\d+)\.(\d+)\.(\d+)$')
ASSET = re.compile(r'^warder-picon-factory-(\d+)\.(\d+)\.(\d+)\.zip$')
MAX_METADATA = 1024 * 1024


def check_factory_release(current=(0, 0, 0), *, opener=None):
    """Find newest valid Factory release, ignoring unrelated plugin releases."""
    if opener is None:
        opener = urllib.request.urlopen
    req = urllib.request.Request(API, headers={
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'Warder-Picon-Factory',
    })
    try:
        with opener(req, timeout=6) as response:
            if response.geturl() != API:
                raise ValueError('Unexpected GitHub API redirect')
            raw = response.read(MAX_METADATA + 1)
            if len(raw) > MAX_METADATA:
                raise ValueError('Oversized release metadata')
        releases = json.loads(raw)
        if not isinstance(releases, list):
            raise ValueError('Unexpected release response')
        candidates = []
        for obj in releases:
            if not isinstance(obj, dict) or obj.get('draft') :
                continue
            tag = obj.get('tag_name', '')
            match = VERSION.fullmatch(tag) if isinstance(tag, str) else None
            if not match:
                continue
            version = tuple(map(int, match.groups()))
            if version <= tuple(current):
                continue
            for asset in obj.get('assets', []):
                if not isinstance(asset, dict):
                    continue
                name = asset.get('name', '')
                m = ASSET.fullmatch(name) if isinstance(name, str) else None
                if not m or tuple(map(int, m.groups())) != version:
                    continue
                size = asset.get('size')
                url = asset.get('browser_download_url', '')
                prefix = 'https://github.com/' + REPO + '/releases/download/' + tag + '/'
                if type(size) is int and 1024 < size < 1024 * 1024 * 1024 and url == prefix + name:
                    candidates.append((version, tag, url, size))
        if not candidates:
            return {'status': 'current_or_unpublished'}
        version, tag, url, size = max(candidates)
        return {'status': 'available', 'version': tag, 'url': url, 'size': size,
                'installation': 'blocked_until_manifest_and_integrity_verified'}
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        return {'status': 'offline_or_invalid', 'detail': type(exc).__name__}
