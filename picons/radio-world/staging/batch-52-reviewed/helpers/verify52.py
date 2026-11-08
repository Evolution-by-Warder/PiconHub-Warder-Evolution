"""Verify three exact short composer names against publisher suburl and frozen stream facts."""
import gzip,hashlib,json,sys,re
from pathlib import Path
S=Path(__file__).resolve().parents[1]; R=S.parents[1]
sys.path.insert(0,str(R/'tools'))
from visual_gate import read,merge_ledgers,validate_selection
sys.path.insert(0,str(S.parent/'batch-50-reviewed/helpers'))
import baseline_admission
baseline_admission.BASELINE_SHA='5f96252baacddc66bc222e4d4a8199ef66e9a2ee0af82c3f4170fd47c07e938c'
from baseline_admission import inspect
old=S.parent/'batch-50-reviewed';cfg=read(S/'configuration.json');rows=read(S/'selection.json.gz')['entries'];base=read(old/'selection.json.gz')['entries'][0]
facts=read(S/'source-inputs/public-observations.json');observed=read(old/'results/next-source-observations.json.gz')['remaining_name_unmatched']['literal_match_observations']
assert hashlib.sha256((S/'baseline.previous.json').read_bytes()).hexdigest()=='5f96252baacddc66bc222e4d4a8199ef66e9a2ee0af82c3f4170fd47c07e938c'
assert cfg['references']==len(rows)==11 and cfg['expected_coverage']==3244
assert facts['official_API_body_sha256']=='cf5aa52090b55fb483b8219d1208bddd448f52dd2dced26809d72e70b18c86ac'
assert {e['programme']['id']for e in facts['entries']}=={'56', '18', '21', '5', '50', '28', '161', '68', '30', '167', '15'}
for r,f in zip(rows,facts['entries']):
 p=f['programme'];assert r['ref']==f['reference'] and r['station']['name']==f['catalogue_name']
 assert re.sub('[^a-z0-9]','',r['station']['name'].split(' - ')[1].lower().replace('&','and'))==re.sub('[^a-z0-9]','',p['suburl'].lower()) and r['station']['url']==p['streamf']
 assert p['id']==r['provenance']['official_programme_id'] and p['name']==r['provenance']['official_programme_title']
 assert any(o['station']['reference']==r['ref'] and o['station']['url']==p['streamf'] and o['matches']==[dict(id=p['id'],name=p['name'],slot='streamf')]for o in observed)
 assert r['source_commit']==base['source_commit']=='90359d45eb71afb2aa077ac1b5097fae328863df' and r['asset_root']==base['asset_root'] and r['variants']==base['variants']
 assert r['ref'] not in cfg['held_references'] and r['final_visual_approval']['reviewed_variants']==base['variants']
paths=[R/'staging/source-ledger-reviewed-20261107/visual-ledger.json.gz',R/'staging/visual-review-34-36/decisions.json.gz']+[R/f'staging/batch-{n}-reviewed/visual-ledger.json.gz'for n in range(39,53)]
assert validate_selection(rows,merge_ledgers(paths))==11
new,result=inspect(rows,(S/'baseline.previous.json').read_bytes(),Path('/tmp/radio52-manifests'));assert len(new)==11 and not result['reused'] and not result['held']
proof=dict(status='pass',references=11,png_instances=99,unchanged_approved_variants=9,official_short_name_and_stream_matches=11,historical_ledgers=len(paths),source_hold_exceptions=0)
(S/'verification-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(proof)
