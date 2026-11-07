"""Prepare batch42 locally from immutable reviewed source exports; never render/upload/merge.
Run only after both producer exports are pinned. Counts derive from validated files.
"""
from pathlib import Path
import argparse,copy,gzip,hashlib,json,re,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from visual_gate import read,merge_ledgers,validate_selection,identity_blocks
ROOT=Path('continuation/output/picons/radio-world/staging')
BASE='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'
HISTORICAL=[ROOT/'source-ledger-reviewed-20261107/visual-ledger.json.gz',ROOT/'visual-review-34-36/decisions.json.gz',*[ROOT/f'batch-{n}-reviewed/visual-ledger.json.gz' for n in (39,40,41)]]
def packed(value):return gzip.compress((json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n').encode(),mtime=0)
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--laut-selection',type=Path,required=True);p.add_argument('--laut-ledger',type=Path,required=True)
 p.add_argument('--singleton-selection',type=Path,required=True);p.add_argument('--singleton-ledger',type=Path,required=True)
 p.add_argument('--parent',default='673062395da2f49cf2c739a16c605eedc9553480')
 p.add_argument('--baseline',type=Path,default=Path('continuation/results-41-reviewed/countries.proposed.json'))
 p.add_argument('--expected-baseline-sha256',default='85f17a3022d770a31dd1cd2fcf53ba19a6681d4c7ec0a0133ebe56e59a14fd30')
 p.add_argument('--expected-laut',type=int,default=435);p.add_argument('--expected-singletons',type=int,default=6)
 p.add_argument('--stage',type=Path,default=ROOT/'batch-42-reviewed');a=p.parse_args()
 assert re.fullmatch('[0-9a-f]{40}',a.parent)
 raw=a.baseline.read_bytes();assert hashlib.sha256(raw).hexdigest()==a.expected_baseline_sha256
 baseline=json.loads(raw);assert len(baseline['countries'])==219
 baseline_count=sum(r['picons']for r in baseline['countries']);assert baseline_count==2429
 source_paths=[a.laut_selection,a.singleton_selection];counts=[];rows=[]
 for path,wanted in zip(source_paths,[a.expected_laut,a.expected_singletons]):
  data=read(path);entries=data['entries']if isinstance(data,dict)else data
  assert len(entries)==wanted,(str(path),len(entries),wanted);counts.append(len(entries));rows+=entries
 assert len(rows)==len({r['ref']for r in rows})
 for r in rows:
  assert re.fullmatch('[0-9a-f]{40}',r['source_commit']),('Source not pinned',r['ref'])
  assert r['asset_root'] and 'pending'not in r['asset_root'] and not r['asset_root'].startswith('/')
  assert set(r['station'])>={'name','url','group'} and len(r['variants'])==9
  assert all(isinstance(v,list)and len(v)==3 and re.fullmatch('[0-9a-f]{64}',v[0])and isinstance(v[1],int)and v[1]>0 and re.fullmatch('[0-9a-f]{40}',v[2])for v in r['variants'].values())
 new_ledger=merge_ledgers([a.laut_ledger,a.singleton_ledger]);assert validate_selection(rows,new_ledger)==len(rows)
 # Include metadata-only source holds with no invented PNG fingerprints.
 combined=merge_ledgers(HISTORICAL+[a.laut_ledger,a.singleton_ledger]);validate_selection(rows,combined)
 cfg=read(ROOT/'batch-41-reviewed/configuration.json');cfg.update(batch='42-reviewed',references=len(rows),parent_candidate=a.parent,expected_coverage=baseline_count+len(rows),selection_filename='selection.json.gz',visual_ledger_filename='visual-ledger.json.gz')
 cfg.pop('source_ledger_commit',None);cfg.pop('reuse_index',None)
 cfg['baseline_index']={'url':BASE+a.parent+'/picons/radio-world/catalog/countries.json','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
 cfg['held_references']=sorted(set(cfg['held_references'])|{ref for country,ref in identity_blocks(combined)})
 assert not set(cfg['held_references'])&{r['ref']for r in rows},'Held reference in selection'
 selection=packed({'entries':rows});cfg['selection_sha256']=hashlib.sha256(selection).hexdigest()
 a.stage.mkdir(parents=True,exist_ok=True);(a.stage/'selection.json.gz').write_bytes(selection);(a.stage/'visual-ledger.json.gz').write_bytes(packed(new_ledger));(a.stage/'configuration.json').write_text(json.dumps(cfg,indent=2)+'\n')
 provenance={'status':'prepared-locally-not-built-or-published','parent':a.parent,'baseline_covered':baseline_count,'source_reference_counts':counts,'references':len(rows),'expected_coverage':cfg['expected_coverage'],'protected_production_png_variant_entries':10332,'source_inputs':[{'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}for f in [a.laut_selection,a.laut_ledger,a.singleton_selection,a.singleton_ledger]],'active_prior_ledgers':[str(f)for f in HISTORICAL],'metadata_only_source_holds':len(new_ledger.get('source_holds',[]))}
 (a.stage/'preparation-proof.json').write_text(json.dumps(provenance,indent=2)+'\n');print(json.dumps(provenance,indent=2))
if __name__=='__main__':main()
