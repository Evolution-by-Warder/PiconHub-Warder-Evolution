import copy
import datetime
import hashlib
import importlib
import io
import json
import os
import pathlib
import struct
import sys
import tempfile
import threading
import types
import unittest
import xml.etree.ElementTree as ET
import zipfile
import zlib
from unittest.mock import patch

ROOT=pathlib.Path(__file__).parents[1]/"src/Plugins/Extensions/WarderPiconHub"
package=types.ModuleType("warder_interface_tests")
package.__path__=[str(ROOT)]
sys.modules[package.__name__]=package
model=importlib.import_module(package.__name__+".warder_model")
layout=importlib.import_module(package.__name__+".warder_layout")
engine=importlib.import_module(package.__name__+".warder_engine")
sync=model.sync

NAME="1_0_1_1_1_1_EB0000_0_0_0.png"
STALE="1_0_1_2_1_1_EB0000_0_0_0.png"
OTHER="1_0_1_3_1_1_C00000_0_0_0.png"


def png(rgb=b"\xff\x00\x00",width=220,height=132):
    def chunk(tag,payload):
        return struct.pack(">I",len(payload))+tag+payload+struct.pack(">I",zlib.crc32(tag+payload)&0xffffffff)
    header=chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,2,0,0,0))
    pixels=chunk(b"IDAT",zlib.compress((b"\0"+rgb*width)*height))
    padding=chunk(b"tEXt",b"test\0"+b"x"*(1024-8-len(header)-len(pixels)-12-12-5))
    result=b"\x89PNG\r\n\x1a\n"+header+pixels+padding+chunk(b"IEND",b"")
    assert len(result)==1024
    return result


def fixture(files=None):
    out=io.BytesIO()
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as archive:
        for name,data in (files or {NAME:png()}).items():archive.writestr(name,data)
    data=out.getvalue()
    sha=hashlib.sha256(data).hexdigest()
    filename="warder-test.zip"
    url=sync.publication_source("production")["package_root"]+filename+".part00"
    document={"schema":1,"generated_from":{"repository":"Evolution-by-Warder/PiconHub-Warder-Evolution","ref":"1234567"},"delivery":"raw-github-parts",
              "parts":[{"filename":filename+".part00","bytes":len(data),"sha256":sha}],
              "packages":[{"selector_id":"235E","family":"channel-transparent","resolution":"220x132","filename":filename,"bytes":len(data),"sha256":sha,"parts":[url]}]}
    def opener(address):
        return io.BytesIO(json.dumps(document).encode() if address==sync.RUNTIME_MANIFEST_URL else data)
    return document,data,url,opener


def prefs(destination,mode=sync.UPDATE_MODE_INCREMENTAL):
    value=sync.set_task_position_bindings(sync.default_preferences(),[sync.task_binding_for_package_selector("235E")])
    value.update(style="transparent",resolution="220x132",update_mode=mode,destination=str(destination))
    return value


class MenuTests(unittest.TestCase):
    def setUp(self):
        language_patch=patch.object(sys.modules[layout.__package__+".warder_i18n"],"language_code",return_value="sk")
        language_patch.start();self.addCleanup(language_patch.stop)

    def test_skin_choices_and_provider_identity(self):
        self.assertEqual(tuple(x for x,label in model.RESOLUTIONS),("50x30","220x132","400x240"))
        self.assertEqual(model.STYLES,(("transparent","Transparent"),("white","Biele"),("black","Čierne")))
        self.assertEqual(len(model.SATELLITES),54)
        self.assertEqual(tuple(s for s,label in model.SATELLITES[:2]),("DAB","DVB-T-SK-CZ"))
        self.assertEqual(len({s for s,label in model.SATELLITES}),54)
        self.assertNotIn("SKYLINK",dict(model.SATELLITES))
        self.assertIn("CANALPLUS_SK",dict(model.SATELLITES))
        self.assertIn("CANALPLUS_CZ",dict(model.SATELLITES))

    def test_picker_keeps_working_copy_and_returns_explicit_order(self):
        original=["CANALPLUS_SK"]
        state=model.PickerState(model.SATELLITES,original,True)
        state.toggle("CANALPLUS_CZ")
        self.assertEqual(original,["CANALPLUS_SK"])
        self.assertEqual(state.apply(),["CANALPLUS_SK","CANALPLUS_CZ"])
        state.toggle("CANALPLUS_SK")
        self.assertEqual(state.apply(),["CANALPLUS_CZ"])
        with self.assertRaises(ValueError):state.toggle("invented")

    def test_original_satellite_settings_map_to_existing_ids(self):
        profile=types.SimpleNamespace(sats=types.SimpleNamespace(value="19.2E 23.5E"))
        self.assertEqual(model.initial_selectors(profile),["192E","235E"])

    def test_progress_uses_positions_and_keeps_provider_names_distinct(self):
        self.assertEqual(model.selector_display_label("130E"),"13.0E")
        self.assertEqual(model.selector_display_label("192E"),"19.2E")
        self.assertEqual(model.selector_display_label("235E"),"23.5E")
        self.assertIn("Canal+ SK",model.selector_display_label("CANALPLUS_SK"))
        self.assertIn("Canal+ CZ",model.selector_display_label("CANALPLUS_CZ"))

    def test_live_clock_changes_date_and_localization(self):
        self.assertEqual(model.clock_text(datetime.datetime(2026,10,23,10,48),"sk_SK"),("Piatok","23. októbra 2026","10:48","00"))
        self.assertEqual(model.clock_text(datetime.datetime(2026,10,24,0,0),"sk_SK"),("Sobota","24. októbra 2026","00:00","00"))
        self.assertEqual(model.clock_text(datetime.datetime(2026,10,23,10,48),"cs_CZ")[0],"Pátek")

    def test_native_layouts_have_bounded_widgets_and_live_fields(self):
        for width,height in ((1920,1080),(1280,720)):
            root=ET.fromstring(layout.main_skin(width,height))
            names={item.get("name") for item in root}
            self.assertTrue({"day","date","clock","seconds","version","list","preview"}<=names)
            self.assertFalse({"profile1","profile2","profile3"}&names)
            self.assertTrue({"recent%d" % i for i in range(6)}<=names)
            self.assertNotIn("Nastavenie piconov",layout.main_skin(width,height))
            self.assertTrue({"brand_logo"}<=names)
            self.assertNotIn("profil",layout.main_skin(width,height).lower())
            fields={item.get("name"):item for item in root if item.get("name")}
            self.assertLess(int(fields["seconds"].get("font").split(";")[1]),int(fields["clock"].get("font").split(";")[1]))
            for item in root:
                x,y=map(int,item.get("position").split(","));w,h=map(int,item.get("size").split(","))
                self.assertGreater(w,0);self.assertGreater(h,0)
                self.assertGreaterEqual(x,0);self.assertGreaterEqual(y,0)
                self.assertLessEqual(x+w,width);self.assertLessEqual(y+h,height)
            self.assertNotIn("10:48",layout.main_skin(width,height))
            self.assertNotIn("More channels",layout.main_skin(width,height))
            for count in (1,3,6,53):ET.fromstring(layout.dialog_skin(width,height,count))

    def test_header_seconds_colors_spacing_and_direct_footer_labels(self):
        root=ET.fromstring(layout.main_skin())
        fields={item.get("name"):item for item in root if item.get("name")}
        for name in ("day","date","clock","seconds","version"):
            self.assertEqual(fields[name].get("noWrap"),"1")
        self.assertGreaterEqual(int(fields["date"].get("size").split(",")[0]),400)
        self.assertGreaterEqual(int(fields["day"].get("size").split(",")[0]),270)
        self.assertEqual(fields["seconds"].get("foregroundColor"),"#00ffffff")
        self.assertEqual(fields["version"].get("foregroundColor"),"#003ee8ff")
        self.assertEqual(fields["seconds"].get("font"),"Regular;38")
        self.assertGreaterEqual(int(fields["version"].get("size").split(",")[0]),210)
        self.assertLess(int(fields["clock"].get("position").split(",")[0]),1498)
        self.assertTrue({"key_red","key_green","key_yellow","key_blue"}<=fields.keys())
        self.assertEqual(fields["key_red"].get("foregroundColor"),"#00ff526a")

    def test_multiselect_footer_has_button_colors_and_fits_hd(self):
        for width,height in ((1920,1080),(1280,720)):
            root=ET.fromstring(layout.dialog_skin(width,height,53,multiple=True))
            sw,sh=map(int,root.get("size").split(","))
            fields={item.get("name"):item for item in root}
            self.assertEqual(fields["hint_ok"].get("foregroundColor"),"#00ffffff")
            self.assertEqual(fields["hint_green"].get("foregroundColor"),"#0039ff59")
            self.assertEqual(fields["hint_red"].get("foregroundColor"),"#00ff526a")
            self.assertNotIn("hint",fields)
            for item in root:
                x,y=map(int,item.get("position").split(","));w,h=map(int,item.get("size").split(","))
                self.assertLessEqual(x+w,sw);self.assertLessEqual(y+h,sh)

    def test_all_popup_kinds_have_one_opaque_background_and_bounded_widgets(self):
        for width,height in ((1920,1080),(1280,720)):
            for kind in ("choice","directory","text","progress","install"):
                root=ET.fromstring(layout.dialog_skin(width,height,8,kind=kind))
                sw,sh=map(int,root.get("size").split(","))
                self.assertEqual(root.get("backgroundColor"),layout.POPUP_BACKGROUND)
                self.assertEqual(root.get("flags"),"wfNoBorder")
                for widget in root.findall("widget"):
                    self.assertEqual(widget.get("backgroundColor"),layout.POPUP_BACKGROUND,(kind,widget.get("name")))
                    self.assertEqual(widget.get("transparent"),"0")
                    x,y=map(int,widget.get("position").split(","));w,h=map(int,widget.get("size").split(","))
                    self.assertLessEqual(x+w,sw);self.assertLessEqual(y+h,sh)
                fields={w.get("name"):w for w in root.findall("widget")}
                hints=[w for name,w in fields.items() if name.startswith("hint_")]
                self.assertEqual(len({w.get("size") for w in hints}),1)
                for hint in hints:
                    self.assertEqual(hint.get("halign"),"center")
                    self.assertEqual(hint.get("valign"),"center")
                    self.assertEqual(hint.get("noWrap"),"1")
                self.assertEqual(fields["hint_red"].get("foregroundColor"),"#00ff526a")
                if kind=="progress":
                    self.assertEqual(fields["hint_blue"].get("foregroundColor"),"#0045b9ff")


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=pathlib.Path(self.tmp.name)
        self.target=self.root/"picon"
        self.target.mkdir()

    def tearDown(self):self.tmp.cleanup()

    def run_fixture(self,files=None,mode=sync.UPDATE_MODE_INCREMENTAL,cancel=None):
        document,data,url,opener=fixture(files)
        self.assertEqual(sync.validate_publication_manifest(document),[])
        runner=engine.PiconRunner(opener=opener,cancel=cancel,enigma2_dir=str(self.root/"enigma2"),lock_path=str(self.root/"lock"))
        return runner.run([prefs(self.target,mode)])

    def test_exact_bytes_are_installed_and_identical_files_are_untouched(self):
        self.assertEqual(self.run_fixture(),{"added":1,"changed":0,"removed":0})
        path=self.target/NAME;before=path.stat().st_mtime_ns
        self.assertEqual(path.read_bytes(),png())
        self.assertEqual(self.run_fixture(),{"added":0,"changed":0,"removed":0})
        self.assertEqual(path.stat().st_mtime_ns,before)

    def test_same_size_changed_png_is_updated_by_content(self):
        old=png(b"\x00\xff\x00");new=png()
        self.assertEqual(len(old),len(new))
        (self.target/NAME).write_bytes(old)
        self.assertEqual(self.run_fixture()["changed"],1)
        self.assertEqual((self.target/NAME).read_bytes(),new)

    def test_four_positions_ignore_foreign_aliases_and_install_native_versions(self):
        collision="1_0_1_100A_451_35_C00000_0_0_0.png"
        own={"130E":"1_0_1_1_1_1_820000_0_0_0.png","160E":"1_0_1_1_1_1_A00000_0_0_0.png",
             "192E":collision,"235E":NAME}
        for reverse in (False,True):
            document=fixture()[0];document["parts"]=[];document["packages"]=[];payloads={}
            for sid,name in own.items():
                stream=io.BytesIO()
                with zipfile.ZipFile(stream,"w",zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr(name,png())
                    if sid!="192E":
                        archive.writestr("old/"+collision,png(b"\xff\x00\x00"))
                        archive.writestr("aliases/"+collision,png(b"\x00\x00\xff"))
                data=stream.getvalue();sha=hashlib.sha256(data).hexdigest();filename="test-"+sid+".zip"
                url=sync.publication_source("production")["package_root"]+filename+".part00"
                payloads[url]=data
                document["parts"].append({"filename":filename+".part00","bytes":len(data),"sha256":sha})
                document["packages"].append({"selector_id":sid,"family":"channel-transparent","resolution":"220x132",
                                             "filename":filename,"bytes":len(data),"sha256":sha,"parts":[url]})
            if reverse:document["packages"].reverse()
            self.assertEqual(sync.validate_publication_manifest(document),[])
            def opener(url):return io.BytesIO(json.dumps(document).encode() if url==sync.RUNTIME_MANIFEST_URL else payloads[url])
            value=sync.set_task_position_bindings(prefs(self.target),[sync.task_binding_for_package_selector(sid) for sid in own])
            events=[]
            runner=engine.PiconRunner(opener=opener,event=lambda *args:events.append(args),lock_path=str(self.root/"lock"))
            result=runner.run([value])
            self.assertEqual(result,{"added":4 if not reverse else 0,"changed":0,"removed":0})
            for name in own.values():self.assertEqual((self.target/name).read_bytes(),png())
            self.assertTrue(any(e[0]=="download" and e[1]=="13.0E" for e in events))
            self.assertTrue(any(e[0]=="stage" and "13.0E" in e[1] for e in events))
            self.assertEqual(sum(e[1]["foreign_picons_ignored"] for e in events if e[0]=="package-filter"),6)

    def test_foreign_only_archive_cannot_delete_selected_position_files(self):
        (self.target/STALE).write_bytes(png())
        with self.assertRaises(engine.PiconError):self.run_fixture({OTHER:png()},sync.UPDATE_MODE_REPLACE_ALL)
        self.assertEqual((self.target/STALE).read_bytes(),png())
        self.assertFalse((self.target/OTHER).exists())

    def test_native_conflicting_images_still_abort_before_changes(self):
        (self.target/NAME).write_bytes(png())
        files={"old/"+NAME:png(),"new/"+NAME:png(b"\x00\x00\xff")}
        with self.assertRaises(engine.PiconError):self.run_fixture(files)
        self.assertEqual((self.target/NAME).read_bytes(),png())

    def test_replace_prunes_only_selected_orbits_and_native_service_names(self):
        for name in (STALE,OTHER,"my-logo.png"):(self.target/name).write_bytes(png())
        result=self.run_fixture(mode=sync.UPDATE_MODE_REPLACE_ALL)
        self.assertEqual(result["removed"],1)
        self.assertFalse((self.target/STALE).exists())
        self.assertTrue((self.target/OTHER).exists())
        self.assertTrue((self.target/"my-logo.png").exists())

    def test_bouquet_sync_installs_only_selected_services(self):
        e2=self.root/"enigma2";e2.mkdir()
        (e2/"bouquets.tv").write_text('#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.test.tv" ORDER BY bouquet\n')
        (e2/"userbouquet.test.tv").write_text('#SERVICE '+NAME[:-4].replace("_",":")+':\n')
        (self.target/STALE).write_bytes(png())
        result=self.run_fixture({NAME:png(),STALE:png()},sync.UPDATE_MODE_SYNC_TV)
        self.assertEqual(result,{"added":1,"changed":0,"removed":1})
        self.assertFalse((self.target/STALE).exists())

    def test_empty_bouquets_never_delete_existing_files(self):
        (self.target/STALE).write_bytes(png())
        with self.assertRaises(engine.PiconError):self.run_fixture(mode=sync.UPDATE_MODE_SYNC_TV)
        self.assertEqual((self.target/STALE).read_bytes(),png())

    def test_corrupt_download_cannot_trigger_replace_deletion(self):
        document,data,url,opener=fixture()
        (self.target/STALE).write_bytes(png())
        def corrupt(address):return opener(address) if address==sync.RUNTIME_MANIFEST_URL else io.BytesIO(data[:-1])
        with self.assertRaises(engine.PiconError):
            engine.PiconRunner(opener=corrupt,lock_path=str(self.root/"lock")).run([prefs(self.target,sync.UPDATE_MODE_REPLACE_ALL)])
        self.assertEqual((self.target/STALE).read_bytes(),png())

    def test_unsafe_zip_members_and_wrong_png_dimensions_are_rejected(self):
        for files in ({"../"+NAME:png()},{NAME:png(width=132,height=220)}):
            with self.assertRaises(engine.PiconError):self.run_fixture(files)
            self.assertEqual(list(self.target.glob("*.png")),[])

    def test_symlink_is_replaced_without_touching_its_target(self):
        other=self.root/"keep";other.write_bytes(b"keep")
        (self.target/NAME).symlink_to(other)
        result=self.run_fixture()
        self.assertEqual(result,{"added":0,"changed":1,"removed":0})
        self.assertEqual(other.read_bytes(),b"keep")
        self.assertFalse((self.target/NAME).is_symlink())
        self.assertEqual((self.target/NAME).read_bytes(),png())

    def test_dangling_symlink_is_replaced_and_missing_target_is_not_created(self):
        other=self.root/"missing"
        (self.target/NAME).symlink_to(other)
        self.assertEqual(self.run_fixture()["changed"],1)
        self.assertFalse(other.exists())
        self.assertFalse((self.target/NAME).is_symlink())
        self.assertEqual((self.target/NAME).read_bytes(),png())

    def test_write_failure_restores_valid_and_dangling_relative_symlinks(self):
        other=self.root/"keep";other.write_bytes(b"keep")
        for destination in ('../keep','../missing'):
            path=self.target/NAME
            path.unlink(missing_ok=True);path.symlink_to(destination)
            real_replace=os.replace
            def fail_ready(source,target):
                if pathlib.Path(source).parent.name=="ready":raise OSError("injected write failure")
                return real_replace(source,target)
            with patch.object(engine.os,"replace",side_effect=fail_ready):
                with self.assertRaises(OSError):self.run_fixture()
            self.assertTrue(path.is_symlink());self.assertEqual(os.readlink(path),destination)
            self.assertEqual(other.read_bytes(),b"keep")
            self.assertFalse((self.root/'missing').exists())

    def test_directory_at_picon_path_is_preserved(self):
        (self.target/NAME).mkdir()
        (self.target/NAME/'keep').write_text('safe')
        with self.assertRaises(engine.PiconError):self.run_fixture()
        self.assertEqual((self.target/NAME/'keep').read_text(),'safe')

    def test_sync_removes_only_the_stale_link_not_its_target(self):
        other=self.root/'outside';other.write_bytes(b'safe')
        (self.target/STALE).symlink_to(other)
        self.assertEqual(self.run_fixture(mode=sync.UPDATE_MODE_REPLACE_ALL)['removed'],1)
        self.assertFalse((self.target/STALE).is_symlink())
        self.assertEqual(other.read_bytes(),b'safe')

    def test_cancel_before_commit_preserves_existing_files(self):
        event=threading.Event();event.set()
        (self.target/STALE).write_bytes(png())
        with self.assertRaises(engine.Cancelled):self.run_fixture(cancel=event)
        self.assertEqual((self.target/STALE).read_bytes(),png())

    def test_failed_file_replace_restores_original_bytes(self):
        original=png(b"\x00\xff\x00")
        (self.target/NAME).write_bytes(original)
        real_replace=os.replace
        def fail_ready(source,target):
            if pathlib.Path(source).parent.name=="ready":raise OSError("injected write failure")
            return real_replace(source,target)
        with patch.object(engine.os,"replace",side_effect=fail_ready):
            with self.assertRaises(OSError):self.run_fixture()
        self.assertEqual((self.target/NAME).read_bytes(),original)

    def test_archive_without_picons_cannot_erase_selected_position(self):
        (self.target/STALE).write_bytes(png())
        with self.assertRaises(engine.PiconError):
            self.run_fixture({"README.txt":b"empty"},sync.UPDATE_MODE_REPLACE_ALL)
        self.assertEqual((self.target/STALE).read_bytes(),png())

    def test_second_profile_failure_rolls_back_first_profile(self):
        original=png(b"\x00\xff\x00")
        (self.target/NAME).write_bytes(original)
        second=self.root/"second";second.mkdir();(second/NAME).write_bytes(original)
        document,data,url,opener=fixture()
        real_replace=os.replace
        def fail_second(source,target):
            if pathlib.Path(source).parent.name=="ready" and pathlib.Path(target).parent==second:
                raise OSError("second profile failed")
            return real_replace(source,target)
        with patch.object(engine.os,"replace",side_effect=fail_second):
            with self.assertRaises(OSError):
                engine.PiconRunner(opener=opener,lock_path=str(self.root/"lock")).run([prefs(self.target),prefs(second)])
        self.assertEqual((self.target/NAME).read_bytes(),original)
        self.assertEqual((second/NAME).read_bytes(),original)

    def test_failed_rollback_keeps_backup_for_recovery(self):
        original=png(b"\x00\xff\x00")
        (self.target/NAME).write_bytes(original)
        queue={"destination":str(self.target),"positions":["23.5e"],"mode":sync.UPDATE_MODE_INCREMENTAL}
        stage=engine.Stage(queue)
        (stage.ready/NAME).write_bytes(png());stage.hashes[NAME]=hashlib.sha256(png()).hexdigest()
        real_replace=os.replace
        def cannot_restore(source,target):
            if pathlib.Path(source).parent.name in ("ready","backup"):raise OSError("filesystem failure")
            return real_replace(source,target)
        with patch.object(engine.os,"replace",side_effect=cannot_restore):
            with self.assertRaises(engine.PiconError):stage.apply()
        stage.cleanup()
        self.assertTrue(stage.keep)
        self.assertEqual((stage.backup/NAME).read_bytes(),original)

    def test_native_plugin_entrypoint_opens_the_modern_screen(self):
        source=(ROOT/"plugin.py").read_text()
        self.assertIn("session.open(WarderMainScreen)",source)
        self.assertIn("p.method = ConfigSelection",source)
        gui=(ROOT/"warder_gui.py").read_text()
        self.assertIn("self.warderUpdateCheck=StartupUpdateCheck(self)",gui)


if __name__=="__main__":unittest.main()
