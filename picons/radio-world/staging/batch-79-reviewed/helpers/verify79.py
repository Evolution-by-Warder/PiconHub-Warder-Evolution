import json,gzip,hashlib,sys
from pathlib import Path
S=Path('picons/radio-world/staging/batch-79-reviewed');sys.path.insert(0,'picons/radio-world/tools');from visual_gate import read,merge_ledgers,validate_selection
sys.path.insert(0,'picons/radio-world/staging/batch-50-reviewed/helpers');import baseline_admission
cfg=read(S/'configuration.json');desc=read(S/'source-inputs/recovery-spec.json');rows=read(S/'selection.json.gz')['entries'];assert len(rows)==cfg['references']==40 and len({r['ref']for r in rows})==40
for r,src in zip(rows,desc['stations']):
 assert r['ref']==src['station']['reference']and r['variants']==src['variants']and r['provenance']['publisher']==src['publisher']
 raw=(S/'originals'/(src['original']['sha256']+'.img')).read_bytes();assert hashlib.sha256(raw).hexdigest()==src['original']['sha256']and len(raw)==src['original']['bytes']
 for digest,n,blob in r['variants'].values():
  b=(S/'verified-assets'/(digest+'.png')).read_bytes();assert len(b)==n and hashlib.sha256(b).hexdigest()==digest and hashlib.sha1(f'blob {n}\0'.encode()+b).hexdigest()==blob
paths=[S.parent/'source-ledger-reviewed-20261107/visual-ledger.json.gz',S.parent/'visual-review-34-36/decisions.json.gz']+[S.parent/f'batch-{n}-reviewed/visual-ledger.json.gz'for n in range(39,80)];assert validate_selection(rows,merge_ledgers(paths))==40
baseline_admission.BASELINE_SHA=cfg['baseline_index']['sha256'];raw=(S/'baseline.previous.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==baseline_admission.BASELINE_SHA
new,result=baseline_admission.inspect(rows,raw,Path('/tmp/radio-official-manifests'));assert len(new)==40 and not result['reused']and not result['held']
(S/'verification-proof.json').write_text(json.dumps(dict(status='pass',references=40,PNG_instances=360,publisher_bound_originals=36,existing_artwork_rerendered=0,source_hold_exceptions=0,live_availability='Not confirmed: sampled official streams returned502; no live-audio PASS claimed.'),indent=2)+'\n')
