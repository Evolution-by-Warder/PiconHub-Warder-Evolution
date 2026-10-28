import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import types
import unittest
import zipfile
import zlib

ROOT=Path(__file__).resolve().parents[1]/'src/Plugins/Extensions/WarderPiconHub'
pkg=types.ModuleType('iptv_fixture');pkg.__path__=[str(ROOT)];sys.modules[pkg.__name__]=pkg
sync=types.ModuleType('iptv_fixture.warder_skin_sync')
sync.UPDATE_MODE_SYNC_TV='sync-tv';sync.UPDATE_MODE_SYNC_TV_RADIO='sync-radio';sync.UPDATE_MODE_INCREMENTAL='incremental'
sys.modules[sync.__name__]=sync
spec=importlib.util.spec_from_file_location('iptv_fixture.warder_iptv',ROOT/'warder_iptv.py');iptv=importlib.util.module_from_spec(spec);spec.loader.exec_module(iptv)
NAME='4097_0_2_1234_5678_EC_0_0_0_0.png';OTHER='4097_0_2_1235_5678_EC_0_0_0_0.png'
def png(w,h):
 def chunk(kind,raw):return struct.pack('>I',len(raw))+kind+raw+struct.pack('>I',zlib.crc32(kind+raw)&0xffffffff)
 raw=(b'\0'+bytes((1,2,3,255))*w)*h
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
def manifest():
 d={'schema':1,'status':'verified','collection':iptv.SELECTOR,'packages':{}}
 for res in iptv.RESOLUTIONS:
  d['packages'][res]={}
  for style in iptv.STYLES:
   raw=png(*map(int,res.split('x')));d['packages'][res][style]={'resolution':res,'url':'https://raw.githubusercontent.com/'+iptv.REPOSITORY+'/'+'a'*40+'/picons/IPTV-SK-CZ/packages/iptv-sk-cz-'+style+'-'+res+'.zip','bytes':100,'sha256':'0'*64,'files':{NAME:hashlib.sha256(raw).hexdigest()}}
 return d
class IPTVTests(unittest.TestCase):
 def test_all_nine_variants_accept_the_same_nonzero_radio_references(self):
  d=manifest();self.assertEqual(iptv.read_manifest(lambda u:io.BytesIO(json.dumps(d).encode())),d)
 def test_package_urls_require_exact_repo_commit_collection_style_and_size(self):
  d=manifest();p=d['packages']['50x30']['black'];p['url']=p['url'].replace('/'+'a'*40+'/', '/main/')
  with self.assertRaises(ValueError):iptv.read_manifest(lambda u:io.BytesIO(json.dumps(d).encode()))
  self.assertFalse(iptv.trusted_url(p['url']));self.assertFalse(iptv.trusted_url(iptv.MANIFEST_URL.replace(iptv.REPOSITORY,'other/repo')))
 def test_styles_cannot_silently_cover_different_stations(self):
  d=manifest();d['packages']['400x240']['white']['files'][OTHER]='f'*64
  with self.assertRaises(ValueError):iptv.read_manifest(lambda u:io.BytesIO(json.dumps(d).encode()))
 def test_flags_tv_references_path_traversal_and_shared_zero_ids_are_rejected(self):
  for name in ('../'+NAME,NAME.replace('_0_2_','_0_1_'),NAME.replace('_0_2_','_64_2_'),NAME.replace('4097','1'),'4097_0_2_0_0_0_0_0_0_0.png',NAME.replace('.png','\n.png')):
   self.assertFalse(iptv.reference_filename(name),name)
 def test_radio_sync_matches_bouquet_identity_without_url_or_channel_name_guessing(self):
  with tempfile.TemporaryDirectory() as tmp:
   Path(tmp,'userbouquet.test.radio').write_text('#SERVICE '+NAME[:-4].replace('_',':')+':https%3a//example.invalid/radio\n#DESCRIPTION Example\n')
   prefs={'style':'black','resolution':'50x30','update_mode':sync.UPDATE_MODE_SYNC_TV_RADIO,'destination':'/tmp/picon'}
   queue,job=iptv.plan(manifest(),prefs,tmp);self.assertEqual(queue['iptv_names'],{NAME});self.assertEqual(job['selector_id'],iptv.SELECTOR)
   prefs['update_mode']=sync.UPDATE_MODE_SYNC_TV;self.assertIsNone(iptv.plan(manifest(),prefs,tmp))
 def test_hash_and_dimensions_are_checked_before_staging_a_file(self):
  for wrong in ('hash','dimensions'):
   with tempfile.TemporaryDirectory() as tmp:
    ready=Path(tmp,'ready');ready.mkdir();archive=Path(tmp,'test.zip');raw=png(220,132) if wrong=='dimensions' else png(50,30)
    with zipfile.ZipFile(archive,'w') as z:z.writestr(NAME,raw)
    job={'files':{NAME:hashlib.sha256(raw).hexdigest() if wrong=='dimensions' else 'f'*64},'resolution':'50x30'}
    stage=types.SimpleNamespace(queue={'iptv_names':{NAME}},hashes={},upstream=set(),ready=ready)
    with self.assertRaises(ValueError):iptv.unpack(stage,archive,job,lambda:None)
    self.assertEqual(list(ready.iterdir()),[])
 def test_valid_selected_image_stages_without_overwriting_unrelated_picons(self):
  with tempfile.TemporaryDirectory() as tmp:
   ready=Path(tmp,'ready');ready.mkdir();untouched=Path(tmp,'unrelated.png');untouched.write_bytes(b'keep');raw=png(50,30);archive=Path(tmp,'test.zip')
   with zipfile.ZipFile(archive,'w') as z:z.writestr(NAME,raw)
   job={'files':{NAME:hashlib.sha256(raw).hexdigest()},'resolution':'50x30'}
   stage=types.SimpleNamespace(queue={'iptv_names':{NAME}},hashes={},upstream=set(),ready=ready)
   iptv.unpack(stage,archive,job,lambda:None);self.assertEqual((ready/NAME).read_bytes(),raw);self.assertEqual(untouched.read_bytes(),b'keep')
if __name__=='__main__':unittest.main()
