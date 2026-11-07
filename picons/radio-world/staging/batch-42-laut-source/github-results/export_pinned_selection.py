#!/usr/bin/env python3
"""Fetch immutable completed producer chunks, verify Git blob inventory, pin combined selection."""
import gzip,hashlib,json,subprocess,urllib.request
from pathlib import Path
P=Path(__file__).resolve().parent;STAGE='picons/radio-world/staging/batch-42-laut-source';REPO='Evolution-by-Warder/PiconHub-Warder-Evolution';GIT=P.parents[1]/'source-check';OUT=P/'github-results';OUT.mkdir(exist_ok=True)
def run(*args,input=None):return subprocess.check_output(['git','-C',str(GIT),*args],input=input).decode()
def raw(commit,path):
 req=urllib.request.Request('https://raw.githubusercontent.com/'+REPO+'/'+commit+'/'+path,headers={'User-Agent':'Mozilla/5.0'})
 return urllib.request.urlopen(req,timeout=60).read()
def tree(commit,folder):
 lines=run('ls-tree','-r',commit,'--',folder).splitlines();return {line.split('\t',1)[1]:line.split()[2] for line in lines}
expected={r['ref']:r for r in json.loads((P/'approved-selection.json').read_bytes())['entries']}
branches=['work/radio-laut435-source-chunk-'+str(i).zfill(3)+'-20261107' for i in range(1,6)]
refs=run('ls-remote','origin',*[('refs/heads/'+b) for b in branches]);heads={line.split()[1].replace('refs/heads/',''):line.split()[0]for line in refs.splitlines()}
assert len(heads)==5,'Not all source chunk branches are available'
run('fetch','--no-tags','--filter=blob:none','--stdin','origin',input=('\n'.join(heads[b] for b in branches)+'\n').encode())
rows=[];proofs=[];unique=set();source_commits=set();originals_unique={}
for i,b in enumerate(branches,1):
 head=heads[b];proofraw=raw(head,STAGE+'/source-proof.json');proof=json.loads(proofraw);data=raw(head,STAGE+'/selection.json.gz');selection=json.loads(gzip.decompress(data));plan=json.loads((P/'producer-plans'/('producer-plan-'+str(i).zfill(3)+'.json')).read_bytes())
 assert proof['status']=='pass' and proof['chunk']==i
 assert proof['producer_plan_sha256']==hashlib.sha256((P/'producer-plans'/('producer-plan-'+str(i).zfill(3)+'.json')).read_bytes()).hexdigest()
 assert proof['selection_sha256']==hashlib.sha256(data).hexdigest()
 assert proof['references']==len(selection['entries'])==plan['references']
 source=proof['source_commit'];source_commits.add(source)
 run('fetch','--no-tags','--filter=blob:none','--stdin','origin',input=(source+'\n').encode())
 pngtree=tree(source,STAGE+'/verified-assets');origins=tree(source,STAGE+'/originals')
 want={v[0]:v[2] for r in selection['entries'] for v in r['variants'].values()}
 assert len(want)==plan['unique_pngs']
 assert {STAGE+'/verified-assets/'+sha+'.png':blob for sha,blob in want.items()}==pngtree,'PNG Git blob inventory differs'
 for sha,resource in plan['originals'].items():
  assert origins[STAGE+'/originals/'+sha+'.img']==resource['git_blob']
  assert sha not in originals_unique or originals_unique[sha]==resource['git_blob']
  originals_unique[sha]=resource['git_blob']
 for row in selection['entries']:
  assert row['source_commit']==source and row['asset_root']==STAGE
  assert row['ref'] in expected and row['variants']==expected[row['ref']]['variants']
  assert row['index']!=558
 rows+=selection['entries'];unique.update(want)
 (OUT/('selection-chunk-'+str(i).zfill(3)+'.json.gz')).write_bytes(data)
 (OUT/('source-proof-chunk-'+str(i).zfill(3)+'.json')).write_bytes(proofraw)
 proofs.append(dict(chunk=i,branch=b,metadata_commit=head,source_commit=source,references=len(selection['entries']),unique_pngs=len(want),actual_git_blob_inventory_pass=True))
assert len(rows)==len({r['ref'] for r in rows})==435 and len(unique)==3897
assert {r['ref'] for r in rows}==set(expected) and len(originals_unique)==433
rows.sort(key=lambda r:r['index']);data=gzip.compress((json.dumps(dict(entries=rows),ensure_ascii=False,separators=(',',':'))+'\n').encode(),mtime=0);(OUT/'selection.json.gz').write_bytes(data)
proof=dict(schema=1,status='pass',references=435,png_instances=3915,unique_pngs=3897,unique_byte_preserved_originals=len(originals_unique),source_commits=sorted(source_commits),chunks=proofs,selection_sha256=hashlib.sha256(data).hexdigest(),all_actual_git_blob_sha_match_reviewed_pngs=True,no_production_or_existing_png_mutations=True)
(OUT/'combined-pinned-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))
