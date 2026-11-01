"""Modern Warder screens around the retained Chocholousek configuration base."""
from .warder_i18n import _, localize_skin, language_code
import json
import pathlib
import queue
import threading
from collections import deque

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaBlend
from Tools.LoadPixmap import LoadPixmap
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.ScrollLabel import ScrollLabel
from Components.config import ConfigSelection, ConfigText, ConfigYesNo, config, configfile
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from skin import parseColor
from enigma import BT_SCALE, RT_HALIGN_LEFT, RT_VALIGN_CENTER, eListboxPythonMultiContent, eTimer, gFont, getDesktop, ePoint, eSize

from . import plugin as legacy
from . import warder_model as model
from . import warder_recent as recent
from .warder_engine import PiconRunner, fetch_manifest
from .warder_layout import dialog_skin, main_skin
from .warder_brand import BrandLogo
from .warder_release_notes import load_notes
from .warder_update_ui import StartupUpdateCheck, connect_timer, installed_version

ROOT = pathlib.Path(__file__).parent


def directory_choices(path):
    """Include directory aliases used by receiver images, retaining their names."""
    children = []
    try:
        for child in path.iterdir():
            try:
                if child.is_dir():children.append(child)
            except OSError:
                continue
    except OSError:
        pass
    children.sort(key=lambda child:child.name.lower())
    parents = [(str(path.parent), "..")] if path != path.parent else []
    return parents + [(str(child), child.name) for child in children]


def directory_destination(path):
    # Explicitly selecting an alias records its real directory. The installer
    # still validates this canonical path and refuses changed symlinks.
    try:
        return model.sync.validate_destination(str(path.resolve(strict=True)))
    except (OSError, RuntimeError):
        return None


def desktop():
    size = getDesktop(0).size()
    return size.width(), size.height()


def menu_component(scale, item_height=60, fonts=(28,)):
    component = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
    for index,size in enumerate(fonts):
        component.l.setFont(index, gFont("Regular", round(size*scale)))
    component.l.setItemHeight(round(item_height*scale))
    return component


def option_entries(choices, selected, scale, multiple=False, icons=None):
    result = []
    for value,label in choices:
        entry = [(value,label)]
        left = 16
        if multiple:
            color = 0x0039ff59 if value in selected else 0x00b5d4ec
            entry.append(MultiContentEntryText(pos=(round(16*scale),0),
                         size=(round(42*scale),round(60*scale)), font=0,
                         flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER,
                         text="●" if value in selected else "○", color=color, color_sel=color))
            left = 64
        icon = (icons or {}).get(value)
        if icon is not None:
            entry.append(MultiContentEntryPixmapAlphaBlend(pos=(round(64*scale),round(7*scale)),
                         size=(round(75*scale),round(45*scale)), png=icon, flags=BT_SCALE))
            left = 157
        entry.append(MultiContentEntryText(pos=(round(left*scale),0),
                     size=(round((990-left)*scale),round(60*scale)), font=0,
                     flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=_(label)))
        result.append(entry)
    return result


class ChoiceDialog(Screen):
    def __init__(self, session, title, choices, current=None, multiple=False, kind="choice"):
        width,height = desktop()
        self.skin = dialog_skin(width,height,len(choices),multiple=multiple,kind=kind,title=title)
        Screen.__init__(self,session)
        self.warder_scale = min(width/1920.0,height/1080.0)
        self.state = model.PickerState(choices, current or () if multiple else (current,), multiple)
        self["title"] = Label(_(title))
        self.icons = {}
        if multiple:
            for value,label in choices:
                path = ROOT/"images/selectors"/(value+".png")
                if path.is_file():
                    self.icons[value] = LoadPixmap(path=str(path))
            self["hint_ok"] = Label(_("Vybrať s OK"))
            self["hint_green"] = Label(_("Potvrdiť výber"))
            self["hint_red"] = Label(_("Naspäť"))
        else:
            self["hint_ok"] = Label(_("Vybrať s OK"))
            self["hint_red"] = Label(_("Naspäť"))
            if kind=="directory":self["hint_green"] = Label(_("Potvrdiť výber"))
        self["list"] = menu_component(self.warder_scale)
        self["actions"] = ActionMap(["OkCancelActions","ColorActions","DirectionActions"], {
            "ok": self.accept, "green": self.apply, "cancel": lambda:self.close(None),
            "red": lambda:self.close(None), "up":self["list"].up,"down":self["list"].down,
            "left":self["list"].pageUp,"right":self["list"].pageDown},-2)
        self.rebuild()
        if not multiple:
            self.onLayoutFinish.append(self.select_current)

    def select_current(self):
        index = next((i for i,(value,label) in enumerate(self.state.choices) if value in self.state.selected),0)
        self["list"].moveToIndex(index)

    def rebuild(self):
        self["list"].setList(option_entries(self.state.choices,self.state.selected,self.warder_scale,self.state.multiple,self.icons))

    def accept(self):
        entry = self["list"].getCurrent()
        if entry is None:
            return
        value = entry[0][0]
        if self.state.multiple:
            index = self["list"].getSelectionIndex()
            self.state.toggle(value)
            self.rebuild()
            self["list"].moveToIndex(index)
        else:
            self.close(value)

    def apply(self):
        if self.state.multiple:
            self.close(self.state.apply())
        else:
            self.accept()


class DirectoryDialog(ChoiceDialog):
    def __init__(self, session, path):
        self.path = pathlib.Path(path)
        while not self.path.is_dir() and self.path != self.path.parent:
            self.path = self.path.parent
        ChoiceDialog.__init__(self,session,_("Priečinok: ")+str(self.path),self.directory_choices(),kind="directory")
        self["hint_ok"].setText(_("Otvoriť"))
        self["hint_green"].setText(_("Použiť priečinok"))

    def directory_choices(self):
        return directory_choices(self.path)

    def accept(self):
        item = self["list"].getCurrent()
        if item:
            self.path = pathlib.Path(item[0][0])
            self.state = model.PickerState(self.directory_choices())
            self["title"].setText(_("Priečinok: ")+str(self.path))
            self.rebuild()

    def apply(self):
        destination = directory_destination(self.path)
        if not destination:
            self.session.open(MessageBox,_("Tento priečinok nie je platný cieľ pre picony."),type=MessageBox.TYPE_ERROR)
            return
        self.close(destination)


class TextDialog(Screen):
    def __init__(self,session,title,text):
        width,height=desktop()
        self.skin=dialog_skin(width,height,8,kind="text",title=title)
        Screen.__init__(self,session)
        self["title"]=Label(_(title))
        self["hint_red"]=Label(_("Naspäť"))
        self["list"]=ScrollLabel(text)
        self["actions"]=ActionMap(["OkCancelActions","ColorActions","DirectionActions"],{
            "ok":self.close,"cancel":self.close,"red":self.close,"up":self["list"].pageUp,"down":self["list"].pageDown},-2)


class PiconJobController:
    def setup_job(self,preferences):
        self.preferences,self.done,self.started,self.closed=preferences,False,False,False
        self.success=False
        self.events,self.cancel=queue.Queue(),threading.Event()
        self.history,self.download_row,self.follow_progress=[],None,True
        self._log_rows,self._log_lock=deque(maxlen=160),threading.Lock()
        self.timer=eTimer()
        self.connection=connect_timer(self.timer,self.poll)

    def start(self):
        if not self.started:
            self.started=True
            self["progress"].hide()
            threading.Thread(target=self.work,daemon=True).start()
            self.timer.start(200,False)

    def work(self):
        try:
            def event(*args):
                self.events.put(args)
                if args[0]!="download" or args[2] in (0,args[3]):
                    with self._log_lock:self._log_rows.append(str(args)[:1024])
            result=PiconRunner(event=event,cancel=self.cancel).run(self.preferences)
            self.events.put(("result",result))
        except Exception as exc:
            self.events.put(("error",str(exc)))
            with self._log_lock:self._log_rows.append(("ERROR: "+str(exc))[:1024])

    def log_text(self):
        with self._log_lock:text="\n".join(self._log_rows)[-24000:]
        return text or _("Log zatiaľ nie je dostupný.")

    def poll(self):
        if self.closed:
            return
        changed=False
        for unused in range(1000):
            try: item=self.events.get_nowait()
            except queue.Empty: break
            if item[0]=="stage":
                self.history.append(item[1]);self.download_row=None
                self["progress"].hide();changed=True
            elif item[0]=="download":
                percent=int(item[2]*100/item[3])
                text=_("Sťahujem %s • %d %%") % (item[1],percent)
                if self.download_row is None:
                    self.download_row=len(self.history);self.history.append(text)
                else:self.history[self.download_row]=text
                self["progress"].show();self["progress"].setValue(percent);changed=True
            elif item[0]=="processed":
                if self.history:self.history[-1]+=" ✓"
                changed=True
            elif item[0] in ("result","error"):
                self.done=True
                self["progress"].hide()
                if item[0]=="result":
                    self.success=True
                    self.history.append(_("Dokončené.\n\nPridané: %d\nZmenené: %d\nOdstránené: %d") % (item[1]["added"],item[1]["changed"],item[1]["removed"]))
                else:self.history.append(_("Aktualizácia sa nedokončila.\n\n")+item[1])
                self.timer.stop();self.follow_progress=True;changed=True
        if changed:self.render_history()

    def render_history(self):
        position=getattr(self["status"],"currentPosition",0)
        self["status"].setText("\n".join(self.history),showBottom=self.follow_progress)
        if not self.follow_progress:self["status"].setPos(position)

    def history_up(self):
        self.follow_progress=False;self["status"].pageUp()

    def history_down(self):
        self["status"].pageDown()
        self.follow_progress=self["status"].isAtLastPage()

    def finish(self):
        if self.done:self.close(self.success)
        else:
            self.cancel.set()
            self.history.append(_("Čakám na bezpečné ukončenie…"))
            self["status"].setText("\n".join(self.history),showBottom=True)

    def show_log(self):
        text=self.log_text()
        self.session.open(TextDialog,_("Log aktualizácie"),text)

    def cleanup(self):
        self.closed=True;self.cancel.set();self.timer.stop()


class PiconJobScreen(PiconJobController,Screen):
    def __init__(self,session,preferences):
        width,height=desktop()
        self.skin=dialog_skin(width,height,8,kind="progress",title="Aktualizácia piconov")
        Screen.__init__(self,session)
        self["title"]=Label(_("Aktualizácia piconov"))
        self["status"]=ScrollLabel(_("Pripravujem aktualizáciu piconov…"))
        self["hint_red"]=Label(_("Naspäť"))
        self["hint_blue"]=Label(_("Log"))
        self["progress"]=ProgressBar()
        self["actions"]=ActionMap(["OkCancelActions","ColorActions","DirectionActions"],{
            "ok":self.finish,"cancel":self.finish,"red":self.finish,"blue":self.show_log,
            "up":self.history_up,"down":self.history_down},-2)
        self.setup_job(preferences)
        self.onLayoutFinish.append(self.start)
        self.onClose.append(self.cleanup)


class EmbeddedPiconJob(PiconJobController):
    def __init__(self,host,preferences):
        self.host,self.view_log=host,False
        self.title=_("Aktualizácia piconov")+" • "+(_("Profily: %s")%", ".join(str(p["profile_number"]) for p in preferences if "profile_number" in p))
        self.setup_job(preferences)
        host.onClose.append(self.cleanup)
        host.show_update_notice(_("Pripravujem aktualizáciu piconov…"),title=self.title)
        self.start()

    def __getitem__(self,key):
        return self.host[{"status":"panel_text","progress":"panel_progress"}[key]]

    def render_history(self):
        if not self.view_log:PiconJobController.render_history(self)

    def show_log(self):
        if self.view_log:return
        self.view_log=True
        text=self.log_text()
        self.host["picker_title"].setText(_("Log aktualizácie"))
        self.host["panel_text"].setText(text,showBottom=True)
        self.host.set_footer()

    def back_from_log(self):
        self.view_log=False
        self.host["picker_title"].setText(self.title)
        self.render_history()
        self.host.set_footer()

    def close(self,success):
        self.cleanup()
        if self.cleanup in self.host.onClose:self.host.onClose.remove(self.cleanup)
        self.host.job=None
        self.host["panel_progress"].hide()
        self.host.close_update_notice()
        self.host.picon_job_finished(success)


class PanelText(ScrollLabel):
    def applySkin(self,desktop,parent):
        result=ScrollLabel.applySkin(self,desktop,parent)
        self.instance.setZPosition(5)
        return result


class WarderMainScreen(Screen):
    def __init__(self,session):
        width,height=desktop()
        self.skin=main_skin(width,height)
        Screen.__init__(self,session)
        self.warder_scale=min(width/1920.0,height/1080.0)
        self.closed=False
        self.layout_ready=False
        self.picker=None
        self.panel=None
        self.job=None
        self.catalog=json.loads((ROOT/"data/channel-manifest.json").read_text())
        self.catalog_results=queue.Queue()
        self.recent_results=queue.Queue()
        self.selection={key:None for key in ("satellites","resolution","style","method","destination")}
        for profile in config.plugins.chocholousekpicons[1:legacy.PROFILE_COUNT+1]:
            self.prepare_profile(profile)
        self.load_profile(config.plugins.chocholousekpicons_id.getValue())
        for number in range(1,legacy.PROFILE_COUNT+1):
            self['profile%d'%number]=Label('')
            self['profile_mark%d'%number]=Label('')
        for name in ("day","date","clock","seconds","version","preview_caption","summary","status","picker_cover","picker_title","navigation_hint"):
            self[name]=Label("")
        for color in ("red","green","yellow","blue"):
            for prefix in ("key_","line_","footer_"):
                self[prefix+color]=Label("")
        self["picker_cover"].hide();self["picker_title"].hide()
        self["panel_text"]=PanelText("")
        self["panel_text"].hide()
        self["panel_progress"]=ProgressBar()
        self["panel_progress"].hide()
        self["background"],self["preview"]=Pixmap(),Pixmap()
        self["brand_logo"]=BrandLogo(ROOT/"images/warder-emblem.png")
        for number in range(recent.COUNT):
            self["recent%d" % number]=Pixmap()
        self["list"]=menu_component(self.warder_scale,100,(32,29,23))
        self["actions"]=ActionMap(["OkCancelActions","DirectionActions","ColorActions","NumberActions"],{
            "up":self.move_up,"down":self.move_down,"left":self.page_up,"right":self.page_down,"ok":self.open_row,"0":self.toggle_profile,
            "cancel":self.exit,"red":self.exit,"green":self.green_action,"yellow":self.check_plugin_update,"blue":self.about},-2)
        self.clock_timer=eTimer();self.clock_connection=connect_timer(self.clock_timer,self.tick)
        self.warderUpdateCheck=StartupUpdateCheck(self)
        self.onLayoutFinish.append(self.ready)
        self.onClose.append(self.cleanup)
        self.refresh()

    def prepare_profile(self,profile):
        if not hasattr(profile,"warder_process"):
            profile.warder_process=ConfigYesNo(default=False)
        if not hasattr(profile,"warder_selectors"):
            profile.warder_selectors=ConfigText(default="",fixed_size=False)
        value=getattr(profile.background,"saved_value",None) or profile.background.value
        if value is None:
            value="no_satellites_was_selected"
        choices=[("no_satellites_was_selected",_("Vyber si…"))]+list(model.STYLES)
        if value not in dict(choices):choices.append((value,_("Vyber si…") if value in ("no_satellites_was_selected","no_picons") else _("Pôvodná voľba: ")+str(value)))
        # Enigma2 omits default values when saving; never make the user's style the default.
        profile.background=ConfigSelection(default="no_satellites_was_selected",choices=choices)
        profile.background.setValue(value)

    def load_profile(self,number):
        self.profile_id=max(1,min(legacy.PROFILE_COUNT,int(number)))
        self.prepare_profile(self.profile)
        self.selection=model.profile_selection(self.profile)

    def marked_profiles(self):
        return [number for number in range(1,legacy.PROFILE_COUNT+1)
                if config.plugins.chocholousekpicons[number].warder_process.value]

    def toggle_profile(self):
        if self.closed or self.job is not None or self.picker is not None or self.panel is not None:return
        setting=self.profile.warder_process
        setting.setValue(not setting.value);setting.save();configfile.save();self.refresh()

    def switch_profile(self,number):
        if self.closed or self.job is not None or self.picker is not None or self.panel is not None:return
        number=(int(number)-1)%legacy.PROFILE_COUNT+1
        if number==self.profile_id:return
        self.save()
        config.plugins.chocholousekpicons_id.setValue(number)
        config.plugins.chocholousekpicons_id.save()
        self.load_profile(number)
        configfile.save()
        self.refresh()

    @property
    def profile(self):
        return config.plugins.chocholousekpicons[self.profile_id]

    def ready(self):
        if self.layout_ready:return
        self.layout_ready=True
        self["background"].instance.setPixmapFromFile(str(ROOT/"images/warder-background.png"))
        self["background"].instance.setScale(1)
        self.tick();self.clock_timer.start(1000,False);self.refresh()
        self.show_recent(recent.bundled(ROOT))
        self["status"].setText(_("Načítavam aktuálny katalóg balíkov…"))
        threading.Thread(target=self.refresh_catalog,daemon=True).start()
        threading.Thread(target=self.refresh_recent,daemon=True).start()

    def refresh_recent(self):
        self.recent_results.put(recent.load_recent(ROOT))

    def show_recent(self,paths):
        if self.closed:return
        for number in range(recent.COUNT):
            widget=self["recent%d" % number]
            if number<len(paths) and widget.instance:
                widget.instance.setPixmapFromFile(str(paths[number]))
                widget.instance.setScale(1);widget.show()
            else:widget.hide()

    def refresh_catalog(self):
        try:self.catalog_results.put((fetch_manifest(),None))
        except Exception as exc:self.catalog_results.put((None,str(exc)))

    def tick(self):
        if self.closed:return
        language=getattr(getattr(config,"osd",None),"language",None)
        day,date,clock,seconds=model.clock_text(language=language.value if language else "sk")
        for name,value in (("day",day),("date",date),("clock",clock),("seconds",":"+seconds),("version",installed_version())):
            self[name].setText(value)
        try:self.show_recent(self.recent_results.get_nowait())
        except queue.Empty:pass
        try:catalog,error=self.catalog_results.get_nowait()
        except queue.Empty:return
        if catalog:
            self.catalog=catalog;self["status"].setText(_("Katalóg je aktuálny • %d balíkov") % len(catalog["packages"]))
        else:self["status"].setText(_("Offline • zobrazený je priložený katalóg; picony sa nemenili."))

    def refresh(self):
        if self.picker is not None or self.panel is not None:return
        for number in range(1,legacy.PROFILE_COUNT+1):
            tab=self['profile%d'%number]
            selected=config.plugins.chocholousekpicons[number].warder_process.value
            tab.setText(_('Profil %d')%number)
            mark=self['profile_mark%d'%number]
            mark.setText('✓' if selected else '□')
            if mark.instance:
                mark.instance.setForegroundColor(parseColor('#0000ea9b' if selected else '#00b5d4ec'))
            if tab.instance:
                tab.instance.setBackgroundColor(parseColor('#002a70ad' if number==self.profile_id else '#0010243c'))
                tab.instance.setForegroundColor(parseColor('#00ffffff' if number==self.profile_id else '#00b5d4ec'))
        self.set_footer()
        profile=self.profile
        selections=self.selection["satellites"] or []
        labels=dict(model.SATELLITES)
        satellites=", ".join(labels.get(s,s) for s in selections)
        if len(satellites)>42:satellites=satellites[:35]+"… (%d)" % len(selections)
        destination=self.selection["destination"]
        rows=(("satellites",_("Satelity"),satellites or _("Vyber si…")),
              ("resolution",_("Rozlíšenie"),dict(model.RESOLUTIONS).get(self.selection["resolution"],_("Vyber si…"))),
              ("style",_("Pozadie"),dict(model.STYLES).get(self.selection["style"],_("Vyber si…"))),
              ("method",_("Režim"),dict(model.METHODS).get(self.selection["method"],_("Vyber si…"))),
              ("destination",_("Priečinok"),destination or _("Vyber si…")))
        entries=[]
        for number,(key,label,value) in enumerate(rows,1):
            scale=self.warder_scale
            entries.append([(key,label,value),
                MultiContentEntryText(pos=(0,round(12*scale)),size=(round(5*scale),round(76*scale)),font=0,text="",backcolor_sel=0x003ee8ff),
                MultiContentEntryText(pos=(round(20*scale),0),size=(round(50*scale),round(100*scale)),font=2,flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER,text="%02d" % number,color=0x003ee8ff,color_sel=0x00ffffff),
                MultiContentEntryText(pos=(round(80*scale),0),size=(round(290*scale),round(100*scale)),font=0,flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER,text=label,color=0x00b5d4ec,color_sel=0x00ffffff),
                MultiContentEntryText(pos=(round(380*scale),0),size=(round(650*scale),round(100*scale)),font=1,flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER,text=_(value),color=0x00ffffff,color_sel=0x00ffffff),
                MultiContentEntryText(pos=(round(1060*scale),0),size=(round(40*scale),round(100*scale)),font=0,flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER,text="›",color=0x003ee8ff,color_sel=0x00ffffff)])
        index=self["list"].getSelectionIndex()
        self["list"].setList(entries)
        self["list"].moveToIndex(max(index,0))
        complete=sum(bool(value) for value in self.selection.values())
        self["summary"].setText(_("Vybrané: %d z 5\n%s") % (complete,_("Pripravené na stiahnutie.") if complete==5 else _("Doplň svoj výber.")))
        style=self.selection["style"]
        preview=ROOT/"images"/("preview-"+str(style)+".png")
        if style and self["preview"].instance and preview.is_file():
            self["brand_logo"].hide()
            resolution=self.selection["resolution"]
            width,height=map(int,(resolution or "220x132").split("x"))
            scale=self.warder_scale
            self["preview"].instance.resize(eSize(round(width*scale),round(height*scale)))
            self["preview"].instance.move(ePoint(round((1320+(440-width)/2)*scale),round((465+(264-height)/2)*scale)))
            self["preview"].instance.setScale(1)
            self["preview"].instance.setPixmapFromFile(str(preview));self["preview"].show()
            caption=(resolution.replace("x","×") if resolution else _("Vyber si rozlíšenie…"))
            self["preview_caption"].setText(_(dict(model.STYLES)[style])+" • "+caption)
        else:
            self["preview"].hide();self["brand_logo"].show_logo()
            self["preview_caption"].setText(_("PiconHub by Warder • Vyber si pozadie…"))

    def save(self):
        legacy.mainConfigScreen.cfgProfileSave(self,self.profile_id)
        self.profile.warder_selectors.save();configfile.save();self.refresh()

    def open_row(self):
        if self.panel is not None:
            if not self.panel["callback"]:self.exit()
            return
        if self.picker is not None:
            self.picker_accept();return
        row=self["list"].getCurrent()
        if not row:return
        key=row[0][0]
        if key=="satellites":self.select_satellites();return
        choices,current={
            "resolution":(model.RESOLUTIONS,self.selection["resolution"]),
            "style":(model.STYLES,self.selection["style"]),
            "method":(model.METHODS,self.selection["method"]),
            "destination":(tuple((p,label+" — "+p) for p,label in model.DESTINATIONS)+(("custom",_("Vlastný priečinok…")),),None)}[key]
        self.open_picker(row[0][1],choices,current,callback=lambda value:self.choose(key,value))

    def choose(self,key,value):
        if value is None:return
        if key=="destination":
            if value=="custom":
                self.open_directory("/")
                return
            self.profile.picon_folder.setValue("user_defined");self.profile.picon_folder_user.setValue(value)
        else:
            field={"style":"background","resolution":"resolution","method":"method"}[key]
            getattr(self.profile,field).setValue(value)
        self.selection[key]=value
        self.save()

    def select_satellites(self):
        style,resolution=self.selection["style"],self.selection["resolution"]
        family=model.sync.family_for_style(style) if style else None
        available={p["selector_id"] for p in self.catalog["packages"] if (not family or p.get("family")==family) and (not resolution or p.get("resolution")==resolution)}
        # DAB uses a separate approved catalog, not the native satellite catalog.
        if not resolution or resolution == "220x132":available.add("DAB")
        available.add("IPTV-SK-CZ")
        choices=[(sid,label+(_(" • zatiaľ nedostupné") if sid not in available else "")) for sid,label in model.SATELLITES]
        self.open_picker(_("Satelity a poskytovatelia"),choices,self.selection["satellites"] or [],True,self.satellites_chosen)

    def set_footer(self):
        picking=self.picker is not None
        multiple=picking and self.picker.multiple
        directory=picking and self.picker_path is not None
        marked=self.marked_profiles()
        download=_("Stiahnuť (%d)")%len(marked)
        captions=(_("Naspäť"),_("Použiť priečinok") if directory else _("Potvrdiť výber") if multiple else "","","") if picking else (_("Zatvoriť"),download,_("Aktualizácia pluginu"),_("O projekte"))
        if self.panel is not None:
            captions=(_("Naspäť") if self.panel["enabled"] else "",self.panel["confirm"] if self.panel["enabled"] else "","","")
        if self.job is not None:
            captions=(_("Naspäť"),"","", "" if self.job.view_log else _("Log"))
        for color,text in zip(("red","green","yellow","blue"),captions):
            self["key_"+color].setText(text)
            for prefix in ("key_","line_","footer_"):
                (self[prefix+color].show if text else self[prefix+color].hide)()
        disabled=not picking and self.panel is None and self.job is None and not marked
        if self["key_green"].instance:
            self["key_green"].instance.setForegroundColor(parseColor("#00738696" if disabled else "#0000ea9b"))
        if self["line_green"].instance:
            self["line_green"].instance.setBackgroundColor(parseColor("#00314b65" if disabled else "#0000ea9b"))
        self["navigation_hint"].setText(_("Otvoriť")+" • OK" if directory else _("Vybrať s OK") if picking else _("←→: profil • 0: označiť • ↑↓: riadok • OK: výber • Stiahnuť: označené profily" if marked else "←→: profil • 0: označiť • ↑↓: riadok • OK: výber • Najprv označ profil"))
        if self.panel is not None:self["navigation_hint"].setText("")

    def move_up(self):
        if self.job is not None and not self.job.view_log:
            self.job.history_up();return
        (self["panel_text"].pageUp if self.panel is not None else self["list"].up)()

    def move_down(self):
        if self.job is not None and not self.job.view_log:
            self.job.history_down();return
        (self["panel_text"].pageDown if self.panel is not None else self["list"].down)()

    def page_up(self):
        if self.panel is not None:self.move_up()
        elif self.picker is not None:self["list"].pageUp()
        else:self.switch_profile(self.profile_id-1)

    def page_down(self):
        if self.panel is not None:self.move_down()
        elif self.picker is not None:self["list"].pageDown()
        else:self.switch_profile(self.profile_id+1)

    def show_update_notice(self,text,callback=None,confirm="",enabled=True,title=None):
        if self.panel is None:self.panel_return_index=self["list"].getSelectionIndex()
        self.panel={"callback":callback,"confirm":confirm,"enabled":enabled}
        self["picker_title"].setText(title or _("Aktualizácia PiconHub Warder Evolution"))
        self["picker_cover"].show();self["picker_title"].show()
        self["list"].hide()
        self["panel_text"].setText(text);self["panel_text"].show();self.set_footer()

    def close_update_notice(self,accepted=False):
        if not self.panel or not self.panel["enabled"]:return
        callback=self.panel["callback"]
        self.panel=None
        self["panel_text"].hide();self["picker_cover"].hide();self["picker_title"].hide();self["list"].show()
        self.refresh();self["list"].moveToIndex(self.panel_return_index)
        if callback:callback(accepted)

    def open_picker(self,title,choices,current=None,multiple=False,callback=None,path=None):
        # Keep the main screen alive; only the left panel changes its contents.
        if self.picker is None:self.picker_return_index=self["list"].getSelectionIndex()
        self.picker=model.PickerState(choices,(current or ()) if multiple else (current,),multiple)
        self.picker_callback=callback
        self.picker_path=path
        self.picker_icons={}
        if multiple:
            for value,label in choices:
                icon=ROOT/"images/selectors"/(value+".png")
                if icon.is_file():self.picker_icons[value]=LoadPixmap(path=str(icon))
        self["picker_title"].setText(title)
        self["picker_cover"].show();self["picker_title"].show()
        scale=self.warder_scale
        self["list"].instance.move(ePoint(round(70*scale),round(410*scale)))
        self["list"].instance.resize(eSize(round(1120*scale),round(420*scale)))
        self["list"].l.setItemHeight(round(60*scale))
        self["list"].l.setFont(0,gFont("Regular",round(28*scale)))
        self.picker_rebuild()
        index=next((i for i,(value,label) in enumerate(choices) if value in self.picker.selected),0)
        self["list"].moveToIndex(index);self.set_footer()

    def picker_rebuild(self):
        self["list"].setList(option_entries(self.picker.choices,self.picker.selected,self.warder_scale,self.picker.multiple,self.picker_icons))

    def picker_accept(self):
        item=self["list"].getCurrent()
        if not item:return
        value=item[0][0]
        if self.picker_path is not None:
            self.open_directory(value);return
        if self.picker.multiple:
            index=self["list"].getSelectionIndex()
            self.picker.toggle(value);self.picker_rebuild();self["list"].moveToIndex(index)
        else:self.close_picker(value,True)

    def close_picker(self,value=None,confirmed=False):
        callback=self.picker_callback
        self.picker=None
        self["picker_cover"].hide();self["picker_title"].hide()
        scale=self.warder_scale
        self["list"].instance.move(ePoint(round(70*scale),round(390*scale)))
        self["list"].instance.resize(eSize(round(1120*scale),5*round(100*scale)))
        self["list"].l.setItemHeight(round(100*scale))
        self["list"].l.setFont(0,gFont("Regular",round(32*scale)))
        self.refresh();self["list"].moveToIndex(self.picker_return_index)
        if confirmed and callback:callback(value)

    def open_directory(self,path):
        path=pathlib.Path(path)
        while not path.is_dir() and path!=path.parent:path=path.parent
        choices=directory_choices(path)
        self.open_picker(_("Priečinok: ")+str(path),choices,callback=lambda value:self.choose("destination",value),path=path)

    def green_action(self):
        if self.panel is not None:
            if self.panel["confirm"]:self.close_update_notice(True)
            return
        if self.picker is None:self.update_picons();return
        if self.picker_path is not None:
            path=directory_destination(self.picker_path)
            if not path:
                self["status"].setText(_("Tento priečinok nie je platný cieľ pre picony."));return
            self.close_picker(path,True)
        elif self.picker.multiple:self.close_picker(self.picker.apply(),True)

    def satellites_chosen(self,values):
        if values is None:return
        self.selection["satellites"]=list(values)
        self.profile.warder_selectors.setValue(" ".join(values))
        positions=model.sync.task_positions_from_bindings([model.sync.task_binding_for_package_selector(s) for s in values if s not in ("DAB", "IPTV-SK-CZ")])
        self.profile.sats.setValue(" ".join(positions));self.save()

    def update_picons(self):
        if self.closed or self.job is not None or self.picker is not None or self.panel is not None:return
        selected=self.marked_profiles()
        if not selected:return
        preferences=[]
        for number in selected:
            profile=config.plugins.chocholousekpicons[number]
            selection=model.profile_selection(profile)
            try:
                missing=[name for key,name in (("satellites",_("Satelity")),("resolution",_("Rozlíšenie")),("style",_("Pozadie")),("method",_("Režim")),("destination",_("Priečinok"))) if not selection[key]]
                if missing:raise ValueError(_("Najprv vyber: ")+", ".join(missing)+".")
                prefs=model.profile_preferences(profile)
                prefs['profile_number']=number
                preferences.append(prefs)
            except ValueError as exc:
                self.show_update_notice((_("Profil %d")%number)+": "+str(exc),title=_("Aktualizácia piconov"));return
        if any(p["update_mode"]==model.sync.UPDATE_MODE_REPLACE_ALL for p in preferences):
            self.show_update_notice(_("Úplné nahradenie odstráni staré kanálové picony vybraných pozícií. Pokračovať?"),callback=lambda yes:self.start_picon_job(preferences) if yes else None,confirm=_("Potvrdiť výber"),title=_("Aktualizácia piconov"))
        else:self.start_picon_job(preferences)

    def start_picon_job(self,preferences):
        if self.job is not None:return
        self.job=EmbeddedPiconJob(self,preferences)
        self.set_footer()

    def picon_job_finished(self,success):
        if success is True:
            self.refresh()

    def check_plugin_update(self):
        if self.picker is not None or self.panel is not None:return
        self.warderUpdateCheck.request(manual=True)

    def about(self):
        if self.job is not None:
            self.job.show_log();return
        if self.picker is not None or self.panel is not None:return
        version=installed_version()
        text=_("PiconHub Warder Evolution\nVerzia ")+version+_("\n\nWarder Evolution\nPlugin vychádza z práce s3n0 a Chocholousek.\nKatalóg a plánovanie piconov: FullHDGlass Warder Evolution.")
        notes=load_notes(ROOT/"data/release-notes.json",version,language_code())
        if notes:text+="\n\n"+notes
        self.show_update_notice(text,title=_("O projekte"))

    def exit(self):
        if self.job is not None:
            if self.job.view_log:self.job.back_from_log()
            else:self.job.finish()
            return
        if self.panel is not None:
            self.close_update_notice();return
        if self.picker is not None:
            self.close_picker();return
        configfile.save();self.close()

    def cleanup(self):
        self.closed=True;self.clock_timer.stop()

