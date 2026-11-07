"""Join only explicitly pinned public JSON plan parts; never downloads anything."""
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]);manifest=json.loads((root/'input-parts.json').read_text())
for file in manifest['files']:
 data=b''
 for part in file['parts']:
  raw=(root/part['path']).read_bytes();assert len(raw)==part['bytes']and hashlib.sha256(raw).hexdigest()==part['sha256'];data+=raw
 assert len(data)==file['bytes']and hashlib.sha256(data).hexdigest()==file['sha256'];json.loads(data);dest=root/file['path'];dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists():assert dest.read_bytes()==data
 else:dest.write_bytes(data)
print('Public JSON input parts SHA/bytes/parse PASS')
