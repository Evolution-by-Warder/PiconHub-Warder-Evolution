"""Exercise real screen controllers with Enigma2 components replaced by test doubles."""
import importlib
import pathlib
import sys
import tempfile
import types
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

ROOT=pathlib.Path(__file__).parents[1]/"src/Plugins/Extensions/WarderPiconHub"


class Setting:
    def __init__(self,default=None,**kwargs):self.value,self.default,self.saves=default,default,0
    def setValue(self,value):self.value=value
    def getValue(self):return self.value
    def save(self):self.saves+=1


class Component:
    def __init__(self,text=""):
        self.text,self.instance,self.visible,self.background,self.filename=text,self,True,None,None
    def setText(self,text,showBottom=False):self.text=text;self.showBottom=showBottom
    def setBackgroundColor(self,color):self.background=color
    def setPixmapFromFile(self,path):self.filename=path
    def setScale(self,value):pass
    def setAlphatest(self,value):pass
    def resize(self,size):self.dimensions=size
    def move(self,point):self.location=point
    def size(self):return types.SimpleNamespace(width=lambda:440,height=lambda:264)
    def setValue(self,value):self.value=value
    def show(self):self.visible=True
    def hide(self):self.visible=False
    def pageUp(self):pass
    def pageDown(self):pass
    def isAtLastPage(self):return True
    def setPos(self,value):self.currentPosition=value


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
        attrs={"Components.GUIComponent":{"GUIComponent":Component},"Components.ActionMap":{"ActionMap":Actions},"Components.Label":{"Label":Component},
               "Components.MenuList":{"MenuList":Menu},"Components.MultiContent":{"MultiContentEntryText":lambda **kwargs:kwargs,"MultiContentEntryPixmapAlphaBlend":lambda **kwargs:kwargs},"Tools.LoadPixmap":{"LoadPixmap":lambda **kwargs:kwargs},
               "Components.Pixmap":{"Pixmap":Component},"Components.ProgressBar":{"ProgressBar":Component},
               "Components.ScrollLabel":{"ScrollLabel":Component},
               "Components.config":{"ConfigSelection":Setting,"ConfigText":Setting,"config":cls.config,"configfile":cls.configfile},
               "Screens.MessageBox":{"MessageBox":types.SimpleNamespace(TYPE_INFO=0,TYPE_ERROR=1,TYPE_YESNO=2)},
               "Screens.Screen":{"Screen":Screen},"skin":{"parseColor":lambda x:x},
               "enigma":{"BT_SCALE":1,"ePixmap":Component,"eWidget":Component,"ePoint":lambda *v:v,"eSize":lambda *v:v,"eTimer":Timer,"gFont":lambda *a:a,"RT_HALIGN_LEFT":1,"RT_VALIGN_CENTER":2,
                         "eListboxPythonMultiContent":object,
                         "getDesktop":lambda unused:types.SimpleNamespace(size=lambda:types.SimpleNamespace(width=lambda:1920,height=lambda:1080))}}
        for name,values in attrs.items():
            module=types.ModuleType(name)
            for key,value in values.items():setattr(module,key,value)
            modules[name]=module
        with patch.dict(sys.modules,modules):
            cls.gui=importlib.import_module(namespace+".warder_gui")
            cls.i18n=sys.modules[namespace+".warder_i18n"]

    def setUp(self):
        self.config.osd.language.value="sk_SK"
        language_patch=patch.object(self.i18n,"language_code",lambda:self.config.osd.language.value.split("_")[0])
        language_patch.start();self.addCleanup(language_patch.stop)
        gui_language_patch=patch.object(self.gui,"language_code",lambda:self.i18n.language_code())
        gui_language_patch.start();self.addCleanup(gui_language_patch.stop)
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
        worker_patch=patch.object(self.gui.threading,"Thread")
        worker_patch.start();self.addCleanup(worker_patch.stop)
        self.main=self.gui.WarderMainScreen(self.session)
        self.session.current_dialog=self.main

    def complete_selection(self):
        self.main.satellites_chosen(["192E","235E"])
        for key,value in (("resolution","220x132"),("style","transparent"),("method","sync_tv"),("destination","/media/hdd/picon")):
            self.main.choose(key,value)

    def test_startup_is_neutral_even_with_saved_settings_and_reopens_neutral(self):
        self.assertEqual([row[0][2] for row in self.main["list"].values],["Vyber si…"]*5)
        self.assertTrue(self.main["brand_logo"].visible)
        self.assertFalse(self.main["preview"].visible)
        self.assertTrue(self.main["brand_logo"].picture.filename.endswith("warder-emblem.png"))
        self.main.update_picons()
        self.assertIsNotNone(self.main.panel)
        self.assertEqual(self.calls,[])
        self.main.exit()
        self.complete_selection()
        other=self.gui.WarderMainScreen(self.session)
        self.assertEqual([row[0][2] for row in other["list"].values],["Vyber si…"]*5)
        self.assertTrue(other["brand_logo"].visible)
        self.assertEqual(self.main.profile.picon_folder_user.value,"/media/hdd/picon")

    def test_partial_selection_preview_follows_background_and_native_resolution(self):
        self.main.choose("resolution","400x240")
        self.assertTrue(self.main["brand_logo"].visible)
        self.main.choose("style","black")
        self.assertFalse(self.main["brand_logo"].visible)
        self.assertTrue(self.main["preview"].visible)
        self.assertTrue(self.main["preview"].filename.endswith("preview-black.png"))
        self.assertEqual(self.main["preview"].dimensions,(400,240))
        self.assertIn("400×240",self.main["preview_caption"].text)
        self.main.choose("resolution","50x30")
        self.assertEqual(self.main["preview"].dimensions,(50,30))
        self.main.update_picons()
        self.assertIsNotNone(self.main.panel)
        self.assertEqual(self.calls,[])
        self.main.exit()
        self.assertEqual(self.main.selection["satellites"],None)

    def test_footer_actions_open_plugin_update_about_and_close_directly(self):
        with patch.object(self.main.warderUpdateCheck,"request") as request:
            self.main["actions"]["yellow"]()
            request.assert_called_once_with(manual=True)
        self.main["actions"]["blue"]()
        self.assertEqual(self.main["picker_title"].text,"O projekte")
        self.assertEqual(self.calls,[])
        self.main.exit()
        self.main["actions"]["red"]()
        self.assertTrue(self.main.closed)

    def test_all_rows_open_a_picker_without_changing_settings(self):
        before=[p.method.value for p in self.config.plugins.chocholousekpicons]
        for row in range(5):
            self.main["list"].moveToIndex(row);self.main.open_row()
            self.assertIsNotNone(self.main.picker)
            self.assertTrue(self.main["picker_title"].visible)
            self.assertEqual(self.main["list"].location,(70,410))
            self.assertEqual(self.calls,[])
            self.main.exit()
            self.assertEqual(self.main["list"].getSelectionIndex(),row)
        self.assertEqual(self.saves,[])
        self.assertEqual([p.method.value for p in self.config.plugins.chocholousekpicons],before)

    def test_embedded_satellite_cancel_discards_and_green_commits(self):
        self.main.satellites_chosen(["FREESAT"])
        self.main.select_satellites()
        self.assertEqual(self.main["list"].values[0][1]["color"],0x0039ff59)
        self.main.open_row()
        self.main.exit()
        self.assertEqual(self.main.selection["satellites"],["FREESAT"])
        self.main.select_satellites()
        self.main["list"].moveToIndex(1);self.main.open_row();self.main.green_action()
        self.assertEqual(self.main.selection["satellites"],["FREESAT",self.gui.model.SATELLITES[1][0]])
        self.assertIsNone(self.main.picker)
        self.assertFalse(self.main.closed)
        self.assertEqual(self.calls,[])

    def test_embedded_single_selection_restores_row_and_footer(self):
        self.main["list"].moveToIndex(1);self.main.open_row()
        self.main["list"].moveToIndex(2);self.main.open_row()
        self.assertEqual(self.main.selection["resolution"],"400x240")
        self.assertEqual(self.main["list"].getSelectionIndex(),1)
        self.assertEqual(self.main["list"].location,(70,350))
        self.assertEqual(self.main["list"].dimensions,(1120,500))
        self.assertEqual(self.main["key_green"].text,"Stiahnuť")
        self.assertFalse(self.main["picker_cover"].visible)
        self.assertEqual(self.calls,[])

    def test_update_notice_uses_left_panel_and_blocks_install_exit(self):
        answers=[]
        self.main["list"].moveToIndex(3)
        self.main.show_update_notice("New version",callback=answers.append,confirm="Potvrdiť")
        self.assertFalse(self.main["list"].visible)
        self.assertTrue(self.main["panel_text"].visible)
        self.main.open_row()
        self.assertEqual(answers,[])
        self.main.green_action()
        self.assertEqual(answers,[True])
        self.assertEqual(self.main["list"].getSelectionIndex(),3)
        self.main.show_update_notice("Installing",enabled=False)
        self.main.exit();self.main.green_action();self.main.open_row()
        self.assertIsNotNone(self.main.panel)
        self.assertFalse(self.main.closed)
        self.assertFalse(self.main["key_red"].visible)
        self.main.show_update_notice("Failed")
        self.main.exit()
        self.assertIsNone(self.main.panel)
        self.assertEqual(self.calls,[])

    def test_embedded_custom_directory_navigates_and_cancels_without_saving(self):
        with tempfile.TemporaryDirectory() as folder:
            child=pathlib.Path(folder)/"picon";child.mkdir()
            self.main.open_directory(folder)
            self.main["list"].moveToIndex(1);self.main.open_row()
            self.assertEqual(self.main.picker_path,child)
            self.main.exit()
            self.assertIsNone(self.main.selection["destination"])
            self.main.open_directory(str(child))
            self.main.green_action()
            self.assertEqual(self.main.selection["destination"],str(child))
            self.assertEqual(self.calls,[])

    def test_main_opens_after_openatv_skin_sets_scale(self):
        with patch.object(self.gui.threading,"Thread") as worker:
            self.main.applySkin()
        self.assertTrue(self.main.clock_timer.running)
        self.assertEqual(len(self.main["list"].values),5)
        self.assertEqual(self.main.scale,((1920,1920),(1080,1080)))
        self.main.choose("style","white")
        self.assertEqual(self.main.profile_id,1)
        self.assertEqual(worker.call_count,2)
        self.main.cleanup()

    def test_satellite_picker_rebuilds_after_openatv_skin_sets_scale(self):
        dialog=self.gui.ChoiceDialog(self.session,"Satelity",self.gui.model.SATELLITES,["CANALPLUS_SK"],True)
        dialog.applySkin()
        index=next(i for i,x in enumerate(dialog.state.choices) if x[0]=="CANALPLUS_CZ")
        dialog["list"].moveToIndex(index);dialog.accept();dialog.apply()
        self.assertEqual(dialog.result,["CANALPLUS_SK","CANALPLUS_CZ"])
        self.assertEqual(dialog.scale,((1920,1920),(1080,1080)))

    def test_satellite_icons_green_marks_and_colored_footer(self):
        dialog=self.gui.ChoiceDialog(self.session,"Satelity",self.gui.model.SATELLITES,["FREESAT"],True)
        self.assertEqual(len(dialog.icons),53)
        row=dialog["list"].values[0]
        self.assertEqual(row[0][0],"FREESAT")
        self.assertEqual(row[1]["text"],"●")
        self.assertEqual(row[1]["color"],0x0039ff59)
        self.assertEqual(row[1]["color_sel"],0x0039ff59)
        self.assertIn("png",row[2])
        self.assertEqual(dialog["hint_ok"].text,"Vybrať s OK")
        self.assertEqual(dialog["hint_green"].text,"Potvrdiť výber")
        self.assertEqual(dialog["hint_red"].text,"Naspäť")
        dialog.accept()
        self.assertEqual(dialog["list"].values[0][1]["text"],"○")
        dialog["actions"]["red"]()
        self.assertIsNone(dialog.result)

    def test_reopened_interface_translates_without_changing_selection_ids(self):
        for code,label,white in (("en_GB","Satellites","White"),("de_DE","Satelliten","Weiß"),("pl_PL","Satelity","Białe"),("cs_CZ","Satelity","Bílé"),("hu_HU","Műholdak","Fehér"),("ru_RU","Спутники","Белый"),("fr_FR","Satellites","Blanc"),("it_IT","Satelliti","Bianco"),("es_ES","Satélites","Blanco")):
            self.config.osd.language.value=code
            main=self.gui.WarderMainScreen(self.session)
            self.assertEqual(main["list"].values[0][0][0],"satellites")
            self.assertEqual(main["list"].values[0][0][1],label)
            main.choose("style","white")
            self.assertIn(white,main["preview_caption"].text)
            dialog=self.gui.ChoiceDialog(self.session,"Pozadie",self.gui.model.STYLES)
            row=dialog["list"].values[1]
            self.assertEqual(row[0][0],"white")
            self.assertEqual(row[-1]["text"],white)
            main.cleanup()

    def test_job_footer_is_colored_and_red_waits_for_safe_completion(self):
        job=self.gui.PiconJobScreen(self.session,[])
        self.assertEqual(job["hint_red"].text,"Naspäť")
        self.assertEqual(job["hint_blue"].text,"Log")
        with patch.object(job,"close") as close:
            job["actions"]["red"]()
            self.assertTrue(job.cancel.is_set());close.assert_not_called()
            self.assertIn("bezpečné",job["status"].text)
            job.events.put(("result",{"added":1,"changed":2,"removed":0}))
            job.poll()
            self.assertTrue(job.done)
            self.assertIn("Dokončené",job["status"].text)
            self.assertEqual(job["hint_red"].text,"Naspäť")
            job["actions"]["blue"]()
            self.assertIs(self.calls[-1][1][0],self.gui.TextDialog)
            job["actions"]["red"]();close.assert_called_once()
        job.cleanup()

    def test_four_satellite_phases_accumulate_in_one_window(self):
        job=self.gui.PiconJobScreen(self.session,[])
        calls=len(self.calls)
        for label in ('13.0E','16.0E','19.2E','23.5E'):
            for count in (0,50,100):
                job.events.put(('download',label,count,100));job.poll()
            job.events.put(('stage','Overujem a rozbaľujem '+label));job.poll()
            job.events.put(('processed',label));job.poll()
        self.assertEqual(len(job.history),8)
        for index,label in enumerate(('13.0E','16.0E','19.2E','23.5E')):
            self.assertEqual(job.history[2*index],'Sťahujem '+label+' • 100 %')
            self.assertEqual(job.history[2*index+1],'Overujem a rozbaľujem '+label+' ✓')
        self.assertEqual(len(self.calls),calls)
        self.assertTrue(job['status'].showBottom)
        job['actions']['up']();self.assertFalse(job.follow_progress)
        job['status'].currentPosition=42
        job.events.put(('stage','Zapisujem overené picony'));job.poll()
        self.assertFalse(job['status'].showBottom)
        self.assertEqual(job['status'].currentPosition,42)
        job['actions']['down']();self.assertTrue(job.follow_progress)
        job.events.put(('result',{'added':4,'changed':1,'removed':0}));job.poll()
        self.assertIn('13.0E',job['status'].text)
        self.assertIn('Dokončené',job['status'].text)
        self.assertEqual(len(self.calls),calls)
        job.cleanup()

    def test_error_keeps_download_and_processing_history_in_the_same_window(self):
        job=self.gui.PiconJobScreen(self.session,[])
        job.events.put(('download','13.0E',100,100))
        job.events.put(('stage','Overujem a rozbaľujem 13.0E'))
        job.events.put(('error','Injected failure'))
        job.poll()
        self.assertIn('Sťahujem 13.0E • 100 %',job['status'].text)
        self.assertIn('Overujem a rozbaľujem 13.0E',job['status'].text)
        self.assertIn('Injected failure',job['status'].text)
        self.assertTrue(job.done);self.assertFalse(job.timer.running)
        job.cleanup()

    def test_successful_job_returns_to_empty_first_row_and_default_preview(self):
        self.complete_selection()
        self.main['list'].moveToIndex(4)
        stored=(self.main.profile.sats.value,self.main.profile.resolution.value,
                self.main.profile.background.value,self.main.profile.method.value)
        self.main.update_picons()
        job=self.main.job
        self.assertEqual(self.calls,[])
        job.events.put(('result',{'added':1,'changed':0,'removed':0}));job.poll()
        self.assertEqual(sum(bool(v) for v in self.main.selection.values()),5)
        job.finish();self.assertIsNone(self.main.job)
        self.assertTrue(all(v is None for v in self.main.selection.values()))
        self.assertEqual(self.main['list'].getSelectionIndex(),0)
        self.assertTrue(all(row[0][2]=='Vyber si…' for row in self.main['list'].values))
        self.assertIn('0 z 5',self.main['summary'].text)
        self.assertFalse(self.main['preview'].visible)
        self.assertTrue(self.main['brand_logo'].visible)
        self.assertEqual(stored,(self.main.profile.sats.value,self.main.profile.resolution.value,
                                self.main.profile.background.value,self.main.profile.method.value))

    def test_failed_job_preserves_choices_for_retry(self):
        self.complete_selection();before=dict(self.main.selection)
        self.main['list'].moveToIndex(3)
        self.main.update_picons();job=self.main.job
        job.events.put(('error','injected failure'));job.poll();job.finish()
        self.assertFalse(job.success);self.assertIsNone(self.main.job)
        self.assertEqual(self.main.selection,before)
        self.assertEqual(self.main['list'].getSelectionIndex(),3)
        self.main.picon_job_finished(None)
        self.assertEqual(self.main.selection,before)

    def test_embedded_job_accumulates_all_positions_and_shows_progress(self):
        self.complete_selection();self.main.update_picons();job=self.main.job
        for name in ('13.0E','16.0E','19.2E','23.5E'):
            job.events.put(('stage','Downloading '+name))
            job.events.put(('download',name,50,100));job.poll()
            self.assertEqual(self.main['panel_progress'].value,50)
            self.assertTrue(self.main['panel_progress'].visible)
            job.events.put(('stage','Processing '+name));job.events.put(('processed',name))
            job.poll()
        text=self.main['panel_text'].text
        for name in ('13.0E','16.0E','19.2E','23.5E'):
            self.assertIn('Processing '+name+' ✓',text)
        self.assertTrue(self.main['panel_text'].showBottom)
        self.assertFalse(self.main['list'].visible)
        self.assertEqual(self.main['key_blue'].text,'Log')
        self.assertEqual(self.calls,[])

    def test_embedded_log_returns_to_latest_progress_without_cancelling(self):
        self.complete_selection();self.main.update_picons();job=self.main.job
        self.main.about()
        self.assertTrue(job.view_log)
        self.assertEqual(self.main['picker_title'].text,'Log aktualizácie')
        job.events.put(('stage','New progress while reading log'));job.poll()
        self.assertNotIn('New progress while reading log',self.main['panel_text'].text)
        self.main.exit()
        self.assertFalse(job.view_log);self.assertFalse(job.cancel.is_set())
        self.assertIn('New progress while reading log',self.main['panel_text'].text)
        self.assertEqual(self.calls,[])

    def test_embedded_cancel_waits_for_worker_and_blocks_duplicate_jobs(self):
        self.complete_selection();self.main.update_picons();job=self.main.job
        self.main.start_picon_job([]);self.assertIs(self.main.job,job)
        self.main.exit()
        self.assertTrue(job.cancel.is_set());self.assertIs(self.main.job,job)
        self.assertFalse(self.main.closed)
        job.events.put(('error','Cancelled'));job.poll();self.main.exit()
        self.assertIsNone(self.main.job)
        self.assertIsNone(self.main.panel)
        self.assertTrue(self.main['list'].visible)
        self.assertNotIn(job.cleanup,self.main.onClose)

    def test_replace_confirmation_starts_job_with_the_same_reset_callback(self):
        self.complete_selection();self.main.choose('method','all')
        self.main.update_picons()
        self.assertIsNotNone(self.main.panel["callback"])
        self.main.exit();self.assertIsNone(self.main.job)
        self.main.update_picons();self.main.green_action()
        self.assertIsInstance(self.main.job,self.gui.EmbeddedPiconJob)
        self.assertEqual(self.calls,[])

    def test_about_shows_credits_and_offline_installed_notes_in_system_language(self):
        import json
        with tempfile.TemporaryDirectory() as folder:
            root=pathlib.Path(folder);(root/'data').mkdir()
            (root/'data/release-notes.json').write_text(json.dumps({
                'version':self.gui.installed_version(),
                'notes':{'sk':'Opravené sťahovanie.','en':'Improved downloads.'}}))
            with patch.object(self.gui,'ROOT',root):
                self.main.about()
                text=self.main['panel_text'].text
                self.assertEqual(self.calls,[])
                self.assertIn('Plugin vychádza z práce s3n0 a Chocholousek.',text)
                self.assertIn('Zmeny v tejto verzii:\nOpravené sťahovanie.',text)
                self.main.exit()
                self.config.osd.language.value='en_GB'
                self.main.about()
                text=self.main['panel_text'].text
                self.assertIn('work of s3n0 and Chocholousek.',text)
                self.assertIn('Changes in this version:\nImproved downloads.',text)

    def test_text_dialog_uses_red_to_return(self):
        dialog=self.gui.TextDialog(self.session,"O projekte","PiconHub")
        self.assertEqual(dialog["hint_red"].text,"Naspäť")
        self.assertIn("red",dialog["actions"])
        closed=[];dialog.onClose.append(lambda:closed.append(True))
        dialog["actions"]["red"]()
        self.assertEqual(closed,[True])

    def test_recent_worker_results_are_displayed_only_on_gui_tick(self):
        paths=self.gui.recent.bundled(ROOT)
        with patch.object(self.gui.recent,"load_recent",return_value=paths):
            self.main.refresh_recent()
        self.assertIsNone(self.main["recent0"].filename)
        self.main.tick()
        for number,path in enumerate(paths):
            self.assertEqual(self.main["recent%d" % number].filename,str(path))
        self.main.cleanup()
        self.main.recent_results.put([])
        self.main.tick()
        self.assertTrue(self.main["recent0"].visible)

    def test_directory_picker_navigates_after_openatv_skin_sets_scale(self):
        with tempfile.TemporaryDirectory() as folder:
            child=pathlib.Path(folder)/"picons";child.mkdir()
            dialog=self.gui.DirectoryDialog(self.session,folder)
            dialog.applySkin()
            dialog["list"].moveToIndex(1);dialog.accept()
            self.assertEqual(dialog.path,child)
            self.assertEqual(dialog.scale,((1920,1920),(1080,1080)))

    def test_cancelled_style_picker_saves_nothing(self):
        self.main["list"].moveToIndex(2);self.main.open_row()
        self.main.exit()
        self.assertEqual(self.main.profile.background.value,"transparent")
        self.assertEqual(self.saves,[])

    def test_confirmed_style_changes_only_current_profile(self):
        self.main["list"].moveToIndex(2);self.main.open_row()
        self.assertEqual(self.main.picker.choices,self.gui.model.STYLES)
        self.main["list"].moveToIndex(1);self.main.open_row()
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
        self.assertIsNotNone(self.main.panel)
        self.assertEqual(self.calls,[])
        self.main.exit()

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
        self.assertEqual(self.main["version"].text,(ROOT/"version.txt").read_text().strip())
        self.main.clock_timer.start();self.main.cleanup()
        self.assertFalse(self.main.clock_timer.running)

    def test_saved_active_settings_are_retained_without_profile_controls(self):
        self.config.plugins.chocholousekpicons_id.setValue(2)
        settings=self.config.plugins.chocholousekpicons[2]
        settings.background.setValue("black")
        settings.picon_folder_user.setValue("/media/usb/picon")
        self.main=self.gui.WarderMainScreen(self.session)
        self.assertIs(self.main.profile,settings)
        self.assertEqual(self.main.profile.background.value,"black")
        self.assertEqual(self.main.profile.picon_folder_user.value,"/media/usb/picon")
        self.main.choose("method","all_inc")
        self.assertEqual(self.saves,[2])
        self.assertEqual(self.config.plugins.chocholousekpicons[1].method.value,"sync_tv")
        self.assertEqual([row[0][0] for row in self.main["list"].values],
                         ["satellites","resolution","style","method","destination"])
        for action in ("1","2","3"):
            self.assertNotIn(action,self.main["actions"])
        self.assertFalse(any(name.startswith("profile") for name in self.main.widgets))

    def test_update_uses_only_visible_settings_even_if_old_profiles_are_enabled(self):
        self.complete_selection()
        self.main.profile.allowed.setValue(False)
        other=self.config.plugins.chocholousekpicons[2]
        other.allowed.setValue(True);other.resolution.setValue("unsupported")
        self.main.update_picons()
        preferences=self.main.job.preferences
        self.assertEqual(self.calls,[])
        self.assertEqual(len(preferences),1)
        self.assertEqual(preferences[0]["resolution"],"220x132")
        self.assertFalse(self.main.profile.allowed.value)
        self.assertTrue(other.allowed.value)

    def test_green_action_uses_the_warder_job_and_native_profiles(self):
        self.complete_selection()
        self.main.update_picons()
        self.assertIsInstance(self.main.job,self.gui.EmbeddedPiconJob)
        self.assertEqual(self.main.job.preferences[0]["package_selectors"],["192E","235E"])


if __name__=="__main__":unittest.main()
