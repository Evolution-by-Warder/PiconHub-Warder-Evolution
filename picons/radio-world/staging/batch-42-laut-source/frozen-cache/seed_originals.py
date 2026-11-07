#!/usr/bin/env python3
"""Restore only pinned preflight-failing original bytes; never replace unequal files."""
import hashlib,io,json,tarfile
from pathlib import Path
root=Path(__file__).resolve().parent
manifest=json.loads((root/'manifest.json').read_bytes())
parts=[]
for row in manifest['parts']:
 b=(root/row['name']).read_bytes()
 assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'], 'Frozen seed part differs'
 parts.append(b)
raw=b''.join(parts)
assert len(raw)==manifest['archive_bytes'] and hashlib.sha256(raw).hexdigest()==manifest['archive_sha256'], 'Frozen seed archive differs'
expected=manifest['originals'];writes={}
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
 members=archive.getmembers()
 assert len(members)==len(expected) and len({m.name for m in members})==len(members)
 for m in members:
  assert m.isfile() and m.name.endswith('.img') and '/' not in m.name and m.name[:-4] in expected
  sha=m.name[:-4];resource=expected[sha];b=archive.extractfile(m).read()
  assert len(b)==resource['bytes'] and hashlib.sha256(b).hexdigest()==sha
  assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==resource['git_blob']
  writes[root.parent/'originals'/m.name]=b
for path,b in writes.items():
 assert not path.exists() or path.read_bytes()==b, 'Refusing unequal original overwrite'
for path,b in writes.items():
 if not path.exists():
  path.parent.mkdir(parents=True,exist_ok=True)
  with path.open('xb') as f:f.write(b)
print('Restored exact frozen preflight originals:',len(writes))
