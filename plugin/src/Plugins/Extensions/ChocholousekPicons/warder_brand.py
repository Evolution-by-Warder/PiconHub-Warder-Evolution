"""Display the Warder emblem at full preview height without distorting it."""
from Components.GUIComponent import GUIComponent
from enigma import ePixmap, ePoint, eSize, eWidget


class BrandLogo(GUIComponent):
    GUI_WIDGET = eWidget

    def __init__(self, path):
        GUIComponent.__init__(self)
        self.path, self.picture, self.loaded = str(path), None, False

    def postWidgetCreate(self, instance):
        self.picture = ePixmap(instance)
        self.picture.setScale(1)
        self.picture.setAlphatest(2)

    def show_logo(self):
        if self.instance is None:
            return
        if self.picture is None:
            self.postWidgetCreate(self.instance)
        if not self.loaded:
            viewport = self.instance.size()
            # The production emblem is a transparent square; contain it at the
            # full available height instead of clipping the wide header image.
            side = min(viewport.width(), viewport.height())
            self.picture.resize(eSize(side, side))
            self.picture.move(ePoint((viewport.width()-side)//2, (viewport.height()-side)//2))
            self.picture.setPixmapFromFile(self.path)
            self.loaded = True
        self.show()

    def preWidgetRemove(self, instance):
        self.picture, self.loaded = None, False
