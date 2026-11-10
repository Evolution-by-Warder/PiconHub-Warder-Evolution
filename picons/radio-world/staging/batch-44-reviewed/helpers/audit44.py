"""Independent immutable read-only postwrite ZIP audit; no PNG/ZIP generation."""
import json,gzip,hashlib,urllib.request,concurrent.futures,zipfile,io,time
from pathlib import Path
P=Path(__file__).parent;CACHE=P/'cache';CACHE.mkdir(exist_ok=True);REPO='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/';H='fc6dc2a0b3c31847a02576f0e082c61043127f16';PAYLOAD='508e018e83e510c2c717c90480e4aaa4358c1609';MANIFEST='2ebc036ce3455b56fbb0e09a3b83959d84ec964b';STAGE='picons/radio-world/staging/batch-44-reviewed/'
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def fetch(url,expected_sha=None,expected_bytes=None):
 f=CACHE/(expected_sha if expected_sha else sha(url.encode()))
 if f.exists():b=f.read_bytes()
 else:
  err=None
  for attempt in range(3):
   try:
    with urllib.request.urlopen(url,timeout=45)as r:
     assert r.url.startswith('https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/');b=r.read()
    break
   except Exception as e:
    err=e
    if attempt==2:raise
  f.write_bytes(b)
 if expected_sha:assert sha(b)==expected_sha,('SHA',url)
 if expected_bytes is not None:assert len(b)==expected_bytes,('bytes',url)
 return b
c=json.load(open(P/'countries.proposed.json'));proof=json.load(open(P/'proof.json'));cfg=json.load(open(P/'configuration.json'));selection=(P/'selection.json.gz').read_bytes();assert sha(selection)==cfg['selection_sha256'];rows=json.loads(gzip.decompress(selection))['entries'];assert len(rows)==80 and len({r['ref']for r in rows})==80 and len({v[0]for r in rows for v in r['variants'].values()})==711
bycode={}
for r in rows:bycode.setdefault(r['country'],[]).append(r)
assert set(bycode)==set(proof['additions'])and len(bycode)==23
changed=[r for r in c['countries']if r['id']in bycode];assert len(changed)==23
assert len(c['countries'])==219 and sum(x['picons']for x in c['countries'])==3090 and sum(x['status']!='unavailable'for x in c['countries'])==131 and sum(x['status']=='complete'for x in c['countries'])==12
print('SOURCE80_COUNTRY23_UNIQUE711_INDEX3090_PASS',flush=True)
def manifest(row):
 r=row['release'];assert r['commit']==MANIFEST and '/'+MANIFEST+'/'in r['url'];b=fetch(r['url'],r['sha256'],r['bytes']);m=json.loads(b);assert m['country']==row['id']and m['payload_commit']==PAYLOAD;return row['id'],m,dict(country=row['id'],url=r['url'],sha256=sha(b),bytes=len(b),git_blob=blob(b))
with concurrent.futures.ThreadPoolExecutor(4)as pool:ms=list(pool.map(manifest,changed))
tasks=[]
for cc,m,ev in ms:
 assert set(m['packages'])=={'50x30','220x132','400x240'}
 for size,styles in m['packages'].items():
  assert set(styles)=={'black','white','transparent'}
  for style,e in styles.items():
   assert '/'+PAYLOAD+'/'in e['url'];tasks.append((cc,size,style,e))
assert len(tasks)==207
pathproof=json.load(open(P/'zip-path-proof.json'));paths={x['path']:x for x in pathproof['entries']};assert len(paths)==207
for cc,size,style,e in tasks:
 path=e['url'].split('/'+PAYLOAD+'/',1)[1];r=paths[path];assert r['new_sha256']==e['sha256']and r['new_bytes']==e['bytes']
print('MANIFEST23_ALL207PINNED_METADATA_PASS bytes',sum(t[3]['bytes']for t in tasks),flush=True)
def archive(t):
 cc,size,style,e=t;b=fetch(e['url'],e['sha256'],e['bytes']);membership=[]
 with zipfile.ZipFile(io.BytesIO(b))as z:
  assert z.testzip()is None;names=z.namelist();assert len(names)==len(set(names))and set(names)==set(e['files'])
  for n in names:assert '/'not in n and n.endswith('.png')and sha(z.read(n))==e['files'][n],('memberhash',cc,size,style,n)
  for row in bycode[cc]:
   name=row['ref'].replace(':','_')+'.png';raw=z.read(name);v=row['variants'][size+'/'+style];assert [sha(raw),len(raw),blob(raw)]==v,('new_source_tuple',row['ref'],size,style);membership.append(dict(ref=row['ref'],variant=size+'/'+style,sha256=v[0],bytes=v[1],git_blob=v[2]))
 return dict(country=cc,variant=size+'/'+style,url=e['url'],sha256=sha(b),bytes=len(b),git_blob=blob(b),union_png_members=len(e['files']),source_members=membership)
results=[]
with concurrent.futures.ThreadPoolExecutor(4)as pool:
 for r in pool.map(archive,tasks):
  results.append(r)
  (P/'zip-progress.json').write_text(json.dumps(dict(status='running',completed=len(results),target=207,entries=results),indent=2)+'\n')
  print('ZIP',len(results),'/207',r['country'],r['variant'],'PASS',flush=True)
assert sum(len(r['source_members'])for r in results)==720
out=dict(schema=1,status='pass',audit_kind='independent read-only actual immutable ZIP bytes and PNG source membership',reviewed_pr_head=H,payload_commit=PAYLOAD,manifest_commit=MANIFEST,countries=23,new_references=80,source_png_instances=720,unique_source_pngs=711,new_zip_files=207,new_zip_bytes=sum(r['bytes']for r in results),all_zip_sha256_bytes_crc_and_manifest_member_sha256=True,all_source_png_sha256_bytes_gitblob_membership=True,proposed_index=dict(countries=219,available=131,complete=12,partial=119,unavailable=88,picons=3090,remaining=32470,sha256=sha((P/'countries.proposed.json').read_bytes()),git_blob=blob((P/'countries.proposed.json').read_bytes())),manifests=[x[2]for x in ms],zip_entries=results,no_PNG_or_ZIP_generated=True,no_remote_writes=True)
(P/'independent-postwrite-zip-audit44.json').write_text(json.dumps(out,indent=2)+'\n');print('ALL207ACTUAL_BYTES_AND720SOURCE_TUPLES_PASS',flush=True)
