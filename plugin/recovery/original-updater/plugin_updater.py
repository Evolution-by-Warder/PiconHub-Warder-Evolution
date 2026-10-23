# -*- coding: utf-8 -*-
from __future__ import print_function

import hashlib
import json
import os
import shutil
import time

try:
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import Request, urlopen

from Screens.MessageBox import MessageBox
from enigma import eTimer

from . import plugin as _plugin
from .release import VERSION as RELEASE_VERSION


MANIFEST_URL = (
    'https://raw.githubusercontent.com/PiconHub-Warder/'
    'piconhub-server/main/plugin-update/manifest.json'
)
_ALLOWED_UPDATE_PREFIX = (
    'https://raw.githubusercontent.com/PiconHub-Warder/'
    'piconhub-server/'
)
_AUTO_CHECK_DONE = False


class PiconHubPluginUpdateError(Exception):
    pass


def _version_key(value):
    result = []
    for part in str(value or '').strip().lstrip('vV').split('.'):
        digits = ''.join(ch for ch in part if ch.isdigit())
        result.append(int(digits or 0))
    while len(result) < 4:
        result.append(0)
    return tuple(result[:4])


def _safe_relative_path(value):
    value = str(value or '').replace('\\', '/').strip().lstrip('/')
    parts = [part for part in value.split('/') if part not in ('', '.')]
    if not parts or '..' in parts:
        raise PiconHubPluginUpdateError('Neplatná cesta v update manifeste.')
    return os.path.join(*parts)


class PiconHubPluginUpdater(object):
    def __init__(self, timeout=6):
        self.timeout = timeout
        self.plugin_path = os.path.dirname(os.path.abspath(__file__))

    def _fetch(self, url):
        if not str(url or '').startswith('https://'):
            raise PiconHubPluginUpdateError('Update URL musí používať HTTPS.')
        request = Request(url, headers={'User-Agent': 'PiconHub/%s' % RELEASE_VERSION})
        response = urlopen(request, timeout=self.timeout)
        try:
            return response.read()
        finally:
            try:
                response.close()
            except Exception:
                pass

    def _fetch_json(self, url):
        raw = self._fetch(url)
        try:
            if not isinstance(raw, str):
                raw = raw.decode('utf-8')
            data = json.loads(raw)
        except Exception as e:
            raise PiconHubPluginUpdateError('Neplatný update manifest: %s' % e)
        if not isinstance(data, dict):
            raise PiconHubPluginUpdateError('Update manifest nemá správny formát.')
        return data

    def check(self):
        manifest = self._fetch_json(MANIFEST_URL)
        remote_version = str(manifest.get('version') or '').strip()
        files = manifest.get('files')
        if not remote_version or not isinstance(files, list):
            raise PiconHubPluginUpdateError('Update manifest neobsahuje verziu alebo súbory.')
        return {
            'available': _version_key(remote_version) > _version_key(RELEASE_VERSION),
            'current_version': RELEASE_VERSION,
            'remote_version': remote_version,
            'notes': str(manifest.get('notes') or '').strip(),
            'manifest': manifest,
        }

    def install(self, manifest):
        remote_version = str(manifest.get('version') or '').strip()
        files = manifest.get('files')
        if not remote_version or not isinstance(files, list) or not files:
            raise PiconHubPluginUpdateError('Update manifest je prázdny.')

        prepared = []
        for item in files:
            if not isinstance(item, dict):
                raise PiconHubPluginUpdateError('Neplatná položka v update manifeste.')
            rel = _safe_relative_path(item.get('path'))
            url = str(item.get('url') or '').strip()
            digest = str(item.get('sha256') or '').strip().lower()
            if not url.startswith(_ALLOWED_UPDATE_PREFIX):
                raise PiconHubPluginUpdateError('Update súbor nie je z dôveryhodného PiconHub repozitára.')
            if len(digest) != 64:
                raise PiconHubPluginUpdateError('Chýba SHA-256 kontrola update súboru %s.' % rel)

            payload = self._fetch(url)
            actual = hashlib.sha256(payload).hexdigest().lower()
            if actual != digest:
                raise PiconHubPluginUpdateError('SHA-256 nesúhlasí pre %s.' % rel)
            prepared.append((rel, payload))

        backup_root = '/tmp/piconhub-plugin-backup-%d' % int(time.time())
        changed = []
        try:
            os.makedirs(backup_root)
            for rel, payload in prepared:
                target = os.path.join(self.plugin_path, rel)
                target_dir = os.path.dirname(target)
                if not os.path.isdir(target_dir):
                    os.makedirs(target_dir)

                backup = os.path.join(backup_root, rel)
                if os.path.exists(target):
                    backup_dir = os.path.dirname(backup)
                    if not os.path.isdir(backup_dir):
                        os.makedirs(backup_dir)
                    shutil.copy2(target, backup)

                tmp = target + '.piconhub-update'
                with open(tmp, 'wb') as handle:
                    handle.write(payload)
                    handle.flush()
                    try:
                        os.fsync(handle.fileno())
                    except Exception:
                        pass
                try:
                    os.chmod(tmp, 0o644)
                except Exception:
                    pass
                os.rename(tmp, target)
                changed.append((target, backup if os.path.exists(backup) else None))
        except Exception as e:
            for target, backup in reversed(changed):
                try:
                    if backup and os.path.exists(backup):
                        shutil.copy2(backup, target)
                    elif os.path.exists(target):
                        os.remove(target)
                except Exception as restore_error:
                    print('[PiconHub] plugin update restore error:', restore_error)
            raise PiconHubPluginUpdateError('Aktualizácia zlyhala a bola vrátená späť: %s' % e)

        return remote_version


def _restart_gui(session):
    try:
        from Screens.Standby import TryQuitMainloop
        session.open(TryQuitMainloop, 3)
    except Exception as e:
        session.open(
            MessageBox,
            'Aktualizácia je nainštalovaná. Reštartujte Enigma2 GUI ručne.\n\n%s' % e,
            MessageBox.TYPE_INFO,
            timeout=12,
        )


def _install_answer(screen, manifest, answer):
    if not answer:
        return
    try:
        remote = PiconHubPluginUpdater().install(manifest)
    except Exception as e:
        screen.session.open(
            MessageBox,
            'Aktualizáciu PiconHubu sa nepodarilo nainštalovať:\n\n%s' % e,
            MessageBox.TYPE_ERROR,
            timeout=15,
        )
        return

    def restart_answer(value):
        if value:
            _restart_gui(screen.session)

    screen.session.openWithCallback(
        restart_answer,
        MessageBox,
        'PiconHub bol aktualizovaný na verziu %s.\n\n'
        'Pre načítanie novej verzie je potrebný reštart GUI.\n'
        'Reštartovať GUI teraz?' % remote,
        MessageBox.TYPE_YESNO,
        default=True,
    )


def _offer_update(screen, result, manual=False):
    if result.get('available'):
        notes = result.get('notes') or 'K dispozícii je nová verzia PiconHubu.'
        text = (
            'Dostupná je nová verzia PiconHubu.\n\n'
            'Aktuálna verzia: %s\n'
            'Nová verzia: %s\n\n'
            '%s\n\n'
            'Nainštalovať aktualizáciu priamo z GitHubu?'
        ) % (result.get('current_version'), result.get('remote_version'), notes)
        screen.session.openWithCallback(
            lambda answer: _install_answer(screen, result.get('manifest'), answer),
            MessageBox,
            text,
            MessageBox.TYPE_YESNO,
            default=True,
        )
        return

    if manual:
        screen.session.open(
            MessageBox,
            'PiconHub by Warder\n'
            'Verzia %s\n\n'
            'Používaš najnovšiu dostupnú verziu.\n\n'
            'Your channels. Your logos. Our passion.' % RELEASE_VERSION,
            MessageBox.TYPE_INFO,
            timeout=10,
        )


def _manual_update_check(screen):
    try:
        result = PiconHubPluginUpdater().check()
    except Exception as e:
        screen.session.open(
            MessageBox,
            'PiconHub by Warder\n'
            'Verzia %s\n\n'
            'Kontrola aktualizácie zlyhala:\n%s' % (RELEASE_VERSION, e),
            MessageBox.TYPE_ERROR,
            timeout=12,
        )
        return
    _offer_update(screen, result, manual=True)


_original_about = _plugin.PiconHubMain.about
_original_layout_ready = _plugin.PiconHubMain._layoutReady


def _about_with_update(self):
    _manual_update_check(self)


def _layout_ready_with_update(self):
    global _AUTO_CHECK_DONE
    _original_layout_ready(self)
    if _AUTO_CHECK_DONE:
        return
    _AUTO_CHECK_DONE = True
    self._piconhub_plugin_update_timer = eTimer()

    def auto_check():
        try:
            result = PiconHubPluginUpdater(timeout=4).check()
            _offer_update(self, result, manual=False)
        except Exception as e:
            print('[PiconHub] automatic plugin update check error:', e)

    self._piconhub_plugin_update_timer.callback.append(auto_check)
    try:
        self._piconhub_plugin_update_timer.start(1800, True)
    except Exception as e:
        print('[PiconHub] automatic plugin update timer error:', e)


# Keep the visible header version in sync without touching the large legacy
# plugin.py. The header reads this module global dynamically.
_plugin.VERSION = RELEASE_VERSION
_plugin.PiconHubPluginUpdater = PiconHubPluginUpdater
_plugin.PiconHubMain.about = _about_with_update
_plugin.PiconHubMain._layoutReady = _layout_ready_with_update
