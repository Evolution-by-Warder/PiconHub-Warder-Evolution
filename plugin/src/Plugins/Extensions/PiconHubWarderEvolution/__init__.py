# -*- coding: utf-8 -*-
"""PiconHub Warder Evolution runtime package.

Modernized continuation of the Chocholousek Picons Enigma2 plugin by s3n0.
Upstream authorship/credits are preserved; new Warder Evolution work lives in
its own runtime namespace and directory.
"""
from __future__ import print_function

import gettext
import os

PLUGIN_NAME = "PiconHub-Warder-Evolution"
PLUGIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/PiconHubWarderEvolution/"
LOCALE_PATH = os.path.join(PLUGIN_PATH, "locale")
GETTEXT_DOMAIN = "PiconHubWarderEvolution"


def localeInit():
    """Bind translations to the new runtime directory/domain."""
    try:
        from Components.Language import language
        language.addCallback(localeInit)
    except Exception:
        pass
    gettext.bindtextdomain(GETTEXT_DOMAIN, LOCALE_PATH)


def _(txt):
    translated = gettext.dgettext(GETTEXT_DOMAIN, txt)
    if translated == txt:
        translated = gettext.gettext(txt)
    return translated


localeInit()
