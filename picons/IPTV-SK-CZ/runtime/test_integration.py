import hashlib
import importlib
import io
import json
from pathlib import Path
import runpy
import sys
import tempfile
import types
import unittest
import zipfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent
pkg=types.ModuleType('iptv_full');pkg.__path__=[str(ROOT/'patched')];sys.modules['iptv_full']=pkg
engine=importlib.import_module('iptv_full.warder_engine');model=importlib.import_module('iptv_full.warder_model');iptv=importlib.import_module('iptv_full.warder_iptv');dab=importlib.import_module('iptv_full.warder_dab')
helper=runpy.run_path(str(ROOT/'test_iptv.py'));png=helper['png'];NAME=helper['NAME'];DAB='4115_0_2_1019_C98_3_EB0000_1019_10C4_10BC.png'
class Response(io.BytesIO):
 def __init__(self,raw,url=''):super().__init__(raw);self.url=url
 def geturl(self):return self.url

def fixture():
 resources={};manifest=helper['manifest']()
 def package(name,w,h,url):
  raw=png(w,h);buf=io.BytesIO()
  with zipfile.ZipFile(buf,'w') as archive:archive.writestr(name,raw)
  data=buf.getvalue();resources[url]=data
  return {'url':url,'resolution':f'{w}x{h}','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'files':{name:hashlib.sha256(raw).hexdigest()}}
 for res,styles in manifest['packages'].items():
  for style,p in styles.items():styles[style]=package(NAME,*map(int,res.split('x')),p['url'])
 resources[iptv.MANIFEST_URL]=json.dumps(manifest).encode()
 dm={'schema':1,'status':'verified','packages':{}}
 for style in ('transparent','white','black'):
  url='https://raw.githubusercontent.com/'+dab.REPOSITORY+'/'+'a'*40+'/picons/DAB/packages/dab-'+style+'-220x132.zip'
  dm['packages'][style]=package(DAB,220,132,url)
 resources[dab.MANIFEST_URL]=json.dumps(dm).encode();return resources,manifest

def profile(dest,selectors='IPTV-SK-CZ',res='220x132'):
 V=lambda x:types.SimpleNamespace(value=x)
 return types.SimpleNamespace(warder_selectors=V(selectors),sats=V(''),resolution=V(res),background=V('black'),method=V('all_inc'),picon_folder=V('user_defined'),picon_folder_user=V(dest))

class IntegrationTests(unittest.TestCase):
 def test_skin_host_uses_the_same_verified_packages_and_preserves_native_filtering(self):
  host=types.ModuleType('skin_fixture');host.__path__=[str(ROOT/'patched')];sys.modules['skin_fixture']=host
  sys.modules['skin_fixture.warderRadioCore']=sys.modules['iptv_full']
  radio=importlib.import_module('skin_fixture.warderRadio')
  cases=[('IPTV-SK-CZ','50x30',1),('DAB IPTV-SK-CZ','220x132',2),('DAB','220x132',1)]
  for selectors,resolution,expected in cases:
   with tempfile.TemporaryDirectory() as tmp:
    target=Path(tmp,'picon');target.mkdir();resources,_=fixture()
    prefs=model.profile_preferences(profile(str(target),selectors,resolution))
    worker=radio.Worker(prefs,opener=lambda u:Response(resources[u],u),enigma2_dir=tmp,lock_path=str(Path(tmp,'lock')))
    worker.run();terminal=[item for item in worker.drain() if item[0] in ('done','error')]
    self.assertEqual(terminal[0][0],'done',terminal)
    self.assertEqual(terminal[0][1]['added'],expected)
  self.assertTrue(radio.is_radio(radio.IPTV_BINDING));self.assertFalse(radio.is_dab(radio.IPTV_BINDING))
 def test_only_iptv_and_combined_dab_use_no_satellite_manifest(self):
  for selectors,expected in [('IPTV-SK-CZ',1),('DAB IPTV-SK-CZ',2)]:
   with tempfile.TemporaryDirectory() as tmp:
    target=Path(tmp,'picon');target.mkdir();other=target/'unrelated.png';other.write_bytes(b'keep')
    resources,_=fixture();calls=[]
    def opener(url):calls.append(url);return Response(resources[url],url)
    prefs=model.profile_preferences(profile(str(target),selectors));runner=engine.PiconRunner(opener=opener,enigma2_dir=tmp,lock_path=str(Path(tmp,'lock')))
    result=runner.run([prefs]);self.assertEqual(result['added'],expected);self.assertNotIn(engine.sync.RUNTIME_MANIFEST_URL,calls);self.assertEqual(other.read_bytes(),b'keep');self.assertTrue((target/NAME).exists())
 def test_corrupt_second_transport_keeps_all_receiver_files_unchanged(self):
  with tempfile.TemporaryDirectory() as tmp:
   target=Path(tmp,'picon');target.mkdir();other=target/'unrelated.png';other.write_bytes(b'keep');resources,manifest=fixture();bad=manifest['packages']['220x132']['black']['url'];resources[bad]+=b'corrupt'
   prefs=model.profile_preferences(profile(str(target),'DAB IPTV-SK-CZ'));runner=engine.PiconRunner(opener=lambda u:Response(resources[u],u),enigma2_dir=tmp,lock_path=str(Path(tmp,'lock')))
   with self.assertRaises(engine.PiconError):runner.run([prefs])
   self.assertEqual({p.name:p.read_bytes() for p in target.iterdir()},{'unrelated.png':b'keep'})
 def test_all_iptv_sizes_work_without_relaxing_the_existing_dab_limit(self):
  self.assertTrue(model.profile_preferences(profile('/tmp/picon',res='50x30'))['iptv_only'])
  with self.assertRaises(ValueError):model.profile_preferences(profile('/tmp/picon','DAB IPTV-SK-CZ','50x30'))
 def test_default_network_opener_rejects_cross_origin_redirects(self):
  with patch.object(engine,'urlopen',return_value=Response(b'','https://example.invalid/fake')):
   with self.assertRaises(engine.PiconError):engine.network_open(iptv.MANIFEST_URL)
if __name__=='__main__':unittest.main()
