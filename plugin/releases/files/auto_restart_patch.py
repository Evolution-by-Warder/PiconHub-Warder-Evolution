# -*- coding: utf-8 -*-
from __future__ import print_function

from Screens.MessageBox import MessageBox
from enigma import eTimer

from . import plugin_updater as updater


def _install_answer(screen, manifest, answer):
    if not answer:
        return
    try:
        remote = updater.PiconHubPluginUpdater().install(manifest)
    except Exception as e:
        screen.session.open(MessageBox,
            'Aktualizáciu PiconHubu sa nepodarilo nainštalovať:\n\n%s' % e,
            MessageBox.TYPE_ERROR, timeout=15)
        return

    screen.session.open(MessageBox,
        'PiconHub bol úspešne aktualizovaný na verziu %s.\n\n'
        'Pre načítanie novej verzie sa Enigma2 GUI automaticky reštartuje.\n\n'
        'Reštart GUI za 3 sekundy...' % remote,
        MessageBox.TYPE_INFO, timeout=3)
    screen._piconhub_restart_timer = eTimer()

    def do_restart():
        updater._restart_gui(screen.session)

    screen._piconhub_restart_timer.callback.append(do_restart)
    screen._piconhub_restart_timer.start(3000, True)


# The automatic startup checker resolves this global when the user confirms.
# Replacing it removes the old second YES/NO restart question.
updater._install_answer = _install_answer
