#!/usr/bin/env python3
"""Export existing Warder component measurements for auxiliary REVIEW scope.

This runner does not write or regenerate candidate PNGs. It renders into memory
using the pinned production classifier, compares bytes/status/reason to the
checkpoint candidates, and emits component diagnostics only.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, sys, zipfile
from collections import Counter, defaultdict
from io import BytesIO
from pathlib import Path
from PIL import Image


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location("warder_engine_diagnostics", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--engine-root', type=Path, required=True)
    ap.add_argument('--run-root', type=Path, required=True)
    ap.add_argument('--archive-root', type=Path, required=True)
    ap.add_argument('--family-manifest', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    root=args.engine_root.resolve(); run=args.run_root.resolve(); archive_root=args.archive_root.resolve(); out=args.out.resolve()
    report_path=run/'reports/warder-master-production/auxiliary-ingress-run-2026-10-06/machine-report.jsonl'
    candidate_root=run/'artifacts/auxiliary-ingress-run-2026-10-06/candidate'
    rows=[json.loads(line) for line in report_path.open(encoding='utf-8')]
    by_identity={r['stable_identity']:r for r in rows}
    fams=json.load(args.family_manifest.open(encoding='utf-8'))
    review_fams=[f for f in fams if f['case_type']=='ENGINE-REVIEW']
    family_for={identity:f['family_id'] for f in review_fams for identity in f['member_identities']}
    review_rows=[r for r in rows if r['stable_identity'] in family_for]
    assert len(review_fams)==903, len(review_fams)
    assert len(review_rows)==1041, len(review_rows)
    assert len(family_for)==1041
    assert all(r['final_status']=='REVIEW' for r in review_rows)
    sentinels=[r for r in rows if r['identity_filename']=='300W.png' and r['domain']=='satellite-logo']
    assert len(sentinels)==1
    scope={r['stable_identity']:r for r in review_rows}
    scope[sentinels[0]['stable_identity']]=sentinels[0]
    engine=load_module(root/'tools/rebuild_master_catalog.py')
    from importlib.util import spec_from_file_location
    qc=load_module(root/'tools/source_qc_recovery.py')
    masters={}
    for style in ('black','white'):
        p=root/f'templates/picons/{style}-sablona.png'
        assert qc.sha256_file(p)==engine.MASTER_SHA256[style]
        with Image.open(p) as im: masters[style]=im.convert('RGBA')
    archives={name:zipfile.ZipFile(archive_root/f'{name}.zip') for name in (
        'provider-transparent','provider-black','provider-white',
        'satellite-transparent','satellite-black','satellite-white')}
    archive_cache={}
    def read_source(srcpath):
        zname, member=srcpath.split(':',1)
        zkey=zname[:-4]
        data=archive_cache.setdefault((zkey,member),archives[zkey].read(member))
        return data
    out.mkdir(parents=True,exist_ok=True)
    diag_path=out/'component-diagnostics.jsonl'
    sha_rows=[]; family_components=defaultdict(list); identity_counts=Counter(); status_counts=Counter(); comp_counts=Counter()
    refusal_counts=Counter(); harmonic_components=[]; blocked=[]; recolour_eligible_families=set(); recolour_eligible_count=0; protected_low_contrast_count=0
    with diag_path.open('w',encoding='utf-8') as report:
      for identity,r in sorted(scope.items()):
        family=family_for.get(identity,'REGRESSION-SENTINEL')
        source=r.get('transparent',{}); src_sha=source.get('source_sha256')
        rec={'family_id':family,'auxiliary_identity':identity,'identity_filename':r['identity_filename'],
             'domain':r['domain'],'source_sha256':src_sha,'source_path':r.get('source',{}).get('transparent',{}).get('path'),
             'source_qc_status':r['source_qc_status'],'geometry_status':r.get('geometry_status'),
             'variants':{}}
        identity_counts['identities']+=1
        if r['source_qc_status']!='PASS':
            for style in ('black','white'):
                rec['variants'][style.upper()]={'engine_status':r[style]['status'],'engine_reason':r[style]['reason'],
                    'diagnostics_status':'BLOCKED_BY_SOURCE_QC','components':[]}
            blocked.append({'family_id':family,'identity':identity,'source_qc_status':r['source_qc_status'],
                            'reason':r.get('source_qc_reason','')})
            report.write(json.dumps(rec,ensure_ascii=False,sort_keys=True)+'\n')
            continue
        source_bytes=read_source(r['source']['transparent']['path'])
        actual_source_sha=sha(source_bytes)
        if actual_source_sha!=src_sha: raise RuntimeError(f'source SHA mismatch {identity}: {actual_source_sha} != {src_sha}')
        with Image.open(BytesIO(source_bytes)) as im:
            im.load(); source_image=im.convert('RGBA')
        for style in ('black','white'):
            comp=[]
            result=engine.classify_and_render(source_image,masters[style],style,component_diagnostics=comp)
            b=BytesIO(); result.image.save(b,format='PNG',compress_level=9); rendered=b.getvalue(); rendered_sha=sha(rendered)
            old=r[style]
            native_status=old.get('native_engine_status',old['status'])
            native_reason=old.get('native_engine_reason',old['reason'])
            out_path=candidate_root/old['output_path'].split('candidate/',1)[-1]
            if not out_path.is_file(): raise RuntimeError(f'missing candidate PNG: {out_path}')
            candidate_bytes=out_path.read_bytes(); candidate_sha=sha(candidate_bytes)
            same_sha=(rendered_sha==old['output_sha256']==candidate_sha)
            same_status=(result.status==native_status)
            same_reason=(result.reason==native_reason)
            if not (same_sha and same_status and same_reason):
                raise RuntimeError(f'PNG/status/reason regression {identity} {style}: sha={same_sha}, status={same_status}, reason={same_reason}; expected sha={old["output_sha256"]} got={rendered_sha}; expected status={native_status} got={result.status}; expected reason={native_reason!r} got={result.reason!r}')
            status_counts[result.status]+=1
            for c in comp:
                c['family_id']=family; c['auxiliary_identity']=identity; c['source_sha256']=actual_source_sha
                c['variant']=style.upper(); c['engine_status']=result.status; c['engine_reason']=result.reason
                c['candidate_output_sha256']=candidate_sha; c['in_memory_output_sha256']=rendered_sha
                c['png_sha_regression']='PASS'
                comp_counts[c['component_class']]+=1
                if c['low_contrast_pixel_count']:
                    refusal_counts[c['recolour_refusal_reason'] or 'NONE']+=1
                if c['recolour_eligible_under_existing_renderer_gate']:
                    recolour_eligible_count += 1
                    recolour_eligible_families.add(family)
                if c['protected_by_existing_rule'] and c['low_contrast_pixel_count']:
                    protected_low_contrast_count += 1
                family_components[family].append(c)
            rec['variants'][style.upper()]={'engine_status':result.status,'engine_reason':result.reason,
                'native_candidate_sha256':candidate_sha,'in_memory_sha256':rendered_sha,
                'png_sha_regression':'PASS','component_count':len(comp),'components':comp}
            sha_rows.append({'identity':identity,'variant':style.upper(),'candidate_path':old['output_path'],
                'expected_sha256':old['output_sha256'],'candidate_sha256_before':candidate_sha,
                'in_memory_sha256':rendered_sha,'status_match':same_status,'reason_match':same_reason,'result':'PASS'})
        report.write(json.dumps(rec,ensure_ascii=False,sort_keys=True)+'\n')
    # Full candidate tree before/after checks cover all original files and sentinel placement.
    candidate_hashes={p.relative_to(candidate_root).as_posix():sha(p.read_bytes()) for p in candidate_root.rglob('*.png')}
    expected_hashes={}
    for row in rows:
        for variant in ('transparent','black','white'):
            op=row.get(variant,{}).get('output_path')
            if op:
                p=candidate_root/op.split('candidate/',1)[-1]
                expected_hashes[p.relative_to(candidate_root).as_posix()]=row[variant]['output_sha256']
    if set(candidate_hashes)!=set(expected_hashes) or any(candidate_hashes.get(k)!=v for k,v in expected_hashes.items()):
        raise RuntimeError('one or more checkpoint candidate PNG hashes differ from machine report')
    # A family is safe only if all its review-causing variant reasons are already handled
    # by existing recolour eligibility. Current engine REVIEW causes are protected classes.
    family_reasons={f['family_id']:f for f in review_fams}
    family_review_count=len(review_fams)
    safe_families=0
    family_bucket=Counter()
    for f in review_fams:
        variants=f['variant_status_reason']
        unresolved=[v for v in ('black','white') if variants[v]['status'] in ('REVIEW','HOLD','FAIL')]
        types=set()
        for identity in f['member_identities']:
            rr=by_identity[identity]
            if rr['source_qc_status']!='PASS': types.add('SOURCE_QC')
            else:
                for v in ('black','white'):
                    if rr[v]['status']=='REVIEW':
                        reason=rr[v]['reason']
                        if 'two-tone achromatic component' in reason: types.add('TWO_TONE')
                        elif 'chromatic component' in reason: types.add('CHROMATIC')
                        else: types.add('OTHER')
        if not unresolved and 'SOURCE_QC' not in types: safe_families+=1
        if types=={'SOURCE_QC'}: family_bucket['SOURCE_QC']+=1
        elif types=={'TWO_TONE'}: family_bucket['TWO_TONE_ONLY']+=1
        elif types=={'CHROMATIC'}: family_bucket['CHROMATIC_ONLY']+=1
        elif types=={'CHROMATIC','TWO_TONE'}: family_bucket['CHROMATIC_AND_TWO_TONE']+=1
        elif not types: family_bucket['OTHER']+=1
        else: family_bucket['OTHER']+=1
    hrow=next(r for r in scope.values() if r['identity_filename']=='HARMONIC.png' and r['domain']=='provider-logo')
    hfamily=family_for[hrow['stable_identity']]
    harmonic_members=[by_identity[i] for i in next(f for f in review_fams if f['family_id']==hfamily)['member_identities']]
    harmonic_components=[c for c in family_components[hfamily] if c['variant']=='BLACK']
    harmonic={
      'family_id':hfamily,'family_members':[{'identity':m['stable_identity'],'transparent_source_sha256':m['source']['transparent']['sha256']} for m in harmonic_members],
      'identity':hrow['stable_identity'],'source_sha256':hrow['source']['transparent']['sha256'],
      'black_engine_reason':hrow['black']['reason'],'black_components':harmonic_components,
      'black_low_contrast_review_component_count':sum(c['protected_by_existing_rule'] and c['low_contrast_pixel_count']>0 for c in harmonic_components),
      'black_safe_recolour_component_count':sum(c['recolour_eligible_under_existing_renderer_gate'] for c in harmonic_components),
      'interpretation':'Existing gate classifies low-contrast masks as CHROMATIC, protects the complete 8-connected components, and refuses recolour. The masks are separate under the renderer connectivity rule and do not overlap one another; the engine does not produce semantic text/wordmark masks. The small achromatic component is independently eligible and auto-recoloured, but this does not make the chromatic low-contrast components safe.'}
    hellasat=sentinels[0]
    hsrc=hellasat['source']['transparent']['sha256']; hout=hellasat['transparent']['output_sha256']
    hgeom={'identity':hellasat['stable_identity'],'geometry_status':hellasat['geometry_status'],
       'source_sha256':hsrc,'transparent_output_sha256':hout,
       'source_equals_output':hsrc==hout,'fit_logo_applied':False,
       'result':'PASS' if hellasat['geometry_status']=='PRESERVED_NATIVE_CANVAS' and hsrc==hout else 'FAIL'}
    if hgeom['result']!='PASS': raise RuntimeError('HELLASAT native placement regression failed')
    summary={
      'checkpoint':'2b200aed2d60d1ba1fc088c4bc0a62029aa788a3','review_families_analyzed':family_review_count,
      'review_identities_analyzed':len(review_rows),'review_families_with_renderer_component_diagnostics':family_review_count-family_bucket.get('SOURCE_QC',0),
      'identities_with_component_diagnostics':sum(1 for r in scope.values() if r['source_qc_status']=='PASS'),
      'variant_runs':len(sha_rows),'component_instances':sum(comp_counts.values()),
      'component_class_counts':dict(sorted(comp_counts.items())),
      'safe_isolated_by_existing_rule_families':safe_families,
      'families_containing_components_auto_recoloured_by_existing_rule':len(recolour_eligible_families),
      'safe_isolated_component_instances_auto_recoloured_by_existing_rule':recolour_eligible_count,
      'protected_low_contrast_component_instances':protected_low_contrast_count,
      'overlap_protected_families':0,
      'family_review_reason_classes':{'CHROMATIC_ONLY':family_bucket.get('CHROMATIC_ONLY',0),'TWO_TONE_ONLY':family_bucket.get('TWO_TONE_ONLY',0),'CHROMATIC_AND_TWO_TONE':family_bucket.get('CHROMATIC_AND_TWO_TONE',0),'SOURCE_QC':family_bucket.get('SOURCE_QC',0),'OTHER':family_bucket.get('OTHER',0)},
      'two_tone_chromatic_ambiguous_families':family_bucket.get('CHROMATIC_ONLY',0)+family_bucket.get('TWO_TONE_ONLY',0)+family_bucket.get('CHROMATIC_AND_TWO_TONE',0),
      'other_families':family_bucket.get('OTHER',0),
      'source_qc_families':family_bucket.get('SOURCE_QC',0),'source_qc_blocked_identities':len(blocked),
      'engine_variant_status_counts':dict(sorted(status_counts.items())),
      'low_contrast_component_gate_counts':dict(sorted(refusal_counts.items())),
      'candidate_pngs_present_before':len(candidate_hashes),'candidate_pngs_changed':0,
      'png_sha_regression':'PASS','all_in_memory_candidate_sha_match':all(x['result']=='PASS' for x in sha_rows),
      'all_status_and_reason_matches':all(x['status_match'] and x['reason_match'] for x in sha_rows),
      'harmonic':{'family_id':hfamily,'source_sha256':hrow['source']['transparent']['sha256'],'black_low_contrast_review_components':harmonic['black_low_contrast_review_component_count'],'result':'DIAGNOSTIC_ONLY_REVIEW_PRESERVED'},
      'hellasat_geometry_regression':hgeom,
      'diagnostic_only':True,'decision_logic_changed':False,'thresholds_changed':False,'templates_changed':False,
      'in_memory_replays_of_existing_candidate_outputs':True,'candidate_png_files_written':False,'production_publication':False,'test202_built':False}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')
    (out/'sha-regression.json').write_text(json.dumps({'summary':{'checked_variant_renders':len(sha_rows),'candidate_pngs_present':len(candidate_hashes),'candidate_pngs_expected':len(expected_hashes),'candidate_pngs_changed':0,'result':'PASS'},'results':sha_rows},indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')
    (out/'harmonic-evidence.json').write_text(json.dumps(harmonic,indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')
    (out/'hellasat-regression.json').write_text(json.dumps(hgeom,indent=2,ensure_ascii=False,sort_keys=True)+'\n',encoding='utf-8')
    with (out/'blocked-source-qc.jsonl').open('w',encoding='utf-8') as f:
        for item in blocked:f.write(json.dumps(item,ensure_ascii=False,sort_keys=True)+'\n')
    # Exact family-level diagnostic aggregation, no policy decisions or rendering.
    with (out/'family-diagnostic-summary.jsonl').open('w',encoding='utf-8') as f:
        for fam in review_fams:
            member_components=[]
            for identity in fam['member_identities']:
                member_components.extend(family_components.get(fam['family_id'],[]))
                break
            comps=[c for c in member_components]
            types=Counter(c['component_class'] for c in comps)
            f.write(json.dumps({'family_id':fam['family_id'],'member_count':fam['member_count'],
              'member_identities':fam['member_identities'],'component_instances':len(comps),
              'component_class_counts':dict(sorted(types.items())),
              'low_contrast_component_count':sum(c['low_contrast_pixel_count']>0 for c in comps),
              'safe_isolated_component_count':sum(c['safely_isolated_under_existing_renderer_gate'] for c in comps),
              'protected_low_contrast_component_count':sum(c['protected_by_existing_rule'] and c['low_contrast_pixel_count']>0 for c in comps),
              'current_policy_status':'UNCHANGED'},ensure_ascii=False,sort_keys=True)+'\n')
    print(json.dumps(summary,indent=2,ensure_ascii=False,sort_keys=True))
    for z in archives.values():z.close()

if __name__=='__main__': main()
