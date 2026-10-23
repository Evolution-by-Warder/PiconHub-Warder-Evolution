"""Display the original Warder wordmark through a native clipped viewport."""
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

    def show_logo(self):
        if self.instance is None:
            return
        if self.picture is None:
            self.postWidgetCreate(self.instance)
        if not self.loaded:
            viewport = self.instance.size()
            # Only the original left 720px brand area is visible. The parent's
            # native clipping excludes the old slogan, clock and version.
            factor = viewport.width() / 720.0
            width, height = round(1672 * factor), round(941 * factor)
            brand_height = round(190 * factor)
            self.picture.resize(eSize(width, height))
            self.picture.move(ePoint(0, max(0, (viewport.height() - brand_height) // 2)))
            self.picture.setPixmapFromFile(self.path)
            self.loaded = True
        self.show()

    def preWidgetRemove(self, instance):
        self.picture, self.loaded = None, False
