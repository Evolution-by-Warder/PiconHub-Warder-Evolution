"""Restore approved Radio PNGs with exact hashes; no production publication.

Usage: python restore_radio_checkpoint.py WORKSPACE
The workspace contains piconhub/, restored/ and regenerated/. Output checkpoint/.
"""
from pathlib import Path
from collections import defaultdict, Counter
from urllib.parse import urlsplit, urlunsplit
from PIL import Image
import csv, gzip, hashlib, io, json, os, re, shutil, sys, zipfile

ROOT=Path(sys.argv[1]).resolve(); OUT=ROOT/'checkpoint'; OUT.mkdir(exist_ok=True)
SHA=lambda b:hashlib.sha256(b).hexdigest()
SIZES=('50x30','220x132','400x240'); STYLES=('transparent','white','black')
VARIANTS={f'{s}/{t}' for s in SIZES for t in STYLES}
records={}; checks=Counter(); validated=set(); conflicts=[]; batch_reports=[]; metadata={}

def write_json(path,data):
 path.parent.mkdir(parents=True,exist_ok=True)
 tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');tmp.replace(path)

def add(country,ref,variant,raw,origin,pin=None):
 assert re.fullmatch(r'(?:[0-9A-Fa-f]+:){9}[0-9A-Fa-f]+',ref),ref
 assert variant in VARIANTS
 digest=SHA(raw)
 if pin: assert digest==pin,(origin,ref,variant)
 if digest not in validated:
  with Image.open(io.BytesIO(raw)) as image:
   assert image.format=='PNG' and image.mode in ('RGBA','RGB','P') and image.size==tuple(map(int,variant.split('/')[0].split('x'))),(origin,ref,variant,image.mode,image.size)
   image.verify()
  validated.add(digest)
 row=records.setdefault(ref,dict(country=country,reference=ref,origins=[],renders={}))
 if origin not in row['origins']:row['origins'].append(origin)
 previous=row['renders'].get(variant)
 if previous and previous['sha256']!=digest:
  conflicts.append(dict(reference=ref,variant=variant,retained=previous['sha256'],candidate=digest,origin=origin));return
 blob=OUT/'assets'/f'{digest}.png'
 if not blob.exists():blob.parent.mkdir(exist_ok=True);blob.write_bytes(raw)
 row['renders'][variant]=dict(sha256=digest,bytes=len(raw),path=str(blob.relative_to(OUT)))
 checks[origin]+=1

world_path=ROOT/'piconhub/picons/IPTV-SK-CZ/catalog/global/world-radio.receiver.json.gz'
world=json.load(gzip.open(world_path)); byref={s['reference']:s for s in world}
assert len(byref)==len(world)
canonical=json.load(gzip.open(ROOT/'piconhub/picons/IPTV-SK-CZ/catalog/global/world-radio.json.gz'))
country_by_group={s['group']:s.get('countrycode') or 'WORLD' for s in canonical}
for s in world:metadata[s['reference']]=dict(s,country=country_by_group.get(s['group'],'WORLD'))

# Every production archive is frozen and validated against its published per-file manifest.
for release in sorted((ROOT/'piconhub/picons').glob('IPTV-*/catalog/release.json')):
 country=release.parents[1].name[5:];d=json.loads(release.read_text())
 for size,styles in d['packages'].items():
  for style,entry in styles.items():
   p=release.parents[1]/'packages'/entry['url'].rsplit('/',1)[-1];raw=p.read_bytes()
   assert len(raw)==entry['bytes'] and SHA(raw)==entry['sha256'],str(p)
   with zipfile.ZipFile(io.BytesIO(raw)) as z:
    assert set(z.namelist())==set(entry['files']) and len(z.namelist())==len(set(z.namelist()))
    for name,pin in entry['files'].items():add(country,name[:-4].replace('_',':'),f'{size}/{style}',z.read(name),'production/'+country,pin)

production_refs=set(records)
# Merge complete saved batches (including CRC-verified members recovered from the truncated batch01 archive).
for folder in sorted((ROOT/'restored').glob('Warder_Radio_*')):
 if not folder.is_dir():continue
 manifest=folder/'reprodukcia/render-manifest.json';plan_path=folder/'reprodukcia/source-plan.json'
 if not manifest.exists():continue
 d=json.loads(manifest.read_text());plan=json.loads(plan_path.read_text());meta={s['reference']:s for s in plan['stations']}
 for row in d['stations']:
  m=meta[row['reference']];metadata[row['reference']]=dict(m)
  for variant,item in row['renders'].items():
   raw=(folder/item['path']).read_bytes();assert len(raw)==item['bytes']
   add(m['country'],row['reference'],variant,raw,folder.name,item['sha256'])
 batch_reports.append(dict(batch=folder.name,references=len(d['stations']),pngs=9*len(d['stations']),verified=True))

# Earlier small broadcaster batches were reproduced offline with their original scripts and hashes.
for folder in sorted((ROOT/'regenerated').glob('*')):
 meta_root=ROOT/'restored/migration'/folder.name
 d=json.loads((meta_root/'render-manifest.json').read_text());plan=json.loads((meta_root/'source-plan.json').read_text());meta={s['reference']:s for s in plan['stations']}
 for row in d['stations']:
  m=meta[row['reference']];metadata[row['reference']]=dict(m)
  for variant,item in row['renders'].items():add(m['country'],row['reference'],variant,(folder/item['path']).read_bytes(),folder.name,item['sha256'])
 batch_reports.append(dict(batch=folder.name,references=len(d['stations']),pngs=9*len(d['stations']),verified=True,reproduced=True))

folder=ROOT/'restored/migration/radio-review-next-20261105'
if folder.exists():
 d=json.loads((folder/'manifest.json').read_text())
 for row in d['stations']:
  metadata[row['reference']]=dict(row,url=row['stream_url'])
  for variant,item in row['renders'].items():add(row['country'],row['reference'],variant,(folder/item['path']).read_bytes(),folder.name,item['sha256'])

before_alias=set(records)
# Reuse only an exactly equal stream endpoint. Preserve query parameters and paths.
def endpoint(url):
 p=urlsplit(url);return urlunsplit((p.scheme.lower(),p.netloc.lower(),p.path,p.query,''))
byurl=defaultdict(list)
for ref,row in records.items():
 m=metadata.get(ref,{})
 if m.get('url'):byurl[endpoint(m['url'])].append(ref)
for s in world:
 if s['reference'] in records:continue
 matches=byurl.get(endpoint(s['url']),[])
 fingerprints={tuple(records[r]['renders'][v]['sha256'] for v in sorted(VARIANTS)) for r in matches}
 if len(fingerprints)!=1:continue
 source=matches[0];row=records[source];country=row['country']
 for variant,item in row['renders'].items():add(country,s['reference'],variant,(OUT/item['path']).read_bytes(),'exact_stream_alias/'+source,item['sha256'])
 metadata[s['reference']]=dict(s,country=country)

assert all(set(row['renders'])==VARIANTS for row in records.values())
if conflicts:write_json(OUT/'conflicts.json',conflicts);raise SystemExit(f'{len(conflicts)} conflicting PNGs; no packaging')
for ref,row in records.items():
 row['station']=metadata.get(ref,byref.get(ref,{}))
 row['status']='ready_verified_owner_approved'

coverage=[]
for s in world:
 row=dict(s,status='ready' if s['reference'] in records else 'pending_verified_original',country=country_by_group.get(s['group'],'WORLD'))
 if s['reference'] in records:row['origins']=records[s['reference']]['origins']
 else:row['reason']='No completed verified logo set in restored inputs; requires source acquisition and identity/visual verification.'
 coverage.append(row)
counts=Counter(row['status'] for row in coverage)
summary=dict(schema=1,date='2026-11-05',project='Radio plugin',status='partial_verified_checkpoint',catalogue_sha256=SHA(world_path.read_bytes()),catalogue_references=len(world),ready_catalogue_references=counts['ready'],pending_catalogue_references=counts['pending_verified_original'],ready_total_references=len(records),ready_pngs=len(records)*9,production_baseline_references=len(production_refs),restored_additional_references=len(before_alias-production_refs),new_exact_stream_alias_references=len(set(records)-before_alias),unique_verified_pngs=len(validated),all_future_batches_owner_approved=True,production_published=False,conflicts=0,batches=batch_reports)
write_json(OUT/'summary.json',summary);write_json(OUT/'ready-manifest.json',list(records.values()));write_json(OUT/'coverage.json',coverage)
write_json(OUT/'ready-references.json',sorted(records));write_json(OUT/'input-audit.json',dict(checks=checks,source_catalogue=str(world_path),production_baseline_commit='e90a1fe3a2734b555f48f343284f9103530180fb'))
shutil.copyfile(ROOT/'owner-authorization.json',OUT/'owner-authorization.json')
with (OUT/'coverage.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['reference','name','group','country','url','status']);w.writeheader()
 for row in coverage:w.writerow({k:row.get(k,'') for k in w.fieldnames})

# Country packages are independent and split at 300 references for modest, recoverable archives.
groups=defaultdict(list)
for ref,row in records.items():groups[row['country']].append(ref)
packages=[]
for country,refs in sorted(groups.items()):
 refs=sorted(refs)
 for start in range(0,len(refs),300):
  chunk=refs[start:start+300];p=OUT/f'Warder_Radio_{country}_obnova_{start//300+1:02d}_{len(chunk)}_ref.zip'
  with zipfile.ZipFile(p,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
   z.writestr('README.txt','Radio plugin: approved verified PNG checkpoint. Three sizes x three Warder backgrounds. No production activation. See ready-manifest.json and coverage.json.\n')
   z.writestr('references.json',json.dumps([records[r] for r in chunk],ensure_ascii=False,indent=2))
   for ref in chunk:
    for variant,item in sorted(records[ref]['renders'].items()):
     info=zipfile.ZipInfo(f'picons/{variant}/{ref.replace(":","_")}.png',(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
     z.writestr(info,(OUT/item['path']).read_bytes())
  with zipfile.ZipFile(p) as z:
   assert z.testzip() is None
   actual={n for n in z.namelist() if n.endswith('.png')};assert len(actual)==9*len(chunk)
   for ref in chunk:
    for variant,item in records[ref]['renders'].items():assert SHA(z.read(f'picons/{variant}/{ref.replace(":","_")}.png'))==item['sha256']
  packages.append(dict(name=p.name,bytes=p.stat().st_size,sha256=SHA(p.read_bytes()),references=len(chunk),pngs=9*len(chunk)))
write_json(OUT/'packages.json',packages)
write_json(OUT/'journal.json',[dict(date='2026-11-05',event='owner_authorization_persisted',commit='c2bccddec9ac4dc9deb74b7f90b74116796d1bf0'),dict(date='2026-11-05',event='checkpoint_rebuilt_and_verified',summary=summary,packages=packages)])
print(json.dumps(summary,ensure_ascii=False),flush=True)
print(json.dumps(packages),flush=True)
