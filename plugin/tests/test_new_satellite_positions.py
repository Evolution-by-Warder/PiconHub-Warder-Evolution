import copy,importlib,io,json,pathlib,sys,tempfile,types,unittest
ROOT=pathlib.Path(__file__).parents[1]/'src/Plugins/Extensions/WarderPiconHub'
namespace=types.ModuleType('new_satellite_tests');namespace.__path__=[str(ROOT)];sys.modules[namespace.__name__]=namespace
sync=importlib.import_module(namespace.__name__+'.warder_skin_sync');model=importlib.import_module(namespace.__name__+'.warder_model')

class NewSatelliteTests(unittest.TestCase):
 def test_namespace_and_explicit_identity_keep_new_positions_separate(self):
  cases=[('345W','34.5w','1_0_19_1_1_1F90_CB70000_0_0_0'),('500E','50.0e','1_0_1_1_1_FF01_1F42D5E_0_0_0')]
  for sid,pos,ref in cases:
   self.assertEqual(sync.canonical_position_for_selector(sid),pos);self.assertEqual(sync.service_orbital_position(ref.replace('_',':')),pos)
   prefs=sync.set_task_position_bindings(sync.default_preferences(),[sync.task_binding_for_package_selector(sid)])
   prefs.update(style='transparent',resolution='50x30',update_mode=sync.UPDATE_MODE_INCREMENTAL)
   self.assertTrue(sync.channel_preferences_ready(prefs));q=sync.build_runtime_queue(prefs);self.assertEqual(q['package_selectors'],[sid]);self.assertIn(sid,dict(model.SATELLITES))
 def test_all_three_styles_remain_valid_for_both_new_positions(self):
  for sid in ['345W','500E']:
   for size in ['50x30','220x132','400x240']:
    for style in ['transparent','white','black']:
     prefs=sync.set_task_position_bindings(sync.default_preferences(),[sync.task_binding_for_package_selector(sid)]);prefs.update(style=style,resolution=size,update_mode=sync.UPDATE_MODE_INCREMENTAL)
     self.assertTrue(sync.channel_preferences_ready(prefs));self.assertEqual(sync.build_runtime_queue(prefs)['style'],style)
 def test_policy_requires_provider_and_satellite_backgrounds(self):
  policy={'styles':['transparent','white','black'],'resolutions':['50x30','220x132','400x240']};packages=[]
  for sid,key,sizes in [('345W','34.5w',policy['resolutions']),('CANALPLUS_SK','23.5e/canal-plus-sk',['220x132'])]:
   for size in sizes:
    for style in policy['styles']:packages.append(dict(selector_id=sid,warder_key=key,resolution=size,family='channel-'+style))
  doc=dict(satellite_variant_policy=policy,packages=packages);self.assertEqual(sync.validate_background_coverage(doc),[])
  for sid in ['345W','CANALPLUS_SK']:
   for style in policy['styles']:
    bad=copy.deepcopy(doc);bad['packages']=[p for p in bad['packages'] if not(p['selector_id']==sid and p['resolution']=='220x132' and p['family']=='channel-'+style)]
    self.assertTrue(any(sid+'/220x132/'+style in e for e in sync.validate_background_coverage(bad)))
 def test_replacement_removes_only_stale_files_of_exact_new_position(self):
  live='1_0_19_1_1_1F90_CB70000_0_0_0.png';stale='1_0_1_FFFE_1_1F90_CB70000_0_0_0.png';foreign='1_0_1_FFFE_1_1_EB0000_0_0_0.png'
  result=sync.plan_stale_position_picons([live,stale,foreign],['34.5w'],[live]);self.assertEqual(result,[stale])

if __name__=='__main__':unittest.main()
