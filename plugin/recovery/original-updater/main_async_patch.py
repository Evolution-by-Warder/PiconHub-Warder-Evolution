# -*- coding: utf-8 -*-
from __future__ import print_function

import json
import os
from threading import Thread
from time import localtime, strftime

from enigma import eTimer

from . import plugin as p


_CACHE_DIR = '/tmp/.ph_runtime'
_CACHE_FILE = os.path.join(_CACHE_DIR, '.state')
_SESSION_PID = os.getpid()
_SESSION_REFRESH_STARTED = False
_SESSION_REFRESH_DONE = False
_SESSION_RESULT = None
_SESSION_ERROR = None


def _local_latest_cached_path(row, index):
    """Main screen previews must never block GUI on network I/O."""
    filename = str((row or {}).get('_file') or '').strip()
    settings = p.load_settings()
    target = settings.get('target_dir', p.DEFAULTS['target_dir'])
    if filename:
        local_path = os.path.join(target, filename)
        if os.path.isfile(local_path):
            return local_path

    safe = p.re.sub(r'[^A-Za-z0-9_.-]+', '_', filename or ('latest_%d.png' % index))
    cache = os.path.join('/tmp', 'piconhub_main_latest_%s' % safe)
    return cache if os.path.isfile(cache) else ''


def _read_state():
    try:
        with open(_CACHE_FILE, 'r') as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            return None
        data = payload.get('data')
        if not isinstance(data, dict):
            return None
        return payload
    except Exception:
        return None


def _write_state(result):
    try:
        if not os.path.isdir(_CACHE_DIR):
            os.makedirs(_CACHE_DIR)
        try:
            os.chmod(_CACHE_DIR, 0o700)
        except Exception:
            pass

        payload = {
            'schema': 1,
            'session_pid': _SESSION_PID,
            'data': result,
        }
        temp_path = _CACHE_FILE + '.new'
        with open(temp_path, 'w') as handle:
            json.dump(payload, handle, separators=(',', ':'), sort_keys=True)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except Exception:
                pass
        try:
            os.chmod(temp_path, 0o600)
        except Exception:
            pass
        os.rename(temp_path, _CACHE_FILE)
    except Exception as e:
        print('[PiconHub] runtime cache write error:', e)
        try:
            if os.path.exists(_CACHE_FILE + '.new'):
                os.unlink(_CACHE_FILE + '.new')
        except Exception:
            pass


def _apply_result(self, result):
    if not result:
        return
    try:
        self['db_version'].setText(result.get('database_version') or '—')
        self.latest_rows = list(result.get('latest_rows') or [])
        self.news_rows = list(result.get('news_rows') or [])
        self._updateLatestMainPicons()
        self._updateNewsRows()
        self['db_lastcheck'].setText(result.get('lastcheck') or '—')
        self['db_total'].setText(str(result.get('total', 0)))
        self['db_available'].setText(str(result.get('installed', 0)))
        self['db_missing'].setText(str(result.get('missing', 0)))
        self['db_updates'].setText(str(result.get('updates', 0)))
        self['db_percent'].setText('%.1f%%' % float(result.get('percent', 0.0)))
    except Exception as e:
        print('[PiconHub] runtime cache UI update error:', e)


def _build_fresh_result():
    settings = p.load_settings()
    target = settings.get('target_dir', p.DEFAULTS['target_dir'])
    engine = p.PiconHubStyleUpdateEngine(settings, timeout=4)
    catalog = engine._fetch_json(settings.get('catalog_url') or p.DEFAULT_CATALOG_URL)

    result = {
        'database_version': str(catalog.get('database_version') or '').strip(),
        'latest_rows': p._latest_rows_from_catalog(engine, catalog),
        'news_rows': p._news_rows_from_catalog(engine, catalog),
        'lastcheck': strftime('%d.%m.%Y %H:%M', localtime()),
        'total': 0,
        'installed': 0,
        'missing': 0,
        'updates': 0,
        'percent': 0.0,
    }

    scan = p.scan_summary(target)
    services = list((scan.get('services') or {}).values())
    clean = []
    seen = set()
    for row in services:
        name = (row.get('name') or '').strip()
        ref = (row.get('service_reference') or '').strip()
        if not name or not ref or ref in seen:
            continue
        parts = ref.split(':')
        if len(parts) < 7 or parts[0] != '1' or parts[1] != '0':
            continue
        try:
            stype = int(parts[2], 16)
        except Exception:
            continue
        if stype not in (1, 4, 5, 17, 19, 22, 25, 31):
            continue
        seen.add(ref)
        clean.append(row)

    total = len(clean)
    installed = 0
    for row in clean:
        picon = row.get('picon') or ''
        if picon and os.path.isfile(os.path.join(target, picon)):
            installed += 1

    result['total'] = total
    result['installed'] = installed
    result['missing'] = max(0, total - installed)
    result['percent'] = (100.0 * installed / total) if total else 0.0

    try:
        plan = engine.plan()
        result['updates'] = int(plan.get('download_count', 0) or 0)
    except Exception as e:
        print('[PiconHub] async database update-count error:', e)

    return result


def _async_database_loader(self):
    global _SESSION_REFRESH_STARTED
    global _SESSION_REFRESH_DONE
    global _SESSION_RESULT
    global _SESSION_ERROR

    cached = _read_state()
    cached_result = (cached or {}).get('data') or None

    # Never make the user wait for network work. If we have previous-session
    # data, show it immediately. On the very first run keep the normal quiet
    # placeholders and fill them when background refresh finishes.
    if _SESSION_RESULT:
        _apply_result(self, _SESSION_RESULT)
    elif cached_result:
        _apply_result(self, cached_result)

    # A cache written by this exact Enigma2 process is current for the whole
    # GUI session. Reopening PiconHub must not touch GitHub/server again.
    if cached and int(cached.get('session_pid') or -1) == _SESSION_PID:
        _SESSION_RESULT = cached_result
        _SESSION_REFRESH_DONE = True
        return

    # One refresh per Enigma2 GUI process. Other screen instances only poll the
    # shared result; they never start another network job.
    if not _SESSION_REFRESH_STARTED:
        _SESSION_REFRESH_STARTED = True
        _SESSION_REFRESH_DONE = False
        _SESSION_ERROR = None

        def worker():
            global _SESSION_REFRESH_DONE
            global _SESSION_RESULT
            global _SESSION_ERROR
            try:
                fresh = _build_fresh_result()
                _SESSION_RESULT = fresh
                _write_state(fresh)
            except Exception as e:
                _SESSION_ERROR = str(e)
            _SESSION_REFRESH_DONE = True

        thread = Thread(target=worker)
        thread.daemon = True
        thread.start()

    self._piconhub_db_last_applied = id(_SESSION_RESULT) if _SESSION_RESULT is not None else None

    def poll():
        if _SESSION_RESULT is not None:
            marker = id(_SESSION_RESULT)
            if getattr(self, '_piconhub_db_last_applied', None) != marker:
                _apply_result(self, _SESSION_RESULT)
                self._piconhub_db_last_applied = marker

        if _SESSION_REFRESH_DONE:
            if _SESSION_ERROR:
                print('[PiconHub] background database refresh error:', _SESSION_ERROR)
            return

        try:
            self._piconhub_db_poll.start(250, True)
        except Exception:
            pass

    self._piconhub_db_poll = eTimer()
    self._piconhub_db_poll.callback.append(poll)
    self._piconhub_db_poll.start(250, True)


# Main-screen database/status data is session-cached in a hidden /tmp location.
# The UI never waits for network I/O, and GitHub/server is contacted at most
# once per Enigma2 GUI process for this main-screen refresh.
p._main_latest_cached_path = _local_latest_cached_path
p.PiconHubMain._loadDatabaseVersion = _async_database_loader
