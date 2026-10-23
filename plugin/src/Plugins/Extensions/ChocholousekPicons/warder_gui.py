"""Modern Warder screens around the retained Chocholousek configuration base."""
import json
import pathlib
import queue
import threading

from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Components.ScrollLabel import ScrollLabel
from Components.config import ConfigSelection, ConfigText, config, configfile
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from enigma import RT_HALIGN_LEFT, RT_VALIGN_CENTER, eListboxPythonMultiContent, eTimer, gFont, getDesktop
from skin import parseColor

from . import plugin as legacy
from . import warder_model as model
from .warder_engine import PiconRunner, fetch_manifest
from .warder_layout import dialog_skin, main_skin
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


def option_entries(choices, selected, scale, multiple=False):
    result = []
    for value,label in choices:
        marker = ("● " if value in selected else "○ ") if multiple else ""
        result.append([(value,label), MultiContentEntryText(pos=(round(16*scale),0),
                       size=(round(980*scale),round(60*scale)), font=0,
                       flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER, text=marker+label)])
    return result


class ChoiceDialog(Screen):
    def __init__(self, session, title, choices, current=None, multiple=False):
        width,height = desktop()
        self.skin = dialog_skin(width,height,len(choices))
        Screen.__init__(self,session)
        self.warder_scale = min(width/1920.0,height/1080.0)
        self.state = model.PickerState(choices, current or () if multiple else (current,), multiple)
        self["title"] = Label(title)
        self["hint"] = Label("OK: označiť • Zelené: potvrdiť • EXIT: bez zmeny" if multiple else "OK: potvrdiť • EXIT: bez zmeny")
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
        self["list"].setList(option_entries(self.state.choices,self.state.selected,self.warder_scale,self.state.multiple))

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
        ChoiceDialog.__init__(self,session,"Priečinok: "+str(self.path),self.directory_choices())
        self["hint"].setText("OK: otvoriť • Zelené: použiť tento priečinok • EXIT: späť")

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
            self["title"].setText("Priečinok: "+str(self.path))
            self.rebuild()

    def apply(self):
        if not model.sync.validate_destination(str(self.path)):
            self.session.open(MessageBox,"Tento priečinok nie je platný cieľ pre picony.",type=MessageBox.TYPE_ERROR)
            return
        self.close(str(self.path))


class TextDialog(Screen):
    def __init__(self,session,title,text):
        width,height=desktop()
        self.skin=dialog_skin(width,height,8).replace('name="list"','name="list" font="Regular;%d"' % round(25*height/1080.0))
        Screen.__init__(self,session)
        self["title"],self["hint"]=Label(title),Label("EXIT: späť • ↑↓: posun")
        self["list"]=ScrollLabel(text)
        self["actions"]=ActionMap(["OkCancelActions","DirectionActions"],{
            "ok":self.close,"cancel":self.close,"up":self["list"].pageUp,"down":self["list"].pageDown},-2)


class PiconJobScreen(Screen):
    def __init__(self,session,preferences):
        width,height=desktop()
        scale=min(width/1920.0,height/1080.0)
        self.skin='''<screen position="center,center" size="%d,%d" title="Aktualizácia piconov" backgroundColor="#00102136">
          <widget name="status" position="%d,%d" size="%d,%d" font="Regular;%d" />
          <widget name="progress" position="%d,%d" size="%d,%d" borderWidth="2" />
          <widget name="hint" position="%d,%d" size="%d,%d" font="Regular;%d" />
        </screen>''' % tuple(round(v*scale) for v in (1100,540,35,40,1030,300,30,35,375,1030,35,35,450,1030,60,25))
        Screen.__init__(self,session)
        self.preferences,self.done,self.started,self.closed=preferences,False,False,False
        self.events,self.cancel=queue.Queue(),threading.Event()
        self["status"],self["hint"]=Label("Pripravujem aktualizáciu piconov…"),Label("EXIT: zrušiť prípravu • Modré: log")
        self["progress"]=ProgressBar()
        self["actions"]=ActionMap(["OkCancelActions","ColorActions"],{
            "ok":self.finish,"cancel":self.finish,"red":self.finish,"blue":self.show_log},-2)
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
                    if args[0]!="download":
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
        for unused in range(1000):
            try: item=self.events.get_nowait()
            except queue.Empty: break
            if item[0]=="stage":
                self["status"].setText(item[1]);self["progress"].hide()
            elif item[0]=="download":
                self["status"].setText("Sťahujem %s • %d %%" % (item[1],int(item[2]*100/item[3])))
                self["progress"].show();self["progress"].setValue(int(item[2]*100/item[3]))
            elif item[0] in ("result","error"):
                self.done=True
                self["progress"].hide()
                self["hint"].setText("OK alebo EXIT: späť • Modré: log")
                if item[0]=="result":
                    self["status"].setText("Dokončené.\n\nPridané: %d\nZmenené: %d\nOdstránené: %d" % (item[1]["added"],item[1]["changed"],item[1]["removed"]))
                else:self["status"].setText("Aktualizácia sa nedokončila.\n\n"+item[1])
                self.timer.stop()

    def finish(self):
        if self.done:self.close()
        else:
            self.cancel.set();self["hint"].setText("Čakám na bezpečné ukončenie…")

    def show_log(self):
        try:text=pathlib.Path("/tmp/piconhub-picons.log").read_text()[-24000:]
        except OSError:text="Log zatiaľ nie je dostupný."
        self.session.open(TextDialog,"Log aktualizácie",text)

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
        for number in (1,2,3):
            profile=config.plugins.chocholousekpicons[number]
            if not hasattr(profile,"warder_selectors"):
                profile.warder_selectors=ConfigText(default="",fixed_size=False)
            value=profile.background.value
            if value in (None,"no_satellites_was_selected","no_picons"):
                value="transparent"
            choices=list(model.STYLES)
            if value not in dict(choices):choices.append((value,"Pôvodná voľba: "+str(value)))
            profile.background=ConfigSelection(default=value,choices=choices)
            profile.background.setValue(value)
        self.profile_id=max(1,min(3,int(config.plugins.chocholousekpicons_id.getValue())))
        for name in ("day","date","clock","seconds","version","profile1","profile2","profile3","preview_caption","summary","status"):
            self[name]=Label("")
        self["background"],self["preview"]=Pixmap(),Pixmap()
        self["list"]=menu_component(self.warder_scale,82,(32,30))
        self["actions"]=ActionMap(["OkCancelActions","DirectionActions","ColorActions","NumberActions"],{
            "up":self["list"].up,"down":self["list"].down,"ok":self.open_row,
            "left":lambda:self.change_profile(-1),"right":lambda:self.change_profile(1),
            "1":lambda:self.select_profile(1),"2":lambda:self.select_profile(2),"3":lambda:self.select_profile(3),
            "cancel":self.exit,"red":self.exit,"green":self.update_picons,"yellow":self.select_satellites,"blue":self.options},-2)
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
        self["status"].setText("Načítavam aktuálny katalóg balíkov…")
        threading.Thread(target=self.refresh_catalog,daemon=True).start()

    def refresh_catalog(self):
        try:self.catalog_results.put((fetch_manifest(),None))
        except Exception as exc:self.catalog_results.put((None,str(exc)))

    def tick(self):
        if self.closed:return
        language=getattr(getattr(config,"osd",None),"language",None)
        day,date,clock,seconds=model.clock_text(language=language.value if language else "sk")
        for name,value in (("day",day),("date",date),("clock",clock),("seconds",":"+seconds),("version","v"+installed_version())):
            self[name].setText(value)
        try:catalog,error=self.catalog_results.get_nowait()
        except queue.Empty:return
        if catalog:
            self.catalog=catalog;self["status"].setText("Katalóg je aktuálny • %d balíkov" % len(catalog["packages"]))
        else:self["status"].setText("Offline • zobrazený je priložený katalóg; picony sa nemenili.")

    def refresh(self):
        profile=self.profile
        selections=model.initial_selectors(profile)
        labels=dict(model.SATELLITES)
        satellites=", ".join(labels.get(s,s) for s in selections)
        if len(satellites)>49:satellites=satellites[:46]+"… (%d)" % len(selections)
        destination=profile.picon_folder_user.value if profile.picon_folder.value=="user_defined" else profile.picon_folder.value
        rows=(("enabled","Profil","Zapnutý" if profile.allowed.value else "Vypnutý"),
              ("satellites","Satelity",satellites or "Vyberte satelity alebo poskytovateľov"),
              ("resolution","Rozlíšenie",dict(model.RESOLUTIONS).get(profile.resolution.value,profile.resolution.value)),
              ("style","Pozadie",dict(model.STYLES).get(profile.background.value,str(profile.background.value))),
              ("method","Režim",dict(model.METHODS).get(profile.method.value,profile.method.value)),
              ("destination","Priečinok",destination))
        entries=[]
        for key,label,value in rows:
            entries.append([(key,label,value),MultiContentEntryText(pos=(round(20*self.warder_scale),0),size=(round(330*self.warder_scale),round(82*self.warder_scale)),font=0,flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER,text=label),
                            MultiContentEntryText(pos=(round(365*self.warder_scale),0),size=(round(730*self.warder_scale),round(82*self.warder_scale)),font=1,flags=RT_HALIGN_LEFT|RT_VALIGN_CENTER,text=value+"  ›")])
        index=self["list"].getSelectionIndex()
        self["list"].setList(entries)
        self["list"].moveToIndex(max(index,0))
        for number in (1,2,3):
            self["profile%d" % number].setText("Profil %d" % number)
            widget=self["profile%d" % number].instance
            if widget:widget.setBackgroundColor(parseColor("#00245e89" if number==self.profile_id else "#00102136"))
        self["summary"].setText("Zdroj: Warder\nProfil: %d z 3" % self.profile_id)
        preview=ROOT/"images"/("preview-"+str(profile.background.value)+".png")
        if self["preview"].instance and preview.is_file():
            self["preview"].instance.setPixmapFromFile(str(preview));self["preview"].instance.setScale(1);self["preview"].show()
            self["preview_caption"].setText("Ukážka pozadia • 220×132")
        elif self["preview"].instance:
            self["preview"].hide();self["preview_caption"].setText("Náhľad nie je dostupný.")

    def select_profile(self,number):
        self.profile_id=number
        config.plugins.chocholousekpicons_id.setValue(number)
        config.plugins.chocholousekpicons_id.save();configfile.save();self.refresh()

    def change_profile(self,delta):
        self.select_profile((self.profile_id-1+delta)%3+1)

    def save(self):
        legacy.mainConfigScreen.cfgProfileSave(self,self.profile_id)
        self.profile.warder_selectors.save();configfile.save();self.refresh()

    def open_row(self):
        row=self["list"].getCurrent()
        if not row:return
        key=row[0][0]
        if key=="satellites":self.select_satellites();return
        choices,current={
            "enabled":(((True,"Zapnutý"),(False,"Vypnutý")),self.profile.allowed.value),
            "resolution":(model.RESOLUTIONS,self.profile.resolution.value),
            "style":(model.STYLES,self.profile.background.value),
            "method":(model.METHODS,self.profile.method.value),
            "destination":(tuple((p,label+" — "+p) for p,label in model.DESTINATIONS)+(("custom","Vlastný priečinok…"),),None)}[key]
        self.session.openWithCallback(lambda value:self.choose(key,value),ChoiceDialog,row[0][1],choices,current)

    def choose(self,key,value):
        if value is None:return
        if key=="destination":
            if value=="custom":
                self.session.openWithCallback(lambda path:self.choose("destination",path),DirectoryDialog,
                                              self.profile.picon_folder_user.value if self.profile.picon_folder.value=="user_defined" else self.profile.picon_folder.value)
                return
            self.profile.picon_folder.setValue("user_defined");self.profile.picon_folder_user.setValue(value)
        else:
            field={"enabled":"allowed","style":"background","resolution":"resolution","method":"method"}[key]
            getattr(self.profile,field).setValue(value)
        self.save()

    def select_satellites(self):
        family=model.sync.family_for_style(self.profile.background.value)
        available={p["selector_id"] for p in self.catalog["packages"] if p.get("family")==family and p.get("resolution")==self.profile.resolution.value}
        choices=[(sid,label+(" • zatiaľ nedostupné" if sid not in available else "")) for sid,label in model.SATELLITES]
        self.session.openWithCallback(self.satellites_chosen,ChoiceDialog,"Satelity a poskytovatelia",choices,model.initial_selectors(self.profile),True)

    def satellites_chosen(self,values):
        if values is None:return
        self.profile.warder_selectors.setValue(" ".join(values))
        positions=model.sync.task_positions_from_bindings([model.sync.task_binding_for_package_selector(s) for s in values])
        self.profile.sats.setValue(" ".join(positions));self.save()

    def update_picons(self):
        try:
            preferences=[model.profile_preferences(config.plugins.chocholousekpicons[n]) for n in (1,2,3) if config.plugins.chocholousekpicons[n].allowed.value]
            if not preferences:raise ValueError("Najprv zapnite aspoň jeden profil.")
        except ValueError as exc:
            self.session.open(MessageBox,str(exc),type=MessageBox.TYPE_ERROR);return
        if any(p["update_mode"]==model.sync.UPDATE_MODE_REPLACE_ALL for p in preferences):
            self.session.openWithCallback(lambda yes:self.session.open(PiconJobScreen,preferences) if yes else None,MessageBox,
                                         "Úplné nahradenie odstráni staré kanálové picony vybraných pozícií. Pokračovať?",type=MessageBox.TYPE_YESNO,default=False)
        else:self.session.open(PiconJobScreen,preferences)

    def options(self):
        self.session.openWithCallback(self.option_chosen,ChoiceDialog,"Možnosti",(("update","Skontrolovať aktualizáciu pluginu"),("reset","Obnoviť aktuálny profil"),("about","O projekte")))

    def option_chosen(self,value):
        if value=="update":self.warderUpdateCheck.request(manual=True)
        elif value=="reset":self.session.openWithCallback(self.reset_profile,MessageBox,"Obnoviť aktuálny profil?",type=MessageBox.TYPE_YESNO,default=False)
        elif value=="about":self.session.open(TextDialog,"PiconHub Warder Evolution","Verzia "+installed_version()+"\n\nWarder Evolution\nFunkčný základ: Chocholousek Picons 5.0.240904 od s3n0.\nKatalóg a plánovanie piconov: FullHDGlass Warder Evolution.")

    def reset_profile(self,accepted):
        if not accepted:return
        self.profile.allowed.setValue(False);self.profile.method.setValue("sync_tv")
        self.profile.resolution.setValue("220x132");self.profile.background.setValue("transparent")
        self.profile.picon_folder.setValue(self.profile.picon_folder.default)
        self.satellites_chosen(["192E","235E"])

    def exit(self):
        configfile.save();self.close()

    def cleanup(self):
        self.closed=True;self.clock_timer.stop()
