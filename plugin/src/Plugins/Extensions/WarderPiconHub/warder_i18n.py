"""Warder interface catalogs, selected from the current Enigma2 language.

No extra runtime dependency. Look up the language on each call so changing
Enigma2's language takes effect when the plugin is opened again.
"""
import json
import locale
import pathlib
import xml.etree.ElementTree as ET

CATALOGS = json.loads((pathlib.Path(__file__).parent/'data/translations.json').read_text(encoding='utf-8'))
SUPPORTED = tuple(CATALOGS)


def language_code():
    try:
        from Components.Language import language
        value = language.getLanguage()
    except (ImportError, AttributeError):
        try:
            from Components.config import config
            value = config.osd.language.value
        except (ImportError, AttributeError):
            value = locale.getlocale()[0] or 'en'
    return str(value).split('.')[0].replace('-', '_').split('_')[0].lower()


def translate(text, language=None):
    code = str(language or language_code()).replace('-', '_').split('_')[0].lower()
    return CATALOGS.get(code, CATALOGS['en']).get(text, CATALOGS['en'].get(text, text))


_ = translate


def localize_skin(skin):
    root = ET.fromstring(skin)
    for node in root.iter():
        for attribute in ('title', 'text'):
            value = node.get(attribute)
            if value:
                node.set(attribute, _(value))
    return ET.tostring(root, encoding='unicode')
