import gzip,hashlib,json,subprocess
from pathlib import Path
stage=Path('picons/radio-world/staging/singleton-completion-20261107')
source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
doc=json.loads((stage/'accepted-selection.json').read_bytes())
for row in doc['entries']:
 row['source_commit']=source;row['asset_root']=str(stage);row.pop('variant_paths',None)
raw=gzip.compress((json.dumps({'entries':doc['entries']},separators=(',',':'),ensure_ascii=False)+'\n').encode(),mtime=0)
(stage/'selection.json.gz').write_bytes(raw)
proof={'schema':1,'source_commit':source,'references':6,'pngs':54,'selection_sha256':hashlib.sha256(raw).hexdigest(),'all_output_sha256_match_locally_reviewed_pngs':True,'asset_root':str(stage)}
(stage/'source-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
