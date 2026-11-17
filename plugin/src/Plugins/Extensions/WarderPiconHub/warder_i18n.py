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


SETTINGS_TRANSLATIONS = {
    'sk': ('Nastavenia', 'Zobraziť v hlavnom menu', 'O programe', 'Áno', 'Nie'),
    'en': ('Settings', 'Show in main menu', 'About', 'Yes', 'No'),
    'cs': ('Nastavení', 'Zobrazit v hlavním menu', 'O programu', 'Ano', 'Ne'),
    'de': ('Einstellungen', 'Im Hauptmenü anzeigen', 'Über das Programm', 'Ja', 'Nein'),
    'pl': ('Ustawienia', 'Pokaż w menu głównym', 'O programie', 'Tak', 'Nie'),
    'hu': ('Beállítások', 'Megjelenítés a főmenüben', 'A programról', 'Igen', 'Nem'),
    'ru': ('Настройки', 'Показывать в главном меню', 'О программе', 'Да', 'Нет'),
    'fr': ('Paramètres', 'Afficher dans le menu principal', 'À propos', 'Oui', 'Non'),
    'it': ('Impostazioni', 'Mostra nel menu principale', 'Informazioni', 'Sì', 'No'),
    'es': ('Configuración', 'Mostrar en el menú principal', 'Acerca del programa', 'Sí', 'No'),
    'pt': ('Definições', 'Mostrar no menu principal', 'Sobre o programa', 'Sim', 'Não'),
    'nl': ('Instellingen', 'Tonen in het hoofdmenu', 'Over het programma', 'Ja', 'Nee'),
    'ro': ('Setări', 'Afișare în meniul principal', 'Despre program', 'Da', 'Nu'),
    'uk': ('Налаштування', 'Показувати в головному меню', 'Про програму', 'Так', 'Ні'),
    'bg': ('Настройки', 'Показване в главното меню', 'За програмата', 'Да', 'Не'),
    'hr': ('Postavke', 'Prikaži u glavnom izborniku', 'O programu', 'Da', 'Ne'),
    'sr': ('Podešavanja', 'Prikaži u glavnom meniju', 'O programu', 'Da', 'Ne'),
    'sl': ('Nastavitve', 'Prikaži v glavnem meniju', 'O programu', 'Da', 'Ne'),
    'el': ('Ρυθμίσεις', 'Εμφάνιση στο κύριο μενού', 'Σχετικά με το πρόγραμμα', 'Ναι', 'Όχι'),
    'tr': ('Ayarlar', 'Ana menüde göster', 'Program hakkında', 'Evet', 'Hayır'),
    'sv': ('Inställningar', 'Visa i huvudmenyn', 'Om programmet', 'Ja', 'Nej'),
}
SETTINGS_KEYS = SETTINGS_TRANSLATIONS['sk']

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
    if text in SETTINGS_KEYS:
        return SETTINGS_TRANSLATIONS.get(code, SETTINGS_TRANSLATIONS['en'])[SETTINGS_KEYS.index(text)]
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
