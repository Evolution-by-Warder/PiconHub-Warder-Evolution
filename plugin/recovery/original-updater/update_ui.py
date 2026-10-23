# -*- coding: utf-8 -*-
from __future__ import print_function
from threading import Thread
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.Pixmap import Pixmap
from Components.ProgressBar import ProgressBar
from Screens.Screen import Screen
from enigma import eTimer,getDesktop,ePoint
from . import plugin as p
from . import plugin_updater as pu
W='#ffffff'; T='#dbefff'; C='#6fdcff'; G='#4ee878'; R='#ff5968'

def _desk():
    try:
        s=getDesktop(0).size(); return s.width(),s.height()
    except Exception:return 1920,1080

def _head(hd):
    if hd:return ['<widget name="section" position="72,153" size="570,38" zPosition="4" font="Regular;28" foregroundColor="%s" transparent="1" />'%C,'<widget name="summary" position="660,153" size="570,42" zPosition="4" font="Regular;19" foregroundColor="%s" transparent="1" halign="right" />'%W]
    return ['<widget name="section" position="108,230" size="840,55" zPosition="4" font="Regular;40" foregroundColor="%s" transparent="1" />'%C,'<widget name="summary" position="1010,230" size="790,60" zPosition="4" font="Regular;27" foregroundColor="%s" transparent="1" halign="right" />'%W]

def _keys(hd):
    if hd:return ['<widget name="red_btn" position="38,620" size="278,56" zPosition="4" alphatest="blend" />','<widget name="red_icon" position="52,626" size="52,42" zPosition="6" font="Regular;31" foregroundColor="%s" transparent="1" halign="center" valign="center" />'%R,'<widget name="red_title" position="116,628" size="180,21" zPosition="6" font="Regular;18" foregroundColor="%s" transparent="1" />'%W,'<widget name="red_sub" position="116,650" size="180,17" zPosition="6" font="Regular;11" foregroundColor="#d9d9d9" transparent="1" />','<widget name="green_btn" position="347,620" size="278,56" zPosition="4" alphatest="blend" />','<widget name="green_icon" position="361,626" size="52,42" zPosition="6" font="Regular;14" foregroundColor="%s" transparent="1" halign="center" valign="center" />'%G,'<widget name="green_title" position="425,628" size="180,21" zPosition="6" font="Regular;16" foregroundColor="%s" transparent="1" />'%W,'<widget name="green_sub" position="425,650" size="180,17" zPosition="6" font="Regular;11" foregroundColor="#d9d9d9" transparent="1" />']
    return ['<widget name="red_btn" position="58,930" size="416,84" zPosition="4" alphatest="blend" />','<widget name="red_icon" position="78,941" size="78,58" zPosition="6" font="Regular;46" foregroundColor="%s" transparent="1" halign="center" valign="center" />'%R,'<widget name="red_title" position="176,942" size="266,31" zPosition="6" font="Regular;27" foregroundColor="%s" transparent="1" />'%W,'<widget name="red_sub" position="176,977" size="266,22" zPosition="6" font="Regular;16" foregroundColor="#d9d9d9" transparent="1" />','<widget name="green_btn" position="521,930" size="416,84" zPosition="4" alphatest="blend" />','<widget name="green_icon" position="541,941" size="78,58" zPosition="6" font="Regular;18" foregroundColor="%s" transparent="1" halign="center" valign="center" />'%G,'<widget name="green_title" position="639,942" size="266,31" zPosition="6" font="Regular;23" foregroundColor="%s" transparent="1" />'%W,'<widget name="green_sub" position="639,977" size="266,22" zPosition="6" font="Regular;16" foregroundColor="#d9d9d9" transparent="1" />']

def _init(o,s,n,extra,keys=True):
    a=['<widget name="bg" position="0,0" size="%d,%d" zPosition="0" alphatest="blend" />'%(o.gw,o.gh)]+_head(o.hd)+(_keys(o.hd) if keys else [])+extra
    a.extend(p._system_header_widgets(o.hd)); o.skin='<screen name="%s" position="0,0" size="%d,%d" flags="wfNoBorder" backgroundColor="#00000000">%s</screen>'%(n,o.gw,o.gh,''.join(a)); Screen.__init__(o,s)
    o['bg']=Pixmap(); o['version']=Label(''); p._setup_system_header(o)
    if keys:
        o['red_btn']=Pixmap(); o['red_icon']=Label('↩'); o['red_title']=Label(''); o['red_sub']=Label(''); o['green_btn']=Pixmap(); o['green_icon']=Label('OK'); o['green_title']=Label(''); o['green_sub']=Label('')

def _ready(o):
    m='hd' if o.hd else 'fhd'; o['bg'].instance.setPixmapFromFile(p.os.path.join(p.ASSET_PATH,'picons_%s_base.jpg'%m))
    if 'red_btn' in o:
        o['red_btn'].instance.setPixmapFromFile(p.os.path.join(p.ASSET_PATH,'picons_btn_red_%s.png'%m)); o['green_btn'].instance.setPixmapFromFile(p.os.path.join(p.ASSET_PATH,'picons_btn_green_%s.png'%m))

def _buttons(o,red=('SPÄŤ','Návrat do hlavnej ponuky'),green=('OK, SPUSTIŤ','Potvrdiť vybranú aktualizáciu')):
    if red:o['red_title'].setText(red[0]);o['red_sub'].setText(red[1])
    else:
        for k in ('red_btn','red_icon','red_title','red_sub'):o[k].hide()
    if green:o['green_title'].setText(green[0]);o['green_sub'].setText(green[1])
    else:
        for k in ('green_btn','green_icon','green_title','green_sub'):o[k].hide()

def _choice(hd):
    if hd:return ['<widget name="focus" position="72,220" size="770,66" zPosition="2" backgroundColor="#07506a" transparent="0" />','<widget name="list" position="88,222" size="740,124" zPosition="4" font="Regular;22" itemHeight="62" transparent="1" selectionDisabled="1" />','<widget name="name" position="900,275" size="320,45" zPosition="5" font="Regular;25" foregroundColor="%s" transparent="1" halign="center" />'%W,'<widget name="state" position="900,335" size="320,38" zPosition="5" font="Regular;20" foregroundColor="%s" transparent="1" halign="center" />'%G,'<widget name="detail" position="890,395" size="340,105" zPosition="5" font="Regular;17" foregroundColor="%s" transparent="1" halign="center" />'%T]
    return ['<widget name="focus" position="108,330" size="1155,99" zPosition="2" backgroundColor="#07506a" transparent="0" />','<widget name="list" position="132,333" size="1110,186" zPosition="4" font="Regular;30" itemHeight="92" transparent="1" selectionDisabled="1" />','<widget name="name" position="1365,410" size="430,65" zPosition="5" font="Regular;34" foregroundColor="%s" transparent="1" halign="center" />'%W,'<widget name="state" position="1365,500" size="430,50" zPosition="5" font="Regular;26" foregroundColor="%s" transparent="1" halign="center" />'%G,'<widget name="detail" position="1345,590" size="470,150" zPosition="5" font="Regular;23" foregroundColor="%s" transparent="1" halign="center" />'%T]

class PiconHubUpdateChoice(Screen):
    def __init__(self,s):
        self.session=s;self.gw,self.gh=_desk();self.hd=self.gw<=1280;self.checking=False;self.pending=None;self._check_done=False;self._check_result=None;self._check_error=None;_init(self,s,'PiconHubUpdateChoice',_choice(self.hd),True)
        self['section']=Label('↻  AKTUALIZÁCIA');self['summary']=Label('Vyber, čo chceš aktualizovať');self['focus']=Label('');self['list']=MenuList(['AKTUALIZOVAŤ PICONY','AKTUALIZOVAŤ PLUGIN']);self['name']=Label('');self['state']=Label('');self['detail']=Label('');_buttons(self)
        self['actions']=ActionMap(['OkCancelActions','DirectionActions','ColorActions'],{'cancel':self.close,'red':self.close,'ok':self.open_selected,'green':self.open_selected,'up':self.up,'down':self.down},-1);self.poll=eTimer();self.poll.callback.append(self._poll);self.onLayoutFinish.append(self._onready)
    def _onready(self):_ready(self);self._sel()
    def _idx(self):
        try:return self['list'].getSelectedIndex()
        except Exception:return 0
    def _sel(self):
        i=self._idx()
        try:self['focus'].instance.move(ePoint(72 if self.hd else 108,(220 if i==0 else 282) if self.hd else (330 if i==0 else 422)))
        except Exception:pass
        if i==0:self['name'].setText('PICONY');self['state'].setText('AKTUALIZÁCIA DATABÁZY');self['detail'].setText('Stiahne chýbajúce alebo zmenené\npicony podľa tvojich nastavení.')
        else:self['name'].setText('PLUGIN');self['state'].setText('AKTUALIZÁCIA PICONHUBU');self['detail'].setText('Skontroluje novú verziu PiconHubu\na bezpečne ju nainštaluje.')
    def up(self):
        if not self.checking:self['list'].up();self._sel()
    def down(self):
        if not self.checking:self['list'].down();self._sel()
    def open_selected(self):
        if self.checking:return
        if self._idx()==0:self.session.open(p.PiconHubUpdateScreen);return
        self.checking=True;self['summary'].setText('Kontrolujem dostupnú verziu...');self._check_done=False;self._check_result=None;self._check_error=None
        def w():
            try:self._check_result=pu.PiconHubPluginUpdater(timeout=6).check()
            except Exception as e:self._check_error=str(e)
            self._check_done=True
        t=Thread(target=w);t.daemon=True;t.start();self.poll.start(100,True)
    def _poll(self):
        if not self._check_done:self.poll.start(100,True);return
        self.checking=False;self['summary'].setText('Vyber, čo chceš aktualizovať');self._sel()
        if self._check_error:self.session.open(PiconHubUpdateStatus,'KONTROLA AKTUALIZÁCIE ZLYHALA','Nepodarilo sa overiť dostupnú verziu PiconHubu.',self._check_error,True);return
        r=self._check_result or {}
        if not r.get('available'):
            v=r.get('remote_version') or r.get('current_version') or pu.RELEASE_VERSION;self.session.open(PiconHubUpdateStatus,'POUŽÍVAŠ NAJNOVŠIU VERZIU','PiconHub %s je aktuálny.'%v,'Nie je potrebná žiadna aktualizácia pluginu.',False);return
        self.pending=r.get('manifest');self.session.openWithCallback(self._confirmed,PiconHubPluginConfirm,r)
    def _confirmed(self,a):
        if a and self.pending:self.session.open(PiconHubPluginProgress,self.pending)

def _dialog(hd,status=False):
    if hd:
        if status:return ['<widget name="icon" position="150,285" size="150,150" zPosition="5" font="Regular;96" foregroundColor="%s" transparent="1" halign="center" valign="center" />'%G,'<widget name="title" position="330,280" size="800,60" zPosition="5" font="Regular;31" foregroundColor="%s" transparent="1" />'%W,'<widget name="message" position="330,360" size="800,55" zPosition="5" font="Regular;23" foregroundColor="%s" transparent="1" />'%T,'<widget name="detail" position="330,430" size="800,90" zPosition="5" font="Regular;18" foregroundColor="#9fc4d7" transparent="1" />']
        return ['<widget name="title" position="90,260" size="720,55" zPosition="5" font="Regular;30" foregroundColor="%s" transparent="1" halign="center" />'%W,'<widget name="versions" position="90,345" size="720,120" zPosition="5" font="Regular;22" foregroundColor="%s" transparent="1" halign="center" />'%T,'<widget name="notes_title" position="900,270" size="320,42" zPosition="5" font="Regular;24" foregroundColor="%s" transparent="1" halign="center" />'%C,'<widget name="notes" position="880,330" size="360,220" zPosition="5" font="Regular;17" foregroundColor="%s" transparent="1" halign="center" />'%T]
    if status:return ['<widget name="icon" position="225,425" size="225,225" zPosition="5" font="Regular;140" foregroundColor="%s" transparent="1" halign="center" valign="center" />'%G,'<widget name="title" position="510,425" size="1210,80" zPosition="5" font="Regular;45" foregroundColor="%s" transparent="1" />'%W,'<widget name="message" position="510,545" size="1210,75" zPosition="5" font="Regular;33" foregroundColor="%s" transparent="1" />'%T,'<widget name="detail" position="510,650" size="1210,135" zPosition="5" font="Regular;25" foregroundColor="#9fc4d7" transparent="1" />']
    return ['<widget name="title" position="135,390" size="1080,80" zPosition="5" font="Regular;44" foregroundColor="%s" transparent="1" halign="center" />'%W,'<widget name="versions" position="135,520" size="1080,180" zPosition="5" font="Regular;31" foregroundColor="%s" transparent="1" halign="center" />'%T,'<widget name="notes_title" position="1365,405" size="430,55" zPosition="5" font="Regular;34" foregroundColor="%s" transparent="1" halign="center" />'%C,'<widget name="notes" position="1335,490" size="490,330" zPosition="5" font="Regular;23" foregroundColor="%s" transparent="1" halign="center" />'%T]

class PiconHubPluginConfirm(Screen):
    def __init__(self,s,r):
        self.session=s;self.result=r or {};self.gw,self.gh=_desk();self.hd=self.gw<=1280;_init(self,s,'PiconHubPluginConfirm',_dialog(self.hd),True);self['section']=Label('↻  AKTUALIZÁCIA PICONHUBU');self['summary']=Label('Je dostupná nová verzia');self['title']=Label('SPUSTIŤ AKTUALIZÁCIU?');self['versions']=Label('Aktuálna verzia: %s\nNová verzia: %s\n\nPo dokončení sa Enigma2 GUI automaticky reštartuje.'%(self.result.get('current_version') or '—',self.result.get('remote_version') or '—'));self['notes_title']=Label('ČO JE NOVÉ');self['notes']=Label(self.result.get('notes') or 'Bez poznámok k vydaniu.');_buttons(self,('SPÄŤ','Zrušiť aktualizáciu'),('AKTUALIZOVAŤ','Nainštalovať novú verziu'));self['actions']=ActionMap(['OkCancelActions','ColorActions'],{'cancel':lambda:self.close(False),'red':lambda:self.close(False),'ok':lambda:self.close(True),'green':lambda:self.close(True)},-1);self.onLayoutFinish.append(lambda:_ready(self))

class PiconHubUpdateStatus(Screen):
    def __init__(self,s,title,msg,detail='',error=False):
        self.session=s;self.gw,self.gh=_desk();self.hd=self.gw<=1280;_init(self,s,'PiconHubUpdateStatus',_dialog(self.hd,True),True);self['section']=Label('↻  AKTUALIZÁCIA PICONHUBU');self['summary']=Label('Stav aktualizácie');self['icon']=Label('!' if error else '✓');self['title']=Label(title);self['message']=Label(msg);self['detail']=Label(detail);_buttons(self,('SPÄŤ','Návrat do aktualizácie'),None);self['actions']=ActionMap(['OkCancelActions','ColorActions'],{'cancel':self.close,'red':self.close,'ok':self.close},-1);self.onLayoutFinish.append(lambda:_ready(self))

def _prog(hd):
    if hd:return ['<widget name="phase" position="90,300" size="720,60" zPosition="5" font="Regular;29" foregroundColor="%s" transparent="1" halign="center" />'%W,'<widget name="info" position="90,390" size="720,130" zPosition="5" font="Regular;20" foregroundColor="%s" transparent="1" halign="center" />'%T,'<widget name="progress" position="900,365" size="320,28" zPosition="5" borderWidth="2" borderColor="%s" />'%C,'<widget name="percent" position="900,410" size="320,55" zPosition="5" font="Regular;31" foregroundColor="%s" transparent="1" halign="center" />'%W,'<widget name="detail" position="880,480" size="360,75" zPosition="5" font="Regular;16" foregroundColor="#9fc4d7" transparent="1" halign="center" />']
    return ['<widget name="phase" position="135,450" size="1080,90" zPosition="5" font="Regular;42" foregroundColor="%s" transparent="1" halign="center" />'%W,'<widget name="info" position="135,585" size="1080,195" zPosition="5" font="Regular;29" foregroundColor="%s" transparent="1" halign="center" />'%T,'<widget name="progress" position="1360,545" size="440,40" zPosition="5" borderWidth="2" borderColor="%s" />'%C,'<widget name="percent" position="1360,610" size="440,80" zPosition="5" font="Regular;45" foregroundColor="%s" transparent="1" halign="center" />'%W,'<widget name="detail" position="1335,720" size="490,110" zPosition="5" font="Regular;23" foregroundColor="#9fc4d7" transparent="1" halign="center" />']

class PiconHubPluginProgress(Screen):
    def __init__(self,s,m):
        self.session=s;self.manifest=m or {};self.gw,self.gh=_desk();self.hd=self.gw<=1280;self.done=False;self.error=None;self.remote=None;self.countdown=3;_init(self,s,'PiconHubPluginProgress',_prog(self.hd),False);self['section']=Label('↻  AKTUALIZÁCIA PICONHUBU');self['summary']=Label('Bezpečná inštalácia');self['phase']=Label('PRIPRAVUJEM AKTUALIZÁCIU');self['info']=Label('Súbory sa stiahnu, overia SHA-256 a až potom nainštalujú.');self['progress']=ProgressBar();self['progress'].setRange((0,100));self['progress'].setValue(10);self['percent']=Label('10 %');self['detail']=Label('Kontrolujem manifest...');self['actions']=ActionMap(['OkCancelActions'],{'cancel':self.ignore,'ok':self.ignore},-1);self.timer=eTimer();self.timer.callback.append(self._poll);self.onLayoutFinish.append(self._onready)
    def ignore(self):return
    def _onready(self):
        _ready(self)
        def w():
            try:self.remote=pu.PiconHubPluginUpdater(timeout=8).install(self.manifest)
            except Exception as e:self.error=str(e)
            self.done=True
        t=Thread(target=w);t.daemon=True;t.start();self['progress'].setValue(55);self['percent'].setText('55 %');self['phase'].setText('SŤAHUJEM, OVERUJEM A INŠTALUJEM');self['detail'].setText('SHA-256 + záloha + rollback');self.timer.start(150,True)
    def _poll(self):
        if not self.done:self.timer.start(150,True);return
        if self.error:self['progress'].setValue(0);self['percent'].setText('CHYBA');self['phase'].setText('AKTUALIZÁCIA ZLYHALA');self['summary'].setText('Pôvodná verzia zostala zachovaná');self['info'].setText(self.error);self['detail'].setText('GUI sa nereštartuje.');self['actions']=ActionMap(['OkCancelActions'],{'cancel':self.close,'ok':self.close},-1);return
        self['progress'].setValue(100);self['percent'].setText('100 %');self['phase'].setText('AKTUALIZÁCIA DOKONČENÁ');self['summary'].setText('Nová verzia je nainštalovaná');self['detail'].setText('Overenie a inštalácia prebehli úspešne.');self['info'].setText('Enigma2 GUI sa automaticky reštartuje za 3 sekundy.');self.timer.callback.remove(self._poll);self.timer.callback.append(self._tick);self.timer.start(1000,True)
    def _tick(self):
        self.countdown-=1
        if self.countdown<=0:pu._restart_gui(self.session);return
        self['info'].setText('Enigma2 GUI sa automaticky reštartuje za %d sekundy.'%self.countdown);self.timer.start(1000,True)

def _latest(s,r=None):
    r=r or {};v=r.get('remote_version') or r.get('current_version') or pu.RELEASE_VERSION;s.session.open(PiconHubUpdateStatus,'POUŽÍVAŠ NAJNOVŠIU VERZIU','PiconHub %s je aktuálny.'%v,'Nie je potrebná žiadna aktualizácia pluginu.',False)
def _error(s,e):s.session.open(PiconHubUpdateStatus,'KONTROLA AKTUALIZÁCIE ZLYHALA','Nepodarilo sa overiť dostupnú verziu PiconHubu.',str(e or 'Neznáma chyba.'),True)
def _offer(s,r,manual=False):
    r=r or {}
    if r.get('available'):
        def c(a):
            if a and r.get('manifest'):s.session.open(PiconHubPluginProgress,r.get('manifest'))
        s.session.openWithCallback(c,PiconHubPluginConfirm,r)
    elif manual:_latest(s,r)
def _manual(s):
    try:r=pu.PiconHubPluginUpdater().check()
    except Exception as e:_error(s,e);return
    _offer(s,r,True)
def _layout(self):
    pu._original_layout_ready(self)
    if pu._AUTO_CHECK_DONE:return
    pu._AUTO_CHECK_DONE=True;self._phdone=False;self._phr=None;self._phe=None;self._phd=eTimer();self._php=eTimer()
    def w():
        try:self._phr=pu.PiconHubPluginUpdater(timeout=4).check()
        except Exception as e:self._phe=str(e)
        self._phdone=True
    def b():
        t=Thread(target=w);t.daemon=True;t.start();self._php.start(100,True)
    def q():
        if not self._phdone:self._php.start(100,True);return
        if not self._phe:_offer(self,self._phr or {},False)
    self._phd.callback.append(b);self._php.callback.append(q);self._phd.start(1800,True)
p.PiconHubUpdateMenu=PiconHubUpdateChoice;pu._offer_update=_offer;pu._manual_update_check=_manual;p.PiconHubMain._layoutReady=_layout
