"""Exercise real screen controllers with Enigma2 components replaced by test doubles."""
import importlib
import pathlib
import sys
import tempfile
import types
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

ROOT=pathlib.Path(__file__).parents[1]/"src/Plugins/Extensions/ChocholousekPicons"


class Setting:
    def __init__(self,default=None,**kwargs):self.value,self.default,self.saves=default,default,0
    def setValue(self,value):self.value=value
    def getValue(self):return self.value
    def save(self):self.saves+=1


class Component:
    def __init__(self,text=""):
        self.text,self.instance,self.visible,self.background,self.filename=text,self,True,None,None
    def setText(self,text):self.text=text
    def setBackgroundColor(self,color):self.background=color
    def setPixmapFromFile(self,path):self.filename=path
    def setScale(self,value):pass
    def setValue(self,value):self.value=value
    def show(self):self.visible=True
    def hide(self):self.visible=False
    def pageUp(self):pass
    def pageDown(self):pass


class Menu(Component):
    def __init__(self,values,**kwargs):
        super().__init__();self.values,self.index=values,0
        self.l=types.SimpleNamespace(setFont=lambda *a:None,setItemHeight=lambda *a:None)
    def setList(self,values):self.values=values;self.index=min(self.index,max(0,len(values)-1))
    def getCurrent(self):return self.values[self.index] if self.values else None
    def getSelectionIndex(self):return self.index
    def moveToIndex(self,index):self.index=max(0,min(index,len(self.values)-1))
    def up(self):self.moveToIndex(self.index-1)
    def down(self):self.moveToIndex(self.index+1)


class Screen:
    def __init__(self,session):self.session,self.widgets,self.onLayoutFinish,self.onClose,self.result=session,{},[],[],None
    def __getitem__(self,key):return self.widgets[key]
    def __setitem__(self,key,value):self.widgets[key]=value
    def applySkin(self):
        # OpenATV Screen.applySkin owns scale and replaces it before callbacks.
        self.scale=((1920,1920),(1080,1080))
        for callback in self.onLayoutFinish:callback()
    def close(self,result=None):
        self.result=result
        for callback in self.onClose:callback()


class Timer:
    def __init__(self):self.callback,self.running=[],False
    def start(self,*args):self.running=True
    def stop(self):self.running=False


class Actions(dict):
    def __init__(self,contexts,actions,priority):super().__init__(actions)


class NativeControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        namespace="warder_native_controller_tests"
        package=types.ModuleType(namespace);package.__path__=[str(ROOT)]
        cls.config=types.SimpleNamespace(plugins=types.SimpleNamespace(),osd=types.SimpleNamespace(language=Setting("sk_SK")))
        cls.configfile=types.SimpleNamespace(save=lambda:None)
        cls.saves=[]
        legacy=types.ModuleType(namespace+".plugin")
        legacy.mainConfigScreen=types.SimpleNamespace(cfgProfileSave=lambda screen,number:cls.saves.append(number))
        startup=types.ModuleType(namespace+".warder_update_ui")
        class Check:
            def __init__(self,screen):screen.onClose.append(self.stop)
            def request(self,manual=False):return True
            def stop(self):pass
        startup.StartupUpdateCheck=Check
        startup.connect_timer=lambda timer,callback:timer.callback.append(callback)
        startup.installed_version=lambda:(ROOT/"version.txt").read_text().strip()
        modules={namespace:package,namespace+".plugin":legacy,namespace+".warder_update_ui":startup}
        attrs={"Components.ActionMap":{"ActionMap":Actions},"Components.Label":{"Label":Component},
               "Components.MenuList":{"MenuList":Menu},"Components.MultiContent":{"MultiContentEntryText":lambda **kwargs:kwargs},
               "Components.Pixmap":{"Pixmap":Component},"Components.ProgressBar":{"ProgressBar":Component},
               "Components.ScrollLabel":{"ScrollLabel":Component},
               "Components.config":{"ConfigSelection":Setting,"ConfigText":Setting,"config":cls.config,"configfile":cls.configfile},
               "Screens.MessageBox":{"MessageBox":types.SimpleNamespace(TYPE_INFO=0,TYPE_ERROR=1,TYPE_YESNO=2)},
               "Screens.Screen":{"Screen":Screen},"skin":{"parseColor":lambda x:x},
               "enigma":{"eTimer":Timer,"gFont":lambda *a:a,"RT_HALIGN_LEFT":1,"RT_VALIGN_CENTER":2,
                         "eListboxPythonMultiContent":object,
                         "getDesktop":lambda unused:types.SimpleNamespace(size=lambda:types.SimpleNamespace(width=lambda:1920,height=lambda:1080))}}
        for name,values in attrs.items():
            module=types.ModuleType(name)
            for key,value in values.items():setattr(module,key,value)
            modules[name]=module
        with patch.dict(sys.modules,modules):cls.gui=importlib.import_module(namespace+".warder_gui")

    def setUp(self):
        profiles=[]
        for number in range(4):
            profiles.append(types.SimpleNamespace(allowed=Setting(number==1),method=Setting("sync_tv"),
                sats=Setting("19.2E 23.5E"),resolution=Setting("220x132"),background=Setting("transparent"),
                picon_folder=Setting("/usr/share/enigma2/picon"),picon_folder_user=Setting("/")))
        self.config.plugins.chocholousekpicons=profiles
        self.config.plugins.chocholousekpicons_id=Setting(1)
        self.saves.clear();self.calls=[]
        self.session=types.SimpleNamespace(open=lambda *a,**kw:self.calls.append((None,a,kw)),
                                           openWithCallback=lambda cb,*a,**kw:self.calls.append((cb,a,kw)))
        self.main=self.gui.WarderMainScreen(self.session)
        self.session.current_dialog=self.main

    def test_all_rows_open_a_picker_without_changing_settings(self):
        before=[p.method.value for p in self.config.plugins.chocholousekpicons]
        for row in range(6):
            self.main["list"].moveToIndex(row);self.main.open_row()
            self.assertIs(self.calls[-1][1][0],self.gui.ChoiceDialog)
        self.assertEqual(self.saves,[])
        self.assertEqual([p.method.value for p in self.config.plugins.chocholousekpicons],before)

    def test_main_opens_after_openatv_skin_sets_scale(self):
        with patch.object(self.gui.threading,"Thread") as worker:
            self.main.applySkin()
        self.assertTrue(self.main.clock_timer.running)
        self.assertEqual(len(self.main["list"].values),6)
        self.assertEqual(self.main.scale,((1920,1920),(1080,1080)))
        self.main.choose("style","white")
        self.main.change_profile(1)
        self.assertEqual(self.main.profile_id,2)
        worker.assert_called_once()
        self.main.cleanup()

    def test_satellite_picker_rebuilds_after_openatv_skin_sets_scale(self):
        dialog=self.gui.ChoiceDialog(self.session,"Satelity",self.gui.model.SATELLITES,["CANALPLUS_SK"],True)
        dialog.applySkin()
        index=next(i for i,x in enumerate(dialog.state.choices) if x[0]=="CANALPLUS_CZ")
        dialog["list"].moveToIndex(index);dialog.accept();dialog.apply()
        self.assertEqual(dialog.result,["CANALPLUS_SK","CANALPLUS_CZ"])
        self.assertEqual(dialog.scale,((1920,1920),(1080,1080)))

    def test_directory_picker_navigates_after_openatv_skin_sets_scale(self):
        with tempfile.TemporaryDirectory() as folder:
            child=pathlib.Path(folder)/"picons";child.mkdir()
            dialog=self.gui.DirectoryDialog(self.session,folder)
            dialog.applySkin()
            dialog["list"].moveToIndex(1);dialog.accept()
            self.assertEqual(dialog.path,child)
            self.assertEqual(dialog.scale,((1920,1920),(1080,1080)))

    def test_cancelled_style_picker_saves_nothing(self):
        self.main["list"].moveToIndex(3);self.main.open_row()
        self.calls[-1][0](None)
        self.assertEqual(self.main.profile.background.value,"transparent")
        self.assertEqual(self.saves,[])

    def test_confirmed_style_changes_only_current_profile(self):
        self.main["list"].moveToIndex(3);self.main.open_row()
        callback,args,kwargs=self.calls[-1]
        self.assertEqual(args[2],self.gui.model.STYLES)
        callback("white")
        self.assertEqual(self.main.profile.background.value,"white")
        self.assertEqual(self.config.plugins.chocholousekpicons[2].background.value,"transparent")
        self.assertEqual(self.saves,[1])

    def test_popup_checkbox_edits_are_local_until_confirmed(self):
        initial=["CANALPLUS_SK"]
        dialog=self.gui.ChoiceDialog(self.session,"Satelity",self.gui.model.SATELLITES,initial,True)
        index=next(i for i,x in enumerate(dialog.state.choices) if x[0]=="CANALPLUS_CZ")
        dialog["list"].moveToIndex(index);dialog.accept()
        self.assertEqual(initial,["CANALPLUS_SK"])
        dialog.apply()
        self.assertEqual(dialog.result,["CANALPLUS_SK","CANALPLUS_CZ"])
        self.main.satellites_chosen(dialog.result)
        self.assertEqual(self.main.profile.warder_selectors.value,"CANALPLUS_SK CANALPLUS_CZ")
        self.assertEqual(self.main.profile.sats.value,"23.5E")

    def test_unoffered_legacy_resolution_is_not_silently_changed(self):
        self.main.profile.resolution.setValue("150x90")
        self.main.refresh()
        self.assertEqual(self.main.profile.resolution.value,"150x90")
        self.main.update_picons()
        self.assertIs(self.calls[-1][1][0],self.gui.MessageBox)

    def test_native_widget_names_match_xml_and_clock_updates(self):
        names={w.get("name") for w in ET.fromstring(self.main.skin) if w.tag=="widget"}
        self.assertTrue(names<=set(self.main.widgets))
        with patch.object(self.gui.model,"clock_text",return_value=("Piatok","23. októbra 2026","10:48","09")):
            self.main.tick()
        self.assertEqual(self.main["clock"].text,"10:48")
        self.assertEqual(self.main["seconds"].text,":09")
        with patch.object(self.gui.model,"clock_text",return_value=("Piatok","23. októbra 2026","10:48","10")):
            self.main.tick()
        self.assertEqual(self.main["seconds"].text,":10")
        self.assertEqual(self.main["version"].text,"v"+(ROOT/"version.txt").read_text().strip())
        self.main.clock_timer.start();self.main.cleanup()
        self.assertFalse(self.main.clock_timer.running)

    def test_profile_navigation_preserves_other_profiles(self):
        self.main.select_profile(2);self.main.choose("method","all_inc")
        self.main.select_profile(1)
        self.assertEqual(self.main.profile.method.value,"sync_tv")
        self.assertEqual(self.config.plugins.chocholousekpicons[2].method.value,"all_inc")

    def test_green_action_uses_the_warder_job_and_native_profiles(self):
        self.main.update_picons()
        callback,args,kwargs=self.calls[-1]
        self.assertIs(args[0],self.gui.PiconJobScreen)
        self.assertEqual(args[1][0]["package_selectors"],["192E","235E"])


if __name__=="__main__":unittest.main()
