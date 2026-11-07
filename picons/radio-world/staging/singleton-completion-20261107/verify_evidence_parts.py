import hashlib,io,json,tarfile
from pathlib import Path
stage=Path('picons/radio-world/staging/singleton-completion-20261107')
proof=json.load(open(stage/'evidence-archive-proof.json'));manifest=json.load(open(stage/'evidence-parts.json'));parts=[]
for row in manifest['parts']:
 raw=(stage/'evidence-parts'/row['path']).read_bytes();assert len(raw)==row['bytes']and hashlib.sha256(raw).hexdigest()==row['sha256'];parts.append(raw)
raw=b''.join(parts);assert len(raw)==proof['bytes']and hashlib.sha256(raw).hexdigest()==proof['sha256']
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz')as archive:
 inventory=json.load(archive.extractfile('evidence-inventory.json'))['files'];assert len(inventory)==proof['evidence_files']
 for row in inventory:
  body=archive.extractfile(row['path']).read();assert len(body)==row['bytes']and hashlib.sha256(body).hexdigest()==row['sha256']
print('PASS',len(parts),'archiveparts and',len(inventory),'primary evidence member SHA256')
