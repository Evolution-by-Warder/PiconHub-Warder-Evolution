import copy,gzip,json,unittest
from pathlib import Path
from aggregate_source_metadata import aggregate
D=Path(__file__).parent
oldsel=json.loads(gzip.decompress((D/'chunks/chunk-003/selection.json.gz').read_bytes()));oldled=json.loads(gzip.decompress((D/'chunks/chunk-003/visual-ledger.json.gz').read_bytes()));p=json.load(open(D/'chunks/chunk-005/producer-plan.json'));newsel=p['expected_selection'];newled=json.load(open(D/'chunks/chunk-005/visual-ledger.json'))
class Regression(unittest.TestCase):
 def test_exact_white_fix_preserves_closed_hold_history(self):
  s,l=aggregate([(oldsel,oldled),(newsel,newled)]);self.assertEqual(len(s['entries']),30);self.assertEqual(len(l['superseded_render_holds']),9);self.assertEqual(sum(e['decision']=='hold'for e in l['entries']),3);self.assertEqual(l['source_holds'],oldled['source_holds'])
 def reject(self,mutate):
  a=copy.deepcopy(newsel);b=copy.deepcopy(newled);mutate(a,b)
  with self.assertRaises(AssertionError):aggregate([(oldsel,oldled),(a,b)])
 def test_unexplained_duplicate_rejected(self):self.reject(lambda s,l:l['entries'][0].pop('supersedes_render_hold'))
 def test_changed_protected_variant_rejected(self):
  def f(s,l):
   s['entries'][0]['variants']['50x30/black'][0]='0'*64;l['entries'][0]['row']=s['entries'][0]
  self.reject(f)
 def test_source_identity_hold_cannot_be_bypassed(self):
  held=copy.deepcopy(oldled);held['source_holds'].append(dict(ref=newsel['entries'][0]['ref']))
  with self.assertRaises(AssertionError):aggregate([(oldsel,held),(newsel,newled)])
 def test_previously_approved_graphic_cannot_be_replaced(self):
  a=copy.deepcopy(oldsel);b=copy.deepcopy(oldled);ref=newsel['entries'][0]['ref'];e=next(e for e in b['entries']if e['row']['ref']==ref);e['decision']='approve';a['entries'].append(e['row'])
  with self.assertRaises(AssertionError):aggregate([(a,b),(newsel,newled)])
 def test_wrong_old_pixel_commit_rejected(self):self.reject(lambda s,l:l['entries'][0]['supersedes_render_hold'].update(source_commit='0'*40))
if __name__=='__main__':unittest.main()
