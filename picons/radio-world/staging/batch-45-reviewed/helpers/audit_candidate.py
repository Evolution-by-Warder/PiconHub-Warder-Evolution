"""Read-only postwrite audit of a staged country batch; exact dynamic inventories.
No PNG/ZIP rendering. Fetches immutable public GitHub URLs only, max4 requests.
"""
import argparse,concurrent.futures,gzip,hashlib,io,json,re,urllib.request,zipfile
from pathlib import Path
REPOSITORY='Evolution-by-Warder/PiconHub-Warder-Evolution';RAW='https://raw.githubusercontent.com/'+REPOSITORY+'/'
VARIANTS={s+'/'+b for s in ('50x30','220x132','400x240')for b in ('transparent','white','black')}
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def require(ok,why):
 if not ok:raise ValueError(why)
def encoded(o):return (json.dumps(o,ensure_ascii=False,indent=2)+'\n').encode()
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--candidate-commit',required=True);a.add_argument('--stage-path',required=True);a.add_argument('--output',type=Path,required=True);a.add_argument('--cache',type=Path);a.add_argument('--baseline-manifest-cache',type=Path);args=a.parse_args()
 require(re.fullmatch('[0-9a-f]{40}',args.candidate_commit),'Candidate must be immutable');require(args.stage_path.startswith('picons/radio-world/staging/')and '..'not in args.stage_path.split('/'),'Unexpected stage')
 out=args.output;out.mkdir(parents=True,exist_ok=True);cache=args.cache or out/'cache';cache.mkdir(parents=True,exist_ok=True)
 def fetch(url,h=None,n=None):
  require(re.match(re.escape(RAW)+'[0-9a-f]{40}/',url)is not None,'URL must pin full immutable repository commit');f=cache/(h or sha(url.encode()))
  if f.exists():b=f.read_bytes()
  else:
   for attempt in range(3):
    try:
     with urllib.request.urlopen(url,timeout=45)as r:
      require(r.url.startswith(RAW),'Unexpected redirect');b=r.read()
     break
    except Exception:
     if attempt==2:raise
   f.write_bytes(b)
  if h:require(sha(b)==h,'SHA mismatch '+url)
  if n is not None:require(len(b)==n,'Size mismatch '+url)
  return b
 def save(n,o):(out/n).write_bytes(encoded(o))
 prefix=RAW+args.candidate_commit+'/'+args.stage_path.rstrip('/')+'/'
 def stage(n):
  b=fetch(prefix+n);(out/n).write_bytes(b);return b
 cfg=json.loads(stage('configuration.json'));proof=json.loads(stage('proof.json'));proposed_raw=stage('countries.proposed.json');proposed=json.loads(proposed_raw);selection_raw=stage(cfg.get('selection_filename','selection.json.gz'))
 require(sha(selection_raw)==cfg['selection_sha256'],'Selection SHA');selection=json.loads(gzip.decompress(selection_raw)if cfg.get('selection_filename','').endswith('.gz')else selection_raw);rows=selection['entries'];N=len(rows)
 require(N==cfg['references']==proof['references']and len({r['ref']for r in rows})==N,'Reference scope');require(proof.get('pngs',proof.get('png_instances'))==N*len(VARIANTS),'PNG instance scope')
 require(all(set(r['variants'])==VARIANTS for r in rows),'Nine variants missing');require(not({r['ref']for r in rows}&set(cfg['held_references'])),'Held addition')
 baseline_resource=cfg['baseline_index'];baseline_raw=fetch(baseline_resource['url'],baseline_resource['sha256'],baseline_resource['bytes']);(out/'baseline.previous.json').write_bytes(baseline_raw);baseline=json.loads(baseline_raw)
 oldby={c['id']:c for c in baseline['countries']};newby={c['id']:c for c in proposed['countries']};require(set(oldby)==set(newby),'Country inventory changed');bycc={}
 for r in rows:bycc.setdefault(r['country'],[]).append(r)
 require(set(bycc)==set(proof['additions'])and all(len(rs)==proof['additions'][cc]for cc,rs in bycc.items()),'Country additions mismatch');require(len(bycc)==proof['country_count'],'Country scope mismatch')
 unchanged=0
 for cc,c in oldby.items():
  n=newby[cc]
  if cc not in bycc:require(c==n,'Unchanged country row mutation '+cc);unchanged+=1
  else:require(n['stations']==c['stations']and n['picons']==c['picons']+len(bycc[cc]),'Country coverage mutation '+cc)
 require(sum(x['picons']for x in newby.values())==sum(x['picons']for x in oldby.values())+N,'Coverage total');require(sum(x['picons']for x in newby.values())==cfg['expected_coverage'],'Expected coverage mismatch')
 payload=proof['payload_commit'];manifest=proof['manifest_commit'];require(all(re.fullmatch('[0-9a-f]{40}',v)for v in (payload,manifest)),'Unpinned output')
 def load_manifest(cc):
  c=newby[cc];r=c['release'];require(r['commit']==manifest and '/'+manifest+'/'in r['url'],'Manifest pin mismatch');b=fetch(r['url'],r['sha256'],r['bytes']);m=json.loads(b);require(m['country']==cc and m['payload_commit']==payload,'Manifest identity');old=None;orr=oldby[cc].get('release')
  if orr:
   cached=args.baseline_manifest_cache/(orr['sha256']+'.json')if args.baseline_manifest_cache else None
   if cached and cached.exists():
    ob=cached.read_bytes();require(sha(ob)==orr['sha256']and len(ob)==orr['bytes'],'Baseline cached manifest mismatch')
   else:ob=fetch(orr['url'],orr['sha256'],orr['bytes'])
   old=json.loads(ob)
  return cc,m,old,dict(country=cc,url=r['url'],sha256=sha(b),bytes=len(b),git_blob=blob(b),old_manifest_sha256=orr['sha256']if orr else None)
 with concurrent.futures.ThreadPoolExecutor(4)as pool:manifests=list(pool.map(load_manifest,bycc))
 tasks=[];preserved=0
 for cc,m,old,evidence in manifests:
  require(set(m['packages'])=={'50x30','220x132','400x240'},'Size inventory')
  for size,styles in m['packages'].items():
   require(set(styles)=={'transparent','white','black'},'Background inventory')
   for style,e in styles.items():
    before=old['packages'][size][style]['files']if old else {};added={r['ref'].replace(':','_')+'.png':r['variants'][size+'/'+style][0]for r in bycc[cc]};require(not(before.keys()&added.keys()),'Old filename overwritten');require(e['files']=={**before,**added},'Union old/new membership mismatch');require('/'+payload+'/'in e['url'],'ZIP pin mismatch');preserved+=len(before);tasks.append((cc,size,style,e))
 require(len(tasks)==proof['packages'],'ZIP scope mismatch');require(preserved==proof['preserved_pngs_in_new_archives'],'Preservation count mismatch')
 print('DYNAMIC_SCOPE_PASS refs',N,'countries',len(bycc),'ZIPs',len(tasks),'newPNG',N*9,'preserved',preserved,flush=True)
 def archive(t):
  cc,size,style,e=t;b=fetch(e['url'],e['sha256'],e['bytes']);members=[]
  with zipfile.ZipFile(io.BytesIO(b))as z:
   require(z.testzip()is None,'ZIP CRC');names=z.namelist();require(len(names)==len(set(names))and set(names)==set(e['files']),'ZIP filenames')
   for n in names:require('/'not in n and n.endswith('.png')and sha(z.read(n))==e['files'][n],'Union member SHA mismatch')
   for row in bycc[cc]:
    name=row['ref'].replace(':','_')+'.png';raw=z.read(name);v=row['variants'][size+'/'+style];require([sha(raw),len(raw),blob(raw)]==v,'New source tuple mismatch');members.append(dict(ref=row['ref'],variant=size+'/'+style,sha256=v[0],bytes=v[1],git_blob=v[2]))
  return dict(country=cc,variant=size+'/'+style,url=e['url'],sha256=sha(b),bytes=len(b),git_blob=blob(b),union_png_members=len(e['files']),source_members=members)
 results=[]
 with concurrent.futures.ThreadPoolExecutor(4)as pool:
  for r in pool.map(archive,tasks):
   results.append(r);save('zip-progress.json',dict(status='running',completed=len(results),target=len(tasks),entries=results));print('ZIP',len(results),'/',len(tasks),r['country'],r['variant'],'PASS',flush=True)
 require(sum(len(r['source_members'])for r in results)==N*len(VARIANTS),'Source instance membership incomplete')
 counts=dict(countries=len(newby),available=sum(c['status']!='unavailable'for c in newby.values()),complete=sum(c['status']=='complete'for c in newby.values()),partial=sum(c['status']=='partial'for c in newby.values()),unavailable=sum(c['status']=='unavailable'for c in newby.values()),picons=sum(c['picons']for c in newby.values()),remaining=sum(c['stations']-c['picons']for c in newby.values()))
 report=dict(schema=1,status='pass',audit_kind='Independent read-only actual immutable ZIP bytes and source membership',candidate_commit=args.candidate_commit,stage_path=args.stage_path,payload_commit=payload,manifest_commit=manifest,baseline_index_sha256=sha(baseline_raw),proposed_index_sha256=sha(proposed_raw),proposed_index_git_blob=blob(proposed_raw),references=N,png_instances=N*len(VARIANTS),unique_source_pngs=len({v[0]for r in rows for v in r['variants'].values()}),updated_countries=len(bycc),unchanged_country_rows=unchanged,ZIPs=len(results),ZIP_bytes=sum(r['bytes']for r in results),actual_union_PNGs_verified=sum(r['union_png_members']for r in results),old_PNG_entries_preserved=preserved,all_ZIP_SHA_bytes_CRC_and_member_SHA_checked=True,all_source_member_SHA_bytes_Gitblob_checked=True,proposed_counts=counts,manifests=[m[3]for m in manifests],zip_entries=results,no_PNG_or_ZIP_generated=True,no_remote_writes=True)
 raw=encoded(report);(out/'independent-postwrite-audit.json').write_bytes(raw);z=gzip.compress(raw,mtime=0);(out/'independent-postwrite-audit.json.gz').write_bytes(z);save('report-hashes.json',dict(raw_bytes=len(raw),raw_sha256=sha(raw),gzip_bytes=len(z),gzip_sha256=sha(z)));print('ALL_DYNAMIC_ZIP_AND_SOURCE_TUPLES_PASS',flush=True)
if __name__=='__main__':main()
