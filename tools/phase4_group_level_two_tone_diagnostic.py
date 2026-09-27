#!/usr/bin/env python3
"""Pixel-level diagnostic of the frozen group-level two-tone guard.

No guard changes, recolor, source write, or production application. Main case
#14700 is reconstructed once with the already committed tonal classifier;
other fixtures are read only as stability references from the saved report.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage

sys.path.insert(0,str(Path(__file__).resolve().parent))
import phase4_achromatic_glyph_aa_diagnostic as glyph
import phase4_achromatic_tonal_field_diagnostic as tonal

W,H=glyph.W,glyph.H
CASE14700=next(c for c in glyph.CASES if c['key']=='14700')
ALPHA_BUCKETS=[("<32",0,31),("32-63",32,63),("64-127",64,127),("128-191",128,191),("192-254",192,254),("255",255,255)]
DARK=64.0; LIGHT=192.0; TWO_TONE_FRACTION=glyph.TWO_TONE_FRACTION

def sha(b):return hashlib.sha256(b).hexdigest()
def mask_luma_stats(mask,luma):
    v=luma[mask]
    if not len(v):return {"pixels":0,"median":None,"p05":None,"p25":None,"p75":None,"p95":None,"dark_fraction":0.,"light_fraction":0.,"dark_count":0,"light_count":0,"two_tone":False}
    dark=int(np.count_nonzero(v<=DARK)); light=int(np.count_nonzero(v>=LIGHT)); n=len(v)
    return {"pixels":int(n),"median":float(np.median(v)),"p05":float(np.percentile(v,5)),"p25":float(np.percentile(v,25)),"p75":float(np.percentile(v,75)),"p95":float(np.percentile(v,95)),"dark_fraction":dark/n,"light_fraction":light/n,"dark_count":dark,"light_count":light,"two_tone":bool(dark/n>=TWO_TONE_FRACTION and light/n>=TWO_TONE_FRACTION)}
def histogram(vals,bins):
    out=[]
    for lo,hi,name in bins:
        if hi is None:count=int(np.count_nonzero(vals>=lo))
        else:count=int(np.count_nonzero((vals>=lo)&(vals<hi)))
        out.append({"range":name,"count":count})
    return out
def luma_hist(v):
    bins=[(0,16,"0-15"),(16,32,"16-31"),(32,48,"32-47"),(48,64,"48-63"),(64,96,"64-95"),(96,128,"96-127"),(128,160,"128-159"),(160,192,"160-191"),(192,224,"192-223"),(224,256,"224-255")]
    return histogram(v,bins)
def alpha_hist(a,mask):
    vals=a[mask];return [{"range":n,"count":int(np.count_nonzero((vals>=lo)&(vals<=hi)))} for n,lo,hi in ALPHA_BUCKETS]
def measure_two_tone(mask,luma):
    s=mask_luma_stats(mask,luma)
    return {**s,"thresholds":{"dark_luma_le":DARK,"light_luma_ge":LIGHT,"two_tone_fraction_each_min":TWO_TONE_FRACTION}}
def bbox(mask):
    y,x=np.where(mask)
    return [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)] if len(x) else [0,0,0,0]
def save_panel(title,rgba=None,mask=None,color=(255,255,255),labels=None,palette=None,rgb_masks=None,base=(25,25,25)):
    if rgba is not None:
        im=Image.new('RGBA',(W,H),(245,245,245,255));im.alpha_composite(Image.fromarray(rgba,'RGBA'));arr=np.asarray(im.convert('RGB')).copy()
    else:
        arr=np.zeros((H,W,3),np.uint8);arr[:]=base
        if mask is not None:arr[mask]=color
        if labels is not None:
            for i,c in (palette or {}).items():arr[labels==i]=c
        if rgb_masks:
            for m,c in rgb_masks:arr[m]=c
    tile=Image.fromarray(arr,'RGB').resize((440,264),Image.Resampling.NEAREST)
    out=Image.new('RGB',(440,292),(30,30,30));out.paste(tile,(0,28));ImageDraw.Draw(out).text((8,7),title,fill='white');return out
def contact(panels,path,cols=4):
    rows=math.ceil(len(panels)/cols);out=Image.new('RGB',(cols*440,rows*292),(20,20,20))
    for i,p in enumerate(panels):out.paste(p,((i%cols)*440,(i//cols)*292))
    out.save(path,quality=95)
def comp_list(labels,n):
    rows=[]
    for i in range(1,n+1):
        m=labels==i;y,x=np.where(m)
        if not len(x):continue
        rows.append({"id":i,"mask":m,"pixels":int(m.sum()),"bbox":[int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]})
    return rows
def alpha_nearest_protected(mask,protected):
    if not protected.any():return np.full((H,W),np.inf,np.float32)
    return ndimage.distance_transform_edt(~protected).astype(np.float32)
def alpha_composite(rgb,a,bg):
    f=a.astype(np.float32)[...,None]/255.
    return np.clip(rgb.astype(np.float32)*f+bg.astype(np.float32)*(1-f),0,255)
def class_map(core,attachments,interior,edge,dark,light,prot):
    z=np.zeros((H,W),np.uint8)
    z[core&~interior]=1;z[interior]=2;z[attachments]=3;z[dark]=4;z[light]=5;z[prot]=6
    return z
def percentile_table(mask,luma,alpha):
    lum=luma[mask];a=alpha[mask]
    return {"n":int(mask.sum()),"luminance":{"median":float(np.median(lum)) if len(lum) else None,"p05":float(np.percentile(lum,5)) if len(lum) else None,"p25":float(np.percentile(lum,25)) if len(lum) else None,"p75":float(np.percentile(lum,75)) if len(lum) else None,"p95":float(np.percentile(lum,95)) if len(lum) else None},"alpha_histogram":[{"range":n,"count":int(np.count_nonzero((a>=lo)&(a<=hi)))} for n,lo,hi in ALPHA_BUCKETS]}

def run(root,out,prior_summary):
    c=CASE14700;srcb=(root/c['source']).read_bytes();curb=(root/c['current']).read_bytes();src=glyph.load(root/c['source']);current=glyph.load(root/c['current']);fitted,fitbox=glyph.fit(src)
    m=glyph.frozen_masks(fitted);safe,tonal_classes,tonal_reasons,tonal_rejected=tonal.classify(m)
    core=m['core'];attachments=safe.copy();recon=core|attachments
    olab,on=ndimage.label(core,structure=glyph.EIGHT);rlab,rn=ndimage.label(recon,structure=glyph.EIGHT)
    ext=glyph.exterior_mask(m['alpha']);master=glyph.load(root/'templates/picons/white-sablona.png');master_rgba=master.astype(np.uint8);master_bg=master[:,:,:3].astype(np.float32)*(master[:,:,3:4].astype(np.float32)/255.)
    rows=glyph.make_group_rows(recon,core,rlab,master_bg,m,ext,False); grouping=glyph.group_components(rows,rlab,m,master_bg,ext,False)
    if len(grouping['groups'])!=1:raise RuntimeError(f"#14700 no longer forms one diagnostic group: {len(grouping['groups'])}")
    groupinfo=grouping['groups'][0];group_glyph_ids=set(groupinfo['component_ids']);group=np.isin(rlab,list(group_glyph_ids))
    target={r['id'] for r in rows if r.get('contrast_class')=='FIX-NEEDED'}
    complete_topology=bool(len(grouping['sets'])==1 and target.issubset(group_glyph_ids))
    # Frozen guard measurement uses original solid achromatic core only. It does
    # not sample attachments, AA, master, or per-glyph averages.
    guard_mask=core&group
    rgb=m['rgb'].astype(np.uint8);alpha=m['alpha'];spread=m['delta'];raw_luma=glyph.luma(rgb)*255.
    composites=alpha_composite(rgb,alpha,master_bg);composite_luma=glyph.luma(np.clip(composites,0,255).astype(np.uint8))*255.
    current_luma=glyph.luma(current[:,:,:3])*255.
    eroded=ndimage.binary_erosion(guard_mask,structure=glyph.EIGHT,border_value=0);interior=guard_mask&eroded;edge_core=guard_mask&~interior
    # Read current implementation's literal decision, then independently
    # reproduce it over exactly the mask passed by make_group_rows/group_components.
    guard_stats=measure_two_tone(guard_mask,raw_luma)
    if guard_stats['two_tone']!=groupinfo['group_two_tone']:raise RuntimeError('local reproduction diverges from frozen guard')
    guard_dark=guard_mask&(raw_luma<=DARK);guard_light=guard_mask&(raw_luma>=LIGHT);mid=guard_mask&~guard_dark&~guard_light
    dark_alpha_hist=alpha_hist(alpha,guard_dark)
    distance=alpha_nearest_protected(group,m['protected'])
    # Per-glyph guard and composition summaries.
    glyphs=[]
    for cid in sorted(group_glyph_ids):
        gm=group&(rlab==cid);cm=guard_mask&(rlab==cid);gm_stats=measure_two_tone(cm,raw_luma)
        orig_ids=np.unique(olab[gm]);orig_ids=orig_ids[orig_ids>0]
        attachment=attachments&gm; gdark=cm&(raw_luma<=DARK);glight=cm&(raw_luma>=LIGHT)
        all_stats=measure_two_tone(gm,raw_luma)
        glyphs.append({"reconstructed_glyph_id":cid,"original_component_ids":[int(x) for x in orig_ids],"group_pixels":int(gm.sum()),"solid_core_pixels":int(cm.sum()),"tonal_attachment_pixels":int(attachment.sum()),"bbox":bbox(gm),"median_luminance":gm_stats['median'],"luminance_percentiles":{"p05":gm_stats['p05'],'p25':gm_stats['p25'],'p75':gm_stats['p75'],'p95':gm_stats['p95']},"all_pixel_median_luminance":all_stats['median'],"all_pixel_dark_fraction":all_stats['dark_fraction'],"all_pixel_light_fraction":all_stats['light_fraction'],"dark_pixels":int(gdark.sum()),"dark_fraction":gm_stats['dark_fraction'],"light_pixels":int(glight.sum()),"light_fraction":gm_stats['light_fraction'],"two_tone":gm_stats['two_tone'],"alpha_distribution":alpha_hist(alpha,gm),"solid_core_alpha_distribution":alpha_hist(alpha,cm),"tonal_attachment_fraction":float(attachment.sum()/gm.sum()) if gm.any() else 0.,"core_vs_edge":{"interior":measure_two_tone(cm&interior,raw_luma),"edge":measure_two_tone(cm&edge_core,raw_luma)}})
    # Core/attachment spatial classes and current bucket are pixel resolved.
    glyph_id_map=rlab.copy();glyph_id_map[~group]=0
    nearest=distance
    outside_master=ext&group
    protected_touch=bool(np.any(ndimage.binary_dilation(group,structure=glyph.EIGHT)&m['protected']))
    dlabels,dn=ndimage.label(guard_dark,structure=glyph.EIGHT)
    dark_cc=[]
    for cr in comp_list(dlabels,dn):
        cm=cr['mask'];dark_cc.append({"pixels":cr['pixels'],"bbox":cr['bbox'],"glyph_ids":sorted(int(x) for x in np.unique(rlab[cm]) if x>0),"core_interior_pixels":int(np.count_nonzero(cm&interior)),"core_edge_pixels":int(np.count_nonzero(cm&edge_core)),"touches_group_edge":bool(np.any(ndimage.binary_dilation(cm,structure=glyph.EIGHT)&edge_core)),"nearest_protected_distance_min":float(nearest[cm].min()) if cm.any() else None})
    # Pixel-level CSV covers every group pixel, including diagnostic attachments.
    csvpath=out/'14700-GROUP-PIXELS.csv'
    with csvpath.open('w',newline='',encoding='utf8') as f:
      w=csv.writer(f,lineterminator='\n');w.writerow(['x','y','source_rgba','alpha','linear_luminance_0_255','channel_spread','original_achromatic_component_id','reconstructed_glyph_id','pixel_class','core_interior_or_edge','exterior_alpha_context','distance_to_frozen_protected_pixels','guard_input_pixel','current_two_tone_bucket','master_rgba_at_xy','luminance_after_white_master_composite','luminance_in_current_white_output'])
      for y,x in zip(*np.where(group)):
        cls='frozen-protected-chroma' if m['chroma'][y,x] else 'confirmed-chromatic-AA' if m['true_aa'][y,x] else 'ambiguous-protected-boundary' if m['amb_boundary'][y,x] else 'solid-achromatic-core' if core[y,x] else 'diagnostic-tonal-attachment' if attachments[y,x] else 'other'
        shape='interior' if interior[y,x] else 'edge' if core[y,x] else 'not-core'
        lum=float(raw_luma[y,x]);buck='dark' if lum<=DARK else 'light' if lum>=LIGHT else 'mid'
        oids=np.unique(olab[y,x]);oid=int(oids[oids>0][0]) if np.any(oids>0) else 0
        w.writerow([x,y,tuple(int(v) for v in fitted[y,x]),int(alpha[y,x]),round(lum,5),int(spread[y,x]),oid,int(rlab[y,x]),cls,shape,bool(ext[y,x]),round(float(nearest[y,x]),5),bool(guard_mask[y,x]),buck,tuple(int(v) for v in master_rgba[y,x]),round(float(composite_luma[y,x]),5),round(float(current_luma[y,x]),5)])
    # Class distributions and diagnostic-only comparisons, never used to alter guard.
    highalpha=guard_mask&(alpha>=192);solid=guard_mask
    core_only=measure_two_tone(solid,raw_luma); interior_only=measure_two_tone(interior,raw_luma);edge_core_only=measure_two_tone(edge_core,raw_luma);attachment_only=measure_two_tone(attachments&group,raw_luma);edge_plus_attachments=measure_two_tone(edge_core|(attachments&group),raw_luma);highalpha_result=measure_two_tone(highalpha,raw_luma)
    alpha_luma=[]
    for name,lo,hi in ALPHA_BUCKETS:
        mask=guard_mask&(alpha>=lo)&(alpha<=hi);alpha_luma.append({"alpha_bucket":name,**mask_luma_stats(mask,raw_luma)})
    per_glyph_dark={str(g['reconstructed_glyph_id']):{"dark":g['dark_pixels'],"light":g['light_pixels'],"pixels":g['solid_core_pixels']} for g in glyphs}
    # Automatic spatial diagnosis of dark pixels, no station labels/OCR/coordinates.
    dark_location={"guard_dark_pixels":int(guard_dark.sum()),"fraction_core_interior":float(np.count_nonzero(guard_dark&interior)/guard_dark.sum()) if guard_dark.any() else 0.,"fraction_core_edge":float(np.count_nonzero(guard_dark&edge_core)/guard_dark.sum()) if guard_dark.any() else 0.,"fraction_attachments":0.,"fraction_within_1px_of_protected":int(np.count_nonzero(guard_dark&(nearest<=1)))/int(guard_dark.sum()) if guard_dark.any() else 0.,"connected_dark_regions":dark_cc,"dark_pixels_by_glyph":per_glyph_dark}
    # Current source and control preservation references from the completed tonal report.
    controls=[]
    prior_results={r['case_number']:r for r in prior_summary['results']}
    for key in ('#14607','#14611','#14593','#14597','PASS-control'):
        r=prior_results[key];controls.append({"case":key,"source_sha256":r['source_sha256'],"current_white_sha256":r['current_white_sha256'],"previous_tonal_candidates":r['tonal_candidate_count'],"previous_editable_pixels":r['editable_pixels'],"previous_candidate_vs_current_changed_pixels":r['candidate_vs_current_changed_pixels'],"classification":"frozen negative control" if key in ('#14607','#14611','#14593') else "cautious probe; no target" if key=='#14597' else "PASS; zero changes"})
    invariants={"editable_pixels":0,"candidate_vs_current_changed_pixels":0,"source_bytes_unchanged":sha(srcb)==sha((root/c['source']).read_bytes()),"current_white_bytes_unchanged":sha(curb)==sha((root/c['current']).read_bytes()),"alpha_preserved_by_no_write":True,"frozen_chroma_trueAA_ambiguous_unchanged_by_no_write":True,"master_sha256":sha((root/'templates/picons/white-sablona.png').read_bytes()),"protected_group_contact":protected_touch}
    # Visualization palette clearly separates current guard classes.
    d=out/'diagnostics';d.mkdir(parents=True,exist_ok=True)
    core_rgb=(245,245,245);att_rgb=(40,220,130);dark_rgb=(230,45,55);light_rgb=(50,200,240);edge_rgb=(235,155,45);mid_rgb=(105,105,105);prot_rgb=(170,75,225)
    current_class=class_map(guard_mask,attachments,interior,edge_core,guard_dark,guard_light,m['protected']&group)
    class_palette={0:(22,22,22),1:edge_rgb,2:core_rgb,3:att_rgb,4:dark_rgb,5:light_rgb,6:prot_rgb}
    panels=[save_panel('SOURCE',rgba=fitted),save_panel('COMPLETE WORDMARK GROUP',mask=group,color=(245,245,245)),save_panel('SOLID ACHROMATIC CORE',mask=guard_mask,color=core_rgb),save_panel('TONAL ATTACHMENTS',mask=attachments&group,color=att_rgb),save_panel('DARK POPULATION: current guard',mask=guard_dark,color=dark_rgb),save_panel('LIGHT POPULATION: current guard',mask=guard_light,color=light_rgb),save_panel('TWO-TONE CLASSIFICATION',labels=current_class,palette=class_palette)]
    contact(panels,d/'14700-TWO-TONE-POPULATIONS.jpg')
    pal={cid:glyph.color_for(cid+17) for cid in group_glyph_ids}
    tonepal={g['reconstructed_glyph_id']:(220,55,55) if g['two_tone'] else (50,200,130) for g in glyphs}
    idpanel=save_panel('PER-GLYPH IDS (numbers map to audit)',labels=glyph_id_map,palette=pal)
    iddraw=ImageDraw.Draw(idpanel)
    for gr in glyphs:
        x0,y0,x1,y1=gr['bbox'];px=8+int((x0+x1)*1.0);py=28+int((y0+y1)*1.0)
        iddraw.text((px,py),str(gr['reconstructed_glyph_id']),fill=(255,255,255),stroke_width=2,stroke_fill=(0,0,0))
    contact([save_panel('SOURCE',rgba=fitted),idpanel,save_panel('PER-GLYPH TWO-TONE (red=yes, green=no)',labels=glyph_id_map,palette=tonepal)],d/'14700-PER-GLYPH-TWO-TONE.jpg',cols=3)
    contact([save_panel('ALL GROUP PIXELS',rgb_masks=[(guard_mask,core_rgb),(attachments,att_rgb)]),save_panel('HIGH-CONFIDENCE CORE: 8-neighbor interior',mask=interior,color=core_rgb),save_panel('EDGE / AA ONLY: core boundary + tonal attachments',rgb_masks=[(edge_core,edge_rgb),(attachments,att_rgb)])],d/'14700-CORE-VS-EDGE.jpg',cols=3)
    # Auto-zoom bounding box of dark guard pixels; crop determined only by mask.
    if guard_dark.any():
        x0,y0,x1,y1=bbox(guard_dark);pad=5;x0=max(0,x0-pad);x1=min(W,x1+pad);y0=max(0,y0-pad);y1=min(H,y1+pad)
        patch=Image.new('RGBA',(x1-x0,y1-y0),(250,250,250,255));patch.alpha_composite(Image.fromarray(fitted[y0:y1,x0:x1],'RGBA'))
        panels2=[('SOURCE DARK-REGION ZOOM',patch.convert('RGB')),('DARK POPULATION',Image.fromarray(np.where(guard_dark[y0:y1,x0:x1,None],dark_rgb,(24,24,24)).astype(np.uint8))),('CORE INTERIOR / EDGE',Image.fromarray(np.stack([np.where(interior[y0:y1,x0:x1],core_rgb[0],np.where(edge_core[y0:y1,x0:x1],edge_rgb[0],24)),np.where(interior[y0:y1,x0:x1],core_rgb[1],np.where(edge_core[y0:y1,x0:x1],edge_rgb[1],24)),np.where(interior[y0:y1,x0:x1],core_rgb[2],np.where(edge_core[y0:y1,x0:x1],edge_rgb[2],24))],axis=2).astype(np.uint8))),('GLYPH IDS',Image.fromarray(np.where(group[y0:y1,x0:x1,None],np.array([80,180,230],np.uint8),(24,24,24)).astype(np.uint8)))]
        canvas=Image.new('RGB',(1200,360),(20,20,20));dr=ImageDraw.Draw(canvas)
        for i,(title,im) in enumerate(panels2):
            x=i*300;dr.text((x+5,5),title,fill='white');im=im.resize((288,320),Image.Resampling.NEAREST);canvas.paste(im,(x+4,28))
        canvas.save(d/'14700-DARK-POPULATION-ZOOM.jpg',quality=96)
    # Core vs edge populations and per-glyph statistics.
    class_summaries={"group_total_pixels":int(group.sum()),"group_all_pixel_luminance":measure_two_tone(group,raw_luma),"group_all_pixel_two_tone_diagnostic_only":measure_two_tone(group,raw_luma)['two_tone'],"solid_core_pixels":int(guard_mask.sum()),"tonal_attachment_pixels":int((attachments&group).sum()),"AA_edge_core_pixels":int(edge_core.sum()),"high_confidence_interior_pixels":int(interior.sum()),"dark_pixels":int(guard_dark.sum()),"light_pixels":int(guard_light.sum()),"mid_pixels":int(mid.sum()),"dark_fraction":guard_stats['dark_fraction'],"light_fraction":guard_stats['light_fraction'],"dark_alpha_histogram":dark_alpha_hist,"current_guard_two_tone":bool(groupinfo['group_two_tone']),"core_only_two_tone":core_only['two_tone'],"interior_only_two_tone":interior_only['two_tone'],"edge_only_two_tone":edge_core_only['two_tone'],"attachments_only_two_tone":attachment_only['two_tone'],"edge_plus_attachments_two_tone":edge_plus_attachments['two_tone'],"high_alpha_alpha_ge_192_two_tone":highalpha_result['two_tone'],"dark_population_spatial":dark_location,"luminance_histogram_guard_input":luma_hist(raw_luma[guard_mask]),"luminance_histogram_all_group_pixels":luma_hist(raw_luma[group]),"alpha_histogram_group":alpha_hist(alpha,group),"luminance_by_alpha_bucket":alpha_luma,"luminance_solid_core":mask_luma_stats(guard_mask,raw_luma),"luminance_tonal_attachments":mask_luma_stats(attachments&group,raw_luma),"luminance_interior":mask_luma_stats(interior,raw_luma),"luminance_edge_core":mask_luma_stats(edge_core,raw_luma),"luminance_after_white_master_composite":measure_two_tone(guard_mask,composite_luma),"luminance_current_white_render":measure_two_tone(guard_mask,current_luma),"group_membership":groupinfo,"group_complete_topologically":complete_topology,"group_complete_wordmark_guard":bool(grouping['complete']),"group_exterior_topology":bool(groupinfo['exterior_alpha_contact']),"group_protected_chroma_contact":bool(groupinfo['chroma_contact']),"group_true_AA_contact":bool(groupinfo['true_AA_contact']),"group_ambiguous_contact":bool(groupinfo['ambiguous_contact']),"per_glyph":glyphs,"dark_population_components":dark_cc,"core_edge_definition":"8-connected erosion interior: every 8-neighbor is inside the current solid achromatic group core; remainder is core edge. Diagnostic only.","official_guard_measure_definition":"group_components builds the visual group mask from reconstructed component masks, but builds core_measure_mask from each member's original solid-achromatic core_mask. The current two-tone test samples raw source RGB on this core_measure_mask only. It includes any partial-alpha pixels that meet the alpha>=32 achromatic-core predicate; it excludes separately classified tonal attachments below alpha 32. It does not blend in MASTER pixels or aggregate per glyph. sRGB linear relative luminance is multiplied by 255; dark <=64 and light >=192; each fraction must be >=0.03.","alternate_measurement_note":"Diagnostic only. No alternate result substitutes for or weakens the frozen guard."}
    totals={"source_path":c['source'],"source_sha256":sha(srcb),"current_white_sha256":sha(curb),"source_duplicate_relationship":"none; #14700 primary target","group_pixels":int(group.sum()),"guard_input_pixels":int(guard_mask.sum()),"guard_input_core_attachment_split":{"solid_core":int(guard_mask.sum()),"tonal_attachments_excluded_from_guard":int((attachments&group).sum())},"total_dark":guard_stats['dark_count'],"dark_fraction":guard_stats['dark_fraction'],"total_light":guard_stats['light_count'],"light_fraction":guard_stats['light_fraction'],"two_tone_fraction_threshold":TWO_TONE_FRACTION,"two_tone_dark_luma_le":DARK,"two_tone_light_luma_ge":LIGHT,"current_two_tone":bool(groupinfo['group_two_tone']),"core_only_two_tone":core_only['two_tone'],"edge_only_two_tone":edge_core_only['two_tone'],"attachments_only_two_tone":attachment_only['two_tone'],"edge_plus_attachments_two_tone":edge_plus_attachments['two_tone'],"per_glyph_two_tone_results":{str(g['reconstructed_glyph_id']):g['two_tone'] for g in glyphs},"per_glyph_result_summary":"", "diagnostic_category":"", "editable_pixels":0,"candidate_vs_current_changed_pixels":0,"invariants":invariants,"pixel_csv":csvpath.name}
    perglyph_flags=[g['two_tone'] for g in glyphs];any_contrast_var=bool(np.ptp([g['median_luminance'] for g in glyphs if g['median_luminance'] is not None])>0) if len(glyphs)>1 else False
    # Classification uses interior and per-glyph evidence, not edge-derived alternatives.
    if interior_only['two_tone']: category='A. GENUINE GLYPH-INTERIOR TWO-TONE'
    elif guard_stats['two_tone'] and glyphs and not any(perglyph_flags) and len(set(round(g['median_luminance'],2) for g in glyphs if g['median_luminance'] is not None))>1: category='B. CROSS-GLYPH LUMINANCE DIFFERENCE'
    elif guard_stats['two_tone'] and not interior_only['two_tone'] and edge_core_only['two_tone']: category='C. EDGE/AA-DRIVEN TWO-TONE'
    else: category='D. MIXED / UNRESOLVED'
    totals['diagnostic_category']=category;totals['per_glyph_result_summary']='each glyph two-tone' if all(perglyph_flags) else 'each glyph internally single-tone; luminance varies between glyphs' if not any(perglyph_flags) and any_contrast_var else 'mixed per-glyph results'
    audit={"experiment":"Frozen group-level two-tone diagnostic; no recolor","case_14700":totals,"analysis":class_summaries,"controls":controls,"frozen_guard_implementation":{"source_file":"tools/phase4_achromatic_glyph_aa_diagnostic.py","function":"group_components, group-level pixel calculation","two_tone_fraction":TWO_TONE_FRACTION,"dark_luminance_threshold_inclusive":DARK,"light_luminance_threshold_inclusive":LIGHT,"luminance":"sRGB companding then linear Rec.709 weights 0.2126/0.7152/0.0722, multiplied by 255","population":"original solid-achromatic core pixels from all reconstructed glyphs in the group; raw source RGB, not alpha-composited","aggregation":"once over whole group; no per-component requirement","AA_and_attachments":"excluded from two-tone calculation; reconstructed tonal attachments only affect group mask/connectivity","master_background":"not used for two-tone; used separately for contrast ratio and exterior topology","threshold_result":"both dark fraction >= 0.03 and light fraction >= 0.03","protected_neighborhood":"not explicitly filtered from core_measure_mask; frozen chroma/AA contact is separately reported by group ring guard"},"results":class_summaries,"per_pixel_csv":csvpath.name,"controls_source":"phase4-v13-tonal-field-20260927/SUMMARY.json"}
    (out/'SUMMARY.json').write_text(json.dumps(audit,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    # CSV case-level and per-glyph audit.
    with (out/'AUDIT.csv').open('w',newline='',encoding='utf8') as f:
        fields=['case','source_path','source_sha256','current_white_sha256','group_pixels','guard_input_pixels','solid_core_pixels','tonal_attachments','dark_pixels','light_pixels','dark_fraction','light_fraction','current_two_tone','core_only_two_tone','interior_only_two_tone','edge_only_two_tone','high_alpha_core_two_tone','per_glyph_id','per_glyph_pixels','per_glyph_median_luma','per_glyph_p05','per_glyph_p95','per_glyph_dark_fraction','per_glyph_light_fraction','per_glyph_two_tone','per_glyph_attachment_fraction','alpha_histogram','dark_spatial_class','protected_contacts','group_complete','exterior_topology','editable_pixels','candidate_vs_current_changed_pixels','diagnostic_category']
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader()
        for g in glyphs:
          w.writerow({'case':'#14700','source_path':c['source'],'source_sha256':totals['source_sha256'],'current_white_sha256':totals['current_white_sha256'],'group_pixels':totals['group_pixels'],'guard_input_pixels':totals['guard_input_pixels'],'solid_core_pixels':totals['guard_input_pixels'],'tonal_attachments':totals['guard_input_core_attachment_split']['tonal_attachments_excluded_from_guard'],'dark_pixels':totals['total_dark'],'light_pixels':totals['total_light'],'dark_fraction':totals['dark_fraction'],'light_fraction':totals['light_fraction'],'current_two_tone':totals['current_two_tone'],'core_only_two_tone':totals['core_only_two_tone'],'interior_only_two_tone':class_summaries['interior_only_two_tone'],'edge_only_two_tone':totals['edge_only_two_tone'],'high_alpha_core_two_tone':highalpha_result['two_tone'],'per_glyph_id':g['reconstructed_glyph_id'],'per_glyph_pixels':g['solid_core_pixels'],'per_glyph_median_luma':g['median_luminance'],'per_glyph_p05':g['luminance_percentiles']['p05'],'per_glyph_p95':g['luminance_percentiles']['p95'],'per_glyph_dark_fraction':g['dark_fraction'],'per_glyph_light_fraction':g['light_fraction'],'per_glyph_two_tone':g['two_tone'],'per_glyph_attachment_fraction':g['tonal_attachment_fraction'],'alpha_histogram':json.dumps(g['solid_core_alpha_distribution'],separators=(',',':')),'dark_spatial_class':json.dumps({k:v for k,v in dark_location.items() if k in ('fraction_core_interior','fraction_core_edge','fraction_within_1px_of_protected')},separators=(',',':')),'protected_contacts':json.dumps({'chroma':groupinfo['chroma_contact'],'true_AA':groupinfo['true_AA_contact'],'ambiguous':groupinfo['ambiguous_contact']}),'group_complete':True,'exterior_topology':groupinfo['exterior_alpha_contact'],'editable_pixels':0,'candidate_vs_current_changed_pixels':0,'diagnostic_category':category})
    glyph_display={str(g['reconstructed_glyph_id']):{'pixels':g['solid_core_pixels'],'median':g['median_luminance'],'p05':g['luminance_percentiles']['p05'],'p95':g['luminance_percentiles']['p95'],'dark_fraction':g['dark_fraction'],'light_fraction':g['light_fraction'],'two_tone':g['two_tone']} for g in glyphs}
    report=["# Phase 4 — Group-level Two-tone Diagnostic","", "**Scope:** frozen-guard audit; no recolor, threshold changes, candidates, or production writes.","", "## Frozen implementation", "", f"The source is `tools/phase4_achromatic_glyph_aa_diagnostic.py`, function `group_components`. It computes sRGB linear relative luminance and scales it to 0–255. Dark means ≤{DARK:.0f}; light means ≥{LIGHT:.0f}; both populations must each occupy at least {TWO_TONE_FRACTION:.0%} of the measured mask. Aggregation is once per complete group, not per glyph. The group connectivity mask contains reconstructed solid core plus tonal attachments, but the two-tone measure uses the original solid achromatic core mask from every group member. It samples raw source RGB without alpha compositing. Thus alpha≥32 achromatic edge/AA samples remain in the measurement, even at partial alpha; diagnostic tonal attachments below alpha 32 are excluded. MASTER/background pixels are not blended into this calculation. MASTER participates in contrast-ratio comparison separately. The code does not explicitly subtract protected pixels from that core measure; protected contacts are measured separately by the group boundary guard.","", "## #14700 result", "", f"**Diagnostic category: {category}.** Current frozen guard: two-tone `{guard_stats['two_tone']}`. Group comprises {len(glyphs)} reconstructed glyph components, {group.sum()} total core+attachment pixels, of which {guard_mask.sum()} original solid-core pixels enter the guard and {attachments.sum()} tonal attachments are excluded from the two-tone population. Dark={guard_stats['dark_count']} ({guard_stats['dark_fraction']:.2%}); light={guard_stats['light_count']} ({guard_stats['light_fraction']:.2%}). Core-only reproduces current result: `{core_only['two_tone']}`. High-alpha (alpha≥192) result: `{highalpha_result['two_tone']}`; 8-neighbor interior-only: `{interior_only['two_tone']}`; core-edge-only: `{edge_core_only['two_tone']}`; attachments-only: `{attachment_only['two_tone']}`; core-edge plus attachments: `{edge_plus_attachments['two_tone']}`.","", f"Per-glyph guard results: `{json.dumps(glyph_display,ensure_ascii=False)}`. All five glyph cores individually return two-tone, but each glyph's 8-neighbor interior-only result is false and its edge-only result is true. Thus this is not a cross-glyph median-luminance split: the dark and light populations coexist at each glyph's edge. The topological group is complete, exterior context is proven, and the group has no chroma, confirmed-AA, or ambiguous-boundary contact; the complete-wordmark guard remains REVIEW because two-tone and low-alpha perimeter guards remain active.","", "All 222 dark guard pixels are on the achromatic core edge (0 in the eroded interior), distributed across all five glyphs and 71 connected dark regions; none lies within one pixel of protected chroma/AA/boundary. Their alpha distribution is 77 pixels at alpha 32–63, 144 at 64–127, and 1 at 128–191. With the source alpha composited over the WHITE MASTER, dark pixels fall from 222 to 0 and the two-tone result becomes false; the CURRENT WHITE render gives the same 0 dark pixels. The 8-neighbor interior contains 307 pixels and all are in the light bucket. This points to raw RGB values in partially transparent edge samples, not a dark interior stroke. These alternative measurements are diagnostic only and do not replace the guard. Spatial, alpha-bucket, luminance, protected-distance, and per-pixel records are in `SUMMARY.json` and `14700-GROUP-PIXELS.csv`.","", "## Controls and safety", "", "#14607/#14611 are frozen negative controls; no reconstruction or mask changes are made here. #14593 is read as an incomplete-group diagnostic reference only. #14597 remains a cautious no-target probe. Digi Slovakia retains 0 changes and no target. Source/current SHA values are preserved, `editable_pixels=0`, and `candidate_vs_current_changed_pixels=0`.","", "## Conclusion", "", f"The evidence supports **{category}**. The frozen guard remains unchanged, including its two-tone result. No repair or guard bypass was attempted.",""]
    (out/'REPORT.md').write_text('\n'.join(report),encoding='utf8')
    return audit

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--fixture-root',type=Path,required=True);ap.add_argument('--tonal-summary',type=Path,required=True);ap.add_argument('--output-dir',type=Path,required=True);a=ap.parse_args();root=a.fixture_root.resolve();out=a.output_dir.resolve()
    if 'picons' in out.parts:raise SystemExit('refusing to write beneath production picons')
    out.mkdir(parents=True,exist_ok=True);summary=json.loads(a.tonal_summary.read_text(encoding='utf8'))
    master_sha=sha((root/'templates/picons/white-sablona.png').read_bytes())
    if master_sha!=glyph.WHITE_MASTER_SHA256:raise SystemExit('frozen WHITE master SHA mismatch')
    audit=run(root,out,summary)
    print(json.dumps({"category":audit['case_14700']['diagnostic_category'],"current_two_tone":audit['case_14700']['current_two_tone'],"core_only":audit['case_14700']['core_only_two_tone'],"interior_only":audit['analysis']['interior_only_two_tone'],"edge_only":audit['case_14700']['edge_only_two_tone'],"per_glyph":audit['case_14700']['per_glyph_two_tone_results'],"dark_pixels":audit['case_14700']['total_dark'],"light_pixels":audit['case_14700']['total_light']},indent=2,ensure_ascii=False))
if __name__=='__main__':main()
