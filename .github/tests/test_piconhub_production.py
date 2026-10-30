import copy
import hashlib
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('promotion',Path(__file__).parents[1]/'scripts/promote_piconhub.py')
promotion=importlib.util.module_from_spec(spec);spec.loader.exec_module(promotion)


class ProductionTests(unittest.TestCase):
    def setUp(self):
        self.data=b'verified package bytes'
        self.name='enigma2-plugin-extensions-piconhub_0.1.13_all.ipk'
        self.item={'version':'0.1.13','tag':'v0.1.13','sha256':hashlib.sha256(self.data).hexdigest(),
                   'bytes':len(self.data),'url':'https://github.com/'+promotion.REPOSITORY+'/releases/download/v0.1.13/'+self.name}
        self.record={'release':dict(self.item),'source_commit':'a'*40}
        self.feed={'release':dict(self.item)}
        self.release={'tag_name':'v0.1.13','draft':False,'target_commitish':'a'*40,
                      'assets':[{'name':self.name,'size':len(self.data),'digest':'sha256:'+self.item['sha256']}]}

    def test_frozen_public_package_can_be_promoted(self):
        promotion.validate(self.record,self.feed,self.release,self.data)

    def test_corrupt_or_truncated_package_is_rejected(self):
        for data in (self.data[:-1],self.data+b'extra',b'x'*len(self.data)):
            with self.assertRaises(ValueError):promotion.validate(self.record,self.feed,self.release,data)

    def test_changed_feed_or_different_source_cannot_be_promoted(self):
        self.feed['release']['version']='0.1.14'
        with self.assertRaises(ValueError):promotion.validate(self.record,self.feed,self.release,self.data)
        self.feed['release']=dict(self.item);self.release['target_commitish']='b'*40
        with self.assertRaises(ValueError):promotion.validate(self.record,self.feed,self.release,self.data)

    def test_wrong_source_url_or_draft_is_rejected(self):
        self.release['draft']=True
        with self.assertRaises(ValueError):promotion.validate(self.record,self.feed,self.release,self.data)
        self.release['draft']=False
        self.record['release']['url']=self.feed['release']['url']='https://example.org/fake.ipk'
        with self.assertRaises(ValueError):promotion.validate(self.record,self.feed,self.release,self.data)
