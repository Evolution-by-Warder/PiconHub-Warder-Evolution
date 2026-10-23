# -*- coding: utf-8 -*-

from Components.Language import language
import gettext
from pathlib import Path
from .warder_migrate import cleanup_compatibility

PLUGIN_PATH          = str(Path(__file__).resolve().parent) + "/"
PluginLanguagePath   = PLUGIN_PATH + "locale"
PluginLanguageDomain = "ChocholousekPicons"

def localeInit():
	gettext.bindtextdomain(PluginLanguageDomain, PluginLanguagePath)

def _(txt):
	t = gettext.dgettext(PluginLanguageDomain, txt)
	if t == txt:
		t = gettext.gettext(txt)
	return t

cleanup_compatibility(Path(PLUGIN_PATH).parent)
localeInit()
language.addCallback(localeInit)
