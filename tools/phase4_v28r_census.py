#!/usr/bin/env python3
"""Resumable, read-only V28R catalog census with push-before-next-batch durability."""
from __future__ import annotations
import argparse, csv, gzip, hashlib, json, os, shutil, subprocess, sys, tempfile, time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

BRANCH = 'phase4-v10-component-mask-test'
OUT_REL = Path('reports/phase4-v28r-catalog-factory')
WORKER_REL = Path('tools/phase4_v28r_worker.py')
FROZEN_GENERATOR_SHA = 'f931d3eb703021fa90d6c7934e6902cd1ecb49dd7a8e69e087072a9bf00d1722'
WHITE_MASTER_SHA = 'c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589'
BLACK_MASTER_SHA = '61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe'
SCHEMA = 'piconhub-v28r-checkpoint-v1'


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_name(path.name+'.tmp-'+str(os.getpid()))
    with tmp.open('wb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(tmp,path)
    dfd=os.open(path.parent,os.O_RDONLY)
    try: os.fsync(dfd)
    finally: os.close(dfd)


def atomic_json(path: Path, obj) -> None:
    atomic_bytes(path,(json.dumps(obj,indent=2,ensure_ascii=False,sort_keys=True)+'\n').encode())


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def tree_inventory(root: Path):
    rows=subprocess.check_output(['git','-C',str(root),'ls-tree','-r','HEAD'],text=True).splitlines()
    groups=defaultdict(list); total_bytes=0
    for line in rows:
        meta,rel=line.split('\t',1); mode,kind,blob=meta.split()
        parts=Path(rel).parts
        if len(parts)!=5 or parts[0]!='picons' or parts[3]!='transparent' or Path(rel).suffix.lower()!='.png': continue
        path=root/rel
        data=path.read_bytes(); sha=sha256_bytes(data); total_bytes+=len(data)
        groups[sha].append({'source_path':rel,'git_blob_sha':blob,'bytes':len(data)})
    canonical=[]
    for sha,refs in sorted(groups.items()):
        refs=sorted(refs,key=lambda x:x['source_path'])
        canonical.append({'source_sha256':sha,'representative_source_path':refs[0]['source_path'],'service_count':len(refs),'refs':refs})
    payload=json.dumps(canonical,sort_keys=True,separators=(',',':')).encode()
    return {'groups':canonical,'source_count':sum(len(g['refs']) for g in canonical),'unique_count':len(canonical),
            'total_source_bytes':total_bytes,'inventory_sha256':sha256_bytes(payload)}


def assert_repo(root: Path, require_clean=True):
    branch=git(root,'branch','--show-current')
    if branch!=BRANCH: raise SystemExit(f'STOP: expected branch {BRANCH}, found {branch!r}')
    status=git(root,'status','--porcelain')
    if require_clean and status: raise SystemExit('STOP: worktree must be clean before this operation:\n'+status)
    return git(root,'rev-parse','HEAD')


def remote_head(root: Path) -> str:
    lines=subprocess.check_output(['git','-C',str(root),'ls-remote','origin',f'refs/heads/{BRANCH}'],text=True).strip().splitlines()
    if len(lines)!=1: raise SystemExit(f'STOP: cannot resolve exactly one remote branch for {BRANCH}')
    return lines[0].split()[0]


def load_state(root: Path):
    out=root/OUT_REL
    for name in ('CHECKPOINT.json','INVENTORY.json','RUN-MANIFEST.json'):
        if not (out/name).is_file(): raise SystemExit(f'STOP: missing durable state file {OUT_REL/name}')
    inv=read_json(out/'INVENTORY.json'); cp=read_json(out/'CHECKPOINT.json'); manifest=read_json(out/'RUN-MANIFEST.json')
    if cp.get('schema')!=SCHEMA or inv.get('schema')!=SCHEMA: raise SystemExit('STOP: checkpoint/inventory schema mismatch')
    current=tree_inventory(root)
    if current['inventory_sha256']!=inv.get('inventory_sha256') or current['source_count']!=inv.get('source_count') or current['unique_count']!=inv.get('unique_count'):
        raise SystemExit('STOP: source inventory identity mismatch; checkpoint retained unchanged')
    worker=root/WORKER_REL
    if sha256_file(worker)!=manifest.get('worker_sha256'): raise SystemExit('STOP: worker algorithm hash differs from RUN-MANIFEST')
    if sha256_file(root/'tools/phase4_v28r_census.py')!=manifest.get('runner_sha256'): raise SystemExit('STOP: runner algorithm hash differs from RUN-MANIFEST')
    if sha256_file(root/'tools/rebuild_master_catalog.py')!=FROZEN_GENERATOR_SHA: raise SystemExit('STOP: frozen V9 generator hash mismatch')
    if sha256_file(root/'templates/picons/white-sablona.png')!=WHITE_MASTER_SHA or sha256_file(root/'templates/picons/black-sablona.png')!=BLACK_MASTER_SHA:
        raise SystemExit('STOP: MASTER template hash mismatch')
    expected={g['source_sha256'] for g in inv['groups']}
    completed=set(cp.get('completed_sha_groups',[]))
    if not completed<=expected: raise SystemExit('STOP: checkpoint contains SHA groups outside inventory')
    return out,inv,cp,manifest,current


def commit_push(root: Path, message: str, include_infrastructure=False):
    out=OUT_REL.as_posix()
    allowed=[out]
    if include_infrastructure: allowed += [WORKER_REL.as_posix(),'tools/phase4_v28r_census.py']
    subprocess.check_call(['git','-C',str(root),'add','--',*allowed])
    diff=subprocess.check_output(['git','-C',str(root),'diff','--cached','--name-only'],text=True).splitlines()
    if not diff or any(not any(p==x or p.startswith(x+'/') for x in allowed) for p in diff):
        raise SystemExit('STOP: staged file outside V28R infrastructure/audit whitelist')
    subprocess.check_call(['git','-C',str(root),'commit','-m',message])
    commit=git(root,'rev-parse','HEAD')
    subprocess.check_call(['git','-C',str(root),'push','origin',BRANCH])
    actual=remote_head(root)
    if actual!=commit: raise SystemExit(f'STOP: pushed commit not verified remotely ({actual} != {commit})')
    if git(root,'status','--porcelain'): raise SystemExit('STOP: worktree not clean after checkpoint push')
    return commit


def initialize(root: Path):
    head=assert_repo(root,True)
    if remote_head(root)!=head: raise SystemExit('STOP: local target branch is not at current remote HEAD')
    out=root/OUT_REL
    if out.exists(): raise SystemExit('STOP: V28R directory already exists; inspect and resume it instead of overwriting')
    invdata=tree_inventory(root)
    if invdata['source_count']!=9041 or invdata['unique_count']!=6604:
        raise SystemExit(f"STOP: catalog sanity check differs from expected inventory (sources={invdata['source_count']}, unique={invdata['unique_count']})")
    worker=root/WORKER_REL
    manifest={'schema':SCHEMA,'census_version':'V28R-1.0','branch':BRANCH,'snapshot_head':head,
      'inventory_sha256':invdata['inventory_sha256'],'source_count':invdata['source_count'],'unique_sha_count':invdata['unique_count'],
      'worker_path':WORKER_REL.as_posix(),'worker_sha256':sha256_file(worker),'runner_sha256':sha256_file(root/'tools/phase4_v28r_census.py'),'phase3_generator_sha256':FROZEN_GENERATOR_SHA,
      'white_master_sha256':WHITE_MASTER_SHA,'black_master_sha256':BLACK_MASTER_SHA,'batch_size_default':100,
      'created_at_utc':now(),'durability_policy':'one bounded batch per commit; push and verify before another batch'}
    inv={'schema':SCHEMA,'inventory_sha256':invdata['inventory_sha256'],'repository_snapshot_head':head,
      'source_count':invdata['source_count'],'unique_count':invdata['unique_count'],'total_source_bytes':invdata['total_source_bytes'],
      'groups':invdata['groups']}
    cp={'schema':SCHEMA,'census_version':'V28R-1.0','snapshot_head':head,'inventory_sha256':invdata['inventory_sha256'],
      'source_count':invdata['source_count'],'unique_sha_count':invdata['unique_count'],'completed_sha_groups':[],
      'pending_sha_groups':[g['source_sha256'] for g in invdata['groups']],'failed_groups':[],'per_group_status':{},
      'batch_commits':[],'resume_events':0,'state':'INITIALIZED','updated_at_utc':now()}
    atomic_json(out/'RUN-MANIFEST.json',manifest); atomic_json(out/'INVENTORY.json',inv); atomic_json(out/'CHECKPOINT.json',cp)
    readme='''# V28R resumable factory census\n\nThis is a read-only, resumable analysis. It does not write picons, MASTER templates, the production generator, or approvals.\n\n## Recovery commands\n\n- `python tools/phase4_v28r_census.py status` checks the durable checkpoint and current remote head.\n- `python tools/phase4_v28r_census.py resume --batch-size 10 --dry-run` verifies resume state and reports which hashes will be skipped/selected without analysis.\n- `python tools/phase4_v28r_census.py resume --batch-size 10` analyzes one bounded batch, atomically saves it, commits it, pushes it, and verifies the remote branch before returning.\n- Continue with `resume --batch-size 100`; every invocation handles one batch only.\n- `python tools/phase4_v28r_census.py finalize` aggregates only committed batch results after all groups complete.\n\n`CHECKPOINT.json`, `INVENTORY.json`, and `RUN-MANIFEST.json` are authoritative. Batch files are independently checksummed. Any schema, inventory, worker-code, frozen generator, or MASTER hash mismatch stops the run without replacing state. Never delete an interrupted batch or overwrite an existing V28R directory.\n'''
    (out/'README.md').write_text(readme,encoding='utf-8')
    print(json.dumps({'event':'initialized','snapshot_head':head,'sources':inv['source_count'],'unique_sha_groups':inv['unique_count'],
      'inventory_sha256':inv['inventory_sha256'],'source_bytes':inv['total_source_bytes']}))
    commit=commit_push(root,'V28R: initialize resumable catalog census',include_infrastructure=True)
    print(json.dumps({'event':'infrastructure_pushed','commit':commit,'remote_head':remote_head(root)}))


def csv_rows(path: Path):
    with gzip.open(path,'rt',newline='',encoding='utf-8-sig') as f: return list(csv.DictReader(f))


def csv_gz_bytes(rows):
    import io
    if not rows: return b''
    keys=list(dict.fromkeys(k for row in rows for k in row))
    raw=io.BytesIO()
    with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as gz:
        text=io.TextIOWrapper(gz,encoding='utf-8',newline='')
        w=csv.DictWriter(text,fieldnames=keys,lineterminator='\n',extrasaction='ignore');w.writeheader();w.writerows(rows);text.flush();text.detach()
    return raw.getvalue()


def run_batch(root: Path, size: int, resume: bool, dry_run: bool):
    head=assert_repo(root,True)
    out,inv,cp,manifest,current=load_state(root)
    if remote_head(root)!=head: raise SystemExit('STOP: current checkpoint is not at remote HEAD; push/resolve it before more analysis')
    done=set(cp['completed_sha_groups']); pending=[g['source_sha256'] for g in inv['groups'] if g['source_sha256'] not in done]
    if not resume and done: raise SystemExit('STOP: checkpoint already has completed groups; use --resume')
    if resume:
        cp['resume_events']=int(cp.get('resume_events',0))+1
        print(json.dumps({'event':'resume_verified','skipped_completed_groups':len(done),'next_pending_count':len(pending),'inventory_sha256':inv['inventory_sha256']}))
    if dry_run:
        print(json.dumps({'event':'dry_run','selected_sha_groups':pending[:size],'selected_count':min(size,len(pending)),'skipped_completed_groups':len(done)}))
        return
    if not pending:
        print(json.dumps({'event':'complete_no_pending_groups'})); return
    selected=pending[:size]; batch_no=len(cp.get('batch_commits',[]))+1
    batch_id=f'batch-{batch_no:04d}'
    batch_dir=out/'batches'/batch_id
    if batch_dir.exists(): raise SystemExit(f'STOP: batch directory already exists: {batch_dir}')
    batch_dir.mkdir(parents=True)
    start=time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='v28r-worker-') as tmpname:
        tmp=Path(tmpname); worker_out=tmp/'worker'; worker_out.mkdir()
        sha_list=tmp/'sha-groups.txt'; sha_list.write_text('\n'.join(selected)+'\n',encoding='ascii')
        command=[sys.executable,str(root/WORKER_REL),'--repo-root',str(root),'--out',str(worker_out),
          '--expected-head',head,'--sha-list-file',str(sha_list)]
        child_env=os.environ.copy(); child_env['PYTHONDONTWRITEBYTECODE']='1'
        subprocess.check_call(command,cwd=root,env=child_env)
        feat=csv_rows(worker_out/'SOURCE-FEATURES.csv.gz')
        mapping=csv_rows(worker_out/'SERVICE-MAPPING.csv.gz')
        buckets=csv_rows(worker_out/'FACTORY-BUCKETS.csv.gz')
        dups=csv_rows(worker_out/'DUPLICATE-GROUPS.csv.gz')
        perf=read_json(worker_out/'PERFORMANCE.json')
    if sorted(r['source_sha256'] for r in feat)!=sorted(selected): raise SystemExit('STOP: batch feature rows do not equal selected SHA group set')
    if len(buckets)!=2*len(selected) or any(sum(1 for r in buckets if r['source_sha256']==h)!=2 for h in selected):
        raise SystemExit('STOP: batch must contain exactly one WHITE and BLACK row per SHA group')
    expected_refs=sum(next(g['service_count'] for g in inv['groups'] if g['source_sha256']==h) for h in selected)
    if len(mapping)!=expected_refs: raise SystemExit(f'STOP: service mapping row count {len(mapping)} != {expected_refs}')
    if len({r['source_path'] for r in mapping})!=expected_refs: raise SystemExit('STOP: duplicate/missing source path in batch service mapping')
    if any(r['factory_bucket'] not in {f'F{i}' for i in range(8)} for r in buckets): raise SystemExit('STOP: unexpected factory bucket')
    files={'SOURCE-FEATURES.csv.gz':feat,'SERVICE-MAPPING.csv.gz':mapping,'FACTORY-BUCKETS.csv.gz':buckets,'DUPLICATE-GROUPS.csv.gz':dups}
    file_hashes={}
    for name,rows in files.items():
        data=csv_gz_bytes(rows); atomic_bytes(batch_dir/name,data); file_hashes[name]=sha256_bytes(data)
        reread=csv_rows(batch_dir/name)
        if len(reread)!=len(rows): raise SystemExit(f'STOP: saved batch data reread mismatch: {name}')
    worker_perf=perf
    elapsed=time.perf_counter()-start
    bmanifest={'schema':SCHEMA,'batch_id':batch_id,'batch_number':batch_no,'sha_groups':selected,'sha_group_count':len(selected),
      'source_service_count':len(mapping),'feature_rows':len(feat),'bucket_rows':len(buckets),'duplicate_group_rows':len(dups),
      'files_sha256':file_hashes,'worker_performance':worker_perf,'batch_wall_seconds':elapsed,'completed_at_utc':now(),
      'worker_head':head}
    atomic_json(batch_dir/'BATCH-MANIFEST.json',bmanifest)
    completed=sorted(done|set(selected)); status=cp.setdefault('per_group_status',{})
    for h in selected: status[h]={'status':'COMPLETED','batch_id':batch_id,'completed_at_utc':bmanifest['completed_at_utc']}
    cp['completed_sha_groups']=completed; cp['pending_sha_groups']=[g['source_sha256'] for g in inv['groups'] if g['source_sha256'] not in set(completed)]
    cp['failed_groups']=[]; cp['state']='IN_PROGRESS' if cp['pending_sha_groups'] else 'CENSUS_DATA_COMPLETE'; cp['updated_at_utc']=now()
    cp['batch_commits'].append({'batch_id':batch_id,'sha_group_count':len(selected),'source_service_count':len(mapping),
      'batch_wall_seconds':elapsed,'files_sha256':file_hashes})
    atomic_json(out/'CHECKPOINT.json',cp)
    if len(completed)!=len(set(completed)): raise SystemExit('STOP: duplicate SHA completion in checkpoint')
    pushed=commit_push(root,f'V28R: checkpoint unique sources {len(completed)-len(selected)+1:04d}-{len(completed):04d}')
    cp['last_verified_remote_commit']=pushed
    print(json.dumps({'event':'batch_pushed','batch_id':batch_id,'completed':len(completed),'pending':len(cp['pending_sha_groups']),
      'batch_wall_seconds':elapsed,'commit':pushed,'remote_head':remote_head(root)}))


def atomic_csv_gz(path: Path, rows):
    data=csv_gz_bytes(rows); atomic_bytes(path,data)


def finalize(root: Path):
    head=assert_repo(root,True); out,inv,cp,manifest,current=load_state(root)
    if remote_head(root)!=head: raise SystemExit('STOP: final aggregation requires latest checkpoint already pushed')
    expected=[g['source_sha256'] for g in inv['groups']]
    if set(cp['completed_sha_groups'])!=set(expected): raise SystemExit('STOP: cannot finalize while SHA groups are pending')
    feature=[]; mapping=[]; buckets=[]; duplicates=[]; batch_perf=[]
    for rec in cp['batch_commits']:
        bdir=out/'batches'/rec['batch_id']
        bm=read_json(bdir/'BATCH-MANIFEST.json')
        for filename in bm['files_sha256']:
            p=bdir/filename
            if sha256_file(p)!=bm['files_sha256'][filename]: raise SystemExit(f'STOP: batch checksum mismatch {p}')
        feature.extend(csv_rows(bdir/'SOURCE-FEATURES.csv.gz')); mapping.extend(csv_rows(bdir/'SERVICE-MAPPING.csv.gz'))
        buckets.extend(csv_rows(bdir/'FACTORY-BUCKETS.csv.gz')); duplicates.extend(csv_rows(bdir/'DUPLICATE-GROUPS.csv.gz'))
        batch_perf.append(bm)
    feature.sort(key=lambda r:r['source_sha256']); mapping.sort(key=lambda r:r['source_path']); buckets.sort(key=lambda r:(r['style'],r['source_sha256']))
    duplicates.sort(key=lambda r:r['source_sha256'])
    if len(feature)!=inv['unique_count'] or len({r['source_sha256'] for r in feature})!=inv['unique_count']: raise SystemExit('STOP: final unique feature coverage mismatch')
    if len(mapping)!=inv['source_count'] or len({r['source_path'] for r in mapping})!=inv['source_count']: raise SystemExit('STOP: final service mapping coverage mismatch')
    if len(buckets)!=2*inv['unique_count'] or len({(r['source_sha256'],r['style']) for r in buckets})!=2*inv['unique_count']: raise SystemExit('STOP: final WHITE/BLACK classification coverage mismatch')
    inv_paths={ref['source_path'] for group in inv['groups'] for ref in group['refs']}
    if {r['source_path'] for r in mapping}!=inv_paths: raise SystemExit('STOP: final mapping path set differs from inventory')
    for style in ('white','black'):
        counts={f'F{i}':{'unique_sources':0,'service_references':0} for i in range(8)}
        for row in buckets:
            if row['style']!=style: continue
            bucket=row['factory_bucket']; counts[bucket]['unique_sources']+=1; counts[bucket]['service_references']+=int(row['physical_service_refs'])
        if sum(x['unique_sources'] for x in counts.values())!=inv['unique_count'] or sum(x['service_references'] for x in counts.values())!=inv['source_count']:
            raise SystemExit(f'STOP: {style} bucket accounting does not reconcile')
        if any(x['unique_sources']!=sum(1 for r in buckets if r['style']==style and r['factory_bucket']==b) for b,x in counts.items()):
            raise SystemExit(f'STOP: {style} bucket unique count mismatch')
        if any(x['service_references']!=sum(int(r['physical_service_refs']) for r in buckets if r['style']==style and r['factory_bucket']==b) for b,x in counts.items()):
            raise SystemExit(f'STOP: {style} bucket reference count mismatch')
        if style=='white': white_counts=counts
        else: black_counts=counts
    features_by_sha={r['source_sha256']:r for r in feature}
    provenance=[]
    for r in mapping:
        if r.get('historical_source_sha256_consistency')=='MISMATCH':
            provenance.append({'source_path':r['source_path'],'current_sha256':r['source_sha256'],'historical_phase3_sha256':r.get('historical_source_sha256','')})
    # Detect any worker-level data/decode errors from feature rows.
    errors=[{'source_sha256':r['source_sha256'],'source_paths':r.get('source_paths',''),'reason':'decode_or_analysis_error'} for r in feature if r.get('format')=='ERROR']
    clusters=[]; labels={'F0':'no-action / safe','F1':'existing V9 safe adaptation','F2':'known false-two-tone pattern','F3':'protected chromatic / mixed',
      'F4':'insufficient evidence','F5':'genuine two-tone','F6':'other review','F7':'data / geometry / provenance error'}
    for style,counts in (('white',white_counts),('black',black_counts)):
        for b in [f'F{i}' for i in range(8)]:
            refs=counts[b]['service_references']; unique=counts[b]['unique_sources']
            clusters.append({'cluster_id':b,'cluster_name':labels[b],'style':style.upper(),'unique_sources':unique,'service_references':refs,
              'duplicate_leverage':refs/unique if unique else 0.0})
    hist=[]
    for line in []: hist.append(line)
    summary={'outcome':'CATALOG-FACTORY-MAP-READY','census_version':'V28R-1.0','branch':BRANCH,
      'starting_head':cp['snapshot_head'],'inventory_snapshot_head':inv['repository_snapshot_head'],'final_input_head_before_aggregate':head,
      'inventory_sha256':inv['inventory_sha256'],'source_counts':{'source_service_pngs':inv['source_count'],'unique_source_sha256_groups':inv['unique_count'],
        'duplicate_groups':len(duplicates),'refs_in_duplicate_groups':sum(int(r['duplicate_count']) for r in duplicates),
        'duplicate_refs_excess_over_unique':inv['source_count']-inv['unique_count'],'unique_analyses_saved':inv['source_count']-inv['unique_count'],
        'source_png_bytes':inv['total_source_bytes']},
      'coverage':{'feature_rows':len(feature),'service_mapping_rows':len(mapping),'white_bucket_rows':sum(r['style']=='white' for r in buckets),
        'black_bucket_rows':sum(r['style']=='black' for r in buckets),'unique_groups_with_both_decisions':inv['unique_count'],'decode_or_analysis_errors':len(errors)},
      'factory_bucket_counts':{'white':white_counts,'black':black_counts},'problem_clusters':clusters,'f6_manual_review':{
        'white_unique_sources':white_counts['F6']['unique_sources'],'white_service_references':white_counts['F6']['service_references'],
        'black_unique_sources':black_counts['F6']['unique_sources'],'black_service_references':black_counts['F6']['service_references']},
      'f7_provenance_and_data_cases':provenance,'errors':errors,
      'runtime':{'durable_batches':len(batch_perf),'resume_events':cp.get('resume_events',0),
        'sum_batch_wall_seconds':sum(float(b['batch_wall_seconds']) for b in batch_perf),
        'sum_unique_analysis_seconds':sum(float(b['worker_performance'].get('unique_image_analysis_seconds',0)) for b in batch_perf),
        'sum_hashing_seconds':sum(float(b['worker_performance'].get('hashing_seconds',0)) for b in batch_perf),
        'checkpoint_commits':cp.get('batch_commits',[]),'batch_size_distribution':dict(Counter(int(b['sha_group_count']) for b in batch_perf))},
      'durability':{'completed_sha_groups':len(cp['completed_sha_groups']),'pending_sha_groups':len(cp['pending_sha_groups']),
        'remote_head_at_aggregation':remote_head(root),'all_batches_committed_and_pushed':len(cp['batch_commits'])>0 and len(cp['completed_sha_groups'])==inv['unique_count']},
      'protected_trees':{'input_only':True,'generator_sha256':FROZEN_GENERATOR_SHA,'white_master_sha256':WHITE_MASTER_SHA,
        'black_master_sha256':BLACK_MASTER_SHA,'picon_pngs_written':0,'production_generator_modified':False,'approval_records_modified':False}}
    # Independently check frozen V9 status parity against Phase 3 audit rows.
    audit=root/'reports/warder-master-production/catalog-audit.csv'
    if audit.exists():
        with audit.open(newline='',encoding='utf-8-sig') as f: hist=list(csv.DictReader(f))
        status={}
        for row in buckets:
            for path in row['source_paths'].split('|'):
                status[(path,row['style'])]=row['v9_status']
        checked=matched=0; mismatches=[]
        for row in hist:
            path=row.get('source','')
            if path in {p['source_path'] for p in provenance}: continue
            for style in ('white','black'):
                old=row.get(f'{style}_status',''); new=status.get((path,style),'')
                if old and new:
                    checked+=1
                    if old==new: matched+=1
                    else: mismatches.append({'source_path':path,'style':style,'phase3_status':old,'v28r_status':new})
        summary['phase3_replay_parity']={'checked_path_style_pairs':checked,'matching_path_style_pairs':matched,'mismatches':mismatches}
    atomic_csv_gz(out/'SOURCE-FEATURES.csv.gz',feature); atomic_csv_gz(out/'SERVICE-MAPPING.csv.gz',mapping)
    atomic_csv_gz(out/'FACTORY-BUCKETS.csv.gz',buckets); atomic_csv_gz(out/'DUPLICATE-GROUPS.csv.gz',duplicates)
    # Preserve the prior V28 cluster definition as an evidence-based reason map, now with V28R counts.
    old_clusters=[]
    for b,name in labels.items():
        for style,counts in (('WHITE',white_counts),('BLACK',black_counts)):
            old_clusters.append({'cluster_id':b,'cluster_name':name,'style':style,'unique_sources':counts[b]['unique_sources'],
              'service_references':counts[b]['service_references'],'duplicate_leverage':counts[b]['service_references']/counts[b]['unique_sources'] if counts[b]['unique_sources'] else 0.0})
    with (out/'PROBLEM-CLUSTERS.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(old_clusters[0]),lineterminator='\n');w.writeheader();w.writerows(old_clusters)
    perf={'census_version':'V28R-1.0','durable_batch_count':len(batch_perf),'resume_events':cp.get('resume_events',0),
      'sum_batch_wall_seconds':summary['runtime']['sum_batch_wall_seconds'],'sum_unique_image_analysis_seconds':summary['runtime']['sum_unique_analysis_seconds'],
      'sum_hashing_seconds':summary['runtime']['sum_hashing_seconds'],'physical_source_count':inv['source_count'],'unique_image_count':inv['unique_count'],
      'unique_images_per_second':inv['unique_count']/summary['runtime']['sum_unique_analysis_seconds'] if summary['runtime']['sum_unique_analysis_seconds'] else 0,
      'peak_batch_rss_bytes':max((int(b['worker_performance'].get('peak_rss_bytes',0)) for b in batch_perf),default=0),
      'batch_runs':[{'batch_id':b['batch_id'],'sha_group_count':b['sha_group_count'],'batch_wall_seconds':b['batch_wall_seconds'],
        'unique_image_analysis_seconds':b['worker_performance'].get('unique_image_analysis_seconds',0)} for b in batch_perf]}
    atomic_json(out/'PERFORMANCE.json',perf)
    atomic_json(out/'CATALOG-SUMMARY.json',summary)
    report=[f'# V28R — resumable catalog factory census','', '**Read-only analysis. No picon repairs or production writes were made.**','',
      f"- Starting source snapshot HEAD: `{cp['snapshot_head']}`",f"- Remote target branch: `{BRANCH}`",
      f"- Source/service PNGs: **{inv['source_count']:,}**",f"- Unique SHA-256 groups: **{inv['unique_count']:,}**",
      f"- Duplicate groups: **{len(duplicates):,}**; references in duplicate groups: **{sum(int(r['duplicate_count']) for r in duplicates):,}**",
      f"- Unique analyses saved: **{inv['source_count']-inv['unique_count']:,}** ({100*(inv['source_count']-inv['unique_count'])/inv['source_count']:.2f}% of service references)",
      f"- Durable batch checkpoints: **{len(batch_perf)}**; resume events: **{cp.get('resume_events',0)}**",'',
      '## WHITE / BLACK factory accounting','','| Style | Bucket | Unique sources | Service references |','|---|---:|---:|---:|']
    for style,counts in (('WHITE',white_counts),('BLACK',black_counts)):
        for b in [f'F{i}' for i in range(8)]: report.append(f"| {style} | {b} | {counts[b]['unique_sources']:,} | {counts[b]['service_references']:,} |")
    report+=['','## F6 and F7','',f"- F6 manual-review population: WHITE {white_counts['F6']['unique_sources']} unique / {white_counts['F6']['service_references']} refs; BLACK {black_counts['F6']['unique_sources']} / {black_counts['F6']['service_references']}.",
      f"- F7 provenance/data population: {len({r['current_sha256'] for r in provenance})} unique current SHAs; {len(provenance)} affected service references."]
    for p in provenance: report.append(f"  - `{p['source_path']}` — current `{p['current_sha256']}`, historical Phase 3 `{p['historical_phase3_sha256']}`")
    report+=['','## Validation and durability','',f"- Feature rows: {len(feature):,}; service mapping rows: {len(mapping):,}; WHITE and BLACK decisions: {len(buckets):,}.",
      f"- Phase 3 replay parity: {summary.get('phase3_replay_parity',{}).get('matching_path_style_pairs','not available')}/{summary.get('phase3_replay_parity',{}).get('checked_path_style_pairs','not available')} path/style checks matched.",
      f"- Batch results pushed before proceeding: {len(cp['batch_commits'])}; latest verified remote checkpoint: `{remote_head(root)}`.",
      '- Source PNGs, WHITE/BLACK outputs, MASTER templates, production generator, and approval records were read-only.']
    (out/'REPORT.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    cp['state']='FINALIZED';cp['final_summary_generated_at_utc']=now();cp['updated_at_utc']=now();atomic_json(out/'CHECKPOINT.json',cp)
    commit=commit_push(root,'V28R: finalize factory census aggregates')
    print(json.dumps({'event':'finalized','commit':commit,'remote_head':remote_head(root),'sources':inv['source_count'],'unique':inv['unique_count']}))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo-root',type=Path,default=Path('.'))
    sub=ap.add_subparsers(dest='command',required=True)
    sub.add_parser('initialize')
    r=sub.add_parser('resume');r.add_argument('--batch-size',type=int,default=100);r.add_argument('--dry-run',action='store_true')
    sub.add_parser('status')
    sub.add_parser('finalize')
    a=ap.parse_args();root=a.repo_root.resolve()
    if a.command=='initialize': initialize(root);return
    if a.command=='status':
        head=assert_repo(root,True);out,inv,cp,manifest,current=load_state(root)
        print(json.dumps({'head':head,'remote_head':remote_head(root),'completed':len(cp['completed_sha_groups']),'pending':len(cp['pending_sha_groups']),
          'failed':len(cp['failed_groups']),'resume_events':cp['resume_events'],'last_verified_remote_commit':cp.get('last_verified_remote_commit')}));return
    if a.command=='resume':
        if a.batch_size<1 or a.batch_size>100: raise SystemExit('STOP: batch size must be between 1 and 100')
        run_batch(root,a.batch_size,True,a.dry_run);return
    if a.command=='finalize': finalize(root);return

if __name__=='__main__': main()
