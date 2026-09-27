#!/usr/bin/env python3
"""V23 per-frozen-V9-component topology-aware two-tone audit.

Diagnostic only: no candidate and no production/source/master writes.
The topology_guard implementation below reproduces the exact function from
phase4_topology_aware_two_tone_experiment.py at 5a42e95ac6978f66d1f52d834fe3b40c53e93992.
"""
from __future__ import annotations
import argparse, csv, hashlib, importlib.util, json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

EIGHT=np.ones((3,3),dtype=np.uint8)
DARK,LIGHT,FRACTION=64.0,192.0,0.03
SUFFICIENCY_FRACTION=0.08
COMPONENT_IDS=(4,12,13)
ALPHA_BINS=((32,63),(64,127),(128,191),(192,254),(255,255))


def read_rgba(path):
    with Image.open(path) as im:
        im.load(); return im.convert('RGBA')

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def csv_write(path, rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=keys,lineterminator='\n');w.writeheader();w.writerows(rows)

def luma(rgb):
    # Same linear-sRGB / Rec.709 implementation as the pinned glyph module and V9.
    return gen.rel_luma(rgb)*255.0

def luma_stats(mask, lum):
    # Verbatim decision/statistic shape from the cited topology-aware script.
    v=lum[mask];n=int(v.size)
    if n==0:return {'pixels':0,'dark_count':0,'light_count':0,'dark_fraction':0.0,'light_fraction':0.0,'intermediate_count':0,'intermediate_fraction':0.0,'two_tone':False}
    d=int(np.count_nonzero(v<=DARK));li=int(np.count_nonzero(v>=LIGHT));mid=n-d-li
    return {'pixels':n,'dark_count':d,'light_count':li,'intermediate_count':mid,'dark_fraction':d/n,'light_fraction':li/n,'intermediate_fraction':mid/n,'median_luminance':float(np.median(v)),'p05':float(np.percentile(v,5)),'p95':float(np.percentile(v,95)),'two_tone':d/n>=FRACTION and li/n>=FRACTION}

def topology_guard(material, lum):
    # Exact implementation from phase4_topology_aware_two_tone_experiment.py
    # at 5a42e95ac6978f66d1f52d834fe3b40c53e93992, lines 65-77.
    interior=material & ndimage.binary_erosion(material,structure=EIGHT,border_value=0)
    frac=float(interior.sum()/material.sum()) if material.any() else 0.0
    labels,n=ndimage.label(material,structure=EIGHT)
    largest=max((int(np.count_nonzero(labels==i)) for i in range(1,n+1)),default=0)
    evidence_floor=SUFFICIENCY_FRACTION*largest
    enough=bool(material.any() and interior.any() and interior.sum()>=evidence_floor)
    stats=luma_stats(interior,lum)
    result='INSUFFICIENT_INTERIOR_EVIDENCE' if not enough else 'two-tone' if stats['two_tone'] else 'not-two-tone'
    return interior,{**stats,'interior_fraction_of_material':frac,'largest_connected_material_component_pixels':largest,'minimum_interior_pixels_v9_material_floor':evidence_floor,'sufficient_interior_evidence':enough,'result':result}

def v9_stats(gen,src,master,mask,style):
    a=src[...,3];solid=mask&(a>=gen.OPAQUE_ALPHA)
    fallback=not bool(solid.any())
    if fallback:solid=mask.copy()
    rgb=src[...,:3][solid]
    delta=rgb.max(axis=1).astype(np.int16)-rgb.min(axis=1).astype(np.int16)
    achro_fraction=float(np.mean(delta<=gen.ACHROMATIC_DELTA));is_achro=achro_fraction>=gen.ACHROMATIC_REQUIRED
    lum=gen.rel_luma(rgb.reshape((-1,1,3))).reshape(-1)*255.
    dark=lum<=64.;light=lum>=192.;mid=~(dark|light)
    two=bool(float(np.mean(dark))>=gen.TWO_TONE_FRACTION and float(np.mean(light))>=gen.TWO_TONE_FRACTION)
    bg=gen.master_rgb_under(master,solid)
    cr=gen.contrast_ratio(rgb.reshape((-1,1,3)),bg.reshape((-1,1,3))).reshape(-1)
    weak=float(np.mean(cr<gen.ACHROMATIC_CONTRAST_RATIO));needs=weak>=gen.MATERIAL_FRACTION
    if is_achro and not two:branch='RECOLOR' if needs else 'NO-OP'
    else:branch='PROTECTED' if needs else 'NO-OP-PROTECTED'
    y,x=np.where(mask)
    return {'visible_pixels':int(mask.sum()),'bbox_xyxy':[int(x.min()),int(y.min()),int(x.max())+1,int(y.max())+1],
      'solid_pixels':int(solid.sum()),'solid_fallback_used':fallback,'achromatic_pixels':int(np.count_nonzero(delta<=18)),
      'chromatic_pixels':int(np.count_nonzero(delta>18)),'achromatic_fraction':achro_fraction,'achromatic':is_achro,
      'dark_count':int(dark.sum()),'dark_fraction':float(dark.mean()),'light_count':int(light.sum()),'light_fraction':float(light.mean()),
      'intermediate_count':int(mid.sum()),'intermediate_fraction':float(mid.mean()),'two_tone':two,
      'weak_contrast_count':int(np.count_nonzero(cr<2.5)),'weak_contrast_fraction':weak,
      'minimum_contrast_ratio':float(cr.min()),'median_contrast_ratio':float(np.median(cr)),
      'contrast_adaptation_required':needs,'component_branch':branch,'style':style}

def dark_clusters(mask, interior):
    labels,n=ndimage.label(mask,structure=EIGHT); out=[]
    for k in range(1,n+1):
        q=labels==k;y,x=np.where(q)
        out.append({'cluster_id':k,'pixels':int(q.sum()),'interior_pixels':int(np.count_nonzero(q&interior)),
                    'bbox_xyxy':[int(x.min()),int(y.min()),int(x.max())+1,int(y.max())+1]})
    return out

def main():
    global gen
    ap=argparse.ArgumentParser()
    ap.add_argument('--fixtures',type=Path,required=True)
    ap.add_argument('--v22-summary',type=Path,required=True)
    ap.add_argument('--prior-topology-summary',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();root=a.fixtures.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    v22=json.loads(a.v22_summary.read_text());prior=json.loads(a.prior_topology_summary.read_text())
    spec=importlib.util.spec_from_file_location('frozen_phase3_v9',root/'rebuild_master_catalog.py');gen=importlib.util.module_from_spec(spec);sys.modules[spec.name]=gen;spec.loader.exec_module(gen)
    assert (gen.OPAQUE_ALPHA,gen.ACHROMATIC_DELTA,gen.ACHROMATIC_REQUIRED,gen.ACHROMATIC_CONTRAST_RATIO,gen.MATERIAL_FRACTION,gen.TWO_TONE_FRACTION)==(32,18,0.985,2.5,0.08,0.03)
    source_img=read_rgba(root/'14700-source.png');fitted,scale,bbox=gen.fit_logo(source_img);src=np.asarray(fitted,dtype=np.uint8);alpha=src[...,3]
    visible=alpha>0;labels,n=ndimage.label(visible,structure=EIGHT)
    m0=np.zeros(visible.shape,bool)
    for x,y in json.loads((root/'14700-m0-coordinates.json').read_text()):m0[y,x]=True
    actual_ids=sorted(int(x) for x in np.unique(labels[m0]) if x>0)
    assert actual_ids==list(COMPONENT_IDS)==v22['m0_component_ids'],(actual_ids,v22['m0_component_ids'])
    assert [int(np.count_nonzero((labels==cid)&m0)) for cid in COMPONENT_IDS]==[488,155,581]
    assert int(n)==17
    master_img=read_rgba(root/'14700-master-white.png');master=np.asarray(master_img,dtype=np.uint8)
    lum=luma(src[...,:3]);spread=src[...,:3].max(2).astype(np.int16)-src[...,:3].min(2).astype(np.int16)
    m0_px=json.loads((root/'14700-ownership-evidence.json').read_text())
    protected_other={(int(r['x_fitted_220x132']),int(r['y_fitted_220x132'])):r for r in m0_px if r['ownership_decision']=='PROTECTED / OTHER'}
    component_rows=[];dark_rows=[];diagnostics=[]
    for cid in COMPONENT_IDS:
        comp=labels==cid;material=comp&(alpha>=gen.OPAQUE_ALPHA)
        v22comp=next(x for x in v22['per_component'] if x['component_id']==cid)
        assert int(material.sum())==v22comp['material_sample_pixels']
        assert np.all(spread[material]<=gen.ACHROMATIC_DELTA)
        frozen=v9_stats(gen,src,master,comp,'white')
        inside,topo=topology_guard(material,lum)
        # Pixel-level location partition for all frozen V9 dark sample pixels.
        dark=material&(lum<=DARK);edge=dark&~inside
        darkbin={f'{lo}-{hi}':int(np.count_nonzero(dark&(alpha>=lo)&(alpha<=hi))) for lo,hi in ALPHA_BINS}
        clusters=dark_clusters(dark,inside)
        cluster_labels,nc=ndimage.label(dark,structure=EIGHT)
        for y,x in zip(*np.where(dark)):
            cl=int(cluster_labels[y,x])
            loc='topology-interior' if inside[y,x] else 'component/material-edge'
            sub='interior' if inside[y,x] else ('partial-alpha-edge' if alpha[y,x]<255 else 'full-alpha-edge')
            dark_rows.append({'v9_component_id':cid,'x':int(x),'y':int(y),'rgba':json.dumps([int(z) for z in src[y,x]]),
              'alpha':int(alpha[y,x]),'channel_spread':int(spread[y,x]),'linear_rec709_luminance_0_255':float(lum[y,x]),
              'frozen_dark':True,'topology_interior':bool(inside[y,x]),'dark_location':loc,'dark_edge_subclass':sub,'dark_cluster_id':cl})
        area=next(x for x in v22['per_component'] if x['component_id']==cid)
        contrast_needed=frozen['contrast_adaptation_required']
        chroma_intersection=int(np.count_nonzero(material&(spread>gen.ACHROMATIC_DELTA)))
        row={'case':'#14700','v9_component_id':cid,'visible_pixels':int(comp.sum()),'m0_pixels':int((comp&m0).sum()),
          'known_low_alpha_perimeter_pixels':area['known_300_perimeter_pixels'],'other_visible_outside_m0_and_known_300':area['extra_pixels_outside_m0_and_known_300'],
          'solid_material_pixels':int(material.sum()),'frozen_dark_pixels':frozen['dark_count'],'frozen_dark_fraction':frozen['dark_fraction'],
          'frozen_light_pixels':frozen['light_count'],'frozen_light_fraction':frozen['light_fraction'],'frozen_intermediate_pixels':frozen['intermediate_count'],
          'frozen_intermediate_fraction':frozen['intermediate_fraction'],'frozen_two_tone':frozen['two_tone'],
          'topology_interior_pixels':topo['pixels'],'interior_fraction_of_material':topo['interior_fraction_of_material'],
          'largest_connected_solid_material_component_pixels':topo['largest_connected_material_component_pixels'],
          'minimum_interior_pixels_8pct_v9_floor':topo['minimum_interior_pixels_v9_material_floor'],
          'sufficient_interior_evidence':topo['sufficient_interior_evidence'],'interior_dark_pixels':topo['dark_count'],
          'interior_dark_fraction':topo['dark_fraction'],'interior_light_pixels':topo['light_count'],'interior_light_fraction':topo['light_fraction'],
          'interior_intermediate_pixels':topo['intermediate_count'],'interior_intermediate_fraction':topo['intermediate_fraction'],
          'topology_two_tone_result':topo['result'],'dark_pixels_in_topology_interior':int((dark&inside).sum()),
          'dark_pixels_on_material_edge':int(edge.sum()),'dark_pixels_partial_alpha_edge':int((edge&(alpha<255)).sum()),
          'dark_pixels_full_alpha_edge':int((edge&(alpha==255)).sum()),'frozen_dark_alpha_histogram':json.dumps(darkbin,sort_keys=True),
          'dark_connected_subclusters_8conn':nc,'largest_dark_subcluster_pixels':max((q['pixels'] for q in clusters),default=0),
          'dark_subcluster_sizes':json.dumps(sorted((q['pixels'] for q in clusters),reverse=True)),
          'dark_subclusters_with_interior_pixels':sum(1 for q in clusters if q['interior_pixels']>0),
          'achromatic_classification':frozen['achromatic'],'achromatic_fraction':frozen['achromatic_fraction'],
          'contrast_adaptation_required_on_white':contrast_needed,'white_weak_contrast_fraction':frozen['weak_contrast_fraction'],
          'solid_chromatic_intersection_pixels':chroma_intersection,'prior_group_complete_wordmark':True,
          'prior_group_exterior_master_context':True,'prior_group_protected_chroma_trueAA_ambiguous_contact':False,
          'known_protected_other_member_pixels':1 if cid==4 else 0,
          'protected_other_pixel_used_by_topology_material':False if cid==4 else None,
          'next_status':'ELIGIBLE-FOR-NEXT-SAFETY-GATE' if topo['result']=='not-two-tone' and topo['sufficient_interior_evidence'] and frozen['achromatic'] and contrast_needed and chroma_intersection==0 else 'REVIEW',
          'editable_pixels':0,'candidate_generated':False}
        component_rows.append(row)
        diagnostics.append({'component_id':cid,'visible':comp,'solid':material,'interior':inside,'dark':dark,'clusters':clusters,'stats':row,'frozen':frozen,'topo':topo})

    union_material=np.logical_or.reduce([d['solid'] for d in diagnostics])
    union_interior=union_material & ndimage.binary_erosion(union_material,structure=EIGHT,border_value=0)
    per_component_interior=np.logical_or.reduce([d['interior'] for d in diagnostics])
    assert np.array_equal(union_interior,per_component_interior)

    # Positive controls: reproduce the same confirmed core component IDs and the
    # exact V15 topology_guard on that material. Also replay frozen V9 visible component.
    controls=[]
    positive_specs=[('Genuine two-tone #1','pos1-source.png','pos1-white.png','pos1-black.png'),('Genuine two-tone #2','pos2-source.png','pos2-white.png','pos2-black.png')]
    for name,sname,wname,bname in positive_specs:
        im=read_rgba(root/sname);f,_,_=gen.fit_logo(im);arr=np.asarray(f,dtype=np.uint8);aa=arr[...,3];sp=arr[...,:3].max(2).astype(np.int16)-arr[...,:3].min(2).astype(np.int16)
        vlabels,vn=ndimage.label(aa>0,structure=EIGHT);core=(aa>=gen.OPAQUE_ALPHA)&(sp<=gen.ACHROMATIC_DELTA);cl,cn=ndimage.label(core,structure=EIGHT);mat=cl==1
        ov,counts=np.unique(vlabels[mat],return_counts=True);v9cid=int(ov[np.argmax(counts)])
        v9comp=vlabels==v9cid; v9mat=v9comp&(aa>=gen.OPAQUE_ALPHA)
        masterfile=read_rgba(root/'14700-master-white.png');v9frozen=v9_stats(gen,arr,np.asarray(masterfile),v9comp,'white')
        corefrozen=luma_stats(mat,luma(arr[...,:3]));inside,topo=topology_guard(mat,luma(arr[...,:3]))
        replay=gen.classify_and_render(f,masterfile,'white');historical=read_rgba(root/wname)
        controls.append({'case':name,'source_fixture':sname,'source_sha256':sha(root/sname),'selected_topology_material_component_id':1,
          'frozen_v9_alpha_visible_component_id':v9cid,'frozen_v9_visible_pixels':int(v9comp.sum()),'frozen_v9_solid_pixels':int(v9mat.sum()),
          'frozen_v9_dark_count':v9frozen['dark_count'],'frozen_v9_dark_fraction':v9frozen['dark_fraction'],'frozen_v9_light_count':v9frozen['light_count'],
          'frozen_v9_light_fraction':v9frozen['light_fraction'],'frozen_v9_intermediate_count':v9frozen['intermediate_count'],'frozen_v9_two_tone':v9frozen['two_tone'],
          'topology_material_pixels':int(mat.sum()),'topology_frozen_two_tone':corefrozen['two_tone'],'topology_interior_pixels':topo['pixels'],
          'interior_dark_count':topo['dark_count'],'interior_dark_fraction':topo['dark_fraction'],'interior_light_count':topo['light_count'],
          'interior_light_fraction':topo['light_fraction'],'interior_intermediate_count':topo['intermediate_count'],
          'minimum_interior_pixels_8pct_floor':topo['minimum_interior_pixels_v9_material_floor'],'sufficient_interior_evidence':topo['sufficient_interior_evidence'],
          'topology_result':topo['result'],'v9_generator_white_status':replay.status,'v9_generator_white_matches_historical':bool(np.array_equal(np.asarray(replay.image),np.asarray(historical))),
          'candidate_generated':False,'reason':'Exact frozen positive control from V15; topology-aware result must retain genuine two-tone.'})
    assert all(x['frozen_v9_two_tone'] and x['topology_frozen_two_tone'] and x['topology_result']=='two-tone' and x['sufficient_interior_evidence'] for x in controls)

    # Replay the pinned V9 full-image decision on #14700 and prove its stored variants match.
    image_replay={}
    for style in ('white','black'):
        result=gen.classify_and_render(fitted,read_rgba(root/f'14700-master-{style}.png'),style)
        current=read_rgba(root/f'14700-{style}.png')
        image_replay[style]={'status':result.status,'changed_pixels':result.changed_pixels,'protected_pixels':result.protected_pixels,
          'matches_stored_phase3_output':bool(np.array_equal(np.asarray(result.image),np.asarray(current))),
          'current_variant_sha256':sha(root/f'14700-{style}.png')}
    assert all(x['matches_stored_phase3_output'] for x in image_replay.values())

    # Control dispositions are carried forward from the exact V15 topology audit
    # and V22 frozen replay; no new ownership/grouping classifier is run here.
    pr=prior['results']; v22s=json.loads(Path(a.v22_summary).read_text())
    control_rows=[]
    for key in ('#14607','#14611'):
        c=next(x for x in pr['controls'] if x['case']==key); r=v22s['controls']['14607']
        control_rows.append({'case':key,'source_sha256':c['source_sha256'],'frozen_status':'REVIEW','prior_topology_component_summary':json.dumps(c['component_diagnostic_summary'],sort_keys=True),
           'prior_complete_wordmark':c['preserved_prior_status']['complete_wordmark'],'prior_group_blocker':c['preserved_prior_status']['reason'],
           'V22_V9_white':r['white_replay']['status'],'V22_V9_black':r['black_replay']['status'],'candidate':'none','topology_override':'not applied; protected/chromatic cases remain blocked'})
    c=next(x for x in pr['controls'] if x['case']=='#14593')
    control_rows.append({'case':'#14593','source_sha256':c['source_sha256'],'frozen_status':'REVIEW','prior_topology_component_summary':json.dumps(c['component_diagnostic_summary'],sort_keys=True),
      'prior_complete_wordmark':False,'prior_group_blocker':'incomplete group; protected contacts; 14 blocked grouping links','prior_group_topology_result':'not-two-tone on prior group diagnostic','candidate':'none','topology_override':'cannot override incomplete/protected blockers'})
    c=next(x for x in pr['controls'] if x['case']=='#14597')
    control_rows.append({'case':'#14597','source_sha256':c['source_sha256'],'frozen_status':'CAUTIOUS REVIEW','prior_complete_wordmark':False,'prior_group_blocker':'cautious gold/brand probe; no edit target; insufficient topology interior evidence','candidate':'none','topology_override':'not applicable'})
    for name in ('Digi Slovakia',):
        vv=v22s['controls'][name]
        control_rows.append({'case':name,'source_sha256':vv['components']['source_sha256'],'frozen_status':vv['white_replay']['status'],'V9_white_changed_pixels':vv['white_replay']['changed_pixels'],
          'V9_black_changed_pixels':vv['black_replay']['changed_pixels'],'historical_replay_pixel_identical':vv['white_replay']['historical_output_pixel_identical'] and vv['black_replay']['historical_output_pixel_identical'],'candidate':'none','topology_override':'no target'})
    for c in controls:
        control_rows.append({'case':c['case'],'source_sha256':c['source_sha256'],'frozen_status':'genuine two-tone','frozen_two_tone':c['frozen_v9_two_tone'],'topology_two_tone':c['topology_result'],
          'sufficient_interior_evidence':c['sufficient_interior_evidence'],'candidate':'none','topology_override':'positive control retained'})

    # Exact trace of the previously classified low-alpha pixel in component 4.
    low_pixel={'x':109,'y':73,'rgba':[0,63,63,4],'alpha':4,'v9_component_id':int(labels[73,109]),
      'in_visible_component':bool(visible[73,109]),'in_solid_material':bool(alpha[73,109]>=gen.OPAQUE_ALPHA),
      'in_topology_interior':bool(any(d['component_id']==4 and d['interior'][73,109] for d in diagnostics)),
      'prior_phase4_class':'PROTECTED / OTHER','used_for_two_tone':False}
    assert low_pixel['v9_component_id']==4 and low_pixel['in_visible_component'] and not low_pixel['in_solid_material'] and not low_pixel['in_topology_interior']

    # Visualization: exact membership unchanged; show frozen labels/solid/interior/dark.
    bg=Image.alpha_composite(Image.new('RGBA',(220,132),(255,255,255,255)),fitted).convert('RGB')
    panels=[('SOURCE',np.asarray(bg).copy())]
    base=np.full((132,220,3),30,np.uint8)
    colors={4:(60,180,90),12:(60,150,230),13:(200,120,220)}
    for d in diagnostics: base[d['visible']]=colors[d['component_id']]
    panels.append(('FROZEN V9 COMPONENT IDS 4/12/13',base))
    for d in diagnostics:
        arr=np.full((132,220,3),30,np.uint8);arr[d['solid']]=(190,190,190);arr[d['interior']]=(80,200,100);arr[d['dark']]=(245,55,55)
        if d['component_id']==4: arr[73,109]=(240,40,220)
        panels.append((f"COMP {d['component_id']} solid / interior / dark",arr))
    tilew,tileh=440,292;canvas=Image.new('RGB',(tilew*3,tileh*2),(20,20,20));draw=ImageDraw.Draw(canvas)
    for i,(title,arr) in enumerate(panels):
        x=(i%3)*tilew;y=(i//3)*tileh;draw.text((x+8,y+6),title+(' (magenta: 109,73)' if 'COMP 4' in title else ''),fill='white')
        im=Image.fromarray(arr,'RGB').resize((tilew,tileh-28),Image.Resampling.NEAREST);canvas.paste(im,(x,y+28))
    canvas.save(out/'V23-14700-COMPONENT-INTERIOR-MAPS.png')

    csv_write(out/'PER-COMPONENT-TWO-TONE-AUDIT.csv',component_rows)
    csv_write(out/'DARK-PIXEL-AUDIT.csv',dark_rows)
    csv_write(out/'CONTROL-AUDIT.csv',control_rows)
    summary={'experiment':'V23 per-frozen-V9-component topology-aware two-tone replay','topology_rule_source_commit':'5a42e95ac6978f66d1f52d834fe3b40c53e93992',
      'topology_rule_script_blob_sha':'e1165e104af6abd83f2b864a84e8d5cc7a2e350a','glyph_luma_script_blob_sha':'23241e53dc0dcd0bd4592e752276546987d02152',
      'v9_code_commit':'e9b503d76eae3c3c7d7763df4909039a55d3edb8','source_sha256':sha(root/'14700-source.png'),
      'white_master_sha256':sha(root/'14700-master-white.png'),'current_white_sha256':sha(root/'14700-white.png'),'current_black_sha256':sha(root/'14700-black.png'),
      'frozen_v9_alpha_visible_component_ids_unchanged':actual_ids,'component_results':component_rows,'positive_controls':controls,
      'per_component_interior_union_matches_same_frozen_material_union':True,
      'component_4_protected_other_pixel':low_pixel,'controls':control_rows,
      'phase3_full_image_replay':image_replay,
      'prior_group_guards':{'complete_wordmark':True,'exterior_master_context':True,'protected_chroma_trueAA_ambiguous_contact':False,
        'contrast_adaptation_required_on_white':True,'group_source':'V15 topology-aware audit at cited commit; no recomputation or guard change in this V23'},
      'classification':'A — ALL THREE ARE EDGE/AA FALSE POSITIVES' if all(r['frozen_two_tone'] and r['topology_two_tone_result']=='not-two-tone' and r['sufficient_interior_evidence'] and r['dark_pixels_in_topology_interior']==0 for r in component_rows) and all(c['topology_result']=='two-tone' for c in controls) else 'B/C/D — see per-component evidence',
      'question_b_answer':'NO: topology-aware not-two-tone is not approval; all remaining safety gates stay separate.',
      'case_14700_next_status':'ELIGIBLE-FOR-NEXT-SAFETY-GATE — diagnostic status only; no candidate or PASS',
      'editable_pixels':0,'candidate_generated':False,'candidate_vs_current_changed_pixels':0,
      'frozen_thresholds':{'OPAQUE_ALPHA':gen.OPAQUE_ALPHA,'ACHROMATIC_DELTA':gen.ACHROMATIC_DELTA,'ACHROMATIC_REQUIRED':gen.ACHROMATIC_REQUIRED,
        'ACHROMATIC_CONTRAST_RATIO':gen.ACHROMATIC_CONTRAST_RATIO,'MATERIAL_FRACTION':gen.MATERIAL_FRACTION,'TWO_TONE_FRACTION':gen.TWO_TONE_FRACTION,
        'dark_luminance_max':DARK,'light_luminance_min':LIGHT},
      'invariants':{'V9_component_membership_unchanged':True,'alpha_unchanged':True,'source_unchanged':True,'current_white_black_unchanged':True,
        'production_picons_writes':0,'master_template_writes':0,'thresholds_changed':False,'ownership_classifier_used':False,'fringe_classifier_used':False,'case_14599_accessed':False}}
    (out/'SUMMARY.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'classification':summary['classification'],'components':[{k:r[k] for k in ('v9_component_id','frozen_two_tone','topology_two_tone_result','sufficient_interior_evidence','dark_pixels_in_topology_interior','next_status')} for r in component_rows],'positive_controls':[{k:c[k] for k in ('case','frozen_v9_two_tone','topology_frozen_two_tone','topology_result','sufficient_interior_evidence')} for c in controls]},indent=2))

if __name__=='__main__': main()
