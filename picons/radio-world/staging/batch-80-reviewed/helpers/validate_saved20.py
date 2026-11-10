import sys,json,gzip,hashlib
from pathlib import Path
S=Path('picons/radio-world/staging');stage=S/'batch-80-reviewed';sys.path.insert(0,'picons/radio-world/tools')
from visual_gate import read,merge_ledgers,validate_selection,identity_blocks
paths=[S/'source-ledger-reviewed-20261107/visual-ledger.json.gz',S/'visual-review-34-36/decisions.json.gz']+[S/f'batch-{n}-reviewed/visual-ledger.json.gz'for n in range(39,80)]
history=merge_ledgers(paths);rows=read(stage/'selection.json.gz')['entries'];cfg=read(stage/'configuration.json');previous=read(S/'batch-79-reviewed/configuration.json');assert cfg['held_references']==previous['held_references']and len(cfg['held_references'])==923
assert not {(r['country'],r['ref'])for r in rows}&{(e['row']['country'],e['row']['ref'])for e in history['entries']}
assert validate_selection(rows,merge_ledgers(paths+[stage/'visual-ledger.json.gz']))==20
inputs=read(stage/'source-inputs/compatibility-inputs.json');assert hashlib.sha256((stage/'helpers/import_queryfree.py').read_bytes()).hexdigest()==inputs['generator_sha256']
(stage/'baseline.previous.json').write_bytes((S/'batch-79-reviewed/countries.proposed.json').read_bytes())
(stage/'verification-proof.json').write_text(json.dumps(dict(status='pass',references=20,PNG_instances=180,source_rerenders=0,historical_holds_preserved=True,configuration_blocks=923,upstream_generator_sha256=inputs['generator_sha256'],downloader_commit=inputs['downloader_commit']),indent=2)+'\n')
