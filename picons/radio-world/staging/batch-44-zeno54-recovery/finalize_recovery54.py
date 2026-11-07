"""Publish truthful source metadata after physical PNG and proof commits exist."""
import sys,json,gzip,hashlib,re,copy
from pathlib import Path
stage=Path(sys.argv[2]);phase=sys.argv[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def raw(o):return (json.dumps(o,ensure_ascii=False,indent=2)+'\n').encode()
def put(n,b):
 p=stage/n
 if p.exists():assert p.read_bytes()==b,'Refusing unequal existing metadata '+n
 else:p.write_bytes(b)
plan=json.loads((stage/'producer-plan.json').read_bytes());votes=json.loads((stage/'new-nine-variant-votes.json').read_bytes());byid={q['index']:q for q in votes['entries']};observations={o['index']:o for o in plan['primary_observations']}
if phase=='proof':
 pixel=sys.argv[3];assert re.fullmatch('[0-9a-f]{40}',pixel)
 entries=[];holds=[]
 for r in plan['expected_selection']['entries']:
  q=byid[r['index']];o=observations[r['index']]
  for k,v in r['variants'].items():
   directory='verified-assets'if q['decision']=='approve'else'quarantine-assets';b=(stage/directory/(v[0]+'.png')).read_bytes();assert sha(b)==v[0]and len(b)==v[1]and hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==v[2]
  e=dict(index=r['index'],country=r['country'],ref=r['ref'],station=r['station'],source_sha256=o['source_sha256'],api_sha256=o['api_resource']['sha256'],variants=r['variants'],source_commit=pixel,reviewed_variants=q['reviewed_variants'],decision=q['decision'],reason=q['reason'],exact_catalogue_membership=o['exact_catalogue_membership'],primary_fields=o['primary_fields'])
  (entries if q['decision']=='approve'else holds).append(e)
 assert len(entries)==51 and len(holds)==3
 proof=dict(schema=1,status='pass',source_pixel_commit=pixel,references=51,png_instances=459,physically_preserved_references=54,physically_preserved_png_instances=486,old_manual_receipt_sha256=plan['old_manual_receipt_sha256'],old_manual_receipt_commit='9376e0665b74df3f3bece55c924df48ce2ec529e',frozen_source_commit=plan['frozen_checkpoint_commit'],final_frozen_source_commit=plan['final_frozen_source_commit'],new_actual_nine_review_sha256=sha((stage/'new-nine-variant-votes.json').read_bytes()),producer_plan_sha256=sha((stage/'producer-plan.json').read_bytes()),runtime={'pillow':'13.0.0'},unchanged_main_renderer_and_masters=plan['resources'],all_output_sha256_bytes_gitblob_physically_checked=True,all_nine_variants_actually_visually_reviewed=True,entries=entries,new_graphic_holds=holds,no_production_zip_rebuilt=True,no_live_station_request=True,old_lost_tuple_values_not_invented=True)
 put('recovery54-proof.json',raw(proof))
elif phase=='ledger':
 proofcommit=sys.argv[3];assert re.fullmatch('[0-9a-f]{40}',proofcommit);b=(stage/'recovery54-proof.json').read_bytes();proof=json.loads(b);psha=sha(b);pixel=proof['source_pixel_commit'];ledger=[];approved=[]
 for initial in plan['expected_selection']['entries']:
  r=copy.deepcopy(initial);r['source_commit']=pixel;r['asset_root']=str(stage);r.pop('variant_paths',None);q=byid[r['index']];entry=dict(index=r['index'],row=r,decision=q['decision'],reason=q['reason'],reviewed_variants=q['reviewed_variants'])
  if q['decision']=='approve':
   flags=dict(resolves_source_hold=True,resolution_evidence_sha256=psha,resolution_evidence_commit=proofcommit,resolution_evidence_path=str(stage/'recovery54-proof.json'));r.update(flags);entry.update(flags);approved.append(r)
  else:r['quarantine_asset_root']=str(stage/'quarantine-assets')
  ledger.append(entry)
 assert len(approved)==51 and len(ledger)==54
 sel=gzip.compress(raw(dict(schema=1,entries=approved)),mtime=0);led=gzip.compress(raw(dict(schema=3,entries=ledger,source_holds=[])),mtime=0)
 put('selection.json.gz',sel);put('visual-ledger.json.gz',led)
 put('source-proof.json',raw(dict(schema=1,status='pass',source_commit=pixel,recovery_proof_commit=proofcommit,recovery_proof_sha256=psha,recovery_proof_path=str(stage/'recovery54-proof.json'),references=51,png_instances=459,preserved_references=54,preserved_png_instances=486,quarantined_references=3,selection_sha256=sha(sel),ledger_sha256=sha(led),primary_freeze_final=True,final_freeze_reconciliation_required=False,production_ready=False,country_ci_ready=True)))
else:raise ValueError('Unknown phase')
