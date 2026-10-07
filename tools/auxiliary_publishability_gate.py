#!/usr/bin/env python3
"""Build a strict, non-production safe candidate tree for Warder auxiliary logos."""
from __future__ import annotations
import csv, hashlib, json, shutil, zipfile
from collections import Counter, defaultdict
from io import BytesIO
from pathlib import Path, PurePosixPath
from PIL import Image

BASE=Path('reports/warder-master-production')
RUN=BASE/'auxiliary-ingress-run-2026-10-06'
FAMILY=BASE/'auxiliary-family-policy-2026-10-06'
RECOVERY=BASE/'auxiliary-partial-recovery-2026-10-07/source-recovery'
PARTIAL=BASE/'auxiliary-partial-recovery-2026-10-07/partial-improvements/partial-improved-families.jsonl'
CANDIDATE=Path('/tmp/candidate-output.zip')
OUT=BASE/'auxiliary-publishability-gate-2026-10-07'
TREE=OUT/'safe-candidate-tree'
EXPECTED_CANDIDATE_SIZE=93431686
EXPECTED_CANDIDATE_SHA='5e5bff985638203a2b1c540cd49d37b1893357b20e34d349a4369adb3ac654ff'
ACCEPT={'PASS','AUTO-FIXED'}

def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def lines(path):return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
def member_from_output_path(value):
    if '!' not in value: raise ValueError('invalid candidate output locator: '+value)
    member=value.split('!',1)[1]
    p=PurePosixPath(member)
    if p.is_absolute() or '..' in p.parts: raise ValueError('unsafe archive member path: '+member)
    return str(p)
def png_check(data,expected_sha,identity,variant):
    if sha(data)!=expected_sha: raise ValueError(f'SHA mismatch {identity} {variant}')
    im=Image.open(BytesIO(data)); im.load()
    if im.format!='PNG': raise ValueError(f'not PNG {identity} {variant}')
    if im.size!=(220,132): raise ValueError(f'wrong dimensions {identity} {variant}: {im.size}')
    if im.mode!='RGBA': raise ValueError(f'not RGBA {identity} {variant}: {im.mode}')
    if im.getchannel('A').getbbox() is None: raise ValueError(f'blank alpha {identity} {variant}')
    return {'dimensions':[220,132],'mode':'RGBA','sha256':expected_sha,'byte_count':len(data),'png_validation':'PASS'}

def main():
    zbytes=CANDIDATE.read_bytes()
    if len(zbytes)!=EXPECTED_CANDIDATE_SIZE or sha(zbytes)!=EXPECTED_CANDIDATE_SHA: raise SystemExit('candidate-output.zip size/SHA mismatch')
    z=zipfile.ZipFile(CANDIDATE)
    bad=z.testzip()
    if bad: raise SystemExit('candidate-output.zip CRC failure: '+bad)
    raw=b''.join(p.read_bytes() for p in sorted(RUN.glob('machine-report-*.jsonl')))
    machine=[]
    for line in raw.splitlines():
        try: machine.append(json.loads(line))
        except json.JSONDecodeError: raise SystemExit('broken reconstructed machine report line')
    if len(machine)!=1604: raise SystemExit(f'expected 1604 machine rows, got {len(machine)}')
    identities=[x['stable_identity'] for x in machine]
    if len(set(identities))!=1604: raise SystemExit('duplicate machine identities')
    machine_by_id={x['stable_identity']:x for x in machine}
    family_by_identity={}
    family_records={}
    for name in ('remaining-human-review-*.jsonl','remaining-source-unresolved-*.jsonl'):
        for p in FAMILY.glob(name):
            for row in lines(p):
                fid=row['family_id']; family_records[fid]=row
                for identity in row['member_identities']:
                    if identity in family_by_identity and family_by_identity[identity]!=fid:
                        raise SystemExit('identity appears in multiple exception families: '+identity)
                    family_by_identity[identity]=fid
    unresolved={}
    for p in RECOVERY.glob('black-white-pair-analysis.jsonl'):
        for r in lines(p): unresolved[r['family_id']]=r
    for p in RECOVERY.glob('black-only-analysis.jsonl'):
        for r in lines(p): unresolved[r['family_id']]=r
    partial_by_identity={}
    for row in lines(PARTIAL):
        for identity in row['member_identities']: partial_by_identity[identity]=row

    # Explicit gate. Any failure becomes an exclusion; no warning-only pass.
    publish=[]; excluded=[]
    for row in machine:
        identity=row['stable_identity']; filename=row['identity_filename']; domain=row['domain']
        reasons=[]
        if row.get('source_qc_status')!='PASS': reasons.append(f"source QC {row.get('source_qc_status')}: {row.get('source_qc_reason','')}")
        if row.get('geometry_status')!='PRESERVED_NATIVE_CANVAS': reasons.append(f"geometry {row.get('geometry_status')}: {row.get('geometry_reason','')}")
        if row.get('transparent',{}).get('status')!='PASS': reasons.append(f"transparent {row.get('transparent',{}).get('status')}: {row.get('transparent',{}).get('reason','')}")
        for variant in ('black','white'):
            v=row.get(variant,{})
            if v.get('status') not in ACCEPT: reasons.append(f"{variant.upper()} {v.get('status')}: {v.get('reason','')}")
            if v.get('output_validation')!='PASS': reasons.append(f"{variant.upper()} output QC {v.get('output_validation')}")
        if row.get('final_status') not in ACCEPT: reasons.append(f"final status {row.get('final_status')}")
        if not row.get('source',{}).get('transparent',{}).get('sha256'): reasons.append('transparent source missing')
        if row.get('transparent',{}).get('source_sha256')!=row.get('source',{}).get('transparent',{}).get('sha256'): reasons.append('transparent source SHA provenance mismatch')
        if row.get('transparent',{}).get('output_sha256')!=row.get('source',{}).get('transparent',{}).get('sha256'): reasons.append('transparent output differs from source SHA')
        partial=partial_by_identity.get(identity)
        if partial: reasons.append('PARTIAL-IMPROVED / REVIEW; family is explicitly review-blocked')
        fid=family_by_identity.get(identity)
        if row.get('final_status')=='SOURCE-UNRESOLVED' and not fid: reasons.append('missing source-unresolved family binding')
        if row.get('final_status')=='REVIEW' and not fid: reasons.append('missing review family binding')
        if not reasons:
            if '/' in filename or '\\' in filename or filename in ('','.','..'): reasons.append('unsafe filename path')
        if not reasons:
            files={}
            for variant in ('transparent','black','white'):
                v=row[variant]
                member=member_from_output_path(v['output_path'])
                if member not in z.namelist(): raise SystemExit(f'candidate ZIP member missing: {identity} {variant} {member}')
                data=z.read(member)
                meta=png_check(data,v['output_sha256'],identity,variant)
                if variant=='transparent' and meta['sha256']!=row['source']['transparent']['sha256']:
                    raise SystemExit(f'transparent source/output byte mismatch: {identity}')
                files[variant]={'archive_member':member,'data':data,'meta':meta,'source_sha256':v.get('source_sha256')}
            publish.append({'row':row,'files':files})
            continue
        if row.get('final_status')=='SOURCE-UNRESOLVED': exclusion_class='SOURCE-UNRESOLVED'
        else: exclusion_class='REVIEW-BLOCKED'
        fid=fid or None
        recovery=unresolved.get(fid) if fid else None
        if recovery:
            reasons.append(f"source recovery evidence: {recovery.get('category')}: {recovery.get('evidence',{}).get('reason',recovery.get('evidence',{}).get('reason'))}")
        if row.get('final_status')=='REVIEW':
            reasons.extend([f"BLACK: {row.get('black',{}).get('reason','')}",f"WHITE: {row.get('white',{}).get('reason','')}"])
        excluded.append({'identity':identity,'filename':filename,'domain':domain,'family_id':fid,'exclusion_class':exclusion_class,'exact_reason':'; '.join(dict.fromkeys(x for x in reasons if x)),'variant_status':{v:row.get(v,{}).get('status') for v in ('transparent','black','white')},'source_qc_status':row.get('source_qc_status'),'final_status':row.get('final_status')})

    if len(publish)!=173: raise SystemExit(f'expected exactly 173 publishable identities from accepted machine report, got {len(publish)}')
    if len(excluded)!=1431: raise SystemExit(f'expected exactly 1431 excluded identities, got {len(excluded)}')
    if any(not x['family_id'] for x in excluded): raise SystemExit('excluded identity missing family ID')
    if Counter(x['exclusion_class'] for x in excluded)!=Counter({'REVIEW-BLOCKED':1041,'SOURCE-UNRESOLVED':390}): raise SystemExit('excluded class totals mismatch')
    # Recreate isolated tree so stale files cannot silently remain.
    if TREE.exists(): shutil.rmtree(TREE)
    paths={}; publish_manifest=[]; tree_rows=[]; path_hashes={}
    for item in publish:
        row=item['row']; identity=row['stable_identity']; domain='provider' if row['domain']=='provider-logo' else 'satellite'
        source_prov=json.load(open(RUN/'input-provenance.json'))['assets'][('provider' if domain=='provider' else 'satellite')+'-transparent']
        entry={'identity':identity,'identity_filename':row['identity_filename'],'domain':row['domain'],'family_id':None,'source_sha256':row['source']['transparent']['sha256'],'transparent_sha256':None,'black_sha256':None,'white_sha256':None,'qc_status':{'source_qc':'PASS','geometry':row['geometry_status'],'transparent':'PASS','black':row['black']['status'],'white':row['white']['status'],'output_qc':'PASS'},'provenance':{'source_path':row['source']['transparent']['path'],'source_archive':source_prov['archive'],'source_archive_url':source_prov['url'],'source_archive_sha256':source_prov['sha256_input'],'source_archive_size':source_prov['size_input'],'source_manifest':'FullHDGlass-Warder-Evolution/assets/warder/downloads.json','source_repo':'Evolution-by-Warder/FullHDGlass-Warder-Evolution','source_branch':'main','renderer_commit':'f27d7bbdbf2a49bd9ff9af8baaf85c26abba91f3','candidate_output_archive_sha256':EXPECTED_CANDIDATE_SHA},'output_paths':{}}
        for variant,blob in item['files'].items():
            rel=Path(domain)/variant/row['identity_filename']; dest=TREE/rel; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(blob['data'])
            if dest.is_symlink(): raise SystemExit(f'symlink in generated tree: {dest}')
            actual=sha(dest.read_bytes())
            if actual!=blob['meta']['sha256']: raise SystemExit(f'post-copy SHA mismatch: {dest}')
            entry[variant+'_sha256']=actual; entry['output_paths'][variant]=str(Path('safe-candidate-tree')/rel)
            tree_rows.append({'path':str(Path('safe-candidate-tree')/rel),'identity':identity,'variant':variant.upper(),'sha256':actual,'size_bytes':dest.stat().st_size,'dimensions':[220,132],'mode':'RGBA'})
            key=(domain,variant,row['identity_filename'].casefold())
            if key in paths: raise SystemExit(f'case-insensitive filename collision: {key}')
            paths[key]=identity
            path_hashes[key]=actual
        publish_manifest.append(entry)
    # Exhaustive tree collision/integrity gate.
    found=sorted(p.relative_to(TREE).as_posix() for p in TREE.rglob('*') if p.is_file())
    if len(found)!=173*3: raise SystemExit(f'wrong safe tree file count: {len(found)}')
    if any(p.is_symlink() for p in TREE.rglob('*')): raise SystemExit('symlink found in safe tree')
    if len({x['path'] for x in tree_rows})!=len(tree_rows): raise SystemExit('duplicate tree paths')
    publish_ids={e['identity'] for e in publish_manifest}
    excluded_ids={e['identity'] for e in excluded}
    if publish_ids & excluded_ids: raise SystemExit('review/unresolved identity found in safe tree')
    if len(publish_ids)!=len(publish_manifest) or len(excluded_ids)!=len(excluded): raise SystemExit('duplicate identities in manifest')
    if any(sum(1 for e in publish_manifest if e['output_paths'][v])!=len(publish) for v in ('transparent','black','white')): raise SystemExit('missing variant coverage')
    # Recheck all copied PNGs from disk, not only source archive bytes.
    for r in tree_rows:
        with (OUT/r['path']).open('rb') as f: data=f.read()
        png_check(data,r['sha256'],r['identity'],r['variant'])

    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'publishability-manifest.jsonl').write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in publish_manifest))
    (OUT/'exclusion-manifest.jsonl').write_text(''.join(json.dumps(x,sort_keys=True)+'\n' for x in sorted(excluded,key=lambda x:x['identity'])))
    (OUT/'tree-sha-manifest.json').write_text(json.dumps({'files':tree_rows,'file_count':len(tree_rows),'tree_sha256':sha('\n'.join(f"{x['path']} {x['sha256']}" for x in sorted(tree_rows,key=lambda x:x['path'])).encode())},indent=2,sort_keys=True)+'\n')
    by_domain={}
    for domain,short in [('provider-logo','provider'),('satellite-logo','satellite')]:
        rs=[x for x in machine if x['domain']==domain]
        by_domain[short]={'total_identities':len(rs),'publishable_identities':sum(1 for x in rs if x['final_status'] in ACCEPT and not any(p['row']['stable_identity']==x['stable_identity'] for p in publish)) if False else sum(1 for p in publish if p['row']['domain']==domain),'review_blocked_identities':sum(1 for x in excluded if x['domain']==domain and x['exclusion_class']=='REVIEW-BLOCKED'),'source_unresolved_identities':sum(1 for x in excluded if x['domain']==domain and x['exclusion_class']=='SOURCE-UNRESOLVED'),'publishable_variant_files':{v:sum(1 for p in publish if p['row']['domain']==domain) for v in ('transparent','black','white')},'source_variant_statuses':{v:dict(Counter(x.get(v,{}).get('status','MISSING') for x in rs)) for v in ('transparent','black','white')}}
    qc={'status':'PASS','safe_tree_root':str(TREE),'total_complete_triads':len(publish),'publishable_file_count':len(tree_rows),'review_or_unresolved_files_present':int(bool(publish_ids & excluded_ids)),'review_or_unresolved_identities_in_tree':len(publish_ids & excluded_ids),'duplicate_identities':len(publish_manifest)-len(publish_ids),'duplicate_filenames':len(paths)-len(set(paths)),'case_only_filename_collisions':0,'conflicting_hashes':0,'missing_variants':0,'invalid_png':0,'wrong_dimensions':0,'non_rgba_png':0,'symlinks':0,'all_dimensions':'220x132','all_modes':'RGBA','candidate_zip_sha256':EXPECTED_CANDIDATE_SHA}
    summary={'checkpoint':'ee83ac12cd26b72c3020f5fa9e0539f21f9a8758','provider':by_domain['provider'],'satellite':by_domain['satellite'],'total_publishable_complete_triads':len(publish),'total_publishable_files':len(tree_rows),'total_excluded':len(excluded),'excluded_classes':dict(Counter(x['exclusion_class'] for x in excluded)),'safe_tree_qc':qc,'production_changed':False,'test202':'NOT BUILT'}
    (OUT/'qc-summary.json').write_text(json.dumps(qc,indent=2,sort_keys=True)+'\n')
    (OUT/'provenance-summary.json').write_text(json.dumps({'machine_report_source':str(RUN),'candidate_output_archive':str(CANDIDATE),'candidate_output_archive_size':len(zbytes),'candidate_output_archive_sha256':EXPECTED_CANDIDATE_SHA,'source_repo':'Evolution-by-Warder/FullHDGlass-Warder-Evolution','source_branch':'main','renderer_commit':'f27d7bbdbf2a49bd9ff9af8baaf85c26abba91f3','templates':{'black':'61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe','white':'c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589'}},indent=2,sort_keys=True)+'\n')
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print(json.dumps(summary,indent=2,sort_keys=True))
if __name__=='__main__':main()
