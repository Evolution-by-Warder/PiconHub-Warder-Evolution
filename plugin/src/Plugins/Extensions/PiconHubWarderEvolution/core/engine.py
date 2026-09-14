# -*- coding: utf-8 -*-
from __future__ import print_function

import os

from .catalog import RepositoryCatalog
from .errors import UnsafePathError
from .http import download_atomic
from .scanner import git_blob_sha1, local_picons, scan_bouquets

PROTECTED_DIRS = set(['/', '/bin', '/boot', '/dev', '/etc', '/lib', '/proc', '/root', '/sbin', '/sys', '/usr', '/var'])


def validate_target(path):
    path = os.path.realpath(os.path.abspath(path or ''))
    if not path or path in PROTECTED_DIRS or len(path) < 5:
        raise UnsafePathError('Unsafe picon target: %s' % path)
    return path


class PiconHubEngine(object):
    def __init__(self, settings, catalog=None, timeout=15, retries=2):
        self.settings = dict(settings or {})
        self.timeout = timeout
        self.retries = retries
        self.catalog = catalog or RepositoryCatalog(timeout=timeout, retries=retries)

    def _selection(self):
        satellite = str(self.settings.get('satellite') or '').strip()
        provider = str(self.settings.get('provider') or '').strip()
        style = str(self.settings.get('style') or '').strip()
        if not satellite or not provider or not style:
            raise ValueError('Satellite, provider and style must be selected')
        return satellite, provider, style

    def remote_rows(self):
        return self.catalog.picons(*self._selection())

    def wanted_names(self):
        mode = str(self.settings.get('mode') or 'all')
        if mode == 'bouquets_tv':
            return set(name.lower() for name in scan_bouquets(False))
        if mode == 'bouquets_tv_radio':
            return set(name.lower() for name in scan_bouquets(True))
        return None

    def plan(self):
        target = validate_target(self.settings.get('target_dir'))
        remote = self.remote_rows()
        wanted = self.wanted_names()
        local = local_picons(target)
        selected = []
        for row in remote:
            if wanted is not None and row['name'].lower() not in wanted:
                continue
            selected.append(row)

        downloads = []
        unchanged = []
        for row in selected:
            local_path = local.get(row['name'].lower())
            if not local_path:
                downloads.append(row)
                continue
            try:
                if os.path.getsize(local_path) == row['size'] and git_blob_sha1(local_path) == row['sha']:
                    unchanged.append(row)
                else:
                    downloads.append(row)
            except OSError:
                downloads.append(row)

        selected_names = set(row['name'].lower() for row in selected)
        remote_names = set(row['name'].lower() for row in remote)
        remove = []
        if self.settings.get('remove_orphans'):
            for name, path in local.items():
                if name in remote_names and name not in selected_names:
                    remove.append(path)

        return {
            'target': target,
            'remote_count': len(remote),
            'selected_count': len(selected),
            'download_count': len(downloads),
            'unchanged_count': len(unchanged),
            'remove_count': len(remove),
            'downloads': downloads,
            'remove': remove,
        }

    def apply(self, progress=None):
        plan = self.plan()
        target = plan['target']
        if not os.path.isdir(target):
            os.makedirs(target)
        total = len(plan['downloads']) + len(plan['remove'])
        done = 0
        for row in plan['downloads']:
            name = os.path.basename(row['name'])
            destination = os.path.join(target, name)
            download_atomic(row['download_url'], destination,
                            expected_size=row['size'], expected_git_sha=row['sha'],
                            timeout=self.timeout, retries=self.retries)
            done += 1
            if progress:
                progress(done, total, 'download', name)
        for path in plan['remove']:
            try:
                os.remove(path)
            except OSError:
                pass
            done += 1
            if progress:
                progress(done, total, 'remove', os.path.basename(path))
        return plan
