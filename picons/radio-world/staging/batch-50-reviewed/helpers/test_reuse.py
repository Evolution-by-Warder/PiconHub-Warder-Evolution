import copy,json,gzip,unittest
from pathlib import Path
from verify_reuse import validate_alias
S=Path(__file__).resolve().parent.parent/'source-inputs/radioart78'
class AliasIdentityRegression(unittest.TestCase):
 def setUp(self):
  self.rows=json.loads(gzip.decompress((S/'selection.json.gz').read_bytes()))['entries'];self.facts=json.loads((S/'public-observations.json').read_text())['entries'];self.base=json.loads((S/'source-readback-proof.json').read_text())['base_approved_row']
 def test_all78_actual_aliases_pass(self):
  for r,o in zip(self.rows,self.facts):validate_alias(r,o,self.base)
 def reject(self,mutate):
  r=copy.deepcopy(self.rows[0]);o=copy.deepcopy(self.facts[0]);mutate(r,o)
  with self.assertRaises(AssertionError):validate_alias(r,o,self.base)
 def test_other_stream_rejected(self):self.reject(lambda r,o:o['stream_binding'].update(text='https://example.invalid/other'))
 def test_other_programme_name_rejected(self):self.reject(lambda r,o:o['programme'].update(name='Different programme'))
 def test_other_programme_id_rejected(self):self.reject(lambda r,o:o['programme'].update(id='9999'))
 def test_changed_artwork_rejected(self):self.reject(lambda r,o:r['variants']['50x30/white'].__setitem__(0,'0'*64))
 def test_premium_field_is_never_accepted(self):self.reject(lambda r,o:o['stream_binding'].update(field='liveh'))
if __name__=='__main__':unittest.main()
