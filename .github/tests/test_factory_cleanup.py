import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('factory_cleanup',Path(__file__).parents[1]/'scripts/cleanup_factory_releases.py')
cleanup=importlib.util.module_from_spec(spec);spec.loader.exec_module(cleanup)


class FactoryCleanupTests(unittest.TestCase):
    def setUp(self):
        self.target={'id':42,'tag':'factory-v0.2.43','assets':['WARDER-PICON-FACTORY.exe']}
        self.release={'id':42,'tag_name':'factory-v0.2.43','name':'WARDER PICON FACTORY',
                      'assets':[{'name':'WARDER-PICON-FACTORY.exe'}]}

    def test_explicit_factory_target_is_allowed(self):
        cleanup.validate_target(self.target,self.release)

    def test_receiver_release_cannot_be_deleted(self):
        self.target['tag']=self.release['tag_name']='v0.1.13'
        with self.assertRaises(ValueError):cleanup.validate_target(self.target,self.release)

    def test_changed_identity_cannot_be_deleted(self):
        self.release['id']=99
        with self.assertRaises(ValueError):cleanup.validate_target(self.target,self.release)

    def test_assets_changed_or_containing_ipk_cannot_be_deleted(self):
        self.release['assets'].append({'name':'unknown.zip'})
        with self.assertRaises(ValueError):cleanup.validate_target(self.target,self.release)
        self.release['assets']=[{'name':'plugin.ipk'}];self.target['assets']=['plugin.ipk']
        with self.assertRaises(ValueError):cleanup.validate_target(self.target,self.release)
