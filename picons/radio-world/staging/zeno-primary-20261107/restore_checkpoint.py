"""Restore the exact immutable output-branch checkpoint; no station-source refetch."""
import hashlib,io,json,os,sys,tarfile,time,http.client
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen
REPO='Evolution-by-Warder/PiconHub-Warder-Evolution';BRANCH='work/radio-zeno1519-frozen-20261107';STAGE='picons/radio-world/staging/zeno-primary-20261107';root=Path(sys.argv[1]);root.mkdir(parents=True,exist_ok=True)
def read(request,missing=False):
 for attempt in range(3):
  try:
   with urlopen(request,timeout=90)as r:return r.read()
  except HTTPError as e:
   if missing and e.code==404:return None
   if e.code not in(408,425,429,500,502,503,504)or attempt==2:raise
   time.sleep(float(e.headers.get('Retry-After',2**(attempt+1))))
  except(URLError,TimeoutError,OSError,http.client.HTTPException):
   if attempt==2:raise
   time.sleep(2**(attempt+1))
b=read(Request('https://api.github.com/repos/'+REPO+'/git/ref/heads/'+BRANCH,headers={'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json'}),missing=True)
if b is None:print('No previous output checkpoint; using complete successful seed');sys.exit(0)
commit=json.loads(b)['object']['sha']
base='https://raw.githubusercontent.com/'+REPO+'/'+commit+'/'+STAGE+'/'
def raw(name):
 return read(base+name)
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
