import sys,json,gzip,hashlib,subprocess,io,concurrent.futures
from pathlib import Path
from zipfile import ZipFile
from PIL import Image
root=Path(__file__).resolve().parents[5];batch=int(sys.argv[1]);commit=sys.argv[2];stage=root/f'picons/radio-world/staging/batch-{batch}-reviewed';base='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'
def sha(b):return hashlib.sha256(b).hexdigest()
def fetch(url,n=None,h=None):
 r=subprocess.run(['curl','--fail','--location','--silent','--show-error','--max-time','120',url],capture_output=True);assert r.returncode==0,(url,r.stderr.decode());b=r.stdout
 if n is not None:assert len(b)==n
 if h is not None:assert sha(b)==h
 return b
def get(d):return fetch(d['url'],d['bytes'],d['sha256'])
raw=fetch(base+commit+f'/picons/radio-world/staging/batch-{batch}-reviewed/countries.proposed.json');index=json.loads(raw);prior=json.loads((stage/'baseline.previous.json').read_bytes());rows=json.loads(gzip.decompress((stage/'selection.json.gz').read_bytes()))['entries'];codes={r['country']for r in rows};old={c['id']:c for c in prior['countries']};tasks=[]
for c in index['countries']:
 if c['id']not in codes:assert c==old[c['id']]
def manifest_tasks(c):
 m=json.loads(get(c['release']));o=json.loads(get(old[c['id']]['release']));out=[]
 for size,styles in m['packages'].items():
  for style,e in styles.items():out.append((c['id'],size,style,e,o['packages'][size][style]))
 return out
with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:
 for part in pool.map(manifest_tasks,[c for c in index['countries']if c['id']in codes]):tasks.extend(part)
def audit(t):
 code,size,style,e,old=t;b=get(e);expected=dict(old['files']);added={r['ref'].replace(':','_')+'.png':r for r in rows if r['country']==code};key=size+'/'+style
 assert not expected.keys()&added.keys()
 expected.update({n:r['variants'][key][0]for n,r in added.items()});assert expected==e['files']
 with ZipFile(io.BytesIO(b))as z:
  assert z.testzip()is None and len(z.infolist())==len(expected)and set(z.namelist())==set(expected)
  for n in z.namelist():
   data=z.read(n);assert sha(data)==expected[n]
   with Image.open(io.BytesIO(data))as im:assert im.size==tuple(map(int,size.split('x')))and im.mode=='RGBA';im.verify()
   if n in added:
    h,num,blob=added[n]['variants'][key];assert len(data)==num and hashlib.sha1(b'blob '+str(num).encode()+b'\0'+data).hexdigest()==blob
  result=dict(url=e['url'],sha256=sha(b),bytes=len(b),members=len(expected),preserved=len(old['files']),new=len(added),CRC='pass',PNG_dimensions_RGBA='pass',new_exact_approved_bytes='pass')
 print('PASS',code,size,style,len(b),flush=True);return result
with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:results=list(pool.map(audit,tasks))
assert len(results)==45 and sum(e['new']for e in results)==45
out=dict(schema=1,status='pass',audited_commit=commit,independent_actual_ZIP_readback=True,independent_runner=True,baseline_references=sum(c['picons']for c in prior['countries']),covered_references=sum(c['picons']for c in index['countries']),remaining_references=35560-sum(c['picons']for c in index['countries']),references_added=len(rows),PNG_added=9*len(rows),archives=results,unchanged_country_descriptors=len(index['countries'])-len(codes))
(stage/'results/independent-postwrite-audit.json').write_text(json.dumps(out,indent=2)+'\n');(stage/'SHA256SUMS.txt').write_text(''.join(e['sha256']+'  '+e['url']+'\n'for e in results));print(json.dumps({k:v for k,v in out.items()if k!='archives'}))
