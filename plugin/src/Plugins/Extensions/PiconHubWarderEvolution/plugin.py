# -*- coding: utf-8 -*-
from __future__ import print_function

# PiconHub-Warder-Evolution
# Historical picon work: Chocholousek
# Original Chocholousek Picons Enigma2 plugin: s3n0
# Evolution / maintenance: Warder

from threading import Thread

from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.config import ConfigSelection, ConfigText, ConfigYesNo, getConfigListEntry
from enigma import eTimer, getDesktop

from . import _
from .constants import AUTHOR, PLUGIN_NAME, PLUGIN_VERSION
from .core.catalog import RepositoryCatalog
from .core.engine import PiconHubEngine
from .core.settings import load as load_settings, save as save_settings
from .core.updater import check_for_update, install_update


def _choices(values):
    return [(value, value) for value in values] or [('', _('(none)'))]


class _AsyncResult(object):
    def __init__(self):
        self.done = False
        self.value = None
        self.error = None


class PiconHubConfigScreen(Screen, ConfigListScreen):
    if getDesktop(0).size().width() > 1900:
        skin = '''
        <screen name="PiconHubConfigScreen" position="center,center" size="1200,800" title="PiconHub-Warder-Evolution" flags="wfNoBorder" backgroundColor="#44000000">
            <widget name="version_txt" position="0,0" size="1200,60" font="Regular;42" foregroundColor="yellow" transparent="1" halign="center" valign="center" />
            <widget name="author_txt" position="0,60" size="1200,40" font="Regular;28" foregroundColor="yellow" transparent="1" halign="center" valign="center" />
            <widget name="status_txt" position="50,105" size="1100,42" font="Regular;25" foregroundColor="white" transparent="1" halign="center" valign="center" />
            <widget name="config" position="50,155" size="1100,525" font="Regular;30" itemHeight="42" scrollbarMode="showOnDemand" backgroundColor="#1F000000" enableWrapAround="1" />
            <widget name="red" position="45,735" size="225,46" font="Regular;28" foregroundColor="red" transparent="1" valign="center" />
            <widget name="green" position="300,735" size="260,46" font="Regular;28" foregroundColor="green" transparent="1" valign="center" />
            <widget name="yellow" position="590,735" size="260,46" font="Regular;28" foregroundColor="yellow" transparent="1" valign="center" />
            <widget name="blue" position="880,735" size="270,46" font="Regular;28" foregroundColor="blue" transparent="1" valign="center" />
        </screen>'''
    else:
        skin = '''
        <screen name="PiconHubConfigScreen" position="center,center" size="850,600" title="PiconHub-Warder-Evolution" flags="wfNoBorder" backgroundColor="#44000000">
            <widget name="version_txt" position="0,0" size="850,45" font="Regular;30" foregroundColor="yellow" transparent="1" halign="center" valign="center" />
            <widget name="author_txt" position="0,45" size="850,32" font="Regular;21" foregroundColor="yellow" transparent="1" halign="center" valign="center" />
            <widget name="status_txt" position="35,80" size="780,32" font="Regular;20" foregroundColor="white" transparent="1" halign="center" valign="center" />
            <widget name="config" position="35,120" size="780,385" font="Regular;23" itemHeight="34" scrollbarMode="showOnDemand" backgroundColor="#1F000000" enableWrapAround="1" />
            <widget name="red" position="35,535" size="165,40" font="Regular;21" foregroundColor="red" transparent="1" valign="center" />
            <widget name="green" position="210,535" size="205,40" font="Regular;21" foregroundColor="green" transparent="1" valign="center" />
            <widget name="yellow" position="425,535" size="185,40" font="Regular;21" foregroundColor="yellow" transparent="1" valign="center" />
            <widget name="blue" position="620,535" size="195,40" font="Regular;21" foregroundColor="blue" transparent="1" valign="center" />
        </screen>'''

    def __init__(self, session):
        Screen.__init__(self, session)
        self.catalog = RepositoryCatalog(timeout=12, retries=1)
        self.data = load_settings()
        self._job = None
        self._job_callback = None
        self._poll = eTimer()
        self._poll.callback.append(self._pollJob)
        self['version_txt'] = Label('%s  %s' % (PLUGIN_NAME, PLUGIN_VERSION))
        self['author_txt'] = Label('Chocholousek picons  •  plugin by s3n0  •  Evolution by %s' % AUTHOR)
        self['status_txt'] = Label(_('Ready'))
        self['red'] = Label(_('Exit'))
        self['green'] = Label(_('Save + update'))
        self['yellow'] = Label(_('Refresh catalog'))
        self['blue'] = Label(_('Plugin update'))
        self.target = ConfigText(default=self.data['target_dir'], fixed_size=False)
        self.mode = ConfigSelection(default=self.data['mode'], choices=[
            ('all', _('All picons from selected package')),
            ('bouquets_tv', _('Only services from TV bouquets')),
            ('bouquets_tv_radio', _('Only services from TV + radio bouquets')),
        ])
        self.remove_orphans = ConfigYesNo(default=self.data['remove_orphans'])
        self.satellite = ConfigSelection(default=self.data['satellite'], choices=[(self.data['satellite'], self.data['satellite'])])
        self.provider = ConfigSelection(default=self.data['provider'], choices=[(self.data['provider'], self.data['provider'])])
        self.style = ConfigSelection(default=self.data['style'], choices=[(self.data['style'], self.data['style'])])
        ConfigListScreen.__init__(self, [], session=session)
        self['actions'] = ActionMap(['OkCancelActions', 'ColorActions', 'DirectionActions'], {
            'cancel': self.close, 'red': self.close, 'green': self.saveAndUpdate,
            'yellow': self.refreshCatalog, 'blue': self.checkPluginUpdate,
            'ok': self.keyOK, 'left': self.keyLeft, 'right': self.keyRight,
        }, -1)
        self._rebuild()
        self.onLayoutFinish.append(self.refreshCatalog)

    def _rebuild(self):
        self.list = [
            getConfigListEntry(_('Picon folder'), self.target),
            getConfigListEntry(_('Satellite'), self.satellite),
            getConfigListEntry(_('Provider'), self.provider),
            getConfigListEntry(_('Style'), self.style),
            getConfigListEntry(_('Update mode'), self.mode),
            getConfigListEntry(_('Remove obsolete picons from this package'), self.remove_orphans),
        ]
        self['config'].setList(self.list)

    def _startJob(self, label, worker, callback):
        if self._job is not None:
            return
        result = _AsyncResult()
        self._job = result
        self._job_callback = callback
        self['status_txt'].setText(label)

        def run():
            try:
                result.value = worker()
            except Exception as exc:
                result.error = exc
            result.done = True

        thread = Thread(target=run)
        thread.daemon = True
        thread.start()
        self._poll.start(200, True)

    def _pollJob(self):
        result = self._job
        if result is None:
            return
        if not result.done:
            self._poll.start(200, True)
            return
        callback = self._job_callback
        self._job = None
        self._job_callback = None
        if result.error:
            self['status_txt'].setText(_('Error'))
            self.session.open(MessageBox, str(result.error), MessageBox.TYPE_ERROR, timeout=15)
            return
        self['status_txt'].setText(_('Ready'))
        if callback:
            callback(result.value)

    def refreshCatalog(self):
        def worker():
            self.catalog.clear_cache()
            satellites = self.catalog.satellites()
            sat = self.satellite.value if self.satellite.value in satellites else (satellites[0] if satellites else '')
            providers = self.catalog.providers(sat) if sat else []
            provider = self.provider.value if self.provider.value in providers else (providers[0] if providers else '')
            styles = self.catalog.styles(sat, provider) if sat and provider else []
            style = self.style.value if self.style.value in styles else (styles[0] if styles else '')
            return satellites, sat, providers, provider, styles, style

        def apply_result(result):
            satellites, sat, providers, provider, styles, style = result
            self.satellite.setChoices(_choices(satellites), default=sat)
            self.provider.setChoices(_choices(providers), default=provider)
            self.style.setChoices(_choices(styles), default=style)
            self._rebuild()

        self._startJob(_('Loading PiconHub catalog...'), worker, apply_result)

    def _refreshChildren(self):
        sat = self.satellite.value
        provider_current = self.provider.value

        def worker():
            providers = self.catalog.providers(sat) if sat else []
            provider = provider_current if provider_current in providers else (providers[0] if providers else '')
            styles = self.catalog.styles(sat, provider) if sat and provider else []
            style = self.style.value if self.style.value in styles else (styles[0] if styles else '')
            return providers, provider, styles, style

        def apply_result(result):
            providers, provider, styles, style = result
            self.provider.setChoices(_choices(providers), default=provider)
            self.style.setChoices(_choices(styles), default=style)
            self._rebuild()

        self._startJob(_('Loading providers/styles...'), worker, apply_result)

    def keyLeft(self):
        before_sat = self.satellite.value
        before_provider = self.provider.value
        ConfigListScreen.keyLeft(self)
        if self.satellite.value != before_sat or self.provider.value != before_provider:
            self._refreshChildren()

    def keyRight(self):
        before_sat = self.satellite.value
        before_provider = self.provider.value
        ConfigListScreen.keyRight(self)
        if self.satellite.value != before_sat or self.provider.value != before_provider:
            self._refreshChildren()

    def keyOK(self):
        ConfigListScreen.keyOK(self)

    def _settings(self):
        return {'target_dir': self.target.value, 'satellite': self.satellite.value,
                'provider': self.provider.value, 'style': self.style.value,
                'mode': self.mode.value, 'remove_orphans': self.remove_orphans.value}

    def saveAndUpdate(self):
        data = save_settings(self._settings())

        def worker():
            engine = PiconHubEngine(data, catalog=self.catalog, timeout=20, retries=2)
            return engine.apply()

        def finished(plan):
            message = _('Update finished.\n\nSelected: %(selected_count)s\nDownloaded/updated: %(download_count)s\nUnchanged: %(unchanged_count)s\nRemoved: %(remove_count)s') % plan
            self.session.open(MessageBox, message, MessageBox.TYPE_INFO, timeout=15)

        self._startJob(_('Updating picons...'), worker, finished)

    def checkPluginUpdate(self):
        def finished(info):
            if not info.get('enabled'):
                self.session.open(MessageBox, _('Plugin update channel is currently disabled.'), MessageBox.TYPE_INFO, timeout=10)
                return
            if not info.get('available'):
                self.session.open(MessageBox, _('You already have the newest plugin version (%s).') % PLUGIN_VERSION, MessageBox.TYPE_INFO, timeout=10)
                return
            text = _('New plugin version %(version)s is available.\nCurrent version: %(current_version)s') % info
            if info.get('notes'):
                text += '\n\n' + info['notes']
            text += '\n\n' + _('Install this update now?')
            self.session.openWithCallback(lambda answer: self._installPluginUpdate(info) if answer else None,
                                          MessageBox, text, MessageBox.TYPE_YESNO)

        self._startJob(_('Checking plugin update...'),
                       lambda: check_for_update(timeout=15, retries=2), finished)

    def _installPluginUpdate(self, info):
        def installed(result):
            text = _('Plugin update %(version)s was installed successfully.') % result
            if result.get('restart_gui'):
                text += '\n\n' + _('Restart Enigma2 GUI now?')
                self.session.openWithCallback(self._restartGui, MessageBox, text, MessageBox.TYPE_YESNO)
            else:
                self.session.open(MessageBox, text, MessageBox.TYPE_INFO, timeout=12)

        self._startJob(_('Downloading and installing plugin update...'),
                       lambda: install_update(info, timeout=30, retries=2), installed)

    def _restartGui(self, answer):
        if not answer:
            return
        try:
            from Screens.Standby import TryQuitMainloop
            self.session.open(TryQuitMainloop, 3)
        except Exception as exc:
            self.session.open(MessageBox, _('Update installed. Please restart Enigma2 GUI manually.\n%s') % exc,
                              MessageBox.TYPE_INFO, timeout=15)


def pluginMenu(session, **kwargs):
    session.open(PiconHubConfigScreen)


def Plugins(**kwargs):
    description = _('Download and update picons from PiconHub-Warder-Evolution')
    logo = 'images/plugin_fhd.png' if getDesktop(0).size().width() > 1900 else 'images/plugin.png'
    return [
        PluginDescriptor(name=PLUGIN_NAME, description=description,
                         where=PluginDescriptor.WHERE_PLUGINMENU,
                         icon=logo, needsRestart=False, fnc=pluginMenu),
        PluginDescriptor(name=PLUGIN_NAME, description=description,
                         where=PluginDescriptor.WHERE_EXTENSIONSMENU,
                         needsRestart=False, fnc=pluginMenu),
    ]
