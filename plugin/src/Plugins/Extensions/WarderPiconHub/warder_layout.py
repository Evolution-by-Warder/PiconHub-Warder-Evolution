"""Native Enigma2 XML layout, scaled from Full HD to the receiver desktop."""
from .warder_i18n import _, localize_skin
from xml.sax.saxutils import escape


def main_skin(width=1920, height=1080):
    sx, sy = width / 1920.0, height / 1080.0
    def box(x, y, w, h):
        return 'position="%d,%d" size="%d,%d"' % (round(x*sx), round(y*sy), round(w*sx), round(h*sy))
    def label(name, x, y, w, h, font=30, text=None, color="#00ffffff", align="left"):
        nowrap = 'noWrap="1" ' if name in ("day","date","clock","seconds","version") else ""
        identity = 'name="%s"' % name if name else 'text="%s"' % escape(text or "", {'"': '&quot;'})
        element = "widget" if name else "eLabel"
        return '<%s %s %s %sfont="Regular;%d" foregroundColor="%s" transparent="1" valign="center" halign="%s" zPosition="3" />' % (element, identity, box(x,y,w,h), nowrap, round(font*sy),color,align)
    out = ['<screen position="0,0" size="%d,%d" title="PiconHub Warder Evolution" flags="wfNoBorder" backgroundColor="#00071627">' % (width,height),
           '<widget name="background" %s zPosition="0" />' % box(0,0,1920,1080)]
    def fill(x,y,w,h,color,z=2):
        return '<eLabel %s backgroundColor="%s" zPosition="%d" />' % (box(x,y,w,h),color,z)
    for x,y,w,h in ((55,325,1150,570),(1235,325,630,570)):
        out += [fill(x-4,y-4,w+8,h+8,"#00305670",1),
                fill(x,y,w,h,"#003ee8ff",1),fill(x+2,y+2,w-4,h-4,"#18091b30"),
                fill(x+2,y+2,100,4,"#00a4f4ff",3)]
    out += [label("day",1110,25,270,36,25,align="right"),label("date",980,70,400,36,24,align="right"),
            label("clock",1398,32,190,85,62,align="center"),label("seconds",1590,58,66,54,38,color="#00ffffff",align="left"),label(None,1680,25,210,36,25,text=_("Verzia: %s") % "",color="#003ee8ff",align="center"),label("version",1680,70,210,36,24,color="#003ee8ff",align="center"),
            '<eLabel %s backgroundColor="#0019c9ff" zPosition="3" />' % box(1392,25,2,84),
            '<eLabel %s backgroundColor="#0019c9ff" zPosition="3" />' % box(1664,25,2,84),
            label(None,60,236,470,78,30,text=_("Posledné pridané\npicony"),color="#009cf0ff")]
    for number in range(6):
        x=590+number*210
        out += [fill(x,225,170,92,"#00314b65"),fill(x+1,226,168,90,"#18091b30"),
                '<widget name="recent%d" %s alphatest="blend" zPosition="3" />' % (number,box(x+15,229,140,84))]
    # Subtle row separators and a bright selected row, independent of the TV skin.
    for y in (452,552,652,752):
        out.append(fill(145,y,1010,1,"#00314b65"))
    out += ['<widget name="picker_cover" %s backgroundColor="#00102136" zPosition="4" />' % box(60,332,1140,555),
            label("picker_title",80,340,1100,55,30,color="#003ee8ff").replace('zPosition="3"','zPosition="5"'),
            '<widget name="panel_progress" %s foregroundColor="#003ee8ff" backgroundColor="#00102136" transparent="0" borderWidth="1" zPosition="5" />' % box(85,856,1090,20),
            '<widget name="panel_text" %s font="Regular;%d" foregroundColor="#00ffffff" backgroundColor="#00102136" transparent="0" scrollbarMode="showOnDemand" zPosition="5" />' % (box(85,410,1090,440),round(28*sy)),
            '<widget name="list" %s transparent="1" scrollbarMode="showOnDemand" enableWrapAround="1" foregroundColor="#00ffffff" foregroundColorSelected="#00ffffff" backgroundColorSelected="#002a70ad" zPosition="5" />' % box(70,350,1120,500),
            label(None,1280,350,550,60,36,text=_("Náhľad piconu")),
            fill(1280,425,540,2,"#003ee8ff"),
            fill(1298,445,484,304,"#00314b65"),fill(1300,447,480,300,"#00061729"),
            '<widget name="preview" %s alphatest="blend" zPosition="3" />' % box(1320,465,440,264),
            '<widget name="brand_logo" %s transparent="1" zPosition="4" />' % box(1305,450,470,294),
            label("preview_caption",1270,750,560,44,23,align="center"),
            label("summary",1280,805,550,70,25,color="#00b5d4ec"),
            fill(60,916,4,34,"#003ee8ff",3),label("status",80,910,1780,45,25,color="#009cf0ff"),
            label("navigation_hint",60,957,1800,38,22,color="#00b5d4ec")]
    for name,x,color in (("red",60,"#00ff526a"),("green",520,"#0000ea9b"),("yellow",980,"#00ffdb52"),("blue",1440,"#0045b9ff")):
        out += ['<widget name="footer_%s" %s backgroundColor="#0010243c" zPosition="2" />' % (name,box(x,1010,420,60)),
                '<widget name="line_%s" %s backgroundColor="%s" zPosition="3" />' % (name,box(x+110,1010,200,3),color),
                label("key_"+name,x+10,1018,400,45,28,color=color,align="center")]
    return localize_skin("\n".join(out + ["</screen>"]))


POPUP_BACKGROUND = "#00102136"


def dialog_skin(width, height, rows=8, multiple=False, kind="choice", title="Výber"):
    """One opaque popup style, including every child text and list widget.

    Explicit backgrounds prevent receiver skins from supplying translucent TV
    backdrops to labels, ScrollLabel children or the unselected list rows.
    """
    scale = min(width / 1920.0, height / 1080.0)
    w, h = 1050, 170 + min(rows,8)*60
    def box(x,y,wide,high):
        return 'position="%d,%d" size="%d,%d"' % tuple(round(v*scale) for v in (x,y,wide,high))
    def widget(name,x,y,wide,high,font=24,color="#00ffffff",extra=""):
        font_attr = 'font="Regular;%d"' % round(font*scale) if font is not None else ""
        return '<widget name="%s" %s %s foregroundColor="%s" backgroundColor="%s" transparent="0" %s />' % (
            name,box(x,y,wide,high),font_attr,color,POPUP_BACKGROUND,extra)
    out=['<screen position="center,center" size="%d,%d" title="%s" flags="wfNoBorder" backgroundColor="%s">' %
         (round(w*scale),round(h*scale),escape(_(title),{'"':'&quot;'}),POPUP_BACKGROUND),
         widget("title",25,15,1000,50,32,"#0019c9ff"),
         '<eLabel %s backgroundColor="#003ee8ff" />' % box(20,70,1010,2)]
    for x,y,wide,high in ((0,0,w,2),(0,h-2,w,2),(0,2,2,h-4),(w-2,2,2,h-4)):
        out.append('<eLabel %s backgroundColor="#003ee8ff" />' % box(x,y,wide,high))
    if kind in ("progress","install"):
        out.append(widget("status",25,85,1000,h-235 if kind=="progress" else h-160,24 if kind=="progress" else 28,
                          extra='scrollbarMode="showOnDemand"' if kind=="progress" else ""))
        if kind=="progress":
            out.append('<widget name="progress" %s foregroundColor="#003ee8ff" backgroundColor="%s" transparent="0" borderWidth="1" />' % (box(25,h-135,1000,26),POPUP_BACKGROUND))
        footer=[("hint_red",25,490,"#00ff526a")]
        if kind=="progress":footer.append(("hint_blue",535,490,"#0045b9ff"))
    else:
        out.append(widget("list",20,80,1010,h-150,25 if kind=="text" else None,
                          extra='scrollbarMode="showOnDemand" enableWrapAround="1" foregroundColorSelected="#00ffffff" backgroundColorSelected="#002a70ad"'))
        if kind=="text":
            footer=[("hint_red",25,1000,"#00ff526a")]
        elif multiple or kind=="directory":
            footer=[("hint_ok",25,210,"#00ffffff"),("hint_green",245,440,"#0039ff59"),("hint_red",695,330,"#00ff526a")]
        else:
            footer=[("hint_ok",25,490,"#00ffffff"),("hint_red",535,490,"#00ff526a")]
    # Equal footer slots keep the action centered in its own visual position.
    slot_width = (1000 - 20*(len(footer)-1)) / len(footer)
    out.extend(widget(name,25+index*(slot_width+20),h-55,slot_width,45,24,color,
                      extra='halign="center" valign="center" noWrap="1"')
               for index,(name,x,wide,color) in enumerate(footer))
    return localize_skin("\n".join(out+["</screen>"]))


def update_skin(width, height, kind="message", version=""):
    """Full-screen Warder update family, independent of the active TV skin."""
    sx, sy = width / 1920.0, height / 1080.0
    def box(x,y,w,h):
        return 'position="%d,%d" size="%d,%d"' % (round(x*sx),round(y*sy),round(w*sx),round(h*sy))
    def label(name,x,y,w,h,font=30,color="#00ffffff",extra=""):
        return '<widget name="%s" %s font="Regular;%d" foregroundColor="%s" backgroundColor="%s" transparent="0" zPosition="5" %s />' % (name,box(x,y,w,h),round(font*sy),color,"#00071627" if y>=996 else "#00102136",extra)
    def fill(x,y,w,h,color,z=1):
        return '<eLabel %s backgroundColor="%s" zPosition="%d" />' % (box(x,y,w,h),color,z)
    out=['<screen position="0,0" size="%d,%d" flags="wfNoBorder" backgroundColor="#00071627">' % (width,height),
         '<ePixmap %s pixmap="/usr/lib/enigma2/python/Plugins/Extensions/WarderPiconHub/images/warder-background.png" scale="1" zPosition="0" />' % box(0,0,1920,1080),
         fill(135,244,1650,716,"#00102136"),fill(135,244,1650,2,"#003ee8ff"),fill(135,958,1650,2,"#003ee8ff"),
         fill(135,244,2,716,"#003ee8ff"),fill(1783,244,2,716,"#003ee8ff"),
         label("title",850,170,900,42,26,"#003ee8ff",'halign="center" valign="center"')]
    for x,y,w,h,font,fmt,align in [(1120,25,250,36,25,"%A","right"),(1020,70,350,36,24,"%d. %B %Y","right"),(1398,32,190,85,62,"%H:%M","center"),(1590,58,66,54,38,":%S","left")]:
        out.append('<widget source="global.CurrentTime" render="Label" %s font="Regular;%d" foregroundColor="#00ffffff" transparent="1" zPosition="5" halign="%s" valign="center" noWrap="1"><convert type="ClockToText">Format:%s</convert></widget>' % (box(x,y,w,h),round(font*sy),align,fmt))
    out += [fill(1392,25,2,84,"#003ee8ff",5),fill(1664,25,2,84,"#003ee8ff",5),
            '<eLabel %s text="%s" font="Regular;%d" foregroundColor="#003ee8ff" transparent="1" halign="center" valign="center" noWrap="1" zPosition="5" />' % (box(1680,70,210,36),escape(version),round(24*sy))]
    out.append('<eLabel %s text="%s" font="Regular;%d" foregroundColor="#003ee8ff" transparent="1" halign="center" valign="center" noWrap="1" zPosition="5" />' % (box(1680,25,210,36),escape((_("Verzia: %s") % "").strip()),round(25*sy)))
    if kind=="message":
        out += ['<widget name="icon" %s pixmaps="icons/input_question.png,icons/input_info.png,icons/input_warning.png,icons/input_error.png,icons/input_message.png" scale="1" alphatest="blend" conditional="icon" zPosition="5" />' % box(170,280,70,70),
                label("text",260,280,1480,460,32,extra='scrollbarMode="showOnDemand"'),
                label("list",260,770,1480,170,32,extra='itemHeight="50" foregroundColorSelected="#00ffffff" backgroundColorSelected="#002a70ad" scrollbarMode="showOnDemand"')]
    else:
        out.append('<ePixmap %s pixmap="icons/input_info.png" scale="1" alphatest="blend" zPosition="5" />' % box(170,280,70,70))
        out.append(label("status",260,280,1480,650,32,extra='scrollbarMode="showOnDemand"'))
    for name,x,color in [("red",135,"#00ff526a"),("green",968,"#0039ff59")]:
        out += ['<widget name="line_%s" %s backgroundColor="%s" zPosition="5" />' % (name,box(x+308,996,200,2),color),label("key_"+name,x,1006,817,50,28,color,'halign="center" valign="center" noWrap="1"')]
    out.append(fill(0,984,1920,96,"#00071627",1))
    # Footer backgrounds match the surrounding page, including hidden controls.
    return localize_skin("\n".join(out+["</screen>"]))
