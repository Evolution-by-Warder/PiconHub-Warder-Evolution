#!/usr/bin/env python3
"""Verify complete satellite/provider coverage and actual two-client installations."""
from pathlib import Path
import argparse,ast,copy,hashlib,importlib.util,io,json,os,shutil,stat,sys,tempfile,types,urllib.request,zipfile
ROOT=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def main():
 a=argparse.ArgumentParser();a.add_argument('--manifest',type=Path,required=True);a.add_argument('--part-dir',type=Path);a.add_argument('--skin-root',type=Path,required=True);a.add_argument('--report',type=Path,required=True);args=a.parse_args()
 doc=json.loads(args.manifest.read_text());namespace='three_background_actual_hub';pkg=types.ModuleType(namespace);pkg.__path__=[str(ROOT/'plugin/src/Plugins/Extensions/WarderPiconHub')];sys.modules[namespace]=pkg
 engine=__import__(namespace+'.warder_engine',fromlist=['PiconRunner']);native=args.skin_root/'source/package-root/usr/lib/enigma2/python/Plugins/Extensions/setupGlass17';skin=load('three_background_actual_skin',native/'warderPiconSync.py')
 node=next(n for n in ast.walk(ast.parse((native/'plugin.py').read_bytes())) if isinstance(n,ast.FunctionDef) and n.name=='_warderInstallChannelArchive');scope=dict(warderPiconSync=skin,os=os,shutil=shutil,stat=stat,tempfile=tempfile,zipfile=zipfile);exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-FullHDGlass-installer','exec'),scope);install=scope[node.name]
 for sync in [skin,engine.sync]:assert not sync.validate_publication_manifest(doc,sync.RUNTIME_MANIFEST_URL)
 groups={(p['selector_id'],p['resolution']) for p in doc['packages'] if p['family'].startswith('channel-')}
 for selector,size in groups:assert {p['family'] for p in doc['packages'] if p['selector_id']==selector and p['resolution']==size}>=set('channel-'+s for s in ['transparent','white','black'])
 physical={p['selector_id'] for p in doc['packages'] if p.get('warder_key','').lower().endswith(('e','w')) and '/' not in p.get('warder_key','')};plans=0
 for selector in sorted(physical):
  for size in ['50x30','220x132','400x240']:
   for style in ['transparent','white','black']:
    for sync in [skin,engine.sync]:
     binding=sync.task_binding_for_package_selector(selector);assert binding,(selector,'missing client binding');prefs=sync.set_task_position_bindings(sync.default_preferences(),[binding]);prefs.update(resolution=size,style=style,update_mode=sync.UPDATE_MODE_INCREMENTAL);q=sync.build_runtime_queue(prefs);plan=sync.plan_runtime_packages(doc,q);jobs=sync.build_download_jobs(doc,plan);assert plan['state']=='ready' and jobs['state']=='ready' and len(jobs['jobs'])==1,(selector,size,style,plan);plans+=1
 # Missing either satellite or provider backgrounds must be rejected explicitly.
 for selector in ['345W','500E','CANALPLUS_SK','DIGI_TELLY','FREESAT']:
  for style in ['transparent','white','black']:
   bad=copy.deepcopy(doc);bad['packages']=[p for p in bad['packages'] if not(p['selector_id']==selector and p['resolution']=='220x132' and p['family']=='channel-'+style)]
   for sync in [skin,engine.sync]:assert any(selector+'/220x132/'+style in e for e in sync.validate_background_coverage(bad))
 metadata={p['filename']:p for p in doc['parts']};loaded={}
 packages=[p for p in doc['packages'] if p['selector_id'] in ['345W','500E'] or p['selector_id']=='450W' and p['resolution']=='50x30'];assert len(packages)==21
 for p in packages:
  chunks=[]
  for url in p['parts']:
   name=url.rsplit('/',1)[-1];path=args.part_dir/name if args.part_dir else None
   b=path.read_bytes() if path and path.exists() else urllib.request.urlopen(url,timeout=90).read();m=metadata[name];assert sha(b)==m['sha256'] and len(b)==m['bytes'];chunks.append(b);loaded[url]=b
   if path and not path.exists():path.write_bytes(b)
  raw=b''.join(chunks);assert sha(raw)==p['sha256'] and len(raw)==p['bytes']
  with zipfile.ZipFile(io.BytesIO(raw)) as z:
   assert z.testzip() is None;images={n:z.read(n) for n in z.namelist()};assert len(images)==p.get('png_count',len(images))
   for n,b in images.items():assert b[:8]==b'\x89PNG\r\n\x1a\n' and tuple(int.from_bytes(b[k:k+4],'big') for k in [16,20])==tuple(map(int,p['resolution'].split('x')))
  with tempfile.TemporaryDirectory() as t:
   folder=Path(t);archive=folder/'in.zip';archive.write_bytes(raw);dest=folder/'picons';dest.mkdir();foreign=dest/'1_0_1_FFFE_FFFE_3_EB0000_0_0_0.png';foreign.write_bytes(b'foreign-position-user-file');installed,available=install(None,str(archive),str(dest),wanted=set(images));assert installed==available==set(images);assert all((dest/n).read_bytes()==b for n,b in images.items());assert foreign.read_bytes()==b'foreign-position-user-file'
  print('FULLHDGLASS INSTALLED',p['selector_id'],p['resolution'],p['family'],flush=True)
  p['_images']=images
 body=json.dumps({**doc,'packages':[{k:v for k,v in p.items() if k!='_images'} for p in doc['packages']]}).encode()
 def opener(url):return io.BytesIO(body if url==engine.sync.RUNTIME_MANIFEST_URL else loaded[url])
 checks=0
 for p in packages:
  images=p['_images'];tv=next(n for n in images if n.split('_')[2]!='2');rad=next((n for n in images if n.split('_')[2]=='2'),None)
  for mode in [engine.sync.UPDATE_MODE_INCREMENTAL,engine.sync.UPDATE_MODE_REPLACE_ALL,engine.sync.UPDATE_MODE_SYNC_TV,engine.sync.UPDATE_MODE_SYNC_TV_RADIO]:
   with tempfile.TemporaryDirectory() as t:
    folder=Path(t);dest=folder/'picons';dest.mkdir();foreign=dest/'1_0_1_FFFE_FFFE_3_EB0000_0_0_0.png';foreign.write_bytes(b'foreign-position-user-file');fields=tv[:-4].split('_');stale=dest/('_'.join(fields[:3]+['FFFD','FFFD']+fields[5:])+'.png');stale.write_bytes(next(iter(images.values())));(dest/tv).write_bytes(b'old')
    enigma=folder/'enigma2';enigma.mkdir();(enigma/'bouquets.tv').write_text('#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.new.tv" ORDER BY bouquet\n');(enigma/'userbouquet.new.tv').write_text('#NAME New position\n#SERVICE '+tv[:-4].replace('_',':')+':\n')
    if rad:(enigma/'bouquets.radio').write_text('#SERVICE 1:7:2:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.new.radio" ORDER BY bouquet\n');(enigma/'userbouquet.new.radio').write_text('#NAME New radio\n#SERVICE '+rad[:-4].replace('_',':')+':\n')
    prefs=engine.sync.set_task_position_bindings(engine.sync.default_preferences(),[engine.sync.task_binding_for_package_selector(p['selector_id'])]);prefs.update(resolution=p['resolution'],style=p['family'][8:],update_mode=mode,destination=str(dest));runner=engine.PiconRunner(opener=opener,enigma2_dir=str(enigma),lock_path=str(folder/'lock'));result=runner.run([prefs]);wanted=set(images) if mode in [engine.sync.UPDATE_MODE_INCREMENTAL,engine.sync.UPDATE_MODE_REPLACE_ALL] else {tv}|({rad} if rad and mode==engine.sync.UPDATE_MODE_SYNC_TV_RADIO else set());assert all((dest/n).read_bytes()==images[n] for n in wanted);assert foreign.read_bytes()==b'foreign-position-user-file';assert stale.exists()==(mode in [engine.sync.UPDATE_MODE_INCREMENTAL,engine.sync.UPDATE_MODE_SYNC_TV_RADIO])
    if mode==engine.sync.UPDATE_MODE_INCREMENTAL:assert runner.run([prefs])=={'added':0,'changed':0,'removed':0}
    checks+=1
  print('PICONHUB ALL FOUR MODES',p['selector_id'],p['resolution'],p['family'],flush=True)
 model_providers={'ANTIKSAT','DIGI_TELLY','FREESAT','CANALPLUS_SK','CANALPLUS_CZ'}
 report=dict(status='ALL_SATELLITE_PROVIDER_BACKGROUNDS_VERIFIED',physical_positions=len([s for s in physical if s not in model_providers]),native_download_selectors=len(physical),satellite_variants=len([s for s in physical if s not in model_providers])*9,selector_resolution_groups=len(groups),download_plans_both_clients=plans,actual_fullhdglass_installs=len(packages),actual_piconhub_mode_installs=checks,all_three_backgrounds=True,provider_and_satellite_missing_style_rejections=True,foreign_position_files_preserved=True,repeat_incremental_zero_changes=True,physical_receiver_tested=False)
 args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
