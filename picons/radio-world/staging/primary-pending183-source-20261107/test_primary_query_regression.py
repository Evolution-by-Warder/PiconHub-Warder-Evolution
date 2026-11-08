import copy,json,unittest
from pathlib import Path
from reproduce_source import verify_primary_public_query
D=Path(__file__).parent
class PrimaryQueryRegression(unittest.TestCase):
 def setUp(self):
  self.p=json.load(open(D/'chunks/chunk-006/producer-plan.json'));self.f=json.load(open(D/'chunks/chunk-006/public-observations.json'))
 def test_actual_three_station_identities_pass(self):
  for o,r in zip(self.f['entries'],self.p['expected_selection']['entries']):verify_primary_public_query(o,r)
 def reject(self,mutate):
  o=copy.deepcopy(self.f['entries'][0]);r=copy.deepcopy(self.p['expected_selection']['entries'][0]);mutate(o,r)
  with self.assertRaises(AssertionError):verify_primary_public_query(o,r)
 def test_other_mount_rejected(self):self.reject(lambda o,r:r['station'].update(url=r['station']['url']+'other'))
 def test_unexpected_query_rejected(self):self.reject(lambda o,r:o['own_public_station'].update(advertised_stream_url=o['own_public_station']['advertised_stream_url']+'&other=1'))
 def test_other_station_head_identity_rejected(self):self.reject(lambda o,r:o['public_stream_station_facts'][1].update(public_station_name='Different programme'))
 def test_matching_generic_network_name_is_insufficient(self):
  def f(o,r):
   for h in o['public_stream_station_facts']:h['public_station_name']='1.FM'
  self.reject(f)
 def test_different_official_programme_title_rejected(self):self.reject(lambda o,r:o['own_public_station'].update(title='Different programme'))
if __name__=='__main__':unittest.main()
