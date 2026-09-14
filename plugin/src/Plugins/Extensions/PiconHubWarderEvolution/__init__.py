# -*- coding: utf-8 -*-
from __future__ import print_function

import os

PLUGIN_PATH = os.path.dirname(__file__) + '/'

try:
    from Components.Language import language
    from Tools.Directories import resolveFilename, SCOPE_PLUGINS
    import gettext

    def localeInit():
        gettext.bindtextdomain('PiconHubWarderEvolution', resolveFilename(
            SCOPE_PLUGINS, 'Extensions/PiconHubWarderEvolution/locale'))

    def _(txt):
        translated = gettext.dgettext('PiconHubWarderEvolution', txt)
        if translated == txt:
            translated = gettext.gettext(txt)
        return translated

    localeInit()
    language.addCallback(localeInit)
except Exception:
    def _(txt):
        return txt
