import json,hashlib,sys
from pathlib import Path
p=Path(sys.argv[1]);m=json.loads((p/'input-parts-manifest.json').read_bytes())
for n,r in m.items():
 b=b''.join((p/x).read_bytes()for x in r['parts']);assert len(b)==r['bytes']and hashlib.sha256(b).hexdigest()==r['sha256'];json.loads(b)
 t=p/n
 if t.exists():assert t.read_bytes()==b
 else:t.write_bytes(b)
