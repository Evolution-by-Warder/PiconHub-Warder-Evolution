"""Regressions against actual51 physical recovery and actual2db baseline metadata."""
import copy,gzip,json,os,sys,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE.parents[2]/'tools'))
from technical_resolution import authority,recovery,authorize,RECEIPT_SHA
from visual_gate import read,fingerprint
from baseline_admission import inspect,fetch_release

class RealRecovery44(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage=Path(os.environ.get('WARDER_STAGE44',HERE.parent))
        cls.snapshot=Path(os.environ['WARDER_SNAPSHOT']);cls.final=Path(os.environ['WARDER_FINAL_SNAPSHOT'])
        cls.authority=authority(HERE/'evidence/recovered-new96-review-receipts.json',cls.snapshot,cls.final)
        cls.proof=read(cls.stage/'resolution-proof.json');cls.physical=recovery(cls.stage/'recovery-proof.json',cls.proof['new_recovery_proof_sha256'],cls.authority)
        cls.rows=read(cls.stage/'selection.json.gz')['entries'];cls.ledger=read(cls.stage/'visual-ledger.json.gz')
        cls.historical=read(HERE.parents[2]/'staging/batch-43-reviewed/visual-ledger.json.gz')
        cls.holds={}
        for h in cls.historical['source_holds']:cls.holds.setdefault((h['country'],h['ref']),[]).append(h)
        cls.recovered=[r for r in cls.rows if(r['country'],r['ref'])in cls.physical['entries']]
    def review(self,row):return next(e for e in self.ledger['entries']if e['decision']=='approve'and fingerprint(e['row'])==fingerprint(row))
    def test_all_actual51_physical_rows_resolve_exact_technical_holds(self):
        self.assertEqual(len(self.recovered),51)
        for r in self.recovered:
            x=authorize(r,self.review(r),self.holds[(r['country'],r['ref'])],self.authority,self.physical);self.assertEqual(x['resolution_evidence_sha256'],self.physical['sha256'])
    def test_actual_new80_counts_are_derived(self):
        cfg=read(self.stage/'configuration.json');self.assertEqual(cfg['references'],len(self.rows));self.assertEqual(cfg['expected_coverage'],3010+len(self.rows));self.assertEqual(len(self.rows),80)
    def test_old_receipt_digest_alone_cannot_resolve_new_pngs(self):
        r=self.recovered[0];e=copy.deepcopy(self.review(r));e['resolution_evidence_sha256']=RECEIPT_SHA
        with self.assertRaises(ValueError):authorize(r,e,self.holds[(r['country'],r['ref'])],self.authority,self.physical)
    def test_three_actually_new_graphic_holds_cannot_use_old_approval(self):
        held=[e for e in self.ledger['entries']if e['decision']=='hold'and(e['row']['country'],e['row']['ref'])in self.authority]
        self.assertEqual(len(held),3)
        for e in held:
            row=e['row'];forged=copy.deepcopy(e);forged.update(decision='approve',resolves_source_hold=True,resolution_evidence_sha256=self.physical['sha256'])
            with self.assertRaises(ValueError):authorize(row,forged,self.holds[(row['country'],row['ref'])],self.authority,self.physical)
    def test_changed_api_source_cannot_inherit_recovery(self):
        row=copy.deepcopy(self.recovered[0]);row['provenance']['page_sha256']='0'*64
        with self.assertRaises(ValueError):authorize(row,self.review(self.recovered[0]),self.holds[(row['country'],row['ref'])],self.authority,self.physical)
    def test_genuine_hold_cannot_be_cleared_as_technical(self):
        row=self.recovered[0];holds=copy.deepcopy(self.holds[(row['country'],row['ref'])]);holds[0]['hold_kind']='permanent-country-excluded'
        with self.assertRaises(ValueError):authorize(row,self.review(row),holds,self.authority,self.physical)
    def test_new_physical_proof_changed_bytes_fail_pinned_sha(self):
        raw=(self.stage/'recovery-proof.json').read_bytes()
        with tempfile.TemporaryDirectory()as d:
            p=Path(d)/'proof.json';p.write_bytes(raw+b' ')
            with self.assertRaises(ValueError):recovery(p,self.physical['sha256'],self.authority)
    def test_old_receipt_is_not_a_physical_recovery_proof(self):
        with self.assertRaises((ValueError,KeyError)):recovery(HERE/'evidence/recovered-new96-review-receipts.json',RECEIPT_SHA,self.authority)
    def test_baseline_same_nine_hashes_reuse_and_changed_new_artwork_holds(self):
        raw=(self.stage/'baseline.previous.json').read_bytes();countries=read(self.stage/'baseline.previous.json')['countries'];country=next(r for r in countries if r['id']=='AL')
        cache=Path(os.environ.get('WARDER_MANIFEST_CACHE',self.stage/'manifest-cache'));m=fetch_release(country['release'],cache)
        variants={size+'/'+style:values['files']for size,styles in m['packages'].items()for style,values in styles.items()};name=next(iter(set.intersection(*(set(v)for v in variants.values()))))
        row=dict(country='AL',ref=name[:-4].replace('_',':'),variants={k:dict(sha256=v[name])for k,v in variants.items()})
        new,proof=inspect([row],raw,cache);self.assertEqual(len(new),0);self.assertEqual(proof['already_covered_identical'],1)
        bad=copy.deepcopy(row);bad['variants']['220x132/white']['sha256']='0'*64
        new,proof=inspect([bad],raw,cache);self.assertEqual(len(new),0);self.assertEqual(proof['held_new_artwork'],1)
if __name__=='__main__':unittest.main()
