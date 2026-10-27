import importlib,types,sys,json,io,tempfile,pathlib,hashlib
root=pathlib.Path(__file__).resolve().parents[2]/'plugin/src/Plugins/Extensions/WarderPiconHub'
pkg=types.ModuleType('dtt_verify');pkg.__path__=[str(root)];sys.modules[pkg.__name__]=pkg
e=importlib.import_module(pkg.__name__+'.warder_engine');s=e.sync
import argparse
p=argparse.ArgumentParser();p.add_argument('--artifacts',type=pathlib.Path,required=True);a=p.parse_args();out=a.artifacts;doc=json.loads((out/'manifest.json').read_text())
assert s.validate_publication_manifest(doc)==[],s.validate_publication_manifest(doc)
def opener(url):
 if url==s.RUNTIME_MANIFEST_URL:return io.BytesIO(json.dumps(doc).encode())
 return (out/url.rsplit('/',1)[-1]).open('rb')
report=json.loads((out/'variants.json').read_text());results={}
for style in ('white','black'):
 with tempfile.TemporaryDirectory() as temp:
  target=pathlib.Path(temp)/'picon';target.mkdir();(target/'user.png').write_bytes(b'user file preserved')
  prefs=s.default_preferences(str(target));prefs=s.set_task_position_bindings(prefs,[s.task_binding_for_package_selector('DVB-T-SK-CZ')]);prefs.update(resolution='220x132',style=style,update_mode=s.UPDATE_MODE_INCREMENTAL,prepared=True)
  result=e.PiconRunner(opener=opener,lock_path=temp+'/lock',enigma2_dir=temp+'/enigma2').run([prefs]);assert result=={'added':2674,'changed':0,'removed':0},result
  assert (target/'user.png').read_bytes()==b'user file preserved'
  for name,r in report['records'].items():assert hashlib.sha256((target/name).read_bytes()).hexdigest()==r[style]
  results[style]=dict(result,all_file_sha256_verified=True,user_file_preserved=True)
(out/'install-verification.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results))
