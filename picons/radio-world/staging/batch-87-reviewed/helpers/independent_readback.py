"""One final independent public-URL audit; cache downloaded bytes for real downloader replay."""
import sys,json,gzip,hashlib,io,concurrent.futures,urllib.request
from pathlib import Path
from zipfile import ZipFile
from PIL import Image
stage=Path('picons/radio-world/staging/batch-87-reviewed');checkpoint=sys.argv[1];cache=Path(sys.argv[2]);cache.mkdir(parents=True,exist_ok=True)
BASE='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'
sha=lambda b:hashlib.sha256(b).hexdigest()
def fetch(url,n=None,h=None):
 assert url.startswith(BASE)
 path=cache/sha(url.encode())
 if path.exists():b=path.read_bytes()
 else:
  with urllib.request.urlopen(url,timeout=60)as response:b=response.read((n+1)if n is not None else 10*1024*1024)
  path.write_bytes(b)
 if n is not None:assert len(b)==n
 if h is not None:assert sha(b)==h
 return b
def get(e):return fetch(e['url'],e['bytes'],e['sha256'])
index=json.loads(fetch(BASE+checkpoint+'/picons/radio-world/staging/batch-87-reviewed/countries.proposed.json'));prior=json.loads((stage/'baseline.previous.json').read_bytes());rows=json.loads(gzip.decompress((stage/'selection.json.gz').read_bytes()))['entries'];assert len(rows)==3
old={c['id']:c for c in prior['countries']};new={c['id']:c for c in index['countries']};assert sum(c['picons']for c in prior['countries'])==3586 and sum(c['picons']for c in index['countries'])==3589
for code,c in new.items():
 if code!='FR':assert c==old[code]
manifest=json.loads(get(new['FR']['release']));before=json.loads(get(old['FR']['release']));alpha={}
for r in json.loads((stage/'source-inputs/recovery-spec.json').read_bytes())['stations']:
 for k,v in r['variants'].items():alpha[v[0]]=r['alpha_extrema'][k]
tasks=[]
for size in ['50x30','220x132','400x240']:
 for sty in ['transparent','white','black']:
  e=manifest['packages'][size][sty];oldfiles=before['packages'][size][sty]['files'];added={r['ref'].replace(':','_')+'.png':r for r in rows};assert not oldfiles.keys()&added.keys();expected=dict(oldfiles);expected.update({n:r['variants'][size+'/'+sty][0]for n,r in added.items()});assert e['files']==expected
  union={}
  for i,part in enumerate(e.get('parts')or[e],1):
   expected_url=BASE+manifest['payload_commit']+'/picons/IPTV-FR/packages/iptv-fr-'+sty+'-'+size+(('-part%02d'%i)if e.get('parts')else'')+'.zip';assert part['url']==expected_url and part['bytes']<=32*1024*1024
   assert not union.keys()&part['files'].keys();union.update(part['files']);tasks.append((size,sty,part,added,oldfiles))
  assert union==expected
assert 9<=len(tasks)<=27

def audit(t):
 size,sty,e,added,oldfiles=t;b=get(e);new_count=0
 with ZipFile(io.BytesIO(b))as z:
  assert z.testzip()is None and len(z.infolist())==len(e['files'])and set(z.namelist())==set(e['files'])
  for n in z.namelist():
   data=z.read(n);assert sha(data)==e['files'][n]
   with Image.open(io.BytesIO(data))as im:
    assert im.mode=='RGBA'and im.size==tuple(map(int,size.split('x')))
    if n in added:assert list(im.getchannel('A').getextrema())==alpha[sha(data)]
   with Image.open(io.BytesIO(data))as verified:verified.verify()
   if n in added:
    h,length,blob=added[n]['variants'][size+'/'+sty];assert sha(data)==h and len(data)==length and hashlib.sha1(b'blob '+str(length).encode()+b'\0'+data).hexdigest()==blob;new_count+=1
   else:assert sha(data)==oldfiles[n]
 return dict(url=e['url'],bytes=len(b),sha256=sha(b),members=len(e['files']),new=new_count,preserved=len(e['files'])-new_count,CRC='pass',PNG_dimensions_RGBA='pass',alpha_matches_saved_approved_source='pass',new_exact_approved_bytes='pass')
with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:results=list(pool.map(audit,tasks))
assert sum(e['new']for e in results)==27
out=dict(schema=1,status='pass',audited_commit=checkpoint,independent_runner=True,independent_actual_ZIP_readback=True,baseline_references=3586,covered_references=3589,remaining_references=31971,references_added=3,PNG_added=27,existing_PNGs_rerendered=0,archives=results,part_limit_bytes=33554432,unchanged_country_descriptors=218)
(stage/'results').mkdir(exist_ok=True);(stage/'results/independent-postwrite-audit.json').write_text(json.dumps(out,indent=2)+'\n');(stage/'SHA256SUMS.txt').write_text(''.join(e['sha256']+'  '+e['url']+'\n'for e in results));print('PASS:',len(results),'public GitHub ZIPs,27 exact saved PNGs,old members and alpha preserved',flush=True)
