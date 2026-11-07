import hashlib,json
from pathlib import Path,PurePosixPath
stage=Path('picons/radio-world/staging/singleton-completion-20261107');manifest=json.load(open(stage/'original-parts-manifest.json'));plan=json.load(open(stage/'reproduce-plan.json'))
assert manifest['schema']==1
def blob(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
def check(raw,row):
 assert len(raw)==row['bytes']and hashlib.sha256(raw).hexdigest()==row['sha256']
 if 'git_blob'in row:assert blob(raw)==row['git_blob']
def safe(relative):
 p=PurePosixPath(relative);assert not p.is_absolute()and '..'not in p.parts and '\\'not in relative;return Path(p)
assert len(manifest['originals'])==1 and len(plan['originals'])==8
reconstructed={}
for row in manifest['originals']:
 expected=plan['originals'][row['sha256']];assert all(row[k]==expected[k]for k in ['path','bytes','sha256','git_blob']);dest=safe(row['path']);assert dest.parent==stage/'originals';bodies=[]
 for part in row['parts']:
  path=safe(part['path']);assert path.parent==stage/'original-parts';raw=path.read_bytes();check(raw,part);bodies.append(raw)
 raw=b''.join(bodies);check(raw,row)
 if dest.exists():assert dest.read_bytes()==raw
 reconstructed[row['sha256']]=(dest,raw)
for digest,row in plan['originals'].items():
 raw=reconstructed[digest][1]if digest in reconstructed else safe(row['path']).read_bytes();check(raw,row)
for dest,raw in reconstructed.values():
 if not dest.exists():
  dest.parent.mkdir(parents=True,exist_ok=True)
  with dest.open('xb')as f:f.write(raw)
print('PASS all8 raw original SHA256/bytes/Gitblob; GW reassembled from4 exact parts')
