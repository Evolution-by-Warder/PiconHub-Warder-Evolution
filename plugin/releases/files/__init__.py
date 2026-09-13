# -*- coding: utf-8 -*-
from __future__ import print_function
import gettext
import os
try:
    from Components.Language import language
except Exception:
    language = None
PLUGIN_PATH = os.path.dirname(os.path.abspath(__file__))
LOCALE_PATH = os.path.join(PLUGIN_PATH, 'locale')
DOMAIN = 'PiconHub'
def localeInit():
    try:
        if language is not None: os.environ['LANGUAGE'] = language.getLanguage()[:2]
        gettext.bindtextdomain(DOMAIN, LOCALE_PATH)
    except Exception as e: print('[PiconHub] gettext bind error:', e)
localeInit()
try:
    if language is not None: language.addCallback(localeInit)
except Exception as e: print('[PiconHub] language callback error:', e)
def _(txt):
    try:
        translated=gettext.dgettext(DOMAIN,txt); return translated if translated else txt
    except Exception: return txt
try:
    from . import provider_extension  # noqa: F401
except Exception as e: print('[PiconHub] provider extension load error:', e)
try:
    from . import hierarchy_patch  # noqa: F401
except Exception as e: print('[PiconHub] hierarchy patch load error:', e)
try:
    from . import plugin_updater  # noqa: F401
except Exception as e: print('[PiconHub] plugin updater load error:', e)
try:
    from . import auto_restart_patch  # noqa: F401
except Exception as e: print('[PiconHub] auto restart patch load error:', e)
try:
    from . import update_ui  # noqa: F401
except Exception as e: print('[PiconHub] update UI load error:', e)
try:
    from . import update_menu_patch  # noqa: F401
except Exception as e: print('[PiconHub] update menu patch load error:', e)
try:
    from . import main_async_patch  # noqa: F401
except Exception as e: print('[PiconHub] main async patch load error:', e)
