"""Read-only recovery of exact pre-reviewed54 frozen source identities; no rendering."""
import json,hashlib,io,tarfile,urllib.request,concurrent.futures
from pathlib import Path
from urllib.parse import urlsplit
from PIL import Image
P=Path(__file__).parent;RES=P/'resource-cache';RES.mkdir(exist_ok=True);(P/'originals').mkdir(exist_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def save(n,o):(P/n).write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
receipt=json.load(open(P/'receipt96.json'));old=json.load(open(P/'snapshot2322.json'))['entries'];new=json.load(open(P/'final890c.json'))['entries'];manifest=json.load(open(P/'cache-manifest.json'));shards={s['path']:s for s in manifest['shards']};template=json.load(open(P/'plan113.json'));ids=receipt['final_review']['approve_indices'];assert len(ids)==len(set(ids))==54 and not(set(ids)&{e['index']for e in receipt['final_review']['holds']})
observations=[];holds=[];resources=template['resources']
for i in ids:
 try:
  a=old[i];z=new[i];assert a['index']==z['index']==i and a['row']==z['row'];r=a['row'];assert a['status']==z['status']=='logo-frozen';assert a['source']['sha256']==z['source']['sha256']and a['api_evidence']['sha256']==z['api_evidence']['sha256'];api=a['api_station'];assert all(api[k]==z['api_station'][k]for k in ['id','title','country','streamURL','streamName','metaLogo']);u=urlsplit(r['station']['url']);v=urlsplit(api['streamURL']);assert u.hostname==v.hostname=='stream.zeno.fm'and u.path.strip('/')==v.path.strip('/')==api['streamName']==r['zeno_mount'];assert api['country']==r['station']['group'];s=a['source'];logo=urlsplit(s['url']);end=urlsplit(s['final_url']);assert api['metaLogo']==s['url']and logo.hostname=='proxy.zeno.fm'and logo.path.rstrip('/')=='/content/stations/'+api['id']+'/image';assert end.hostname=='zenoimages.s3.us-west-001.backblazeb2.com'and end.path=='/'+api['id']+'/images/logo';observations.append(dict(index=i,row=r,primary_fields={k:api[k]for k in ['id','title','country','streamURL','streamName','metaLogo']},api_sha256=a['api_evidence']['sha256'],api_url=a['api_evidence']['url'],source_sha256=s['sha256'],source_url=s['url'],source_final_url=s['final_url'],source_bytes=s['bytes'],source_dimensions=s['dimensions'],source_format=s['format'],final_snapshot_exact_match=True))
 except Exception as e:holds.append(dict(index=i,decision='hold',reason='Frozen receipt/final country/source/API/ID reconciliation failed: '+type(e).__name__+': '+str(e)))
needed={}
for r in resources.values():needed[r['sha256']]=dict(r,url='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'+r['commit']+'/'+r['path'])
for o in observations:
 for h in [o['api_sha256'],o['source_sha256']]:
  s=shards[manifest['objects'][h]];needed[s['sha256']]=dict(s,url='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/2322e554ea89b024db8c184ed193e5be40c8a996/picons/radio-world/staging/zeno-primary-20261107/'+s['path'])
def fetch(r):
 p=RES/(r['sha256']+'.blob')
 if not p.exists():
  with urllib.request.urlopen(r['url'],timeout=90)as s:b=s.read()
  p.write_bytes(b)
 b=p.read_bytes();assert len(b)==r['bytes']and sha(b)==r['sha256']and blob(b)==r['git_blob'];return r['sha256']
with concurrent.futures.ThreadPoolExecutor(4)as pool:
 for h in pool.map(fetch,needed.values()):print('Pinned input verified',h,flush=True)
for o in observations:
 for h in [o['api_sha256'],o['source_sha256']]:
  s=shards[manifest['objects'][h]]
  with tarfile.open(RES/(s['sha256']+'.blob'),'r:gz')as tar:
   member=tar.getmember('objects/'+h+'.body');assert member.isfile();b=tar.extractfile(member).read();assert sha(b)==h
  if h==o['api_sha256']:
   api=json.loads(b);assert all(api[k]==v for k,v in o['primary_fields'].items())
  else:
   assert len(b)==o['source_bytes'];im=Image.open(io.BytesIO(b));im.verify();im=Image.open(io.BytesIO(b));assert list(im.size)==o['source_dimensions'];(P/'originals'/(h+'.img')).write_bytes(b);o['source_git_blob']=blob(b)
# Exact authoritative country membership; never infer a country from a HDF-only row.
import gzip
world=json.loads(gzip.decompress((RES/(resources['catalogue']['sha256']+'.blob')).read_bytes()));by_ref={}
for r in world:by_ref.setdefault(r['reference'],[]).append(r)
for o in observations:
 row=o['row'];matches=[x for x in by_ref[row['ref']]if all(x[k]==row['station'][k]for k in ['name','url','group'])]
 assert len(matches)==1 and 'HDF'not in matches[0]['group']
 o['exact_catalogue_membership']=dict(reference=row['ref'],name=matches[0]['name'],url=matches[0]['url'],group=matches[0]['group'],matches=1,HDF=False)
proof=dict(schema=1,status='inputs-reconciled-no-render-performed',requested=54,reconciled=len(observations),held=len(holds),receipt=dict(commit='9376e0665b74df3f3bece55c924df48ce2ec529e',path='picons/radio-world/staging/batch-43-44-zeno-source/consumer113/recovered-new96-review-receipts.json',git_blob='2a8d58e477dc376e8ae095ba7c5c08a20f42f024',sha256=sha((P/'receipt96.json').read_bytes())),snapshot2322_sha256=sha((P/'snapshot2322.json').read_bytes()),final890c_sha256=sha((P/'final890c.json').read_bytes()),immutable_resources=resources,read_only_existing_GitHub_shards=True,live_Zeno_requests=0,all_origin_SHA_bytes_Gitblob_decode_verified=True,exact_country_catalogue_membership_verified=len(observations),all_HDF_outside=True,published_prior_PNG_tuples_found=False,old54branch_head='b99fe072f36d03871cc9c0e7546a5fc9294846a0',old54_workflow_runs=0,country_ci_ready=False,production_ready=False,entries=observations,holds=holds)
save('input-recovery-proof.json',proof);save('eligible-source-observations.json',{'entries':observations});print('INPUT_RECOVERY',len(observations),'holds',len(holds),flush=True)
