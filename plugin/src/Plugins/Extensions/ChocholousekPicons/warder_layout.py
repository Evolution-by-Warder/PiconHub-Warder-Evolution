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
    def fill(x,y,w,h,color,z=2):
        return '<eLabel %s backgroundColor="%s" zPosition="%d" />' % (box(x,y,w,h),color,z)
    for x,y,w,h in ((55,325,1150,570),(1235,325,630,570)):
        out += [fill(x-4,y-4,w+8,h+8,"#00305670",1),
                fill(x,y,w,h,"#003ee8ff",1),fill(x+2,y+2,w-4,h-4,"#18091b30"),
                fill(x+2,y+2,100,4,"#00a4f4ff",3)]
    out += [label("day",1150,32,230,42,26,align="right"),label("date",1060,76,320,40,25,align="right"),
            label("clock",1398,32,190,85,62,align="center"),label("seconds",1590,58,66,54,38,color="#00ffffff",align="left"),label("version",1680,45,210,60,24,color="#003ee8ff",align="center"),
            '<eLabel %s backgroundColor="#0019c9ff" zPosition="3" />' % box(1392,35,2,80),
            '<eLabel %s backgroundColor="#0019c9ff" zPosition="3" />' % box(1664,35,2,80),
            label(None,60,236,470,78,30,text="Posledné pridané\npicony",color="#009cf0ff")]
    for number in range(6):
        x=590+number*210
        out += [fill(x,225,170,92,"#00314b65"),fill(x+1,226,168,90,"#18091b30"),
                '<widget name="recent%d" %s alphatest="blend" zPosition="3" />' % (number,box(x+15,229,140,84))]
    # Subtle row separators and a bright selected row, independent of the TV skin.
    for y in (452,552,652,752):
        out.append(fill(145,y,1010,1,"#00314b65"))
    out += ['<widget name="list" %s transparent="1" scrollbarMode="showOnDemand" enableWrapAround="1" foregroundColor="#00ffffff" foregroundColorSelected="#00ffffff" backgroundColorSelected="#002a70ad" zPosition="3" />' % box(70,350,1120,500),
            label(None,1280,350,550,60,36,text="Náhľad piconu"),
            fill(1280,425,540,2,"#003ee8ff"),
            fill(1298,445,484,304,"#00314b65"),fill(1300,447,480,300,"#00061729"),
            '<widget name="preview" %s alphatest="blend" zPosition="3" />' % box(1320,465,440,264),
            '<widget name="brand_logo" %s transparent="1" zPosition="4" />' % box(1320,465,440,264),
            label("preview_caption",1270,750,560,44,23,align="center"),
            label("summary",1280,805,550,70,25,color="#00b5d4ec"),
            fill(60,916,4,34,"#003ee8ff",3),label("status",80,910,1780,45,25,color="#009cf0ff"),
            label(None,60,957,1800,38,22,text="↑↓: výber riadka • OK: otvoriť ponuku • Vyber všetkých päť položiek a stlač Stiahnuť.",color="#00b5d4ec")]
    for x,color,title in ((60,"#00ff526a","Zatvoriť"),(520,"#0000ea9b","Stiahnuť"),(980,"#00ffdb52","Aktualizácia pluginu"),(1440,"#0045b9ff","O projekte")):
        out += [fill(x,1010,420,60,"#0010243c"),fill(x,1010,420,3,color,3),
                label(None,x+18,1018,40,45,32,text="●",color=color),label(None,x+72,1018,330,45,28,text=title)]
    return "\n".join(out + ["</screen>"])


def dialog_skin(width, height, rows=8):
    scale = min(width / 1920.0, height / 1080.0)
    w, h = round(1050*scale), round((170+min(rows,8)*60)*scale)
    return '''<screen position="center,center" size="%d,%d" title="Výber" backgroundColor="#00102136">
      <widget name="title" position="%d,%d" size="%d,%d" font="Regular;%d" foregroundColor="#0019c9ff" />
      <widget name="list" position="%d,%d" size="%d,%d" scrollbarMode="showOnDemand" enableWrapAround="1" foregroundColor="#00ffffff" foregroundColorSelected="#00ffffff" backgroundColorSelected="#002a70ad" />
      <widget name="hint" position="%d,%d" size="%d,%d" font="Regular;%d" foregroundColor="#00ffffff" />
    </screen>''' % (w,h,round(25*scale),round(15*scale),w-round(50*scale),round(50*scale),round(32*scale),
                   round(20*scale),round(80*scale),w-round(40*scale),h-round(150*scale),
                   round(25*scale),h-round(55*scale),w-round(50*scale),round(45*scale),round(24*scale))
