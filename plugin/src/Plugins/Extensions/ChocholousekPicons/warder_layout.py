"""Native Enigma2 XML layout, scaled from Full HD to the receiver desktop."""
from xml.sax.saxutils import escape


def main_skin(width=1920, height=1080):
    sx, sy = width / 1920.0, height / 1080.0
    def box(x, y, w, h):
        return 'position="%d,%d" size="%d,%d"' % (round(x*sx), round(y*sy), round(w*sx), round(h*sy))
    def label(name, x, y, w, h, font=30, text=None, color="#00ffffff", align="left"):
        identity = 'name="%s"' % name if name else 'text="%s"' % escape(text or "", {'"': '&quot;'})
        element = "widget" if name else "eLabel"
        return '<%s %s %s font="Regular;%d" foregroundColor="%s" transparent="1" valign="center" halign="%s" zPosition="3" />' % (element, identity, box(x,y,w,h), round(font*sy),color,align)
    out = ['<screen position="0,0" size="%d,%d" title="PiconHub Warder Evolution" flags="wfNoBorder" backgroundColor="#00071627">' % (width,height),
           '<widget name="background" %s zPosition="0" />' % box(0,0,1920,1080)]
    for x,y,w,h in ((55,340,1150,555),(1235,340,630,555)):
        out += ['<eLabel %s backgroundColor="#0019c9ff" zPosition="1" />' % box(x,y,w,h),
                '<eLabel %s backgroundColor="#00102136" zPosition="2" />' % box(x+2,y+2,w-4,h-4)]
    out += [label("day",1250,32,230,42,26,align="right"),label("date",1160,76,320,40,25,align="right"),
            label("clock",1498,32,190,85,62,align="center"),label("seconds",1690,64,56,48,32,align="left"),label("version",1770,45,140,60,24,align="center"),
            '<eLabel %s backgroundColor="#0019c9ff" zPosition="3" />' % box(1492,35,2,80),
            '<eLabel %s backgroundColor="#0019c9ff" zPosition="3" />' % box(1752,35,2,80),
            label(None,60,250,650,70,46,text="Nastavenie piconov")]
    for index,x in enumerate((740,1120,1500),1):
        out.append(label("profile%d" % index,x,260,350,65,34,align="center").replace('transparent="1"','backgroundColor="#00102136" transparent="0"'))
    out += ['<widget name="list" %s transparent="1" scrollbarMode="showOnDemand" enableWrapAround="1" foregroundColor="#00ffffff" backgroundColorSelected="#00245e89" zPosition="3" />' % box(70,365,1120,510),
            label(None,1280,360,550,60,38,text="Náhľad piconu"),
            '<widget name="preview" %s alphatest="blend" zPosition="3" />' % box(1320,465,440,264),
            label("preview_caption",1270,750,560,44,23,align="center"),
            label("summary",1280,805,550,70,25),label("status",60,915,1800,45,25),
            label(None,60,960,1650,38,22,text="Nastavenia sa ukladajú automaticky.  ← → alebo 1–3: profil • OK: výber")]
    for x,color,title in ((65,"#00ff4055","Späť"),(510,"#0000df70","Aktualizovať"),(990,"#00ffdb25","Satelity"),(1430,"#002ca4ff","Možnosti")):
        out += [label(None,x,1010,55,60,46,text="●",color=color),label(None,x+65,1010,370,60,29,text=title)]
    return "\n".join(out + ["</screen>"])


def dialog_skin(width, height, rows=8):
    scale = min(width / 1920.0, height / 1080.0)
    w, h = round(1050*scale), round((170+min(rows,8)*60)*scale)
    return '''<screen position="center,center" size="%d,%d" title="Výber" backgroundColor="#00102136">
      <widget name="title" position="%d,%d" size="%d,%d" font="Regular;%d" foregroundColor="#0019c9ff" />
      <widget name="list" position="%d,%d" size="%d,%d" scrollbarMode="showOnDemand" enableWrapAround="1" foregroundColor="#00ffffff" backgroundColorSelected="#00245e89" />
      <widget name="hint" position="%d,%d" size="%d,%d" font="Regular;%d" foregroundColor="#00ffffff" />
    </screen>''' % (w,h,round(25*scale),round(15*scale),w-round(50*scale),round(50*scale),round(32*scale),
                   round(20*scale),round(80*scale),w-round(40*scale),h-round(150*scale),
                   round(25*scale),h-round(55*scale),w-round(50*scale),round(45*scale),round(24*scale))
