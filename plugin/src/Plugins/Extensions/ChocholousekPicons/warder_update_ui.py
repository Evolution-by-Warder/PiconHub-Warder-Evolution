"""Enigma2 startup hook: one background check for every new plugin screen."""

import pathlib
import queue
import threading

from Components.ActionMap import ActionMap
from Components.Label import Label
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from enigma import eTimer

from .warder_update import check_release, install_release


def installed_version():
    return (pathlib.Path(__file__).parent / "version.txt").read_text().strip()


def connect_timer(timer, callback):
    if hasattr(timer, "callback"):
        timer.callback.append(callback)
        return None
    return timer.timeout.connect(callback)


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
        if error:
            print("[PiconHub] Plugin update check failed: " + error)
            if self.manual:
                self.screen.session.open(MessageBox, "Kontrola aktualizácie sa nepodarila.\n" + error,
                                         type=MessageBox.TYPE_ERROR, timeout=10)
        elif release:
            text = ("Dostupná je nová verzia PiconHub Warder Evolution.\n\n"
                    "Nainštalovaná: %s\nNová verzia: %s\n\n%s\n\nNainštalovať aktualizáciu?"
                    % (installed_version(), release.version, release.notes))
            self.screen.session.openWithCallback(lambda answer: self._answer(release, answer),
                                                 MessageBox, text, type=MessageBox.TYPE_YESNO, default=False)
        elif self.manual:
            self.screen.session.open(MessageBox, "Novšie vydanie pluginu nie je dostupné.",
                                     type=MessageBox.TYPE_INFO, timeout=8)

    def _answer(self, release, accepted):
        if accepted and self.alive:
            self.screen.session.open(PluginInstallScreen, release)

    def stop(self):
        self.alive = False
        self.timer.stop()


class PluginInstallScreen(Screen):
    skin = '''<screen position="center,center" size="900,400" title="Aktualizácia PiconHub Warder Evolution">
        <widget name="status" position="35,30" size="830,330" font="Regular;26" />
    </screen>'''

    def __init__(self, session, release):
        Screen.__init__(self, session)
        self.release, self.started, self.done, self.closed = release, False, False, False
        self.results = queue.Queue()
        self["status"] = Label("Sťahujem a overujem aktualizáciu pluginu.\nPočas inštalácie nevypínajte prijímač.")
        self["actions"] = ActionMap(["OkCancelActions"], {"ok": self.finish, "cancel": self.finish}, -2)
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
            self["status"].setText("Aktualizácia pluginu zlyhala.\n\n" + error + "\n\nOK alebo EXIT: späť.")
            return
        self["status"].setText("Plugin bol aktualizovaný na verziu " + version + ".")
        self.session.openWithCallback(self.restart_answer, MessageBox,
                                      "Aktualizácia je nainštalovaná.\nReštartovať GUI pre načítanie novej verzie?",
                                      type=MessageBox.TYPE_YESNO, default=False)

    def restart_answer(self, accepted):
        if accepted and not self.closed:
            from Screens.Standby import TryQuitMainloop
            self.session.open(TryQuitMainloop, 3)
        elif not self.closed:
            self.close()

    def finish(self):
        if self.done:
            self.close()

    def cleanup(self):
        self.closed = True
        self.timer.stop()
