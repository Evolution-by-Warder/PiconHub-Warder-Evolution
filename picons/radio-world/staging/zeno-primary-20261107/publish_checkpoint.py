#!/usr/bin/env python3
"""Write source evidence only to one explicit output ref using the job-scoped GitHub API token."""
import base64,gzip,hashlib,io,json,os,re,sys,tarfile,time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
REPO='Evolution-by-Warder/PiconHub-Warder-Evolution';SOURCE='work/radio-zeno1519-source-20261107';OUTPUT='work/radio-zeno1519-frozen-20261107';STAGE='picons/radio-world/staging/zeno-primary-20261107';API='https://api.github.com/repos/'+REPO
ROOT=Path(sys.argv[1]).resolve();PHASE=sys.argv[2];TOKEN=os.environ['GH_TOKEN'];assert os.environ['GITHUB_REPOSITORY']==REPO and os.environ['GITHUB_REF']=='refs/heads/'+SOURCE

def api(method,path,data=None,missing=False):
 body=json.dumps(data,separators=(',',':')).encode()if data is not None else None
 for attempt in range(3):
  try:
   with urlopen(Request(API+path,data=body,method=method,headers={'Authorization':'Bearer '+TOKEN,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'warder-source-checkpoint'}),timeout=60)as r:return json.load(r)
  except HTTPError as e:
   if e.code==404 and missing:return None
   if e.code not in(429,500,502,503,504)or attempt==2:raise RuntimeError('checkpoint API HTTP '+str(e.code)+' '+path)from None
   time.sleep(float(e.headers.get('Retry-After',2**(attempt+1))))

def digest(b):return hashlib.sha256(b).hexdigest()
def blob(b):return api('POST','/git/blobs',{'content':base64.b64encode(b).decode(),'encoding':'base64'})['sha']
state_path=ROOT.parent/'publisher-state.json';state=json.loads(state_path.read_text())if state_path.exists()else dict(objects={},shards=[],file_blobs={})
ref=api('GET','/git/ref/heads/'+OUTPUT,missing=True);parent=ref['object']['sha']if ref else os.environ['GITHUB_SHA'];tree=api('GET','/git/commits/'+parent)['tree']['sha'];entries=[]
new=[p for p in sorted((ROOT/'objects').glob('*.body'))if p.stem not in state['objects']]
groups=[];group=[];size=0
for p in new:
 n=p.stat().st_size
 if group and(len(group)>=200 or size+n>16*1024*1024):groups.append(group);group=[];size=0
 group.append(p);size+=n
if group:groups.append(group)
for group in groups:
 buf=io.BytesIO()
 with gzip.GzipFile(fileobj=buf,mode='wb',mtime=0)as gz:
  with tarfile.open(fileobj=gz,mode='w')as tar:
   for p in group:
    b=p.read_bytes();assert re.fullmatch('[0-9a-f]{64}',p.stem)and digest(b)==p.stem
    item=tarfile.TarInfo('objects/'+p.name);item.size=len(b);item.mtime=0;item.mode=0o644;tar.addfile(item,io.BytesIO(b))
 raw=buf.getvalue();name=f'raw-cache/shard-{len(state["shards"]):05}.tar.gz';gsha=blob(raw);entries.append(dict(path=STAGE+'/'+name,mode='100644',type='blob',sha=gsha));state['shards'].append(dict(path=name,bytes=len(raw),sha256=digest(raw),git_blob=gsha,objects=[p.stem for p in group]))
 for p in group:state['objects'][p.stem]=name
manifest=dict(schema=1,scope='source-only-not-graphic-approved',objects=state['objects'],shards=state['shards']);raws={'raw-cache/manifest.json':(json.dumps(manifest,indent=2)+'\n').encode()}
for n in('source-review-rows.json','progress.json','http-success-cache.jsonl','http-responses.jsonl'):
 p=ROOT/n
 if p.exists()or n=='http-responses.jsonl':raws['checkpoint/'+n]=p.read_bytes()if p.exists()else b''
for name,b in raws.items():
 gitsha=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
 if state['file_blobs'].get(name)==gitsha:continue
 assert blob(b)==gitsha;entries.append(dict(path=STAGE+'/'+name,mode='100644',type='blob',sha=gitsha));state['file_blobs'][name]=gitsha
if entries:
 tree=api('POST','/git/trees',dict(base_tree=tree,tree=entries))['sha'];commit=api('POST','/git/commits',dict(message='Save Zeno primary source checkpoint: '+PHASE+' [skip ci]',tree=tree,parents=[parent]))['sha']
 if ref:api('PATCH','/git/refs/heads/'+OUTPUT,dict(sha=commit,force=False))
 else:api('POST','/git/refs',dict(ref='refs/heads/'+OUTPUT,sha=commit))
 state['last_commit']=commit;tmp=state_path.with_suffix('.tmp');tmp.write_text(json.dumps(state,indent=2)+'\n');tmp.replace(state_path);print(json.dumps(dict(checkpoint_commit=commit,output_branch=OUTPUT,raw_objects=len(state['objects']),new_objects=len(new),phase=PHASE)),flush=True)
else:print('No changed source evidence checkpoint',flush=True)
