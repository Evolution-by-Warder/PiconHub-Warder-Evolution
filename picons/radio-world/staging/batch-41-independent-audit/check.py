from pathlib import Path
import subprocess,json,urllib.request,concurrent.futures,hashlib,re
R='Evolution-by-Warder/PiconHub-Warder-Evolution';BASE='https://raw.githubusercontent.com/'+R+'/';OUT=Path('continuation/independent41-audit');C41='673062395da2f49cf2c739a16c605eedc9553480';C67='0359575fa65c19c2b2172075ebe4e9c0e37bf0d5';MAIN='8180aa0df6e185efad120338bc53ca04bc5e492a';INDEX='picons/radio-world/catalog/countries.json';sha=lambda b:hashlib.sha256(b).hexdigest()
def git(c,p):return subprocess.check_output(['git','-C','piconhub','show',c+':'+p])
def get(url):
 with urllib.request.urlopen(url,timeout=50) as response:return response.read()
indices={};result={'schema':1,'github_writes':False,'zip_downloads':0,'checks':{}}
for label,c in [('41',C41),('67',C67),('production',MAIN)]:
 b=git(c,INDEX);(OUT/(label+'-index.json')).write_bytes(b);x=json.loads(b);indices[label]=x
 public=get(BASE+c+'/'+INDEX);assert public==b
 rows=x['countries'];v=[r for r in rows if r['release']];result['checks'][label]={'commit':c,'public_index_equals_git':True,'index_sha256':sha(b),'countries':len(rows),'available':len(v),'covered':sum(r['picons'] for r in rows),'total':sum(r['stations'] for r in rows)}
 assert len({r['id'] for r in rows})==219 and sum(r['stations'] for r in rows)==35560
 assert (len(v),sum(r['picons'] for r in rows))==({'41':(109,2429),'67':(81,1303),'production':(33,1084)}[label])
all_entries={}
for x in indices.values():
 for r in x['countries']:
  if not r['release']:continue
  e=r['release'];assert re.fullmatch('[a-f0-9]{40}',e['commit']);assert e['url']==BASE+e['commit']+'/picons/'+r['collection']+'/catalog/release.json';all_entries[e['url']]=e
def fetch(t):
 u,e=t;b=get(u);assert len(b)==e['bytes'] and sha(b)==e['sha256'];(OUT/'manifests').mkdir(exist_ok=True);(OUT/'manifests'/e['sha256']).write_bytes(b);return u,json.loads(b)
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:manifests=dict(pool.map(fetch,all_entries.items()))
for label in ['41','67']:
 old={r['id']:r for r in indices['production']['countries']};new={r['id']:r for r in indices[label]['countries']};protected=0;seen=set();entries=0;packageurls=set();manifests_seen=set()
 for c,r in old.items():
  n=new[c];assert r['collection']==n['collection'] and r['stations']==n['stations'] and n['picons']>=r['picons']
  if not r['release']:continue
  a=manifests[r['release']['url']];b=manifests[n['release']['url']]
  identity=(r['release']['url'],n['release']['url'])
  if identity in seen:continue
  seen.add(identity)
  for size in ['50x30','220x132','400x240']:
   for style in ['transparent','white','black']:
    before=a['packages'][size][style]['files'];after=b['packages'][size][style]['files'];assert before.items()<=after.items();protected+=len(before)
 for c,n in new.items():
  if not n['release'] or n['release']['url'] in manifests_seen:continue
  manifests_seen.add(n['release']['url']);m=manifests[n['release']['url']];assert m['collection']==n['collection']
  assert set(m['packages'])=={'50x30','220x132','400x240'}
  for size,styles in m['packages'].items():
   assert set(styles)=={'transparent','white','black'}
   for style,e in styles.items():
    entries+=len(e['files'])
    for part in e.get('parts',[e]):
     assert re.match(re.escape(BASE)+'[a-f0-9]{40}/',part['url']);assert len(part['sha256'])==64 and part['bytes']>0;packageurls.add(part['url'])
 assert protected==10332
 result['checks'][label].update(protected_png_variant_entries=protected,png_variant_entries=entries,immutable_package_urls=len(packageurls),canonical_manifest_urls=len(manifests_seen))
 if label=='41':assert entries==22437 and len(packageurls)==972
for name in ['downloader-proof.json','production-preservation-proof.json','png-admission-proof.json','proof.json']:
 path='picons/radio-world/staging/batch-41-reviewed/'+name;b=git(C41,path);assert get(BASE+C41+'/'+path)==b;(OUT/name).write_bytes(b)
 result.setdefault('public_proofs',[]).append({'path':path,'sha256':sha(b),'public_equals_git':True})
staged=git(C41,'picons/radio-world/staging/batch-41-reviewed/countries.proposed.json');result['stage_index_sha256']=sha(staged);d=json.loads((OUT/'downloader-proof.json').read_bytes());assert d['index_sha256']==sha(staged);result['checks']['41']['downloader_stage_index_sha_matches']=True
staged=json.loads(staged);a=indices['41'];assert staged['countries'][0]['release']['sha256']==a['countries'][0]['release']['sha256']
for s,t in zip(staged['countries'],a['countries']):
 assert all(s[k]==t[k] for k in ['id','name','collection','stations','picons','status'])
 if s['release']:assert s['release']['sha256']==t['release']['sha256'] and s['release']['bytes']==t['release']['bytes']
result['canonical_repin_preserves_all_manifest_bytes']=True;result['verified_public_manifest_urls']=len(manifests);(OUT/'independent-proof.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
