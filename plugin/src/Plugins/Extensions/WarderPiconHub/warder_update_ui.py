"""Enigma2 startup hook: one background check for every new plugin screen."""
from .warder_i18n import _, localize_skin, language_code

import pathlib
import queue
import threading

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.ScrollLabel import ScrollLabel
from Screens.MessageBox import MessageBox as NativeMessageBox
from Screens.Screen import Screen
from enigma import eTimer

from .warder_layout import update_skin
from .warder_update import check_release, install_release


def localized_notes(release):
    notes = getattr(release, "notes_i18n", {})
    return notes.get(language_code(), notes.get("en", release.notes))


_version_path = pathlib.Path(__file__).parent / "version.txt"
_cached_version = _version_path.read_text().strip()


def installed_version():
    global _cached_version
    try:
        value = _version_path.read_text().strip()
        if value:
            _cached_version = value
    except OSError:
        # opkg can replace files while the main screen clock is still running.
        pass
    return _cached_version


def connect_timer(timer, callback):
    if hasattr(timer, "callback"):
        timer.callback.append(callback)
        return None
    return timer.timeout.connect(callback)


class UpdateText(ScrollLabel):
    def applySkin(self, desktop, parent):
        result = ScrollLabel.applySkin(self, desktop, parent)
        self.instance.setZPosition(5)
        return result


class MessageBox(NativeMessageBox):
    """Only plugin-update notices use the owned full-screen Warder design."""
    def __init__(self, session, *args, **kwargs):
        from enigma import getDesktop
        size = getDesktop(0).size()
        NativeMessageBox.__init__(self, session, *args, **kwargs)
        self.skin = update_skin(size.width(), size.height(), version=installed_version())
        self.skinName = ["WarderPiconHubUpdateMessage"]
        self["text"] = UpdateText(self.text)
        self["title"] = Label(_("Aktualizácia PiconHub Warder Evolution"))
        for color in ("red", "green"):
            self["line_"+color] = Label("")
        self["key_red"] = Label(_("Naspäť"))
        self["key_green"] = Label(_("Potvrdiť výber") if self.list else "")
        enabled = kwargs.get("enable_input", True) and kwargs.get("enableInput", True)
        self["warderActions"] = ActionMap(["ColorActions"], {"red":self.cancel,"green":self.select}, -3)
        self["warderActions"].setEnabled(enabled)
        self["warderScroll"] = ActionMap(["DirectionActions"], {"up":self["text"].pageUp,"down":self["text"].pageDown}, -3)
        self["warderScroll"].setEnabled(enabled and not bool(self.list))
        if not self.list:
            self["line_green"].hide()
            self["key_green"].hide()
        if not enabled:
            for name in ("line_red","key_red","key_green"):
                self[name].hide()
        self.onClose.append(self.timer.stop)

    def autoResize(self):
        pass


class StartupUpdateCheck:
    def __init__(self, screen, check=check_release, timer_factory=eTimer, thread_factory=threading.Thread):
        self.screen, self.check, self.thread_factory = screen, check, thread_factory
        self.alive, self.started, self.busy, self.manual = True, False, False, False
        self.results = queue.Queue()
        self.timer = timer_factory()
        self.connection = connect_timer(self.timer, self.poll)
        screen.onLayoutFinish.append(self.start)
        screen.onClose.append(self.stop)

    def start(self):
        if not self.started:
            self.started = True
            self.request()

    def request(self, manual=False):
        if not self.alive or self.busy:
            return False
        self.busy, self.manual = True, manual
        self.thread_factory(target=self._work, daemon=True).start()
        self.timer.start(250, False)
        return True

    def _work(self):
        # Worker threads do no Enigma2 GUI work.
        try:
            self.results.put((self.check(installed_version()), None))
        except Exception as exc:
            self.results.put((None, str(exc)))

    def poll(self):
        if not self.alive:
            return
        # Delay the offer until the parent is active again, e.g. after leaving
        # the satellite picker. Never open a modal from an inactive screen.
        if getattr(self.screen.session, "current_dialog", self.screen) is not self.screen:
            return
        try:
            release, error = self.results.get_nowait()
        except queue.Empty:
            return
        self.timer.stop()
        self.busy = False
        notice = MessageBox
        if error:
            print("[PiconHub] Plugin update check failed: " + error)
            if self.manual:
                self.screen.session.open(notice, _("Kontrola aktualizácie sa nepodarila.\n") + error,
                                         type=MessageBox.TYPE_ERROR, timeout=10)
        elif release:
            text = (_("Dostupná je nová verzia PiconHub Warder Evolution.\n\n"
                    "Nainštalovaná: %s\nNová verzia: %s\n\n%s\n\nNainštalovať aktualizáciu?")
                    % (installed_version(), release.version, localized_notes(release)))
            self.screen.session.openWithCallback(lambda answer: self._answer(release, answer),
                                                 notice, text, type=notice.TYPE_YESNO, default=False)
        elif self.manual:
            self.screen.session.open(notice, _("Máš aktuálnu verziu, nie je potrebná aktualizácia.") + "\n\n" + installed_version(),
                                     type=MessageBox.TYPE_INFO, timeout=6)

    def _answer(self, release, accepted):
        if accepted and self.alive:
            self.screen.session.open(PluginInstallScreen, release)

    def stop(self):
        self.alive = False
        self.timer.stop()


class PluginInstallScreen(Screen):
    def __init__(self, session, release):
        from enigma import getDesktop
        size = getDesktop(0).size()
        self.skin = update_skin(size.width(),size.height(),kind="install",version=installed_version())
        Screen.__init__(self, session)
        self.release, self.started, self.done, self.closed = release, False, False, False
        self.results = queue.Queue()
        self["title"] = Label(_("Aktualizácia PiconHub Warder Evolution"))
        self["key_red"] = Label(_("Naspäť"))
        self["key_red"].hide()
        self["key_green"] = Label("")
        self["line_red"] = Label("")
        self["line_red"].hide()
        self["line_green"] = Label("")
        self["line_green"].hide()
        self["status"] = UpdateText(_("Sťahujem a overujem aktualizáciu pluginu.\nPočas inštalácie nevypínajte prijímač."))
        self["actions"] = ActionMap(["OkCancelActions","ColorActions"], {"ok": self.finish, "cancel": self.finish,"red": self.finish}, -2)
        self["scrollActions"] = ActionMap(["DirectionActions"], {"up":self["status"].pageUp,"down":self["status"].pageDown}, -3)
        self.timer = eTimer()
        self.connection = connect_timer(self.timer, self.poll)
        self.onLayoutFinish.append(self.start)
        self.onClose.append(self.cleanup)

    def start(self):
        if not self.started:
            self.started = True
            threading.Thread(target=self.work, daemon=True).start()
            self.timer.start(250, False)

    def work(self):
        try:
            self.results.put((install_release(self.release), None))
        except Exception as exc:
            self.results.put((None, str(exc)))

    def poll(self):
        if self.closed:
            return
        try:
            version, error = self.results.get_nowait()
        except queue.Empty:
            return
        self.timer.stop()
        self.done = True
        if error:
            self["status"].setText(_("Aktualizácia pluginu zlyhala.\n\n") + error)
            self["key_red"].show()
            if "line_red" in self:
                self["line_red"].show()
            return
        self["status"].setText(_("Plugin bol aktualizovaný na verziu ") + version + ".")
        self.session.openWithCallback(self.restart_after_notice, MessageBox,
                                      _("Plugin bol aktualizovaný na verziu %s.\nO 3 sekundy sa reštartuje GUI.") % version,
                                      type=MessageBox.TYPE_INFO, timeout=3, enable_input=False)

    def restart_after_notice(self, *args):
        if not self.closed:
            from Screens.Standby import TryQuitMainloop
            self.session.open(TryQuitMainloop, 3)

    def finish(self):
        if self.done:
            self.close()

    def cleanup(self):
        self.closed = True
        self.timer.stop()
