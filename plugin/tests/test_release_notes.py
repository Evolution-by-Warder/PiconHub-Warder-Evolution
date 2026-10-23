"""Installed About notes stay offline, localized and bound to their version."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).parents[1]/'src/Plugins/Extensions/WarderPiconHub'
spec=importlib.util.spec_from_file_location('release_notes_contracts',ROOT/'warder_release_notes.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class ReleaseNotesTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'notes.json'
        self.path.write_text(json.dumps({'version':'0.1.12','notes':{'sk':'Slovenské zmeny','en':'English changes'}}))

    def test_uses_installed_notes_and_normalizes_system_language(self):
        self.assertEqual(module.load_notes(self.path,'0.1.12','sk_SK'),'Slovenské zmeny')
        self.assertEqual(module.load_notes(self.path,'0.1.12','en-GB'),'English changes')

    def test_unsupported_language_falls_back_to_english(self):
        self.assertEqual(module.load_notes(self.path,'0.1.12','nl_NL'),'English changes')

    def test_notes_from_another_version_are_never_displayed(self):
        self.assertEqual(module.load_notes(self.path,'0.1.11','sk'),'')
        self.assertEqual(module.load_notes(self.path,'0.1.13','sk'),'')

    def test_missing_or_invalid_notes_do_not_break_about(self):
        for content in ('bad json','[]','{"version":"0.1.12","notes":[]}',
                        '{"version":"0.1.12","notes":{"sk":42}}'):
            self.path.write_text(content)
            self.assertEqual(module.load_notes(self.path,'0.1.12','sk'),'')
        self.path.unlink()
        self.assertEqual(module.load_notes(self.path,'0.1.12','sk'),'')
