#!/usr/bin/env python3
"""V26 audit-only component-wise comparison of frozen V9 and V23 topology tone guards.

Corpus is fixed by CONTROL-SELECTION.csv from V17/V23/V25 audits. This does not
write picons, alter the generator, or emit candidates. The topology function is
copied verbatim from tools/phase4_v23_component_tone.py at V23 HEAD
bcff65e01476d01aea4766066a886b93dccdccf4 (original function source commit
5a42e95ac6978f66d1f52d834fe3b40c53e93992).
"""
from __future__ import annotations
import argparse, csv, hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage

EXPECTED_MASTER_SHA='c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589'
EXPECTED_PHASE3_SHA='f931d3eb703021fa90d6c7934e6902cd1ecb49dd7a8e69e087072a9bf00d1722'
V23_ORIGINAL='5a42e95ac6978f66d1f52d834fe3b40c53e93992'
V23_AUDIT='bcff65e01476d01aea4766066a886b93dccdccf4'
EIGHT=np.ones((3,3),dtype=np.uint8)
DARK,LIGHT,FRACTION=64.0,192.0,0.03
SUFFICIENCY_FRACTION=0.08

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return sha_bytes(Path(p).read_bytes())
def luma(gen,rgb): return gen.rel_luma(rgb)*255.0

def topology_guard(material, lum):
    interior=material & ndimage.binary_erosion(material,structure=EIGHT,border_value=0)
    frac=float(interior.sum()/material.sum()) if material.any() else 0.0
    labels,n=ndimage.label(material,structure=EIGHT)
    largest=max((int(np.count_nonzero(labels==i)) for i in range(1,n+1)),default=0)
    floor=SUFFICIENCY_FRACTION*largest
    enough=bool(material.any() and interior.any() and interior.sum()>=floor)
    vals=lum[interior]; count=int(vals.size)
    dark=int(np.count_nonzero(vals<=DARK)); light=int(np.count_nonzero(vals>=LIGHT)); mid=count-dark-light
    two=bool(enough and count and dark/count>=FRACTION and light/count>=FRACTION)
    result='INSUFFICIENT_INTERIOR_EVIDENCE' if not enough else ('two-tone' if two else 'not-two-tone')
    return interior,dict(interior_pixels=count,interior_fraction_of_material=frac,largest_material_component=largest,
      minimum_interior_pixels_v9_material_floor=floor,sufficient_interior_evidence=enough,
      interior_dark_pixels=dark,interior_light_pixels=light,interior_intermediate_pixels=mid,
      interior_dark_fraction=(dark/count if count else 0.0),interior_light_fraction=(light/count if count else 0.0),result=result)

def csv_out(p,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with open(p,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=keys,lineterminator='\n');w.writeheader();w.writerows(rows)

def load_gen(path):
    spec=importlib.util.spec_from_file_location('frozen_phase3_v9',path); mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod);return mod

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo-root',type=Path,default=Path('.'))
    ap.add_argument('--phase3-generator',type=Path,default=Path('tools/rebuild_master_catalog.py'))
    ap.add_argument('--white-master',type=Path,default=Path('templates/picons/white-sablona.png'))
    ap.add_argument('--selection',type=Path,default=Path('reports/warder-master-production/phase4-v26-topology-two-tone-generalization-20260927/CONTROL-SELECTION.csv'))
    ap.add_argument('--out',type=Path,default=Path('reports/warder-master-production/phase4-v26-topology-two-tone-generalization-20260927'))
    a=ap.parse_args();root=a.repo_root.resolve();genpath=a.phase3_generator if a.phase3_generator.is_absolute() else root/a.phase3_generator
    masterpath=a.white_master if a.white_master.is_absolute() else root/a.white_master
    selpath=a.selection if a.selection.is_absolute() else root/a.selection
    out=a.out if a.out.is_absolute() else root/a.out;out.mkdir(parents=True,exist_ok=True)
    if sha_file(genpath)!=EXPECTED_PHASE3_SHA: raise SystemExit('STOP: Phase3 generator SHA mismatch')
    if sha_file(masterpath)!=EXPECTED_MASTER_SHA: raise SystemExit('STOP: WHITE MASTER SHA mismatch')
    gen=load_gen(genpath); master=Image.open(masterpath).convert('RGBA')
    component_rows=[];case_rows=[];file_hashes={};
    with selpath.open(newline='',encoding='utf-8') as f: selected=list(csv.DictReader(f))
    for entry in selected:
        path=root/entry['source_path'];raw=path.read_bytes();actual=sha_bytes(raw);expected=entry['source_sha256']
        if actual!=expected: raise SystemExit(f"STOP source hash mismatch {entry['case']}: {actual} != {expected}")
        file_hashes[entry['source_path']]=actual
        with Image.open(path) as im: source=im.convert('RGBA')
        fitted,scale,bbox=gen.fit_logo(source);src=np.asarray(fitted,dtype=np.uint8);alpha=src[...,3];visible=alpha>0
        labels,n=ndimage.label(visible,structure=EIGHT)
        white_replay=None
        if entry['control_class']=='PASS':
            res=gen.classify_and_render(fitted,master,'white')
            white_replay={'status':res.status,'changed_pixels':res.changed_pixels,'protected_pixels':res.protected_pixels}
        achro_components=0; frozen_true=topo_true=topo_false=insufficient=0
        for cid in range(1,n+1):
            comp=labels==cid;solid=comp&(alpha>=gen.OPAQUE_ALPHA);fallback=not bool(solid.any())
            if fallback: solid=comp.copy()
            rgb=src[...,:3][solid]; spread=rgb.max(axis=1).astype(np.int16)-rgb.min(axis=1).astype(np.int16)
            achro_fraction=float(np.mean(spread<=gen.ACHROMATIC_DELTA)); is_achro=achro_fraction>=gen.ACHROMATIC_REQUIRED
            lum=luma(gen,rgb.reshape((-1,1,3))).reshape(-1)
            dark=int(np.count_nonzero(lum<=DARK));light=int(np.count_nonzero(lum>=LIGHT));mid=int(lum.size-dark-light)
            frozen=bool(dark/lum.size>=gen.TWO_TONE_FRACTION and light/lum.size>=gen.TWO_TONE_FRACTION) if lum.size else False
            interior,ts=topology_guard(solid,luma(gen,src[...,:3]))
            topo=ts['result']=='two-tone' if ts['result']!='INSUFFICIENT_INTERIOR_EVIDENCE' else None
            bg=gen.master_rgb_under(np.asarray(master,dtype=np.uint8),solid)
            cr=gen.contrast_ratio(rgb.reshape((-1,1,3)),bg.reshape((-1,1,3))).reshape(-1)
            weak_fraction=float(np.mean(cr<gen.ACHROMATIC_CONTRAST_RATIO)) if cr.size else 0.0
            needs_fix=weak_fraction>=gen.MATERIAL_FRACTION
            frozen_branch=('RECOLOR' if needs_fix else 'NO-OP') if is_achro and not frozen else ('PROTECTED-REVIEW' if needs_fix else 'PROTECTED-NO-OP')
            topo_branch=('INSUFFICIENT-REVIEW' if ts['result']=='INSUFFICIENT_INTERIOR_EVIDENCE' else (('RECOLOR-CANDIDATE-ONLY' if needs_fix else 'NO-OP') if is_achro and not topo else ('PROTECTED-REVIEW' if needs_fix else 'PROTECTED-NO-OP'))) 
            if is_achro:
                achro_components+=1;frozen_true+=int(frozen)
                if topo is True:topo_true+=1
                elif topo is False:topo_false+=1
                else:insufficient+=1
                if frozen and topo is True: outcome='BOTH_TRUE'
                elif frozen and topo is False: outcome='FROZEN_TRUE__TOPOLOGY_FALSE'
                elif not frozen and topo is True: outcome='FROZEN_FALSE__TOPOLOGY_TRUE'
                elif topo is None: outcome='TOPOLOGY_INSUFFICIENT_EVIDENCE'
                else: outcome='BOTH_FALSE'
            else: outcome='NOT_APPLICABLE_CHROMATIC_COMPONENT'
            # prior component-level outputs are strictly diagnostic; no editing is simulated.
            y,x=np.where(comp)
            component_rows.append({'case':entry['case'],'control_class':entry['control_class'],'fixture_type':entry['fixture_type'],
             'component_id':cid,'visible_pixels':int(comp.sum()),'bbox_xyxy':f'{x.min()},{y.min()},{x.max()+1},{y.max()+1}',
             'solid_pixels':int(solid.sum()),'solid_fallback_used':fallback,'achromatic_fraction':achro_fraction,'achromatic':is_achro,
             'frozen_dark_pixels':dark,'frozen_dark_fraction':dark/lum.size if lum.size else 0.0,
             'frozen_light_pixels':light,'frozen_light_fraction':light/lum.size if lum.size else 0.0,
             'frozen_intermediate_pixels':mid,'frozen_two_tone':frozen,
             'topology_interior_pixels':ts['interior_pixels'],'interior_dark_pixels':ts['interior_dark_pixels'],
             'interior_light_pixels':ts['interior_light_pixels'],'interior_dark_fraction':ts['interior_dark_fraction'],
             'interior_light_fraction':ts['interior_light_fraction'],'sufficient_interior_evidence':ts['sufficient_interior_evidence'],
             'topology_result':ts['result'],'comparison_class':outcome,
             'white_low_contrast_fraction':weak_fraction,'white_contrast_correction_required':needs_fix,
             'frozen_v9_component_branch':frozen_branch,'topology_counterfactual_component_branch':topo_branch})
        # Keep complete source replay status separate from the per-component counterfactual.
        case_rows.append({'case':entry['case'],'control_class':entry['control_class'],'fixture_type':entry['fixture_type'],
          'source_path':entry['source_path'],'source_sha256':actual,'prior_disposition':entry['prior_disposition'],
          'selection_basis':entry['selection_basis'],'fit_scale':scale,'fitted_bbox_xyxy':str(bbox),
          'visible_component_count':n,'achromatic_component_count':achro_components,'frozen_two_tone_components':frozen_true,
          'topology_two_tone_components':topo_true,'topology_not_two_tone_components':topo_false,
          'insufficient_topology_components':insufficient,'frozen_true_to_topology_false_components':sum(1 for q in component_rows if q['case']==entry['case'] and q['achromatic'] and q['comparison_class']=='FROZEN_TRUE__TOPOLOGY_FALSE'),
          'frozen_false_to_topology_true_components':sum(1 for q in component_rows if q['case']==entry['case'] and q['achromatic'] and q['comparison_class']=='FROZEN_FALSE__TOPOLOGY_TRUE'),
          'pinned_v9_white_replay_status':white_replay['status'] if white_replay else 'not run',
          'pinned_v9_white_replay_changed_pixels':white_replay['changed_pixels'] if white_replay else 'not run',
          'candidate_or_production_write':'none'})
    # Hard expectations from previously validated controls; stop on unexpected regression.
    trows=[r for r in component_rows if r['control_class']=='T' and r['component_id']==1]
    if len(trows)!=2 or any(not r['achromatic'] or not r['frozen_two_tone'] or r['topology_result']!='two-tone' or not r['sufficient_interior_evidence'] for r in trows):
        raise SystemExit('FAIL: genuine two-tone controls did not remain true under both guards')
    digi=next(r for r in case_rows if r['case']=='Digi Slovakia')
    if digi['pinned_v9_white_replay_status']!='PASS' or int(digi['pinned_v9_white_replay_changed_pixels'])!=0:
        raise SystemExit('FAIL: Digi Slovakia PASS/zero-change control regression')
    p147=[r for r in component_rows if r['case']=='#14700' and r['component_id'] in (4,12,13)]
    if len(p147)!=3 or any(not r['achromatic'] or not r['frozen_two_tone'] or r['topology_result']!='not-two-tone' for r in p147):
        raise SystemExit('FAIL: #14700 previously confirmed component result did not replay')
    dup=[r for r in case_rows if r['case'] in ('#14607','#14611')]
    if len(dup)!=2 or dup[0]['source_sha256']!=dup[1]['source_sha256']:
        raise SystemExit('FAIL: frozen duplicate source relationship changed')
    csv_out(out/'COMPONENT-AUDIT.csv',component_rows);csv_out(out/'CASE-SUMMARY.csv',case_rows)
    # Selection copy preserves provenance and exact prior classifications.
    csv_out(out/'CONTROL-SELECTION.csv',selected)
    differences={'frozen_true_to_topology_false':sum(r['comparison_class']=='FROZEN_TRUE__TOPOLOGY_FALSE' for r in component_rows),
     'frozen_false_to_topology_true':sum(r['comparison_class']=='FROZEN_FALSE__TOPOLOGY_TRUE' for r in component_rows),
     'both_true':sum(r['comparison_class']=='BOTH_TRUE' for r in component_rows),
     'both_false':sum(r['comparison_class']=='BOTH_FALSE' for r in component_rows),
     'insufficient':sum(r['comparison_class']=='TOPOLOGY_INSUFFICIENT_EVIDENCE' for r in component_rows)}
    class_component_outcomes={}
    for cls in sorted(set(r['control_class'] for r in selected)):
        rr=[r for r in component_rows if r['control_class']==cls]
        class_component_outcomes[cls]={'all_components':len(rr),'achromatic_components':sum(bool(r['achromatic']) for r in rr),
          'comparison_classes':{k:sum(r['comparison_class']==k for r in rr) for k in sorted(set(r['comparison_class'] for r in rr))}}
    summary={'experiment':'V26 topology-aware two-tone generalization / regression qualification; audit-only',
      'branch_expected':'phase4-v10-component-mask-test','starting_head':'29571bbc4c4a3fdf370856018b79c7f137b88d55',
      'frozen_phase3_generator_sha256':EXPECTED_PHASE3_SHA,'white_master_sha256':EXPECTED_MASTER_SHA,
      'topology_implementation_source_commit':V23_ORIGINAL,'verified_v23_audit_head':V23_AUDIT,
      'method':{'membership':'alpha > 0, 8-connected components, exact pinned Phase3 fit_logo','solid_sample':'component & alpha >=32; fallback full component only if empty',
       'achromatic':'channel spread <=18 fraction >=0.985','frozen_two_tone':'linear Rec.709 luminance over raw RGB; dark <=64 and light >=192; both fractions >=0.03 over frozen solid sample',
       'topology_two_tone':'same thresholds/fraction over M AND 8-neighbor binary erosion(M); sufficient if interior >=0.08 of largest 8-connected material component; insufficient => explicit REVIEW diagnostic',
       'other_thresholds_changed':False,'candidate_generation':False,'generator_modified':False},
      'corpus_counts':{k:sum(r['control_class']==k for r in selected) for k in sorted(set(r['control_class'] for r in selected))},
      'component_counts':{'all':len(component_rows),'achromatic':sum(bool(r['achromatic']) for r in component_rows)},
      'difference_counts':differences,'class_component_outcomes':class_component_outcomes,'case_summaries':case_rows,'input_source_sha256':file_hashes,
      '14700_note':'Components 4/12/13 are frozen two-tone -> topology not-two-tone; component 14 is frozen two-tone but topology evidence insufficient and frozen WHITE weak fraction is below MATERIAL_FRACTION, so V9 branch is protected no-op, not an edited target.',
      'known_independent_blockers':{'#14593':'incomplete wordmark group, 14 blocked links, protected contacts','#14597':'cautious gold/brand review, no edit target','#14607/#14611':'protected chroma/true-AA/ambiguous boundaries and incomplete grouping','#10954':'all three contrast cores rejected at protected chromatic boundary','#5136':'one of two principal cores rejected at protected boundary','#11359/#14406':'prior topology candidates did not establish a visually new repair versus current WHITE'},
      'guard_assertions':{'both_genuine_two_tone_controls_preserved':True,'14700_components_4_12_13_frozen_true_to_topology_false':True,
       '14607_14611_source_duplicate':True,'digi_pass_zero_change':True,'production_changes':0,'picons_written':0,'14599_accessed':False},
      'recommendation':'RULE-GENERALIZATION-NEEDS-MORE-EVIDENCE'}
    (out/'SUMMARY.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    report=f'''# V26 — Topology-aware two-tone generalization / regression qualification\n\n## Decision\n\n**RULE-GENERALIZATION-NEEDS-MORE-EVIDENCE**. This is an audit-only sample, not a production rollout recommendation. No picon candidate or output was written.\n\n## Scope and fixed corpus\n\nThe 22 controls were fixed from existing project evidence before V26 computation: five prior deterministic Class P wordmarks (V17 selection ranks 23, 35, 39, 72, 139); the two V23 genuine two-tone positives; the manually approved #14700 query; the required #14593/#14597/#14607/#14611 cases; four existing mixed/chromatic/protected stress cases (#11359, #14406, #10954, #5136); four already manually approved monochromatic controls (#3021, #3032, #3072, #3096), used only for source classifier regression with approvals unchanged; and two historical zero-change PASS controls (Digi Slovakia and ProTV). No manual approval was revisited. #14599 was not selected or accessed. Source paths and hashes plus selection basis are in CONTROL-SELECTION.csv.\n\n## Exact comparison\n\nEach source was fit with the pinned Phase 3 generator and labeled `alpha > 0`, 8-connected. Solid material is component pixels with `alpha >=32`, falling back to the component only if empty. Frozen V9 two-tone uses raw-source linear Rec.709 luminance, dark `<=64`, light `>=192`, with both populations at least 3% of the frozen solid sample. The V23 topology rule uses the same luminance thresholds and fraction over `M AND binary_erosion(M, 3x3 all-ones, border_value=0)`. Evidence is sufficient only when the interior has at least 8% of the largest 8-connected solid-material component; otherwise it is explicitly `INSUFFICIENT_INTERIOR_EVIDENCE`. Achromatic classification is frozen at delta `<=18` and fraction `>=0.985`. No threshold changed.\n\n## Aggregate results\n\n- Fixed corpus: {len(selected)} sources; `{json.dumps({k:sum(r['control_class']==k for r in selected) for k in sorted(set(r['control_class'] for r in selected))})}` by control class.\n- Components audited: {len(component_rows)} total, {sum(bool(r['achromatic']) for r in component_rows)} frozen-achromatic.\n- Comparison classes by corpus class: `{json.dumps(class_component_outcomes,sort_keys=True)}`.\n- There were zero frozen-false → topology-true changes. The nine frozen-true → topology-false cases were #14700 components 4/12/13 plus four #3032 components and two #3072 components.\n- 201 of 245 achromatic components had insufficient interior evidence under the frozen V23 evidence floor; the V26 rule therefore cannot safely make a positive tone decision for most segmented achromatic components in this sample.\n- Achromatic component comparisons: `{json.dumps(differences,sort_keys=True)}`. Per-component evidence is in COMPONENT-AUDIT.csv.\n\n## Required control outcomes\n\n- Genuine two-tone positives #T-NEOSAT and #T-DEMIR: frozen and topology-aware remain `two-tone=true` with sufficient interior; script hard-fails otherwise.\n- #14700 components 4, 12, 13: frozen true → topology-aware not-two-tone, matching V23. Component 14 also has frozen `two-tone=true` but topology interior is insufficient; its WHITE low-contrast fraction is 6.67%, below the frozen 8% material fraction, so the frozen branch is a protected no-op and not a contrast target. The approved #14700 output remains specific to components 4/12/13; this does not establish broader rule safety.\n- #14607/#14611: source hashes remain byte-identical duplicates; prior REVIEW/protected status is retained.\n- #14593 remains incomplete-group REVIEW (14 blocked links and protected contacts); #14597 remains cautious gold/brand REVIEW. #14607/#14611 retain protected chroma/true-AA/ambiguous and incomplete-group blockers. #10954 is blocked at protected chromatic boundaries; #5136 retains its protected-boundary rejection. #11359/#14406 retain the prior finding that topology candidates did not establish a visually new repair. These independent dispositions are never overridden by tone statistics.\n- Digi Slovakia: pinned V9 WHITE replay is `{digi['pinned_v9_white_replay_status']}`, changed pixels `{digi['pinned_v9_white_replay_changed_pixels']}`. ProTV is included as a second earlier 0-change PASS fixture.\n- The four old approval-ledger entries are classifier-only regression inputs; their prior approvals and outputs were neither changed nor visually reopened.\n\n## Interpretation\n\nV26 tests the component-level decision change on a small, curated but multi-class corpus. It does not replay complete Phase 4 ownership/grouping safety for every catalog case, and several controls intentionally carry external frozen blockers. This sample cannot establish false-positive/false-negative rates for a catalog-wide rule. Although both genuine positives were retained, 201 of 245 achromatic components had insufficient interior evidence and six already-approved monochrome control components changed from frozen true to topology false; this warrants broader independent, end-to-end qualification before integration. The target #14700 result was not used to select fixtures or tune thresholds. Genuine two-tone retention and zero-change PASS checks passed, but wider independent sampling and end-to-end safety qualification are still needed before considering generator integration.\n\n## Invariants\n\nAudit-only; generator not modified; thresholds unchanged; candidate/production picon writes = 0; templates/Masters/sources unchanged; #14599 untouched.\n\n## Reproduction\n\n`python tools/phase4_v26_topology_two_tone_generalization.py --repo-root . --phase3-generator tools/rebuild_master_catalog.py --white-master templates/picons/white-sablona.png --selection reports/warder-master-production/phase4-v26-topology-two-tone-generalization-20260927/CONTROL-SELECTION.csv --out reports/warder-master-production/phase4-v26-topology-two-tone-generalization-20260927`\n'''
    (out/'REPORT.md').write_text(report,encoding='utf-8')
    print(json.dumps({'out':str(out),'controls':len(selected),'components':len(component_rows),'differences':differences,'14700':p147,'digi':digi},default=str))
if __name__=='__main__': main()
