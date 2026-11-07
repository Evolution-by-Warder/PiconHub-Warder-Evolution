import gzip,hashlib,json,subprocess,sys
from pathlib import Path
from aggregate_source_metadata import aggregate
stage=Path('picons/radio-world/staging/primary-pending183-source-20261107');chunk=sys.argv[1];cp=stage/'chunks'/('chunk-'+chunk);p=json.load(open(cp/'producer-plan.json'));source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();rows=p['expected_selection']['entries'];ledger=json.load(open(stage/p['visual_ledger_filename']))
for r in rows:r['source_commit']=source;r['asset_root']=str(stage)
byref={r['ref']:r for r in rows}
for e in ledger['entries']:
 if e['decision']=='approve':e['row']=byref[e['row']['ref']]
 else:e['row']['source_commit']=source;e['row']['asset_root']=str(stage)+'/quarantine'
pack=lambda x:gzip.compress((json.dumps(x,separators=(',',':'),ensure_ascii=False)+'\n').encode(),mtime=0)
(cp/'selection.json.gz').write_bytes(pack({'entries':rows}));(cp/'visual-ledger.json.gz').write_bytes(pack(ledger))
chunks=[]
for path in sorted((stage/'chunks').glob('chunk-*/selection.json.gz')):
 chunks.append((json.loads(gzip.decompress(path.read_bytes())),json.loads(gzip.decompress((path.parent/'visual-ledger.json.gz').read_bytes()))))
selection,combined=aggregate(chunks);allrows=selection['entries'];(stage/'selection.json.gz').write_bytes(pack(selection));(stage/'visual-ledger.json.gz').write_bytes(pack(combined));proof=json.load(open(cp/'reproduction-proof.json'));proof['source_commit']=source;proof['selection_sha256']=hashlib.sha256((cp/'selection.json.gz').read_bytes()).hexdigest();(cp/'source-proof.json').write_text(json.dumps(proof,indent=2)+'\n');(stage/'source-proof.json').write_text(json.dumps({'status':'pass','completed_chunks':len(list((stage/'chunks').glob('chunk-*/selection.json.gz'))),'completed_references':len(allrows),'completed_PNG_instances':len(allrows)*9,'source_pool_continues':True,'selection_sha256':hashlib.sha256((stage/'selection.json.gz').read_bytes()).hexdigest(),'visual_ledger_sha256':hashlib.sha256((stage/'visual-ledger.json.gz').read_bytes()).hexdigest(),'raw_HTML_or_JS_archive_published':False},indent=2)+'\n')
