# -*- coding: utf-8 -*-
from __future__ import print_function

import os
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from enigma import ePoint
from . import plugin as p
from . import update_ui as ui


def _footer(hd, buttons=True):
    if hd:
        w=['<widget name="u18_footer" position="20,612" size="1240,72" zPosition="1" backgroundColor="#021f2c" transparent="0" />']
        if buttons: w += ['<widget name="u18_red" position="38,620" size="278,56" zPosition="5" alphatest="blend" />','<widget name="u18_green" position="347,620" size="278,56" zPosition="5" alphatest="blend" />','<widget name="u18_red_title" position="102,628" size="194,21" zPosition="7" font="Regular;18" foregroundColor="#ffffff" transparent="1" halign="left" valign="center" />','<widget name="u18_red_sub" position="102,650" size="194,17" zPosition="7" font="Regular;11" foregroundColor="#d9d9d9" transparent="1" halign="left" valign="center" />','<widget name="u18_green_title" position="411,628" size="194,21" zPosition="7" font="Regular;15" foregroundColor="#ffffff" transparent="1" halign="left" valign="center" />','<widget name="u18_green_sub" position="411,650" size="194,17" zPosition="7" font="Regular;11" foregroundColor="#d9d9d9" transparent="1" halign="left" valign="center" />']
        return w
    w=['<widget name="u18_footer" position="30,918" size="1860,108" zPosition="1" backgroundColor="#021f2c" transparent="0" />']
    if buttons: w += ['<widget name="u18_red" position="58,930" size="416,84" zPosition="5" alphatest="blend" />','<widget name="u18_green" position="521,930" size="416,84" zPosition="5" alphatest="blend" />','<widget name="u18_red_title" position="156,942" size="286,31" zPosition="7" font="Regular;27" foregroundColor="#ffffff" transparent="1" halign="left" valign="center" />','<widget name="u18_red_sub" position="156,977" size="286,22" zPosition="7" font="Regular;16" foregroundColor="#d9d9d9" transparent="1" halign="left" valign="center" />','<widget name="u18_green_title" position="619,942" size="286,31" zPosition="7" font="Regular;22" foregroundColor="#ffffff" transparent="1" halign="left" valign="center" />','<widget name="u18_green_sub" position="619,977" size="286,22" zPosition="7" font="Regular;16" foregroundColor="#d9d9d9" transparent="1" halign="left" valign="center" />']
    return w


def _choice_widgets(hd):
    if hd:
        w=['<widget name="bg" position="0,0" size="1280,127" zPosition="0" alphatest="blend" />','<widget name="u18_body" position="20,127" size="1240,485" zPosition="0" backgroundColor="#022635" transparent="0" />','<widget name="section" position="72,153" size="570,38" zPosition="4" font="Regular;28" foregroundColor="#6fdcff" transparent="1" />','<widget name="summary" position="660,153" size="570,42" zPosition="4" font="Regular;19" foregroundColor="#ffffff" transparent="1" halign="right" />','<widget name="u18_card" position="62,214" size="790,156" zPosition="1" backgroundColor="#032b3a" borderWidth="1" borderColor="#1c5368" transparent="0" />','<widget name="u18_focus" position="70,222" size="774,68" zPosition="2" backgroundColor="#07506a" borderWidth="1" borderColor="#55d8ff" transparent="0" />','<widget name="list" position="88,230" size="742,126" zPosition="4" font="Regular;22" itemHeight="62" transparent="1" selectionDisabled="1" />','<widget name="u18_div" position="880,214" size="1,330" zPosition="2" backgroundColor="#39bff8" transparent="0" />','<widget name="name" position="900,275" size="320,45" zPosition="5" font="Regular;25" foregroundColor="#ffffff" transparent="1" halign="center" />','<widget name="state" position="900,335" size="320,38" zPosition="5" font="Regular;20" foregroundColor="#4ee878" transparent="1" halign="center" />','<widget name="detail" position="890,395" size="340,105" zPosition="5" font="Regular;17" foregroundColor="#dbefff" transparent="1" halign="center" />']
    else:
        w=['<widget name="bg" position="0,0" size="1920,190" zPosition="0" alphatest="blend" />','<widget name="u18_body" position="30,190" size="1860,728" zPosition="0" backgroundColor="#022635" transparent="0" />','<widget name="section" position="108,230" size="840,55" zPosition="4" font="Regular;40" foregroundColor="#6fdcff" transparent="1" />','<widget name="summary" position="1010,230" size="790,60" zPosition="4" font="Regular;27" foregroundColor="#ffffff" transparent="1" halign="right" />','<widget name="u18_card" position="92,322" size="1185,234" zPosition="1" backgroundColor="#032b3a" borderWidth="2" borderColor="#1c5368" transparent="0" />','<widget name="u18_focus" position="104,334" size="1161,102" zPosition="2" backgroundColor="#07506a" borderWidth="2" borderColor="#55d8ff" transparent="0" />','<widget name="list" position="132,346" size="1110,190" zPosition="4" font="Regular;30" itemHeight="92" transparent="1" selectionDisabled="1" />','<widget name="u18_div" position="1320,322" size="2,495" zPosition="2" backgroundColor="#39bff8" transparent="0" />','<widget name="name" position="1365,410" size="430,65" zPosition="5" font="Regular;34" foregroundColor="#ffffff" transparent="1" halign="center" />','<widget name="state" position="1365,500" size="430,50" zPosition="5" font="Regular;26" foregroundColor="#4ee878" transparent="1" halign="center" />','<widget name="detail" position="1345,590" size="470,150" zPosition="5" font="Regular;23" foregroundColor="#dbefff" transparent="1" halign="center" />']
    return w+_footer(hd,True)


def _load_buttons(self):
    mode='hd' if self.hd else 'fhd'
    try:
        self['u18_red'].instance.setPixmapFromFile(os.path.join(p.ASSET_PATH,'news_btn_red_%s.png'%mode))
        self['u18_green'].instance.setPixmapFromFile(os.path.join(p.ASSET_PATH,'picons_btn_green_%s.png'%mode))
    except Exception as e: print('[PiconHub] updater button asset error:',e)


def _install(self,rt,rs,gt,gs):
    self['u18_footer']=Label(''); self['u18_red']=Pixmap(); self['u18_green']=Pixmap()
    self['u18_red_title']=Label(rt); self['u18_red_sub']=Label(rs); self['u18_green_title']=Label(gt); self['u18_green_sub']=Label(gs)
    self.onLayoutFinish.append(self._u18_load_buttons)

ui._choice_widgets=_choice_widgets
_old_ci=ui.PiconHubUpdateChoice.__init__; _old_sel=ui.PiconHubUpdateChoice._selected
ui.PiconHubUpdateChoice._u18_load_buttons=_load_buttons
def _ci(self,session):
    _old_ci(self,session); self['u18_body']=Label(''); self['u18_card']=Label(''); self['u18_focus']=Label(''); self['u18_div']=Label('')
    _install(self,'SPÄŤ','Návrat do hlavnej ponuky','OK, SPUSTIŤ AKTUALIZÁCIU','Potvrdiť vybranú aktualizáciu')
    self['actions']=ActionMap(['OkCancelActions','DirectionActions','ColorActions'],{'cancel':self.close,'red':self.close,'ok':self.open_selected,'green':self.open_selected,'up':self.up,'down':self.down},-1)
def _sel(self):
    _old_sel(self)
    try:
        x=70 if self.hd else 104; y=((222 if self._index()==0 else 284) if self.hd else (334 if self._index()==0 else 426))
        self['u18_focus'].instance.move(ePoint(x,y))
    except Exception: pass
ui.PiconHubUpdateChoice.__init__=_ci; ui.PiconHubUpdateChoice._selected=_sel

ui._u18_original_dialog_widgets=ui._dialog_widgets
def _dw(hd,status=False,error=False):
    w=ui._u18_original_dialog_widgets(hd,status,error); w[0]='<widget name="bg" position="0,0" size="%s" zPosition="0" alphatest="blend" />'%('1280,127' if hd else '1920,190')
    body='<widget name="u18_body" position="%s" size="%s" zPosition="0" backgroundColor="#022635" transparent="0" />'%((('20,127','1240,485') if hd else ('30,190','1860,728')))
    return [w[0],body]+w[1:]+_footer(hd,True)
ui._dialog_widgets=_dw

_old_con=ui.PiconHubPluginConfirm.__init__; ui.PiconHubPluginConfirm._u18_load_buttons=_load_buttons
def _con(self,session,result):
    _old_con(self,session,result); self['u18_body']=Label(''); _install(self,'SPÄŤ','Zrušiť aktualizáciu','OK, SPUSTIŤ AKTUALIZÁCIU','Nainštalovať novú verziu')
ui.PiconHubPluginConfirm.__init__=_con

_old_st=ui.PiconHubUpdateStatus.__init__; ui.PiconHubUpdateStatus._u18_load_buttons=_load_buttons
def _st(self,session,title,message,detail='',error=False):
    _old_st(self,session,title,message,detail,error); self['u18_body']=Label(''); _install(self,'SPÄŤ','Návrat na výber','OK','Zavrieť stav aktualizácie')
    self['actions']=ActionMap(['OkCancelActions','ColorActions'],{'cancel':self.close,'red':self.close,'ok':self.close,'green':self.close},-1)
ui.PiconHubUpdateStatus.__init__=_st

ui._u18_original_progress_widgets=ui._progress_widgets
def _pw(hd):
    w=ui._u18_original_progress_widgets(hd); w[0]='<widget name="bg" position="0,0" size="%s" zPosition="0" alphatest="blend" />'%('1280,127' if hd else '1920,190')
    body='<widget name="u18_body" position="%s" size="%s" zPosition="0" backgroundColor="#022635" transparent="0" />'%((('20,127','1240,557') if hd else ('30,190','1860,836')))
    return [w[0],body]+w[1:]
ui._progress_widgets=_pw
_old_pr=ui.PiconHubPluginProgress.__init__
def _pr(self,session,manifest): _old_pr(self,session,manifest); self['u18_body']=Label('')
ui.PiconHubPluginProgress.__init__=_pr
