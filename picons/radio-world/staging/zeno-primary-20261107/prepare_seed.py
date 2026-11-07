import hashlib,json,sys,tarfile
from pathlib import Path,PurePosixPath
stage=Path(sys.argv[1]);dest=Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True);manifest=json.loads((stage/'cache-parts.json').read_text());archive=dest/'cache.tar.gz';data=b''
for part in manifest['parts']:
 b=(stage/part['path']).read_bytes();assert len(b)==part['bytes']and hashlib.sha256(b).hexdigest()==part['sha256'];data+=b
assert len(data)==manifest['bytes']and hashlib.sha256(data).hexdigest()==manifest['sha256'];archive.write_bytes(data)
with tarfile.open(archive,'r:gz')as tar:
 for m in tar.getmembers():
  p=PurePosixPath(m.name);assert not p.is_absolute()and '..'not in p.parts and p.parts[0]=='cache'and not m.issym()and not m.islnk()
 tar.extractall(dest,filter='data')
package=json.loads((stage/'package-manifest.json').read_text())
for name in('freezer.py','input.json'):
 b=(stage/name).read_bytes();assert hashlib.sha256(b).hexdigest()==package['files'][name]['sha256']
print('Seed success cache SHA/parts/input/freezer verified; no HTTP refetch')
