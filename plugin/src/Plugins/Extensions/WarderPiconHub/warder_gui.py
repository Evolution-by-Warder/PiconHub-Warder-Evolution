"""Modern Warder screens around the retained Chocholousek configuration base."""
from .warder_i18n import _, localize_skin
import json
import pathlib
import queue
import threading

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText, MultiContentEntryPixmapAlphaBlend
from Tools.LoadPixmap import LoadPixmap
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.ScrollLabel import ScrollLabel
from Components.config import ConfigSelection, ConfigText, config, configfile
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from enigma import BT_SCALE, RT_HALIGN_LEFT, RT_VALIGN_CENTER, eListboxPythonMultiContent, eTimer, gFont, getDesktop, ePoint, eSize

from . import plugin as legacy
from . import warder_model as model
from . import warder_recent as recent
from .warder_engine import PiconRunner, fetch_manifest
from .warder_layout import dialog_skin, main_skin
from .warder_brand import BrandLogo
from .warder_update_ui import StartupUpdateCheck, connect_timer, installed_version

ROOT = pathlib.Path(__file__).parent


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
        try:
            children = sorted((p for p in self.path.iterdir() if p.is_dir() and not p.is_symlink()),key=lambda p:p.name.lower())
        except OSError:
            children = []
        return [(str(self.path.parent),"..")]+[(str(p),p.name) for p in children]

    def accept(self):
        item = self["list"].getCurrent()
        if item:
            self.path = pathlib.Path(item[0][0])
            self.state = model.PickerState(self.directory_choices())
            self["title"].setText(_("Priečinok: ")+str(self.path))
            self.rebuild()

    def apply(self):
        if not model.sync.validate_destination(str(self.path)):
            self.session.open(MessageBox,_("Tento priečinok nie je platný cieľ pre picony."),type=MessageBox.TYPE_ERROR)
            return
        self.close(str(self.path))


class TextDialog(Screen):
    def __init__(self,session,title,text):
        width,height=desktop()
        self.skin=dialog_skin(width,height,8,kind="text",title=title)
        Screen.__init__(self,session)
        self["title"]=Label(_(title))
        self["hint_red"]=Label(_("Naspäť"))
        self["hint_scroll"]=Label(_("Posun"))
        self["list"]=ScrollLabel(text)
        self["actions"]=ActionMap(["OkCancelActions","ColorActions","DirectionActions"],{
            "ok":self.close,"cancel":self.close,"red":self.close,"up":self["list"].pageUp,"down":self["list"].pageDown},-2)


class PiconJobScreen(Screen):
    def __init__(self,session,preferences):
        width,height=desktop()
        self.skin=dialog_skin(width,height,8,kind="progress",title="Aktualizácia piconov")
        Screen.__init__(self,session)
        self.preferences,self.done,self.started,self.closed=preferences,False,False,False
        self.events,self.cancel=queue.Queue(),threading.Event()
        self.history,self.download_row,self.follow_progress=[],None,True
        self["title"]=Label(_("Aktualizácia piconov"))
        self["status"]=ScrollLabel(_("Pripravujem aktualizáciu piconov…"))
        self["hint_red"]=Label(_("Naspäť"))
        self["hint_blue"]=Label(_("Log"))
        self["progress"]=ProgressBar()
        self["actions"]=ActionMap(["OkCancelActions","ColorActions","DirectionActions"],{
            "ok":self.finish,"cancel":self.finish,"red":self.finish,"blue":self.show_log,
            "up":self.history_up,"down":self.history_down},-2)
        self.timer=eTimer()
        self.connection=connect_timer(self.timer,self.poll)
        self.onLayoutFinish.append(self.start)
        self.onClose.append(self.cleanup)

    def start(self):
        if not self.started:
            self.started=True
            self["progress"].hide()
            threading.Thread(target=self.work,daemon=True).start()
            self.timer.start(200,False)

    def work(self):
        try:
            with open("/tmp/piconhub-picons.log","w") as log:
                def event(*args):
                    self.events.put(args)
                    if args[0]!="download" or args[2] in (0,args[3]):
                        log.write(str(args)+"\n");log.flush()
                result=PiconRunner(event=event,cancel=self.cancel).run(self.preferences)
                self.events.put(("result",result))
        except Exception as exc:
            self.events.put(("error",str(exc)))
            try:
                with open("/tmp/piconhub-picons.log","a") as log:log.write("ERROR: "+str(exc)+"\n")
            except OSError:
                pass

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
                    self.history.append(_("Dokončené.\n\nPridané: %d\nZmenené: %d\nOdstránené: %d") % (item[1]["added"],item[1]["changed"],item[1]["removed"]))
                else:self.history.append(_("Aktualizácia sa nedokončila.\n\n")+item[1])
                self.timer.stop();self.follow_progress=True;changed=True
        if changed:
            position=getattr(self["status"],"currentPosition",0)
            self["status"].setText("\n".join(self.history),showBottom=self.follow_progress)
            if not self.follow_progress:self["status"].setPos(position)

    def history_up(self):
        self.follow_progress=False;self["status"].pageUp()

    def history_down(self):
        self["status"].pageDown()
        self.follow_progress=self["status"].isAtLastPage()

    def finish(self):
        if self.done:self.close()
        else:
            self.cancel.set()
            self.history.append(_("Čakám na bezpečné ukončenie…"))
            self["status"].setText("\n".join(self.history),showBottom=True)

    def show_log(self):
        try:text=pathlib.Path("/tmp/piconhub-picons.log").read_text()[-24000:]
        except OSError:text=_("Log zatiaľ nie je dostupný.")
        self.session.open(TextDialog,_("Log aktualizácie"),text)

    def cleanup(self):
        self.closed=True;self.cancel.set();self.timer.stop()


class WarderMainScreen(Screen):
    def __init__(self,session):
        width,height=desktop()
        self.skin=main_skin(width,height)
        Screen.__init__(self,session)
        self.warder_scale=min(width/1920.0,height/1080.0)
        self.closed=False
        self.layout_ready=False
        self.catalog=json.loads((ROOT/"data/channel-manifest.json").read_text())
        self.catalog_results=queue.Queue()
        self.recent_results=queue.Queue()
        self.selection={key:None for key in ("satellites","resolution","style","method","destination")}
        self.profile_id=max(1,min(3,int(config.plugins.chocholousekpicons_id.getValue())))
        profile=self.profile
        if not hasattr(profile,"warder_selectors"):
            profile.warder_selectors=ConfigText(default="",fixed_size=False)
        value=profile.background.value
        if value in (None,"no_satellites_was_selected","no_picons"):
            value="transparent"
        choices=list(model.STYLES)
        if value not in dict(choices):choices.append((value,_("Pôvodná voľba: ")+str(value)))
        profile.background=ConfigSelection(default=value,choices=choices)
        profile.background.setValue(value)
        for name in ("day","date","clock","seconds","version","preview_caption","summary","status"):
            self[name]=Label("")
        self["background"],self["preview"]=Pixmap(),Pixmap()
        self["brand_logo"]=BrandLogo(ROOT/"images/warder-emblem.png")
        for number in range(recent.COUNT):
            self["recent%d" % number]=Pixmap()
        self["list"]=menu_component(self.warder_scale,100,(32,29,23))
        self["actions"]=ActionMap(["OkCancelActions","DirectionActions","ColorActions"],{
            "up":self["list"].up,"down":self["list"].down,"ok":self.open_row,
            "cancel":self.exit,"red":self.exit,"green":self.update_picons,"yellow":self.check_plugin_update,"blue":self.about},-2)
        self.clock_timer=eTimer();self.clock_connection=connect_timer(self.clock_timer,self.tick)
        self.warderUpdateCheck=StartupUpdateCheck(self)
        self.onLayoutFinish.append(self.ready)
        self.onClose.append(self.cleanup)
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
        for name,value in (("day",day),("date",date),("clock",clock),("seconds",":"+seconds),("version",_("Verzia: %s") % installed_version())):
            self[name].setText(value)
        try:self.show_recent(self.recent_results.get_nowait())
        except queue.Empty:pass
        try:catalog,error=self.catalog_results.get_nowait()
        except queue.Empty:return
        if catalog:
            self.catalog=catalog;self["status"].setText(_("Katalóg je aktuálny • %d balíkov") % len(catalog["packages"]))
        else:self["status"].setText(_("Offline • zobrazený je priložený katalóg; picony sa nemenili."))

    def refresh(self):
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
        row=self["list"].getCurrent()
        if not row:return
        key=row[0][0]
        if key=="satellites":self.select_satellites();return
        choices,current={
            "resolution":(model.RESOLUTIONS,self.selection["resolution"]),
            "style":(model.STYLES,self.selection["style"]),
            "method":(model.METHODS,self.selection["method"]),
            "destination":(tuple((p,label+" — "+p) for p,label in model.DESTINATIONS)+(("custom",_("Vlastný priečinok…")),),None)}[key]
        self.session.openWithCallback(lambda value:self.choose(key,value),ChoiceDialog,row[0][1],choices,current)

    def choose(self,key,value):
        if value is None:return
        if key=="destination":
            if value=="custom":
                self.session.openWithCallback(lambda path:self.choose("destination",path),DirectoryDialog,
                                              self.selection["destination"] or "/media")
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
        choices=[(sid,label+(_(" • zatiaľ nedostupné") if sid not in available else "")) for sid,label in model.SATELLITES]
        self.session.openWithCallback(self.satellites_chosen,ChoiceDialog,_("Satelity a poskytovatelia"),choices,self.selection["satellites"] or [],True)

    def satellites_chosen(self,values):
        if values is None:return
        self.selection["satellites"]=list(values)
        self.profile.warder_selectors.setValue(" ".join(values))
        positions=model.sync.task_positions_from_bindings([model.sync.task_binding_for_package_selector(s) for s in values])
        self.profile.sats.setValue(" ".join(positions));self.save()

    def update_picons(self):
        try:
            missing=[name for key,name in (("satellites",_("Satelity")),("resolution",_("Rozlíšenie")),("style",_("Pozadie")),("method",_("Režim")),("destination",_("Priečinok"))) if not self.selection[key]]
            if missing:raise ValueError(_("Najprv vyber: ")+", ".join(missing)+".")
            preferences=[model.profile_preferences(self.profile)]
        except ValueError as exc:
            self.session.open(MessageBox,str(exc),type=MessageBox.TYPE_ERROR);return
        if any(p["update_mode"]==model.sync.UPDATE_MODE_REPLACE_ALL for p in preferences):
            self.session.openWithCallback(lambda yes:self.session.open(PiconJobScreen,preferences) if yes else None,MessageBox,
                                         _("Úplné nahradenie odstráni staré kanálové picony vybraných pozícií. Pokračovať?"),type=MessageBox.TYPE_YESNO,default=False)
        else:self.session.open(PiconJobScreen,preferences)

    def check_plugin_update(self):
        self.warderUpdateCheck.request(manual=True)

    def about(self):
        self.session.open(TextDialog,_("O projekte"),_("PiconHub Warder Evolution\nVerzia ")+installed_version()+_("\n\nWarder Evolution\nFunkčný základ: Chocholousek Picons 5.0.240904 od s3n0.\nKatalóg a plánovanie piconov: FullHDGlass Warder Evolution."))

    def exit(self):
        configfile.save();self.close()

    def cleanup(self):
        self.closed=True;self.clock_timer.stop()
