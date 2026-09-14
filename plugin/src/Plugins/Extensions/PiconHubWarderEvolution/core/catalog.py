# -*- coding: utf-8 -*-
from __future__ import print_function

from ..constants import PICON_ROOT, REPOSITORY_API, REPOSITORY_BRANCH
from .errors import CatalogError
from .http import fetch_json


def _quote_path(path):
    try:
        from urllib.parse import quote
    except ImportError:
        from urllib import quote
    return quote(path, safe='/')


class RepositoryCatalog(object):
    """Lazy catalog over GitHub Contents API.

    Only the selected satellite/provider/style path is queried. This avoids
    giant recursive tree responses and keeps receiver memory use predictable.
    """

    def __init__(self, timeout=15, retries=2):
        self.timeout = timeout
        self.retries = retries
        self._cache = {}

    def _contents(self, path):
        key = path.strip('/')
        if key in self._cache:
            return self._cache[key]
        url = '%s/contents/%s?ref=%s' % (
            REPOSITORY_API, _quote_path(key), REPOSITORY_BRANCH)
        payload = fetch_json(url, timeout=self.timeout, retries=self.retries)
        if not isinstance(payload, list):
            message = payload.get('message') if isinstance(payload, dict) else payload
            raise CatalogError('Unexpected GitHub response for %s: %s' % (path, message))
        self._cache[key] = payload
        return payload

    def _dirs(self, path):
        return sorted([item['name'] for item in self._contents(path)
                       if item.get('type') == 'dir'], key=lambda x: x.lower())

    def satellites(self):
        return self._dirs(PICON_ROOT)

    def providers(self, satellite):
        return self._dirs('%s/%s' % (PICON_ROOT, satellite))

    def styles(self, satellite, provider):
        return self._dirs('%s/%s/%s' % (PICON_ROOT, satellite, provider))

    def picons(self, satellite, provider, style):
        path = '%s/%s/%s/%s' % (PICON_ROOT, satellite, provider, style)
        rows = []
        for item in self._contents(path):
            name = item.get('name', '')
            if item.get('type') != 'file' or not name.lower().endswith('.png'):
                continue
            rows.append({
                'name': name,
                'size': int(item.get('size') or 0),
                'sha': item.get('sha') or '',
                'download_url': item.get('download_url') or '',
                'path': item.get('path') or '',
            })
        rows.sort(key=lambda x: x['name'].lower())
        return rows

    def clear_cache(self):
        self._cache.clear()
