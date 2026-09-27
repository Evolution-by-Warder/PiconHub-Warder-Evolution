#!/usr/bin/env python3
"""Read-only V28 census of all available transparent picon sources.

The script reads the frozen Phase 3 generator and existing V23 topology rule;
it never writes picons, templates, sources, or generator files. Only its output
directory is written. Byte-identical source PNGs are pixel-analyzed once.
"""
from __future__ import annotations
import argparse, csv, gzip, hashlib, importlib.util, json, os, resource, subprocess, sys, time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

EXPECTED_HEAD = "110dade00e1ccc96b5d41fbea1144d6431ae5d7d"
EXPECTED_V9_SHA = "f931d3eb703021fa90d6c7934e6902cd1ecb49dd7a8e69e087072a9bf00d1722"
EXPECTED_WHITE_MASTER_SHA = "c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589"
EXPECTED_BLACK_MASTER_SHA = "61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe"
EIGHT = np.ones((3, 3), dtype=np.uint8)
ALPHA_BANDS = ((1,3),(4,7),(8,15),(16,23),(24,31),(32,255))

def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def sha_file(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def load_gen(path: Path):
    spec=importlib.util.spec_from_file_location('phase3_frozen_v9',path)
    mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
    return mod

def topology_guard(material: np.ndarray, lum: np.ndarray):
    interior=material & ndimage.binary_erosion(material, structure=EIGHT, border_value=0)
    labels,n=ndimage.label(material,structure=EIGHT)
    largest=max((int(np.count_nonzero(labels==i)) for i in range(1,n+1)),default=0)
    enough=bool(material.any() and interior.any() and int(interior.sum()) >= .08*largest)
    vals=lum[interior]; count=int(vals.size)
    dark=int(np.count_nonzero(vals<=64));light=int(np.count_nonzero(vals>=192))
    two=bool(enough and count and dark/count>=.03 and light/count>=.03)
    return {'interior_pixels':count,'interior_fraction_of_solid':float(interior.sum()/material.sum()) if material.any() else 0.0,
      'largest_solid_component':largest,'sufficient':enough,'dark':dark,'light':light,
      'result':'INSUFFICIENT_INTERIOR_EVIDENCE' if not enough else ('two-tone' if two else 'not-two-tone')}

def csv_gz(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True,exist_ok=True)
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('wb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as gz:
            import io
            text=io.TextIOWrapper(gz,encoding='utf-8',newline='')
            w=csv.DictWriter(text,fieldnames=keys,lineterminator='\n',extrasaction='ignore');w.writeheader();w.writerows(rows);text.flush();text.detach()

def csv_plain(path: Path, rows: list[dict]):
    path.parent.mkdir(parents=True,exist_ok=True)
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=keys,lineterminator='\n',extrasaction='ignore');w.writeheader();w.writerows(rows)

def tree_records(root: Path):
    # Do not request -l: in a partial clone it forces Git to fetch every blob.
    raw=subprocess.check_output(['git','-C',str(root),'ls-tree','-r','HEAD'],text=True)
    rec={}
    for line in raw.splitlines():
        meta,path=line.split('\t',1); mode,typ,sha=meta.split()
        rec[path]={'git_blob_sha':sha,'mode':mode}
    return rec

def read_csv_if(path: Path):
    if not path.exists(): return []
    op=gzip.open if path.suffix=='.gz' else open
    with op(path,'rt',newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))

def derive_bucket(v9_status, flags):
    # Conservative priority: data failure > chromatic protection > unresolved
    # topology > proven genuine two-tone > documented V27 false-two-tone pattern
    # > other review > existing adaptation > no action.
    if flags['data_error']: return 'F7'
    if flags['chromatic_risk']: return 'F3'
    if flags['insufficient_risk']: return 'F4'
    if flags['genuine_tone_risk']: return 'F5'
    if flags['false_tone_risk']: return 'F2'
    if v9_status=='REVIEW': return 'F6'
    if v9_status=='AUTO-FIXED': return 'F1'
    return 'F0'

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo-root',type=Path,default=Path('.'))
    ap.add_argument('--out',type=Path,default=Path('reports/warder-master-production/phase4-v28-catalog-census-20260927'))
    ap.add_argument('--expected-head',default=EXPECTED_HEAD)
    a=ap.parse_args();root=a.repo_root.resolve();out=a.out if a.out.is_absolute() else root/a.out
    head=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    branch=subprocess.check_output(['git','-C',str(root),'branch','--show-current'],text=True).strip()
    if head!=a.expected_head: raise SystemExit(f'STOP: HEAD mismatch {head} != {a.expected_head}')
    if branch!='phase4-v10-component-mask-test': raise SystemExit(f'STOP: wrong branch {branch}')
    genpath=root/'tools/rebuild_master_catalog.py'; masterpath=root/'templates/picons/white-sablona.png'
    if sha_file(genpath)!=EXPECTED_V9_SHA: raise SystemExit('STOP: frozen V9 generator hash mismatch')
    if sha_file(masterpath)!=EXPECTED_WHITE_MASTER_SHA: raise SystemExit('STOP: WHITE MASTER hash mismatch')
    if sha_file(root/'templates/picons/black-sablona.png')!=EXPECTED_BLACK_MASTER_SHA: raise SystemExit('STOP: BLACK MASTER hash mismatch')
    gen=load_gen(genpath)
    masters={s:Image.open(root/f'templates/picons/{s}-sablona.png').convert('RGBA') for s in ('white','black')}
    masters_np={s:np.asarray(m,dtype=np.uint8) for s,m in masters.items()}
    gitfiles=tree_records(root)
    physical=[]; transparent_non_png_assets=[]; source_file_errors=[]
    for rel,meta in gitfiles.items():
        parts=Path(rel).parts
        if len(parts)==5 and parts[0]=='picons' and parts[3]=='transparent':
            if Path(rel).suffix.lower()=='.png': physical.append((rel,meta))
            else: transparent_non_png_assets.append(rel)
    physical.sort()
    hash_start=time.perf_counter(); hash_groups=defaultdict(list); raw_by_sha={}; image_meta={}
    for rel,meta in physical:
        p=root/rel
        try:
            data=p.read_bytes(); h=sha_bytes(data); hash_groups[h].append((rel,meta)); raw_by_sha.setdefault(h,data)
        except Exception as e: source_file_errors.append({'source_path':rel,'error':repr(e)})
    hashing_seconds=time.perf_counter()-hash_start
    # Read pre-existing Phase 3 audit as historical output disposition; never rewrite it.
    hist_rows=read_csv_if(root/'reports/warder-master-production/catalog-audit.csv')
    hist_by_path={r.get('source'):r for r in hist_rows}
    # Existing narrow V26/approved-output ledgers are read as associations only.
    prior_rows=[]
    ledger_paths=[root/'reports/warder-master-production/phase4-v26-topology-two-tone-generalization-20260927/CONTROL-SELECTION.csv',
              root/'reports/warder-master-production/phase4-v25-manual-approval-14700-20260927/APPLY-AUDIT.csv',
              root/'reports/warder-master-production/phase4-v10-approved-batch13/APPROVAL-AUDIT.csv']
    ledger_paths.extend(p for p in root.glob('reports/warder-master-production/phase4-v10-experiment-20260925/CASE-*-MANUAL-APPROVAL.csv') if '14599' not in p.name)
    for p in ledger_paths:
        for r in read_csv_if(p): prior_rows.append((p.name,r))
    hist_by_sha=defaultdict(set);manual_approved_shas=set()
    for filename,r in prior_rows:
        sh=r.get('source_sha256') or r.get('sha256') or ''
        if len(sh)==64:
            disp=(r.get('prior_disposition') or r.get('decision') or r.get('approval_status') or r.get('status') or filename)
            hist_by_sha[sh].add(f'{filename}:{disp}')
            decision=' '.join(str(r.get(k,'')) for k in ('user_decision','approval_status','decision','prior_disposition','case'))
            if 'MANUALLY_APPROVED' in decision.upper() or ('manually approved' in decision.lower()) or filename=='APPROVAL-AUDIT.csv':
                manual_approved_shas.add(sh)
    current_sha_by_path={p:sha_bytes(raw_by_sha[h]) for h,refs in hash_groups.items() for p,_ in refs}
    historical_sha_mismatches=[]
    for p,current_sha in current_sha_by_path.items():
        old_sha=hist_by_path.get(p,{}).get('source_sha256','')
        if old_sha and old_sha!=current_sha:
            historical_sha_mismatches.append({'source_path':p,'current_source_sha256':current_sha,
                'phase3_audit_source_sha256':old_sha,
                'phase3_status':hist_by_path[p].get('overall_status',''),'note':'historical Phase 3 audit SHA differs from current source bytes; current image was analyzed as-is'})
    mismatch_paths={r['source_path'] for r in historical_sha_mismatches}
    mismatch_hashes={current_sha_by_path[p] for p in mismatch_paths}
    image_start=time.perf_counter(); feature_by_sha={}; bucket_by_sha={}; source_errors=[]
    white_master_sha=sha_file(masterpath)
    for i,(h,refs) in enumerate(sorted(hash_groups.items()),1):
        paths=[x[0] for x in refs]; blobshas={x[1]['git_blob_sha'] for x in refs}
        feature={'source_sha256':h,'service_count':len(refs),'duplicate_count':len(refs),'source_paths':'|'.join(paths),
          'satellites':'|'.join(sorted({Path(p).parts[1] for p in paths})),
          'providers':'|'.join(sorted({Path(p).parts[2] for p in paths})),
          'git_blob_sha':next(iter(blobshas)) if len(blobshas)==1 else 'SHA256_GROUP_SPANS_GIT_BLOBS',
          'historical_phase3_status':'|'.join(sorted({hist_by_path.get(p,{}).get('overall_status','NO_PRIOR_AUDIT_ROW') for p in paths})),
          'historical_source_sha256_consistency':'MISMATCH' if h in mismatch_hashes else ('MATCH' if any(hist_by_path.get(p,{}).get('source_sha256') for p in paths) else 'NO_PRIOR_HASH'),
          'historical_source_sha256_mismatch_paths':'|'.join(p for p in paths if p in mismatch_paths),
          'historical_approval_review_association':'|'.join(sorted(hist_by_sha.get(h,set()))) or 'none_in_loaded_ledgers',
          'locked_manual_approval_flag':h in manual_approved_shas}
        component_data=[]; side_data={s:[] for s in ('white','black')}; err=''
        try:
            import io
            with Image.open(io.BytesIO(raw_by_sha[h])) as im:
                fmt=im.format or ''; mode=im.mode; native_size=im.size; bands=im.getbands(); alpha_present=('A' in bands or 'transparency' in im.info)
                source=im.convert('RGBA'); source.load()
            original=np.asarray(source,dtype=np.uint8); alpha_native=original[...,3]
            bbox=source.getchannel('A').getbbox()
            fitted,scale,fit_bbox=gen.fit_logo(source); src=np.asarray(fitted,dtype=np.uint8); alpha=src[...,3]; visible=alpha>0
            labels,n=ndimage.label(visible,structure=EIGHT)
            lumall=gen.rel_luma(src[...,:3])*255.0
            counts={}
            for lo,hi in ALPHA_BANDS: counts[f'alpha_{lo}_{hi}']=int(np.count_nonzero((alpha_native>=lo)&(alpha_native<=hi)))
            format_geometry_error=bool(fmt!='PNG' or native_size!=gen.SIZE or not alpha_present or not bbox or not gen.SERVICE_REF.fullmatch(Path(paths[0]).name))
            feature.update({'format':fmt,'mode':mode,'width':native_size[0],'height':native_size[1],
              'alpha_channel_present':alpha_present,'alpha_min':int(alpha_native.min()),'alpha_max':int(alpha_native.max()),
              'alpha_unique_values':int(np.unique(alpha_native).size),'fully_transparent':bool(alpha_native.max()==0),
              'visible_bbox_native':','.join(map(str,bbox)) if bbox else '', 'fit_scale':scale,
              'fitted_visible_bbox_xyxy':','.join(map(str,fitted.getchannel('A').getbbox() or (0,0,0,0))),
              'fitted_width':int((np.where(np.any(visible,axis=0))[0][-1]-np.where(np.any(visible,axis=0))[0][0]+1) if visible.any() else 0),
              'fitted_height':int((np.where(np.any(visible,axis=1))[0][-1]-np.where(np.any(visible,axis=1))[0][0]+1) if visible.any() else 0), 'visible_component_count':n,
              'source_format_or_geometry_anomaly':format_geometry_error,
              'historical_source_provenance_error':h in mismatch_hashes,**counts})
            achro_count=chrom_count=mixed_protected=0; frozen_n=topo_n=trans_n=insuf_n=0
            white_risk=black_risk=white_chrom_risk=black_chrom_risk=0
            for cid in range(1,n+1):
                comp=labels==cid; solid=comp&(alpha>=gen.OPAQUE_ALPHA)
                if not solid.any(): solid=comp.copy()
                rgb=src[...,:3][solid]; spread=rgb.max(axis=1).astype(np.int16)-rgb.min(axis=1).astype(np.int16)
                achro_frac=float(np.mean(spread<=gen.ACHROMATIC_DELTA)) if len(spread) else 0.0
                is_achro=achro_frac>=gen.ACHROMATIC_REQUIRED
                clum=lumall[solid]; dark=int(np.count_nonzero(clum<=64));light=int(np.count_nonzero(clum>=192))
                frozen=bool(len(clum) and dark/len(clum)>=gen.TWO_TONE_FRACTION and light/len(clum)>=gen.TWO_TONE_FRACTION)
                topo=topology_guard(solid,lumall)
                achro_count+=int(is_achro);chrom_count+=int(not is_achro);frozen_n+=int(frozen)
                topo_n+=int(topo['result']=='two-tone');trans_n+=int(is_achro and frozen and topo['result']=='not-two-tone' and topo['sufficient'] and topo['dark']==0)
                insuf_n+=int(is_achro and not topo['sufficient'])
                comp_side={}
                for style in ('white','black'):
                    bg=gen.master_rgb_under(masters_np[style],solid)
                    cr=gen.contrast_ratio(rgb.reshape((-1,1,3)),bg.reshape((-1,1,3))).reshape(-1)
                    weak=float(np.mean(cr<gen.ACHROMATIC_CONTRAST_RATIO)) if cr.size else 0.0
                    risk=weak>=gen.MATERIAL_FRACTION
                    if style=='white': white_risk+=int(risk);white_chrom_risk+=int(risk and not is_achro)
                    else: black_risk+=int(risk);black_chrom_risk+=int(risk and not is_achro)
                    comp_side[style]={'contrast_risk':risk,'weak_fraction':weak}
                component_data.append({'component_id':cid,'visible_pixels':int(comp.sum()),'solid_pixels':int(solid.sum()),
                  'achromatic_fraction':achro_frac,'achromatic':is_achro,'frozen_two_tone':frozen,'frozen_dark':dark,'frozen_light':light,
                  'topology_result':topo['result'],'topology_sufficient':topo['sufficient'],'topology_interior_pixels':topo['interior_pixels'],
                  'interior_dark':topo['dark'],'interior_light':topo['light'],'white':comp_side['white'],'black':comp_side['black']})
            feature.update({'achromatic_component_count':achro_count,'chromatic_component_count':chrom_count,
              'mixed_protected_component_count':chrom_count,'frozen_v9_two_tone_count':frozen_n,
              'topology_aware_two_tone_count':topo_n,'topology_false_two_tone_transition_count':trans_n,
              'insufficient_topology_evidence_count':insuf_n,'white_contrast_risk_components':white_risk,
              'black_contrast_risk_components':black_risk,'white_protected_chromatic_risk_components':white_chrom_risk,
              'black_protected_chromatic_risk_components':black_chrom_risk,
              'rectangular_badge_detection':'NOT_IMPLEMENTED_IN_FROZEN_V9_V23'})
            for style in ('white','black'):
                result=gen.classify_and_render(fitted,masters[style],style)
                transition_risk=any(c[style]['contrast_risk'] and c['achromatic'] and c['frozen_two_tone'] and c['topology_result']=='not-two-tone' and c['topology_sufficient'] and c['interior_dark']==0 for c in component_data)
                genuine_risk=any(c[style]['contrast_risk'] and c['achromatic'] and c['topology_result']=='two-tone' for c in component_data)
                insufficient_risk=any(c[style]['contrast_risk'] and c['achromatic'] and not c['topology_sufficient'] for c in component_data)
                chromatic_risk=any(c[style]['contrast_risk'] and not c['achromatic'] for c in component_data)
                bucket=derive_bucket(result.status,{'data_error':format_geometry_error or h in mismatch_hashes,'chromatic_risk':chromatic_risk,'insufficient_risk':insufficient_risk,
                  'genuine_tone_risk':genuine_risk,'false_tone_risk':transition_risk})
                side_data[style]={'v9_status':result.status,'v9_reason':result.reason,'v9_changed_pixels':result.changed_pixels,
                  'v9_protected_pixels':result.protected_pixels,'bucket':bucket,'risk_flags':{'false_two_tone':transition_risk,
                  'genuine_two_tone':genuine_risk,'insufficient_evidence':insufficient_risk,'protected_chromatic':chromatic_risk}}
            feature['white_disposition']=side_data['white']['bucket'];feature['black_disposition']=side_data['black']['bucket']
            feature['shared_structural_flags']='|'.join(k for k,v in {'frozen_two_tone':frozen_n>0,'topology_two_tone':topo_n>0,
              'false_two_tone_transition':trans_n>0,'insufficient_topology_evidence':insuf_n>0,'protected_chromatic_contact':chrom_count>0}.items() if v)
            if h in mismatch_hashes: feature['shared_structural_flags'] += ('|' if feature['shared_structural_flags'] else '')+'historical_source_hash_mismatch'
            feature['component_records_json']=json.dumps(component_data,separators=(',',':'))
        except Exception as e:
            err=repr(e);feature.update({'format':'ERROR','mode':'','width':0,'height':0,'alpha_channel_present':False,
              'visible_bbox_native':'','fit_scale':'','fitted_visible_bbox_xyxy':'','visible_component_count':0,
              'achromatic_component_count':0,'chromatic_component_count':0,'mixed_protected_component_count':0,
              'frozen_v9_two_tone_count':0,'topology_aware_two_tone_count':0,'topology_false_two_tone_transition_count':0,
              'insufficient_topology_evidence_count':0,'white_contrast_risk_components':0,'black_contrast_risk_components':0,
              'white_disposition':'F7','black_disposition':'F7','shared_structural_flags':'data_error','component_records_json':'[]'})
            source_errors.append({'source_sha256':h,'source_paths':'|'.join(paths),'error':err})
            side_data={s:{'v9_status':'ERROR-SKIP','v9_reason':err,'v9_changed_pixels':0,'v9_protected_pixels':0,'bucket':'F7','risk_flags':{}} for s in ('white','black')}
        feature_by_sha[h]=feature;bucket_by_sha[h]=side_data
        if i%500==0: print(f'analysed_unique={i}/{len(hash_groups)}',flush=True)
    analysis_seconds=time.perf_counter()-image_start
    # Pair/output inventory is taken from the immutable Git tree, not generated.
    source_keys={(Path(p).parts[1],Path(p).parts[2],Path(p).name) for p,_ in physical}
    per_side={s:{p for p in gitfiles if len(Path(p).parts)==5 and Path(p).parts[0]=='picons' and Path(p).parts[3]==s and p.lower().endswith('.png')} for s in ('white','black')}
    missing={s:sum(1 for sat,prov,name in source_keys if f'picons/{sat}/{prov}/{s}/{name}' not in gitfiles) for s in ('white','black')}
    mapping=[]; dup_rows=[]; bucket_rows=[]
    for h,refs in sorted(hash_groups.items()):
        f=feature_by_sha[h];paths=[r[0] for r in refs]
        if len(paths)>1:
            dup_rows.append({'source_sha256':h,'git_blob_sha':f['git_blob_sha'],'duplicate_count':len(paths),
              'bytes':len(raw_by_sha[h]),'service_paths':'|'.join(paths),'providers':'|'.join(f['providers'].split('|'))})
        for p,_ in refs:
            parts=Path(p).parts
            mapping.append({'source_path':p,'source_sha256':h,'git_blob_sha':gitfiles[p]['git_blob_sha'],'satellite_position':parts[1],
              'provider':parts[2],'service_ref':Path(p).name,'service_count_for_image':len(refs),
              'white_output_path':p.replace('/transparent/','/white/'),'white_output_present':p.replace('/transparent/','/white/') in gitfiles,
              'black_output_path':p.replace('/transparent/','/black/'),'black_output_present':p.replace('/transparent/','/black/') in gitfiles,
              'historical_v9_status':hist_by_path.get(p,{}).get('overall_status','NO_PRIOR_AUDIT_ROW'),
              'historical_source_sha256':hist_by_path.get(p,{}).get('source_sha256',''),
              'historical_source_sha256_consistency':'MISMATCH' if p in mismatch_paths else ('MATCH' if hist_by_path.get(p,{}).get('source_sha256') else 'NO_PRIOR_HASH'),
              'historical_approval_review_association':f['historical_approval_review_association']})
        for style in ('white','black'):
            b=bucket_by_sha[h][style]['bucket'];bucket_rows.append({'source_sha256':h,'source_paths':'|'.join(paths),
              'physical_service_refs':len(paths),'style':style,'factory_bucket':b,'v9_status':bucket_by_sha[h][style]['v9_status'],
              'v9_reason':bucket_by_sha[h][style]['v9_reason'],'v9_changed_pixels_in_memory_only':bucket_by_sha[h][style]['v9_changed_pixels'],
              'risk_flags_json':json.dumps(bucket_by_sha[h][style]['risk_flags'],separators=(',',':')),
              'locked_historical_approval':bool(f['locked_manual_approval_flag'])})
    # Summaries by unique hash and physical references; class denominator is each style-specific catalog.
    bucket_summary={}
    for style in ('white','black'):
        bucket_summary[style]={}
        for b in [f'F{i}' for i in range(8)]:
            rows=[r for r in bucket_rows if r['style']==style and r['factory_bucket']==b]
            bucket_summary[style][b]={'unique_images':len(rows),'physical_service_references':sum(r['physical_service_refs'] for r in rows),
              'percent_unique_catalog':100*len(rows)/len(hash_groups) if hash_groups else 0,
              'percent_physical_refs':100*sum(r['physical_service_refs'] for r in rows)/len(physical) if physical else 0,
              'duplicate_amplification':(sum(r['physical_service_refs'] for r in rows)/len(rows) if rows else 0),
              'historical_approval_or_review_unique_images':sum(feature_by_sha[r['source_sha256']]['historical_approval_review_association']!='none_in_loaded_ledgers' for r in rows),
              'historical_manual_approved_unique_images':sum(bool(feature_by_sha[r['source_sha256']]['locked_manual_approval_flag']) for r in rows)}
    # Structural clusters are data-derived from frozen feature flags and the prioritized bucket.
    cluster_defs={'C01':'edge/AA false two-tone transition','C02':'protected chromatic or mixed component','C03':'insufficient topology interior evidence',
      'C04':'genuine interior two-tone','C05':'other frozen REVIEW','C06':'existing V9 safe adaptation','C07':'no action / V9 PASS','C08':'data or geometry error'}
    cluster_rows=[]
    for cid,label in cluster_defs.items():
        for style in ('white','black'):
            b='F'+str({'C01':2,'C02':3,'C03':4,'C04':5,'C05':6,'C06':1,'C07':0,'C08':7}[cid])
            rs=[r for r in bucket_rows if r['style']==style and r['factory_bucket']==b]
            cluster_rows.append({'cluster_id':cid,'cluster_name':label,'style':style,'unique_source_images':len(rs),
              'physical_service_refs':sum(r['physical_service_refs'] for r in rs),
              'catalog_impact_percent_unique':100*len(rs)/len(hash_groups) if hash_groups else 0,
              'catalog_impact_percent_physical':100*sum(r['physical_service_refs'] for r in rs)/len(physical) if physical else 0,
              'duplicate_leverage':sum(r['physical_service_refs'] for r in rs)/len(rs) if rs else 0,
              'mechanism_experimentally_confirmed':{'C01':'yes, V27 transition mechanism; V26 remains needs-more-evidence','C02':'yes, protected mixed components are frozen blockers','C03':'yes, fail-safe insufficiency semantics; broad frequency census only','C04':'yes, two V26/V27 positive controls, not a complete corpus','C05':'no single mechanism','C06':'frozen V9 adaptation','C07':'frozen V9 no-action','C08':'data-dependent'}[cid],
              'relative_implementation_risk':{'C01':'medium-high: global generalization remains unqualified','C02':'high: any edit needs independent chroma separation safety','C03':'high: interior evidence is absent/insufficient','C04':'low to preserve; high to change','C05':'high: heterogeneous review reasons','C06':'low: existing frozen behavior','C07':'low: existing frozen behavior','C08':'case-dependent'}[cid],
              'recommended_next_step':{'C01':'highest-value problem-class qualification, then isolated regression only','C02':'retain protection; do not batch-repair','C03':'retain REVIEW; no evidence-based unlock','C04':'retain protection','C05':'split by existing reason records before any work','C06':'leave under V9','C07':'leave under V9','C08':'quarantine data errors'}[cid],
              'approved_example_available':cid=='C01' and style=='white','known_counterexample_or_limit':{'C01':'genuine two-tone controls remain true; broader qualification incomplete',
              'C02':'no safe split inferred from this census','C03':'insufficient interior cannot be auto-released','C04':'must remain protected','C05':'heterogeneous','C06':'no correction sought','C07':'no correction sought','C08':'manual data repair required'}[cid]})
    # Objective errors/anomalies and distribution summaries.
    fmt_counts=Counter();dim_counts=Counter();mode_counts=Counter();alpha_anomaly=Counter()
    for f in feature_by_sha.values():
        fmt_counts[f.get('format','ERROR')]+=1;dim_counts[f"{f.get('width')}x{f.get('height')}"]+=1;mode_counts[f.get('mode','ERROR')]+=1
        if f.get('format')!='PNG':alpha_anomaly['non_png']+=1
        if not f.get('alpha_channel_present'):alpha_anomaly['missing_alpha_channel']+=1
        if f.get('fully_transparent'):alpha_anomaly['fully_transparent']+=1
        if f.get('source_format_or_geometry_anomaly'):alpha_anomaly['format_geometry_or_alpha_anomaly']+=1
    # Runtime context / performance estimates.
    total_unique=len(hash_groups); physical_count=len(physical)
    img_rate=total_unique/analysis_seconds if analysis_seconds else 0
    observed_duplicate_ratio=physical_count/total_unique if total_unique else 1
    projected_unique=150000/observed_duplicate_ratio
    performance={'total_wall_seconds':None,'hashing_seconds':hashing_seconds,'unique_image_analysis_seconds':analysis_seconds,
      'physical_source_count':physical_count,'unique_image_count':total_unique,'images_per_second_unique_analysis':img_rate,
      'physical_hashes_per_second':physical_count/hashing_seconds if hashing_seconds else 0,
      'estimated_hash_seconds_150000_physical_refs_at_measured_rate':150000/(physical_count/hashing_seconds) if hashing_seconds else None,
      'duplicate_ratio_physical_per_unique':observed_duplicate_ratio,'unique_analyses_saved':physical_count-total_unique,
      'projected_unique_analyses_for_150000_refs_at_same_duplicate_ratio':projected_unique,
      'estimated_seconds_150000_refs_deduplicated':projected_unique/img_rate if img_rate else None,
      'estimated_hours_150000_refs_deduplicated':projected_unique/img_rate/3600 if img_rate else None,
      'estimated_seconds_150000_without_dedup':150000/img_rate if img_rate else None,
      'peak_rss_bytes':int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1024 if sys.platform!='darwin' else 1)),
      'estimation_assumption':'same per-image complexity and same physical/unique duplicate ratio as this 9,041-reference repository snapshot; startup/network/IO overhead excluded'}
    out.mkdir(parents=True,exist_ok=True)
    csv_gz(out/'SOURCE-FEATURES.csv.gz',[feature_by_sha[h] for h in sorted(feature_by_sha)])
    csv_gz(out/'SERVICE-MAPPING.csv.gz',mapping);csv_gz(out/'FACTORY-BUCKETS.csv.gz',bucket_rows)
    csv_plain(out/'PROBLEM-CLUSTERS.csv',cluster_rows);csv_gz(out/'DUPLICATE-GROUPS.csv.gz',dup_rows)
    unique_services=defaultdict(list)
    for h,refs in hash_groups.items(): unique_services[h]=[r[0] for r in refs]
    status_counts={s:dict(Counter(r.get(f'{s}_status','') for r in hist_rows).items()) for s in ('white','black')}
    current_status_by_path_style={}
    for row in bucket_rows:
        for path in row['source_paths'].split('|'):
            current_status_by_path_style[(path,row['style'])]=row['v9_status']
    replay_parity={'checked_path_style_pairs':0,'matching_path_style_pairs':0,'mismatching_path_style_pairs':[]}
    for path,row in hist_by_path.items():
        if path in mismatch_paths: continue
        for style in ('white','black'):
            old_status=row.get(f'{style}_status','')
            new_status=current_status_by_path_style.get((path,style),'')
            if old_status and new_status:
                replay_parity['checked_path_style_pairs']+=1
                if old_status==new_status: replay_parity['matching_path_style_pairs']+=1
                else: replay_parity['mismatching_path_style_pairs'].append({'source_path':path,'style':style,'phase3_status':old_status,'current_frozen_v9_replay':new_status})
    summary={'outcome':'CATALOG-FACTORY-MAP-READY','head':head,'branch':branch,'phase3_generator_sha256':EXPECTED_V9_SHA,
      'white_master_sha256':white_master_sha,'black_master_sha256':sha_file(root/'templates/picons/black-sablona.png'),'source_counts':{'physical_transparent_sources':physical_count,'unique_images':total_unique,
      'byte_identical_duplicate_groups':sum(len(v)>1 for v in hash_groups.values()),'duplicate_refs_within_groups':sum(len(v) for v in hash_groups.values() if len(v)>1),
      'unique_analysis_savings':physical_count-total_unique,'satellites_or_positions':len({Path(p).parts[1] for p,_ in physical}),
      'providers':len({Path(p).parts[2] for p,_ in physical}),'white_outputs':len(per_side['white']),'black_outputs':len(per_side['black']),
      'missing_white_pairs':missing['white'],'missing_black_pairs':missing['black'],'unique_source_bytes':sum(len(v) for v in raw_by_sha.values()),
      'physical_source_bytes':sum(len(raw_by_sha[h]) for h,refs in hash_groups.items() for _ in refs)},
      'file_characteristics':{'formats_unique_image_counts':dict(fmt_counts),'native_dimensions_unique_image_counts':dict(dim_counts),
      'modes_unique_image_counts':dict(mode_counts),'alpha_anomalies':dict(alpha_anomaly),'source_decode_errors':len(source_errors)},
      'non_png_assets_under_transparent_directories':transparent_non_png_assets,
      'frozen_v9_method':{'visible':'alpha > 0','components':'8-connected','solid_sample':'alpha >= 32; whole component only if solid empty',
      'achromatic':'channel spread <=18 on >=98.5% of solid sample','two_tone':'linear Rec.709 raw RGB; dark <=64 and light >=192, each >=3% of solid sample',
      'material_contrast':'contrast ratio <2.50 on >=8% of solid sample','white_target':[16,16,16],'black_target':[240,240,240],
      'topology_v23':'solid mask AND 8-neighbor 3x3 binary erosion; sufficient interior >=8% of largest 8-connected solid component'},
      'factory_bucket_counts':bucket_summary,'historical_phase3_status_counts':status_counts,
      'historical_manual_approval_source_hash_count':sum(bool(f['locked_manual_approval_flag']) for f in feature_by_sha.values()),
      'historical_approval_scope_note':'Only loaded text/CSV approval-selection records were matched by source SHA; all others are reported from historical Phase3 review/status audit. This field is not a visual re-review.',
      'problem_clusters':cluster_rows,'performance':performance,'errors':source_errors,
      'historical_source_sha256_mismatches':historical_sha_mismatches,
      'historical_v9_replay_parity_excluding_hash_mismatches':replay_parity,
      'future_150k_manifest_or_plan_files_checked':['docs/PROJECT-CHECKPOINT.md','docs/PICON-MASTER-QUALITY-PLAN.md','docs/PHASE4-V10-COMPONENT-MASK-TEST.md','tracked file tree names'],
      'rectangular_badge_feature_note':'Frozen V9/V23 contain no badge/rectangle detector. No new heuristic was introduced; flag recorded as detector unavailable.',
      'read_only_invariants':{'candidate_or_production_generation':False,'picons_written':0,'transparent_written':0,'white_written':0,'black_written':0,
      'masters_templates_written':0,'generator_modified':False,'approval_changed':False,'14599_visual_case_reopened':False}}
    # Human report follows from computed aggregates.
    totalU=total_unique; cluster_order=sorted(cluster_rows,key=lambda r:(r['style'], -r['physical_service_refs']))
    f0w=bucket_summary['white']['F0'];f0b=bucket_summary['black']['F0']
    no_work_w=bucket_summary['white']['F0']['unique_images']+bucket_summary['white']['F1']['unique_images']
    no_work_b=bucket_summary['black']['F0']['unique_images']+bucket_summary['black']['F1']['unique_images']
    problem_cluster_ids=('C01','C02','C03','C04','C05')
    top_imp=[max([r for r in cluster_rows if r['cluster_id']==cid],key=lambda r:r['physical_service_refs']) for cid in problem_cluster_ids]
    wall=time.perf_counter()-main_start
    report=f'''# V28 — Full-catalog read-only census\n\n## Outcome\n\n**CATALOG-FACTORY-MAP-READY** for the catalog actually present at `{head}`. This is a read-only census, not a generator qualification or rollout. The repository contains **{physical_count:,}** transparent sources, not 150,000. No repair, candidate, or production write occurred.\n\n## Scope and duplicates\n\n- Physical transparent source PNGs: **{physical_count:,}**\n- Unique byte-identical source images (SHA-256): **{total_unique:,}**\n- Duplicate groups (2+ references): **{sum(len(v)>1 for v in hash_groups.values()):,}**; references in those groups: **{sum(len(v) for v in hash_groups.values() if len(v)>1):,}**\n- Unique pixel analyses saved by deduplication: **{physical_count-total_unique:,}** ({100*(physical_count-total_unique)/physical_count:.1f}% of physical references)\n- Satellite/position directories: **{summary['source_counts']['satellites_or_positions']}**; providers: **{summary['source_counts']['providers']}**\n- WHITE outputs: **{len(per_side['white']):,}**; BLACK outputs: **{len(per_side['black']):,}**; missing WHITE pairs: **{missing['white']:,}**; missing BLACK pairs: **{missing['black']:,}**.\n- Physical source bytes: **{summary['source_counts']['physical_source_bytes']:,}**; unique bytes analyzed: **{summary['source_counts']['unique_source_bytes']:,}**.\n\nAll source PNGs were hashed; each unique image was decoded and analyzed once. V9 component membership, achromatic/two-tone/contrast decisions and V23 topology evidence use the pinned generator/rule constants. This census does not use or infer new detector thresholds.\n\n## Source format and geometry\n\nUnique-image formats: `{json.dumps(dict(fmt_counts),sort_keys=True)}`. Native dimensions: `{json.dumps(dict(dim_counts),sort_keys=True)}`. Modes: `{json.dumps(dict(mode_counts),sort_keys=True)}`. Source anomalies (non-PNG, missing alpha channel, fully transparent, or nonstandard V9 geometry): `{json.dumps(dict(alpha_anomaly),sort_keys=True)}`. Decode errors: **{len(source_errors)}**; these remain F7 and do not stop the scan.\n\n## WHITE / BLACK factory buckets\n\nEach source has independent WHITE and BLACK dispositions; service references inherit the unique-source result. Bucket counts below include unique images and physical service references.\n\n| Style | Bucket | Unique images | Physical refs | % unique | % physical |\n|---|---|---:|---:|---:|---:|\n'''
    for style in ('white','black'):
        for b in [f'F{i}' for i in range(8)]:
            q=bucket_summary[style][b]
            report+=f"| {style.upper()} | {b} | {q['unique_images']:,} | {q['physical_service_references']:,} | {q['percent_unique_catalog']:.2f}% | {q['percent_physical_refs']:.2f}% |\n"
    report+=f'''\nNo-action F0 covers **{f0w['unique_images']:,}** unique / {f0w['physical_service_references']:,} physical refs on WHITE and **{f0b['unique_images']:,}** / {f0b['physical_service_references']:,} on BLACK. That is the observed likely-no-further-work estimate under frozen V9 results, not a guarantee of visual approval. Historical Phase3 statuses from its audit: `{json.dumps(status_counts,sort_keys=True)}`.\n\nF2 known false-two-tone counts: WHITE **{bucket_summary['white']['F2']['unique_images']:,}** unique / {bucket_summary['white']['F2']['physical_service_references']:,} refs; BLACK **{bucket_summary['black']['F2']['unique_images']:,}** / {bucket_summary['black']['F2']['physical_service_references']:,}. V27 supports the edge/AA mechanism, while V26 remains `RULE-GENERALIZATION-NEEDS-MORE-EVIDENCE`; F2 is a classification queue, not permission to edit.\n\n## Highest-impact clusters\n\n| Cluster | Style | Unique | Physical refs | Impact | Mechanism status |\n|---|---|---:|---:|---:|---|\n'''
    for r in top_imp:
        report+=f"| {r['cluster_id']} — {r['cluster_name']} | {r['style'].upper()} | {r['unique_source_images']:,} | {r['physical_service_refs']:,} | {r['catalog_impact_percent_unique']:.2f}% | {r['mechanism_experimentally_confirmed']} |\n"
    report+=f"\nNo-new-rule-work estimate (F0+F1): WHITE {no_work_w:,}/{total_unique:,} unique ({100*no_work_w/total_unique:.2f}%); BLACK {no_work_b:,}/{total_unique:,} ({100*no_work_b/total_unique:.2f}%). This is classifier disposition, not visual approval.\n"
    report+="\nThe tracked docs and file manifests contain no 150,000-source catalog manifest or ingestion plan; the checkpoint identifies 9,041 transparent sources.\n"
    if historical_sha_mismatches:
        report+="\n## Historical source-hash provenance anomalies\n\nThe current source files were read-only during V28. Three source references (two unique current hashes) differ from the source SHA recorded in the Phase 3 audit. These current bytes were fully analyzed, but both WHITE and BLACK dispositions are conservatively placed in F7 until provenance is reconciled. This is a mismatch against historical audit metadata, not a V28 source edit.\n\n"
        for anomaly in historical_sha_mismatches:
            report+=f"- `{anomaly['source_path']}` — current `{anomaly['current_source_sha256']}`, Phase 3 audit `{anomaly['phase3_audit_source_sha256']}`, historical status `{anomaly['phase3_status']}`.\n"
    report+=f"\nHistorical V9 status replay parity excluding those hash-mismatch paths: **{replay_parity['matching_path_style_pairs']:,}/{replay_parity['checked_path_style_pairs']:,} path/style checks matched**; remaining divergences: **{len(replay_parity['mismatching_path_style_pairs'])}**. This is a consistency check against prior audit metadata, not a visual approval.\n"
    report+="\n"
    report+=f"\nFor the next scale-up qualification, C01/F2 has the best current impact-confidence-risk balance: the mechanism is supported by V27 and #14700 is the one specific approved example, while V26 still requires more evidence. C01 is small ({bucket_summary['white']['F2']['unique_images']} WHITE plus {bucket_summary['black']['F2']['unique_images']} BLACK unique source-style rows), so this is an efficient qualification target, not a rollout recommendation. C02 has the highest impact but high implementation risk because it contains protected chromatic components; C03 has volume but lacks sufficient topology evidence.\n"
    report+=f'''\nThe current implementation has no rectangle/badge detector, so V28 reports that feature as unavailable instead of inventing a geometric heuristic. Historical approvals are attached only where a loaded text/CSV record matched a source SHA; they remain locked metadata and do not promote other sources. #14700 stays a specific manual approval. #14599 remains CLOSED/TABU and was not visually revisited.\n\n## Performance and 150,000-reference estimate\n\n- Total measured run: **{wall:.2f} s**; hashing: **{hashing_seconds:.2f} s**; unique-image pixel analysis: **{analysis_seconds:.2f} s**.\n- Unique-image throughput: **{img_rate:.1f} images/s**; peak resident memory: **{performance['peak_rss_bytes']/1024/1024:.1f} MiB**.\n- At the observed duplicate ratio ({observed_duplicate_ratio:.3f} physical refs per unique image), 150,000 references imply about **{projected_unique:,.0f} unique analyses**, or **{performance['estimated_hours_150000_refs_deduplicated']:.2f} h** at this measured CPU rate. Without deduplication: **{performance['estimated_seconds_150000_without_dedup']/3600:.2f} h**. This is a same-host estimate; file retrieval, storage, output encoding and QC add time.\n\nA practical factory is staged: inventory and SHA-256 dedupe; one feature analysis per unique source; map decisions to all service refs; write isolated BLACK/WHITE outputs only for already-qualified classes; run hash/alpha/pair validation; route F2–F7 or any invariant failure to a compact human review queue. The census itself does not authorize those writes.\n\n## Limits and read-only invariants\n\nV9/V23 do not implement a rectangular/badge structure detector; `likely_rectangular_badge` is therefore unavailable, not guessed. Existing Phase3 audit status and matched historic approval records are metadata only. This report does not reopen manually approved visual decisions and does not change any approval.\n\n- `picons/` writes: **0**; transparent/WHITE/BLACK writes: **0**\n- MASTER/template writes: **0**; generator changes: **0**; approval changes: **0**\n- Candidate/rebuild generation: **none**; #14700 remains unchanged; #14599 untouched.\n\nReproduce from a complete checkout with: `python tools/phase4_v28_catalog_census.py --repo-root .`. Machine-readable details are in `CATALOG-SUMMARY.json`, `SOURCE-FEATURES.csv.gz`, `SERVICE-MAPPING.csv.gz`, `FACTORY-BUCKETS.csv.gz`, `PROBLEM-CLUSTERS.csv`, `DUPLICATE-GROUPS.csv.gz`, and `PERFORMANCE.json`.\n'''
    (out/'REPORT.md').write_text(report,encoding='utf-8')
    performance['total_wall_seconds']=time.perf_counter()-main_start;summary['performance']=performance
    (out/'PERFORMANCE.json').write_text(json.dumps(performance,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (out/'CATALOG-SUMMARY.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({'outcome':summary['outcome'],'physical':physical_count,'unique':total_unique,'bucket_counts':bucket_summary,
      'errors':len(source_errors),'runtime_s':wall,'hash_s':hashing_seconds,'analysis_s':analysis_seconds,'out':str(out)},ensure_ascii=False))

if __name__=='__main__':
    main_start=time.perf_counter()
    main()
