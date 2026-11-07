"""Restore the exact immutable output-branch checkpoint; no station-source refetch."""
import hashlib,io,json,os,sys,tarfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request,urlopen
REPO='Evolution-by-Warder/PiconHub-Warder-Evolution';BRANCH='work/radio-zeno1519-frozen-20261107';STAGE='picons/radio-world/staging/zeno-primary-20261107';root=Path(sys.argv[1]);root.mkdir(parents=True,exist_ok=True)
try:
 with urlopen(Request('https://api.github.com/repos/'+REPO+'/git/ref/heads/'+BRANCH,headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json'}),timeout=60)as r:commit=json.load(r)['object']['sha']
except HTTPError as e:
 if e.code==404:print('No previous output checkpoint; using complete successful seed');sys.exit(0)
 raise
base='https://raw.githubusercontent.com/'+REPO+'/'+commit+'/'+STAGE+'/'
def raw(name):
 with urlopen(base+name,timeout=90)as r:return r.read()
manifest=json.loads(raw('raw-cache/manifest.json'))
for shard in manifest['shards']:
 b=raw(shard['path']);assert len(b)==shard['bytes']and hashlib.sha256(b).hexdigest()==shard['sha256']
 with tarfile.open(fileobj=io.BytesIO(b),mode='r:gz')as tar:
  for member in tar.getmembers():
   assert member.isfile()and member.name.startswith('objects/')and '/'not in member.name[len('objects/'):]
   digest=Path(member.name).stem;body=tar.extractfile(member).read();assert hashlib.sha256(body).hexdigest()==digest and manifest['objects'][digest]==shard['path'];dest=root/member.name;dest.parent.mkdir(exist_ok=True);dest.write_bytes(body)
state=dict(objects=manifest['objects'],shards=manifest['shards'],file_blobs={},last_commit=commit)
for n in('source-review-rows.json','progress.json','http-success-cache.jsonl','http-responses.jsonl'):
 b=raw('checkpoint/'+n);(root/n).write_bytes(b);state['file_blobs']['checkpoint/'+n]=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
manifest_raw=raw('raw-cache/manifest.json');state['file_blobs']['raw-cache/manifest.json']=hashlib.sha1(b'blob '+str(len(manifest_raw)).encode()+b'\0'+manifest_raw).hexdigest();(root.parent/'publisher-state.json').write_text(json.dumps(state,indent=2)+'\n');print('Restored immutable output checkpoint',commit,'objects',len(manifest['objects']))
