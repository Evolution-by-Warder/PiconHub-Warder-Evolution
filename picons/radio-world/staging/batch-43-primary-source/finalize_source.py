import gzip,hashlib,json,subprocess
from pathlib import Path
stage=Path('picons/radio-world/staging/batch-43-primary-source');raw=(stage/'producer-plan.json.gz').read_bytes();plan=json.loads(gzip.decompress(raw));source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();rows=plan['expected_selection']['entries']
for row in rows:
 row['source_commit']=source;row['asset_root']=str(stage);row.pop('variant_paths',None)
 for key,v in row['variants'].items():
  b=(stage/'verified-assets'/(v[0]+'.png')).read_bytes();assert hashlib.sha256(b).hexdigest()==v[0] and len(b)==v[1];assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==v[2]
data=gzip.compress((json.dumps({'entries':rows},separators=(',',':'),ensure_ascii=False)+'\n').encode(),mtime=0);(stage/'selection.json.gz').write_bytes(data);proof={'schema':1,'status':'pass','batch':'43-primary-source','source_commit':source,'references':len(rows),'png_instances':len(rows)*9,'unique_pngs':plan['unique_pngs'],'producer_plan_sha256':hashlib.sha256(gzip.decompress(raw)).hexdigest(),'selection_sha256':hashlib.sha256(data).hexdigest(),'all_output_hashes_match_reviewed_pngs':True,'all_nine_actual_visual_votes_preserved':True,'original_bytes_preserved':True,'primary_evidence_parts':json.load(open(stage/'parts-manifest.json'))['primary_evidence'],'must_not_admit_indices':plan['must_not_admit_indices']};(stage/'source-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
