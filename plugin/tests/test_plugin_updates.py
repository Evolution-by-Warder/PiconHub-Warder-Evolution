import hashlib
import importlib.util
import io
import json
import pathlib
import ssl
import sys
import tarfile
import tempfile
import types
import unittest
from unittest.mock import patch

RUNTIME = pathlib.Path(__file__).parents[1] / "src/Plugins/Extensions/WarderPiconHub"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


updates = load_module("warder_update_tests_core", RUNTIME / "warder_update.py")


def feed(version="0.1.1"):
    return {"schema": 1, "product": "PiconHub Warder Evolution", "channel": "stable",
            "release": {"version": version, "tag": "v" + version,
                        "url": "https://github.com/" + updates.REPOSITORY + "/releases/download/v" + version + "/" + updates.PACKAGE_ID + "_" + version + "_all.ipk",
                        "sha256": "a" * 64, "bytes": 123, "notes": "Changes"}}


def control_tar(package, version="0.1.1", architecture="all"):
    out = io.BytesIO()
    data = ("Package: %s\nVersion: %s\nArchitecture: %s\n" % (package, version, architecture)).encode()
    with tarfile.open(fileobj=out, mode="w:gz") as archive:
        info = tarfile.TarInfo("./control")
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    return out.getvalue()


def ipk(package=updates.PACKAGE_ID, version="0.1.1", architecture="all", outer_tar=False):
    control = control_tar(package, version, architecture)
    if outer_tar:
        out = io.BytesIO()
        with tarfile.open(fileobj=out, mode="w:gz") as archive:
            info = tarfile.TarInfo("./control.tar.gz")
            info.size = len(control)
            archive.addfile(info, io.BytesIO(control))
        return out.getvalue()
    header = ("%-16s%-12s%-6s%-6s%-8s%-10s`\n" % ("control.tar.gz/", 0, 0, 0, "100644", len(control))).encode()
    return b"!<arch>\n" + header + control + (b"\n" if len(control) % 2 else b"")


class ReleaseTests(unittest.TestCase):
    def test_numeric_versions_and_stable_after_development(self):
        self.assertGreater(updates.version_key("1.0.10"), updates.version_key("1.0.9"))
        self.assertGreater(updates.version_key("0.1.0"), updates.version_key("0.1.0-dev1"))
        self.assertGreater(updates.version_key("1.0.0-rc2"), updates.version_key("1.0.0-beta9"))
        for invalid in (None, "", "latest", "1.0.0; reboot", "1.0.0-unknown"):
            with self.assertRaises(updates.UpdateError):
                updates.version_key(invalid)

    def test_only_new_releases_are_offered(self):
        self.assertEqual(updates.parse_release(json.dumps(feed()), "0.1.0-dev1").version, "0.1.1")
        self.assertIsNone(updates.parse_release(json.dumps(feed()), "0.1.1"))
        self.assertIsNone(updates.parse_release(json.dumps(feed()), "0.1.2"))
        empty = feed()
        empty["release"] = None
        self.assertIsNone(updates.parse_release(json.dumps(empty), "0.1.0-dev1"))

    def test_foreign_urls_and_bad_release_records_rejected(self):
        changes = [("url", "https://example.org/file.ipk"), ("tag", "other"),
                   ("sha256", ""), ("bytes", True), ("bytes", updates.MAX_IPK_BYTES + 1),
                   ("version", "0.2.0-dev1")]
        for key, value in changes:
            document = feed()
            document["release"][key] = value
            with self.assertRaises(updates.UpdateError):
                updates.parse_release(json.dumps(document), "0.1.0-dev1")
        for key, value in (("schema", True), ("product", "Other plugin"), ("channel", "development")):
            document = feed()
            document[key] = value
            with self.assertRaises(updates.UpdateError):
                updates.parse_release(json.dumps(document), "0.1.0-dev1")

    def test_manifest_read_is_bounded(self):
        self.assertEqual(updates.check_release("0.1.0", lambda url: io.BytesIO(json.dumps(feed()).encode())).version, "0.1.1")
        with self.assertRaises(updates.UpdateError):
            updates.check_release("0.1.0", lambda url: io.BytesIO(b"x" * 65537))

    def test_https_context_remains_verified(self):
        with patch.object(updates, "urlopen") as opener:
            updates._open("https://github.com")
            context = opener.call_args.kwargs["context"]
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            self.assertTrue(context.check_hostname)

    def test_download_rejects_damage_truncation_and_oversize(self):
        data = b"correct package"
        release = updates.Release("0.1.1", "url", hashlib.sha256(data).hexdigest(), len(data))
        for actual in (data[:-1], data + b"x", b"X" + data[1:]):
            with tempfile.TemporaryDirectory() as folder:
                path = pathlib.Path(folder) / "update.ipk"
                with self.assertRaises(updates.UpdateError):
                    updates.download_release(release, path, lambda *a, **kw: io.BytesIO(actual))
                self.assertFalse(path.exists())

    def test_existing_destination_is_not_deleted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "existing.ipk"
            path.write_bytes(b"preserve")
            with self.assertRaises(FileExistsError):
                updates.download_release(updates.Release("0.1.1", "url", "a" * 64, 1), path)
            self.assertEqual(path.read_bytes(), b"preserve")

    def test_real_control_metadata_both_container_types(self):
        release = updates.Release("0.1.1", "url", "a" * 64, 1)
        for outer_tar in (False, True):
            with tempfile.TemporaryDirectory() as folder:
                path = pathlib.Path(folder) / "update.ipk"
                path.write_bytes(ipk(outer_tar=outer_tar))
                updates.validate_ipk(path, release)
                for data in (ipk(package="other"), ipk(version="0.1.2"), ipk(architecture="aarch64"), b"broken"):
                    path.write_bytes(data)
                    with self.assertRaises(updates.UpdateError):
                        updates.validate_ipk(path, release)

    def test_installer_runs_only_after_integrity_and_identity_checks(self):
        calls = []
        def runner(command, **kwargs):
            calls.append(command)
            return types.SimpleNamespace(returncode=0, stdout="installed")
        data = ipk()
        release = updates.Release("0.1.1", "url", hashlib.sha256(data).hexdigest(), len(data))
        self.assertEqual(updates.install_release(release, lambda *a, **kw: io.BytesIO(data), runner), "0.1.1")
        self.assertEqual(calls[0][:2], ["opkg", "install"])
        self.assertFalse(any("force" in arg or "reboot" in arg for arg in calls[0]))
        bad = updates.Release("0.1.1", "url", "a" * 64, len(data))
        with self.assertRaises(updates.UpdateError):
            updates.install_release(bad, lambda *a, **kw: io.BytesIO(data), runner)
        self.assertEqual(len(calls), 1)

    def test_package_manager_failure_is_not_reported_as_success(self):
        data = ipk()
        release = updates.Release("0.1.1", "url", hashlib.sha256(data).hexdigest(), len(data))
        with self.assertRaises(updates.UpdateError):
            updates.install_release(release, lambda *a, **kw: io.BytesIO(data),
                                    lambda *a, **kw: types.SimpleNamespace(returncode=7, stdout="failed"))


class TranslatedFeedTests(unittest.TestCase):
    def test_translated_notes_are_optional_and_validated(self):
        document=feed("0.1.2")
        document["release"]["notes_i18n"]={"hu":"Magyar","ru":"Русский","en":"English"}
        result=updates.parse_release(json.dumps(document),"0.1.1")
        self.assertEqual(result.notes_i18n["ru"],"Русский")
        for bad in ([],{"en":12},{"en":"x"*8193},{"../../tmp":"text"}):
            document["release"]["notes_i18n"]=bad
            with self.assertRaises(updates.UpdateError):updates.parse_release(json.dumps(document),"0.1.1")


class Timer:
    def __init__(self):
        self.callback, self.running = [], False
    def start(self, *args):
        self.running = True
    def stop(self):
        self.running = False


class Widget:
    def __init__(self,text=""):self.text=text;self.visible=True
    def hide(self):self.visible=False
    def show(self):self.visible=True
    def setText(self,text):self.text=text
    def pageUp(self):pass
    def pageDown(self):pass

class Actions:
    def __init__(self,contexts,actions,priority):self.actions=actions;self.enabled=True
    def setEnabled(self,value):self.enabled=value

class GuiScreen(dict):
    def __init__(self,session):
        super().__init__();self.session=session;self.onLayoutFinish=[];self.onClose=[];self.returned=None
    def close(self,*args):self.returned=args


class NativeMessage(dict):
    TYPE_INFO=0;TYPE_ERROR=1;TYPE_YESNO=2
    def __init__(self,session,text,type=2,default=True,**kwargs):
        super().__init__();self.text=text;self.onClose=[];self.timer=Timer();self.returned=None
        self.list=[('Yes',True),('No',False)] if type==2 else None
        self.selection=default
    def close(self,result=None):self.returned=result
    def cancel(self):self.close(False)
    def select(self):self.close(self.selection if self.list else True)


class StartupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        package = types.ModuleType("warder_update_test_runtime")
        package.__path__ = [str(RUNTIME)]
        modules = {"warder_update_test_runtime": package}
        for name, attribute, value in (
            ("Components.ActionMap", "ActionMap", Actions), ("Components.Label", "Label", Widget),
            ("Components.ScrollLabel", "ScrollLabel", Widget),
            ("Screens.Screen", "Screen", GuiScreen), ("enigma", "eTimer", Timer),
            ("Screens.MessageBox", "MessageBox", NativeMessage)):
            module = types.ModuleType(name)
            setattr(module, attribute, value)
            modules[name] = module
        modules["enigma"].getDesktop=lambda index:types.SimpleNamespace(size=lambda:types.SimpleNamespace(width=lambda:1920,height=lambda:1080))
        cls.desktop_module=modules["enigma"]
        with patch.dict(sys.modules, modules):
            cls.ui = load_module("warder_update_test_runtime.warder_update_ui", RUNTIME / "warder_update_ui.py")
            cls.i18n = sys.modules["warder_update_test_runtime.warder_i18n"]

    def setUp(self):
        language_patch=patch.object(self.i18n,"language_code",return_value="sk")
        language_patch.start();self.addCleanup(language_patch.stop)
        ui_language_patch=patch.object(self.ui,"language_code",return_value="sk")
        ui_language_patch.start();self.addCleanup(ui_language_patch.stop)
        self.tasks, self.opened = [], []
        test = self
        class Worker:
            def __init__(self, target, **kwargs):
                self.target = target
            def start(self):
                test.tasks.append(self.target)
        self.worker = Worker
        session = types.SimpleNamespace(open=lambda *a, **kw: self.opened.append((a, kw)),
                                        openWithCallback=lambda *a, **kw: self.opened.append((a, kw)))
        self.screen = types.SimpleNamespace(onLayoutFinish=[], onClose=[], session=session)
        session.current_dialog = self.screen

    def test_automatic_and_manual_offers_use_the_same_owned_fullscreen_dialog(self):
        import xml.etree.ElementTree as ET
        for manual in (False,True):
            self.opened.clear();check=self.make_check(lambda version:types.SimpleNamespace(version="0.1.17",notes="Changes"))
            check.request(manual=manual);self.tasks.pop()();check.poll()
            self.assertIs(self.opened[0][0][1],self.ui.MessageBox)
        with patch.dict(sys.modules,{"enigma":self.desktop_module}):
            box=self.ui.MessageBox(None,'New version and release notes',type=self.ui.MessageBox.TYPE_YESNO,default=False)
        self.assertEqual(box['text'].text,'New version and release notes')
        box['warderActions'].actions['green']();self.assertFalse(box.returned)
        root=ET.fromstring(box.skin);self.assertEqual(root.get('size'),'1920,1080')
        self.assertIsNotNone(root.find("ePixmap"))
        self.assertIn('WarderPiconHub/images/warder-background.png',box.skin)
        self.assertIn('global.CurrentTime',box.skin)
        self.assertIn('name="key_red"',box.skin)
        self.assertIn('name="key_green"',box.skin)

    def test_noninteractive_notice_and_install_share_the_same_frame(self):
        import xml.etree.ElementTree as ET
        with patch.dict(sys.modules,{"enigma":self.desktop_module}):
            box=self.ui.MessageBox(None,'Restart in 3 seconds',type=self.ui.MessageBox.TYPE_INFO,enable_input=False)
        self.assertFalse(box['warderActions'].enabled)
        self.assertFalse(box['key_red'].visible)
        self.assertFalse(box['key_green'].visible)
        layouts=[ET.fromstring(self.ui.update_skin(1920,1080,kind=k)) for k in ('message','install')]
        self.assertEqual([ET.tostring(n) for n in layouts[0].findall('eLabel')[:5]],
                         [ET.tostring(n) for n in layouts[1].findall('eLabel')[:5]])
        for width,height in ((1920,1080),(1280,720)):
            for kind in ('message','install'):
                root=ET.fromstring(self.ui.update_skin(width,height,kind=kind))
                for element in root:
                    if element.get('position'):
                        x,y=map(int,element.get('position').split(','));w,h=map(int,element.get('size').split(','))
                        self.assertLessEqual(x+w,width);self.assertLessEqual(y+h,height)

    def test_install_failure_keeps_owned_frame_and_only_enables_back_when_done(self):
        import xml.etree.ElementTree as ET
        with patch.dict(sys.modules,{"enigma":self.desktop_module}):
            box=self.ui.PluginInstallScreen(self.screen.session,types.SimpleNamespace(version='0.1.17'))
        self.assertEqual(ET.fromstring(box.skin).get('size'),'1920,1080')
        self.assertNotIn('hint_red',box)
        self.assertFalse(box['key_red'].visible)
        box.finish();self.assertIsNone(box.returned)
        box.results.put((None,'opkg failed'));box.poll()
        self.assertTrue(box['key_red'].visible);self.assertTrue(box['line_red'].visible)
        self.assertIn('opkg failed',box['status'].text)
        self.assertEqual(self.opened,[])
        box.finish();self.assertEqual(box.returned,())

    def test_version_reader_survives_a_file_replacement_gap(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path=pathlib.Path(folder)/"version.txt"
            path.write_text("0.1.7\n")
            with patch.object(self.ui,"_version_path",path):
                self.assertEqual(self.ui.installed_version(),"0.1.7")
                path.unlink()
                self.assertEqual(self.ui.installed_version(),"0.1.7")
                path.write_text("")
                self.assertEqual(self.ui.installed_version(),"0.1.7")
                path.write_text("0.1.8\n")
                self.assertEqual(self.ui.installed_version(),"0.1.8")

    def make_check(self, check=lambda version: None):
        return self.ui.StartupUpdateCheck(self.screen, check=check, timer_factory=Timer, thread_factory=self.worker)

    def test_each_new_launch_checks_again_but_layout_refresh_does_not(self):
        first = self.make_check()
        first.start()
        first.start()
        self.assertEqual(len(self.tasks), 1)
        first.stop()
        second = self.make_check()
        second.start()
        self.assertEqual(len(self.tasks), 2)

    def test_worker_cannot_open_gui_and_result_is_offered_on_gui_tick(self):
        release = types.SimpleNamespace(version="0.1.1", notes="changes")
        check = self.make_check(lambda version: release)
        check.start()
        self.tasks.pop()()
        self.assertEqual(self.opened, [])
        check.poll()
        self.assertEqual(len(self.opened), 1)
        self.assertEqual(self.opened[0][1]["type"], self.ui.MessageBox.TYPE_YESNO)

    def test_current_version_notice_matches_fullhdglass_text_and_line_spacing(self):
        check=self.make_check();check.request(manual=True);self.tasks.pop()();check.poll()
        args,kwargs=self.opened[0]
        self.assertIs(args[0],self.ui.MessageBox)
        self.assertEqual(args[1],self.ui.update_text("current","PiconHub Warder Evolution",current=self.ui.installed_version(),language="sk"))
        self.assertEqual(kwargs['timeout'],6)

    def test_offline_startup_is_silent_and_does_not_close_plugin(self):
        def offline(version):
            raise OSError("offline")
        check = self.make_check(offline)
        check.start()
        self.tasks.pop()()
        check.poll()
        self.assertEqual(self.opened, [])
        self.assertTrue(check.alive)

    def test_closed_screen_discards_delayed_result(self):
        check = self.make_check(lambda version: types.SimpleNamespace(version="0.1.1", notes=""))
        check.start()
        check.stop()
        self.tasks.pop()()
        check.poll()
        self.assertEqual(self.opened, [])
        self.assertFalse(check.timer.running)

    def test_offer_waits_until_parent_screen_is_active(self):
        check = self.make_check(lambda version: types.SimpleNamespace(version="0.1.1", notes=""))
        check.start()
        self.tasks.pop()()
        self.screen.session.current_dialog = object()
        check.poll()
        self.assertEqual(self.opened, [])
        self.screen.session.current_dialog = self.screen
        check.poll()
        self.assertEqual(len(self.opened), 1)

    def test_declining_offer_never_starts_installer(self):
        check = self.make_check()
        check._answer(types.SimpleNamespace(version="0.1.1"), False)
        self.assertEqual(self.opened, [])

    def test_embedded_auto_offer_waits_for_picker_and_uses_no_modal(self):
        notices=[]
        self.screen.show_update_notice=lambda *a,**kw:notices.append((a,kw))
        self.screen.picker=object()
        check=self.make_check(lambda version:types.SimpleNamespace(version="9.0.0",notes="Changes"))
        check.start();self.tasks.pop()();check.poll()
        self.assertEqual(notices,[])
        self.screen.picker=None;check.poll()
        self.assertIn("9.0.0",notices[-1][0][0])
        self.assertEqual(notices[-1][1]["confirm"],"Potvrdiť")
        notices[-1][1]["callback"](False)
        self.assertEqual(self.opened,[])

    def test_embedded_install_success_schedules_restart_only_after_success(self):
        notices=[]
        self.screen.show_update_notice=lambda *a,**kw:notices.append((a,kw))
        with patch.object(self.ui.threading,"Thread",self.worker):
            installer=self.ui.EmbeddedPluginInstall(self.screen,object())
        self.assertFalse(notices[-1][1]["enabled"])
        self.assertFalse(installer.restart_timer.running)
        installer.results.put(("9.0.0",None))
        with patch.object(installer.restart_timer,"start") as start:
            installer.poll();start.assert_called_once_with(3000,True)
        self.assertIn("3 sekundy",notices[-1][0][0])
        self.assertEqual(self.opened,[])
        standby=types.ModuleType("Screens.Standby");standby.TryQuitMainloop=object()
        with patch.dict(sys.modules,{"Screens.Standby":standby}):installer.restart()
        self.assertEqual(self.opened[-1][0],(standby.TryQuitMainloop,3))
        installer.cleanup();self.assertFalse(installer.timer.running)

    def test_embedded_install_failure_stays_readable_without_restart(self):
        notices=[]
        self.screen.show_update_notice=lambda *a,**kw:notices.append((a,kw))
        with patch.object(self.ui.threading,"Thread",self.worker):
            installer=self.ui.EmbeddedPluginInstall(self.screen,object())
        installer.results.put((None,"offline"));installer.poll()
        self.assertIn("offline",notices[-1][0][0])
        self.assertNotIn("enabled",notices[-1][1])
        self.assertFalse(installer.restart_timer.running)
        self.assertEqual(self.opened,[])

    def test_release_notes_follow_language_with_english_fallback(self):
        release=types.SimpleNamespace(notes="Default",notes_i18n={"de":"Deutsch","en":"English"})
        with patch.object(self.ui,"language_code",return_value="de"):
            self.assertEqual(self.ui.localized_notes(release),"Deutsch")
        with patch.object(self.ui,"language_code",return_value="zz"):
            self.assertEqual(self.ui.localized_notes(release),"English")

    def test_success_notice_restarts_gui_after_three_seconds_without_confirmation(self):
        import queue
        opened=[]
        class Installer(dict):
            pass
        installer=Installer(status=types.SimpleNamespace(setText=lambda text:None),key_red=types.SimpleNamespace(show=lambda:None))
        installer.closed=False;installer.done=False;installer.timer=Timer();installer.results=queue.Queue()
        installer.results.put(("0.1.1",None))
        installer.restart_after_notice=lambda *args:self.ui.PluginInstallScreen.restart_after_notice(installer,*args)
        installer.session=types.SimpleNamespace(open=lambda *a,**kw:opened.append((a,kw)),openWithCallback=lambda *a,**kw:opened.append((a,kw)))
        self.ui.PluginInstallScreen.poll(installer)
        args,kwargs=opened.pop()
        self.assertEqual(kwargs["timeout"],3)
        self.assertFalse(kwargs["enable_input"])
        self.assertEqual(kwargs["type"],self.ui.MessageBox.TYPE_INFO)
        self.assertIn("3 sekundy",args[2])
        self.assertEqual(opened,[])
        standby=types.ModuleType("Screens.Standby");standby.TryQuitMainloop=object()
        with patch.dict(sys.modules,{"Screens.Standby":standby}):args[0](True)
        self.assertEqual(opened[0][0],(standby.TryQuitMainloop,3))
        installer.closed=True;opened.clear()
        args[0](True)
        self.assertEqual(opened,[])

    def test_failed_update_does_not_schedule_a_gui_restart(self):
        import queue
        class Installer(dict):
            pass
        installer=Installer(status=types.SimpleNamespace(setText=lambda text:None),key_red=types.SimpleNamespace(show=lambda:None))
        installer.closed=False;installer.done=False;installer.timer=Timer();installer.results=queue.Queue()
        installer.results.put((None,"opkg failed"))
        installer.session=self.screen.session
        self.ui.PluginInstallScreen.poll(installer)
        self.assertEqual(self.opened,[])

    def test_original_entrypoint_contains_the_hook_and_keeps_profiles(self):
        import ast
        source = (RUNTIME / "plugin.py").read_text()
        tree = ast.parse(source)
        screen = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "mainConfigScreen")
        constructor = next(n for n in screen.body if isinstance(n, ast.FunctionDef) and n.name == "__init__")
        self.assertIn("self.warderUpdateCheck = StartupUpdateCheck(self)", ast.get_source_segment(source, constructor))
        self.assertNotIn("_AUTO_CHECK_DONE", source)
        self.assertNotIn("ssl._create_default_https_context =", source)
        self.assertNotIn("def downNinstPlugin", source)
        self.assertIn("ConfigSelectionNumber(1,3,1,default=1)", source)


if __name__ == "__main__":
    unittest.main()
