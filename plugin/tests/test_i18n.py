"""Localization contracts: current system language, safe formatting and fallback."""
import datetime
import importlib
import pathlib
import re
import sys
import types
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

ROOT=pathlib.Path(__file__).parents[1]/'src/Plugins/Extensions/ChocholousekPicons'
package=types.ModuleType('warder_i18n_contracts');package.__path__=[str(ROOT)]
sys.modules[package.__name__]=package
i18n=importlib.import_module(package.__name__+'.warder_i18n')
model=importlib.import_module(package.__name__+'.warder_model')
layout=importlib.import_module(package.__name__+'.warder_layout')


class LocalizationTests(unittest.TestCase):
    def test_complete_catalogs_preserve_interpolation(self):
        self.assertEqual(set(i18n.SUPPORTED),{'sk','cs','en','de','pl','hu','ru','fr','it','es'})
        source=i18n.CATALOGS['sk']
        for code,messages in i18n.CATALOGS.items():
            self.assertEqual(set(messages),set(source),code)
            for key,text in messages.items():
                self.assertTrue(text,(code,key))
                self.assertEqual(re.findall(r'%[sd]',key),re.findall(r'%[sd]',text),(code,key))

    def test_system_language_is_read_again_after_change(self):
        setting=types.SimpleNamespace(value='de_DE')
        module=types.ModuleType('Components.Language')
        module.language=types.SimpleNamespace(getLanguage=lambda:setting.value)
        with patch.dict(sys.modules,{'Components.Language':module}):
            self.assertEqual(i18n._('Stiahnuť'),'Herunterladen')
            setting.value='pl_PL'
            self.assertEqual(i18n._('Stiahnuť'),'Pobierz')
            setting.value='cs-CZ'
            self.assertEqual(i18n._('Stiahnuť'),'Stáhnout')

    def test_unsupported_languages_use_english(self):
        self.assertEqual(i18n.translate('Vyber si…','zz_ZZ'),'Choose…')
        self.assertEqual(i18n.translate('CANALPLUS_SK','zz_ZZ'),'CANALPLUS_SK')

    def test_main_and_popup_skins_follow_selected_language(self):
        for code,close,preview in [('sk','Zatvoriť','Náhľad piconu'),('cs','Zavřít','Náhled piconu'),
                                  ('en','Close','Picon preview'),('de','Schließen','Picon-Vorschau'),('pl','Zamknij','Podgląd pikony'),('hu','Bezárás','Pikon előnézete'),('ru','Закрыть','Просмотр пикона'),('fr','Fermer','Aperçu du picon'),('it','Chiudi','Anteprima picon'),('es','Cerrar','Vista previa del picon')]:
            with patch.object(i18n,'language_code',return_value=code):
                root=ET.fromstring(layout.main_skin())
                labels={item.get('text') for item in root}
                self.assertIn(close,labels);self.assertIn(preview,labels)
                popup=ET.fromstring(layout.dialog_skin(1280,720,53,True))
                self.assertEqual(popup.get('title'),i18n._('Výber'))

    def test_clock_names_are_independent_of_host_locale(self):
        now=datetime.datetime(2026,10,23,17,20,5)
        for code,day,month in [('en','Friday','October'),('de','Freitag','Oktober'),('pl','Piątek','października'),('hu','Péntek','október'),('ru','Пятница','октября'),('fr','Vendredi','octobre'),('it','Venerdì','ottobre'),('es','Viernes','octubre')]:
            result=model.clock_text(now,code)
            self.assertEqual(result[0],day);self.assertIn(month,result[1]);self.assertEqual(result[2:],('17:20','05'))

    def test_engine_validation_uses_system_language(self):
        profile=types.SimpleNamespace(warder_selectors=types.SimpleNamespace(value=''),sats=types.SimpleNamespace(value=''))
        with patch.object(i18n,'language_code',return_value='de'):
            with self.assertRaisesRegex(ValueError,'Unterstützte Satelliten'):
                model.profile_preferences(profile)
