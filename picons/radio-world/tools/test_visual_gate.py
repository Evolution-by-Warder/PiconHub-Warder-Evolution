import copy,gzip,json,unittest
from pathlib import Path
from visual_gate import assert_no_held,fingerprint,read,validate_selection,SIZES,STYLES
ROOT=Path(__file__).resolve().parents[1]
class VisualRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger=read(ROOT/'staging/visual-review-34-36/decisions.json.gz')
        cls.good=next(e['row'] for e in cls.ledger['entries'] if e['decision']=='approve')
        cls.bad=next(e['row'] for e in cls.ledger['entries'] if e['decision']=='hold' and e['row']['station']['name']=='Tre Raadio Ring FM')
    def test_exact_approved_artwork_passes(self):self.assertEqual(validate_selection([self.good],self.ledger),1)
    def test_real_white_on_white_ring_fm_rejected(self):
        with self.assertRaises(ValueError):validate_selection([self.bad],self.ledger)
    def test_changed_png_cannot_inherit_old_approval(self):
        row=copy.deepcopy(self.good);v=row['variants']['220x132/white']
        if isinstance(v,dict):v['sha256']='0'*64
        else:v[0]='0'*64
        with self.assertRaises(ValueError):validate_selection([row],self.ledger)
    def test_missing_size_cannot_pass(self):
        row=copy.deepcopy(self.good);del row['variants']['400x240/black']
        with self.assertRaises(ValueError):validate_selection([row],self.ledger)
    def test_reference_swap_cannot_inherit_logo_approval(self):
        row=copy.deepcopy(self.good);row['ref']=self.bad['ref']
        with self.assertRaises(ValueError):validate_selection([row],self.ledger)
    def test_duplicate_cannot_inflate_counts(self):
        with self.assertRaises(ValueError):validate_selection([self.good,self.good],self.ledger)
    def test_reintroduced_hold_in_any_variant_is_blocked(self):
        for size in SIZES:
            for style in STYLES:
                packages={s:{c:{'files':{}} for c in STYLES} for s in SIZES}
                packages[size][style]['files'][self.bad['ref'].replace(':','_')+'.png']='0'*64
                index={'countries':[{'id':self.bad['country'],'release':{'url':'fixture'}}]}
                ledger={'entries':[{'row':self.bad,'decision':'hold'}]}
                with self.subTest(size=size,style=style),self.assertRaises(ValueError):assert_no_held(index,ledger,lambda e:{'packages':packages})
    def test_prior_source_rejection_cannot_be_erased_by_picture_only_review(self):
        for name in ('Vinilo Mix','Schwany 3'):
            entry=next(e for e in self.ledger['entries'] if e['row']['station']['name']==name)
            self.assertEqual(entry['decision'],'hold')
            with self.subTest(name=name),self.assertRaises(ValueError):validate_selection([entry['row']],self.ledger)
    def test_sponsor_panel_cannot_return_as_wfm(self):
        row=next(e['row'] for e in self.ledger['entries'] if e['row']['station']['name']=='Radio Wfm 105.4 - Westerlo, be')
        with self.assertRaises(ValueError):validate_selection([row],self.ledger)
    def test_ruidos_donation_panel_cannot_return(self):
        row=next(e['row'] for e in self.ledger['entries'] if e['row']['ref']=='4097:0:2:86EC:DC55:ED:0:0:0:0')
        with self.assertRaises(ValueError):validate_selection([row],self.ledger)
    def replacement_fixture(self):
        new=copy.deepcopy(self.bad)
        for k in new['variants']:
            value=new['variants'][k]
            if isinstance(value,dict):value['sha256']='1'*64
            else:value[0]='1'*64
        ledger={'entries':[{'row':self.bad,'decision':'hold'},{'row':new,'decision':'approve'}]}
        name=new['ref'].replace(':','_')+'.png'
        packages={s:{c:{'files':{name:'1'*64}} for c in STYLES} for s in SIZES}
        return ledger,packages,name
    def test_exact_separately_reviewed_nine_variant_repair_is_allowed(self):
        ledger,packages,name=self.replacement_fixture()
        index={'countries':[{'id':self.bad['country'],'release':{'url':'fixture'}}]}
        self.assertEqual(assert_no_held(index,ledger,lambda e:{'packages':packages}),1)
    def test_one_stale_variant_in_otherwise_reviewed_repair_is_rejected(self):
        ledger,packages,name=self.replacement_fixture()
        packages['220x132']['white']['files'][name]='0'*64
        index={'countries':[{'id':self.bad['country'],'release':{'url':'fixture'}}]}
        with self.assertRaises(ValueError):assert_no_held(index,ledger,lambda e:{'packages':packages})
    def test_unrendered_source_hold_blocks_selection_without_fake_variant_hashes(self):
        ledger={'entries':[{'row':self.good,'decision':'approve'}],'source_holds':[{'country':self.good['country'],'ref':self.good['ref'],'reason':'Unresolved placeholder source'}]}
        with self.assertRaises(ValueError):validate_selection([self.good],ledger)
    def test_unrendered_source_hold_cannot_return_in_country_archive(self):
        ledger,packages,name=self.replacement_fixture()
        ledger['source_holds']=[{'country':self.bad['country'],'ref':self.bad['ref'],'reason':'No verified original exists'}]
        index={'countries':[{'id':self.bad['country'],'release':{'url':'fixture'}}]}
        with self.assertRaises(ValueError):assert_no_held(index,ledger,lambda e:{'packages':packages})
    def test_unavailable_country_does_not_need_empty_zip(self):
        index={'countries':[{'id':self.bad['country'],'release':None}]};ledger={'entries':[{'row':self.bad,'decision':'hold'}]}
        self.assertEqual(assert_no_held(index,ledger,lambda e:self.fail('Unexpected download')),1)
if __name__=='__main__':unittest.main()
