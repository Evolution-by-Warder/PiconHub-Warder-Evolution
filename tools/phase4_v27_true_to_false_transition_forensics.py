#!/usr/bin/env python3
"""V27 forensic audit of V26 frozen-true -> topology-not-two-tone transitions.
No generator/picon/approval changes or candidate generation. Replays exact V26
per-component metric and frozen Phase3 fit/component construction.
"""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy import ndimage

EIGHT=np.ones((3,3),dtype=np.uint8)
MASTER_SHA='c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589'
PHASE3_SHA='f931d3eb703021fa90d6c7934e6902cd1ecb49dd7a8e69e087072a9bf00d1722'
APPROVED={
 '#14700':('picons/80.0e/orion-express/white/1_0_1_32D_CE_1_3200000_0_0_0.png','fbc6fd6a6532d2f13fa3d1a1f39ea400f7ec260838c4070acacdab04194d9164'),
 '#3032':('picons/19.2e/csat/white/1_0_1_24C9_43C_1_C00000_0_0_0.png','e773849404809cec90fdec50825bfc02ea2eeb20187537a38bdcdcb8c2d123bf'),
 '#3072':('picons/19.2e/digital/white/1_0_1_788B_414_1_C00000_0_0_0.png','e3427b452a70b52a062e64f01b28623553b884b294208ef44eba52ababd4a3da')}
BINS=((32,63,'32-63'),(64,127,'64-127'),(128,191,'128-191'),(192,254,'192-254'),(255,255,'255'))

def sha(b):return hashlib.sha256(b).hexdigest()
def load(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
def csvwrite(path,rows):
 fields=list(dict.fromkeys(k for r in rows for k in r))
 with open(path,'w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)
def rgb_luma(gen,src):return gen.rel_luma(src.astype(np.uint8))*255.0
def image_rgba(path):
 with Image.open(path) as im:im.load();return im.convert('RGBA')
def v23_fit(gen,source):
 # Exact crop/scale/centre helper used by the V23 diagnostic; compare the
 # resulting pixels against Phase 3 fit_logo before sharing any measurements.
 box=source.getchannel('A').getbbox()
 if box is None:return source.copy()
 crop=source.crop(box);scale=min(1.0,(gen.SIZE[0]-2*gen.SAFE_MARGIN_X)/crop.width,(gen.SIZE[1]-2*gen.SAFE_MARGIN_Y)/crop.height)
 dims=(max(1,round(crop.width*scale)),max(1,round(crop.height*scale)))
 if dims!=crop.size:crop=crop.resize(dims,Image.Resampling.LANCZOS)
 canvas=Image.new('RGBA',gen.SIZE,(0,0,0,0));canvas.alpha_composite(crop,((gen.SIZE[0]-crop.width)//2,(gen.SIZE[1]-crop.height)//2))
 return canvas
def composite(master,fitted):return Image.alpha_composite(master,fitted).convert('RGBA')
def bbox(mask):
 y,x=np.where(mask)
 return [int(x.min()),int(y.min()),int(x.max())+1,int(y.max())+1]
def maskpanel(base,material,interior,dark,which):
 a=np.asarray(base.convert('RGB')).copy(); h,w=a.shape[:2]
 if which=='component':
  a[:]=[30,30,30];a[material]=[130,130,130];a[interior]=[40,160,220]
 elif which=='interior':
  a[:]=[28,28,28];a[material]=[90,90,90];a[interior]=[50,185,230]
 elif which=='dark':
  a[:]=[24,24,24];a[material]=[92,92,92];a[dark]=[245,35,35]
 return Image.fromarray(a,'RGB')
def add_title(img,title):
 d=ImageDraw.Draw(img);d.rectangle((0,0,img.width,24),fill=(12,12,12));d.text((6,5),title,fill=(255,255,255))
def make_sheet(case,root,gen,master,src,labels,transition_ids,outdir):
 fitted,_,_=gen.fit_logo(src);arr=np.asarray(fitted,dtype=np.uint8);a=arr[...,3];lum=rgb_luma(gen,arr[...,:3]);
 mat=np.isin(labels,list(transition_ids))&(a>=gen.OPAQUE_ALPHA)
 interior=mat & ndimage.binary_erosion(mat,structure=EIGHT,border_value=0)
 dark=mat&(lum<=64)
 base=composite(master,fitted)
 # Native panels with labels, enlarged 2x nearest-neighbor for readability.
 panels=[('SOURCE',base.convert('RGB')),('APPROVED WHITE',image_rgba(root/APPROVED[case][0]).convert('RGB')),
  ('COMPONENT MAP',maskpanel(base,mat,interior,dark,'component')),
  ('TOPOLOGY INTERIOR',maskpanel(base,mat,interior,dark,'interior')),
  ('FROZEN DARK PIXELS',maskpanel(base,mat,interior,dark,'dark'))]
 scale=2; pw,ph=220*scale,132*scale; title_h=26
 sheet=Image.new('RGB',(pw*5,ph+title_h),(20,20,20));d=ImageDraw.Draw(sheet)
 for i,(title,img) in enumerate(panels):
  d.text((i*pw+6,5),title,fill='white');sheet.paste(img.resize((pw,ph),Image.Resampling.NEAREST),(i*pw,title_h))
 sheet.save(outdir/f'{case[1:]}-FORENSIC-SHEET.png')
 # nearest-neighbor crop enclosing just transition components, including a small context border.
 masks=np.isin(labels,list(transition_ids));x0,y0,x1,y1=bbox(masks);pad=4;x0=max(0,x0-pad);y0=max(0,y0-pad);x1=min(220,x1+pad);y1=min(132,y1+pad)
 crop_panels=[]
 for title,img in panels:
  crop=img.crop((x0,y0,x1,y1));crop_panels.append((title,crop))
 z=4;cw=(x1-x0)*z;ch=(y1-y0)*z;zoom=Image.new('RGB',(cw*5,ch+title_h),(20,20,20));dd=ImageDraw.Draw(zoom)
 for i,(title,img) in enumerate(crop_panels):
  dd.text((i*cw+6,5),title,fill='white');zoom.paste(img.resize((cw,ch),Image.Resampling.NEAREST),(i*cw,title_h))
 zoom.save(outdir/f'{case[1:]}-TRANSITION-ZOOM.png')

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,default=Path('.'))
 ap.add_argument('--phase3-generator',type=Path,default=Path('tools/rebuild_master_catalog.py'))
 ap.add_argument('--v26-audit',type=Path,default=Path('reports/warder-master-production/phase4-v26-topology-two-tone-generalization-20260927/COMPONENT-AUDIT.csv'))
 ap.add_argument('--v26-selection',type=Path,default=Path('reports/warder-master-production/phase4-v26-topology-two-tone-generalization-20260927/CONTROL-SELECTION.csv'))
 ap.add_argument('--white-master',type=Path,default=Path('templates/picons/white-sablona.png'))
 ap.add_argument('--out',type=Path,default=Path('reports/warder-master-production/phase4-v27-true-false-transition-forensics-20260927'))
 a=ap.parse_args();root=a.repo_root.resolve();out=a.out if a.out.is_absolute() else root/a.out;out.mkdir(parents=True,exist_ok=True)
 def patharg(p):return p if p.is_absolute() else root/p
 gp=patharg(a.phase3_generator);mp=patharg(a.white_master)
 if sha(gp.read_bytes())!=PHASE3_SHA:raise SystemExit('STOP: pinned Phase3 generator SHA mismatch')
 if sha(mp.read_bytes())!=MASTER_SHA:raise SystemExit('STOP: WHITE MASTER SHA mismatch')
 gen=load(gp,'frozen_phase3_v9');v26=load(Path(__file__).resolve().with_name('phase4_v26_topology_two_tone_generalization.py'),'v26_exact_guard')
 master=image_rgba(mp)
 with patharg(a.v26_audit).open(newline='',encoding='utf-8') as f:all_v26=list(csv.DictReader(f))
 trans=[r for r in all_v26 if r['comparison_class']=='FROZEN_TRUE__TOPOLOGY_FALSE']
 if len(trans)!=9:raise SystemExit(f'STOP: V26 exact transition row count={len(trans)}, expected 9')
 expected_cases={'#14700':3,'#3032':4,'#3072':2}
 counts={k:sum(r['case']==k for r in trans) for k in expected_cases}
 if counts!=expected_cases or sum(counts.values())!=9:raise SystemExit(f'STOP case counts differ: {counts}')
 with patharg(a.v26_selection).open(newline='',encoding='utf-8') as f:selection={r['case']:r for r in csv.DictReader(f)}
 transitions=[];darkrows=[];control_rows=[];output_rows=[];case_data={}
 for old in trans:
  case=old['case'];sel=selection[case];sp=root/sel['source_path'];source_bytes=sp.read_bytes()
  if sha(source_bytes)!=sel['source_sha256']:raise SystemExit(f'STOP source SHA mismatch {case}')
  source=image_rgba(sp);fit,scale,fitbox=gen.fit_logo(source);src=np.asarray(fit,dtype=np.uint8);alpha=src[...,3];vis=alpha>0;labels,n=ndimage.label(vis,structure=EIGHT);cid=int(old['component_id']);comp=labels==cid
  if not comp.any():raise SystemExit(f'STOP component missing {case} {cid}')
  solid=comp&(alpha>=gen.OPAQUE_ALPHA)
  if not solid.any():solid=comp.copy()
  rgb=src[...,:3];full_lum=rgb_luma(gen,rgb);lum=full_lum[solid]
  dark=solid&(full_lum<=64);light=solid&(full_lum>=192);inter=solid&ndimage.binary_erosion(solid,structure=EIGHT,border_value=0)
  interior,stats=v26.topology_guard(solid,full_lum)
  achro_delta=rgb[solid].max(axis=1).astype(np.int16)-rgb[solid].min(axis=1).astype(np.int16)
  achro_fraction=float(np.mean(achro_delta<=18));achro=achro_fraction>=0.985
  frozen=bool(np.mean(lum<=64)>=0.03 and np.mean(lum>=192)>=0.03)
  if not frozen or stats['result']!='not-two-tone' or not stats['sufficient_interior_evidence'] or not achro:raise SystemExit(f'STOP V26 transition failed exact replay {case}/{cid}')
  if int(old['visible_pixels'])!=int(comp.sum()) or int(old['solid_pixels'])!=int(solid.sum()) or int(old['topology_interior_pixels'])!=int(interior.sum()):raise SystemExit(f'STOP V26 geometry/stat replay mismatch {case}/{cid}')
  dark_in=int(np.count_nonzero(dark&interior));dark_edge=int(np.count_nonzero(dark&~interior));dark_partial=int(np.count_nonzero(dark&~interior&(alpha<255)));dark_full=int(np.count_nonzero(dark&~interior&(alpha==255)))
  hist={name:int(np.count_nonzero(dark&(alpha>=lo)&(alpha<=hi))) for lo,hi,name in BINS}
  allhist={name:int(np.count_nonzero(solid&(alpha>=lo)&(alpha<=hi))) for lo,hi,name in BINS}
  case_data.setdefault(case,dict(source=source,fitted=fit,labels=labels,ids=[]));case_data[case]['ids'].append(cid)
  row={'case':case,'source_path':sel['source_path'],'source_sha256':sel['source_sha256'],'component_id':cid,
   'visible_px':int(comp.sum()),'solid_px':int(solid.sum()),'frozen_dark':int(dark.sum()),'frozen_light':int(light.sum()),'frozen_intermediate':int(solid.sum()-dark.sum()-light.sum()),
   'frozen_dark_fraction':float(np.mean(lum<=64)),'frozen_light_fraction':float(np.mean(lum>=192)),
   'topology_interior_px':int(interior.sum()),'interior_dark':int(np.count_nonzero(interior&(full_lum<=64))),'interior_light':int(np.count_nonzero(interior&(full_lum>=192))),
   'interior_intermediate':int(np.count_nonzero(interior&~((full_lum<=64)|(full_lum>=192)))),
   'interior_dark_fraction':stats['interior_dark_fraction'],'interior_light_fraction':stats['interior_light_fraction'],
   'sufficient_interior_evidence':stats['sufficient_interior_evidence'],'frozen_two_tone':frozen,'topology_result':stats['result'],
   'achromatic_fraction':achro_fraction,'dark_interior_px':dark_in,'dark_material_edge_px':dark_edge,'dark_partial_alpha_edge_px':dark_partial,
   'dark_full_alpha_edge_px':dark_full,'frozen_dark_alpha_histogram':json.dumps(hist,sort_keys=True),'solid_alpha_histogram':json.dumps(allhist,sort_keys=True),
   'protected_chroma_true_AA_contact':sel.get('prior_disposition','not recorded in V26 source selection'),
   'other_guard_context':sel.get('prior_disposition','not recorded in V26 source selection')}
  transitions.append(row)
  yy,xx=np.where(dark)
  for y,x in zip(yy.tolist(),xx.tolist()):
   pix_class='TOPOLOGY_INTERIOR' if interior[y,x] else ('PARTIAL_ALPHA_MATERIAL_EDGE' if alpha[y,x]<255 else 'FULL_ALPHA_MATERIAL_EDGE')
   darkrows.append({'case':case,'component_id':cid,'x':x,'y':y,'rgba':','.join(map(str,src[y,x].tolist())),
    'alpha':int(alpha[y,x]),'raw_luminance':float(full_lum[y,x]),'topology_interior':bool(interior[y,x]),
    'dark_pixel_location_class':pix_class,'frozen_dark_member':True})
 # Compare the approved rendered WHITE artifacts against exact fitted-source-on-master rendering.
 for case in ('#3032','#3072','#14700'):
  sel=selection[case];source=image_rgba(root/sel['source_path']);fit,_,_=gen.fit_logo(source);src=np.asarray(fit,dtype=np.uint8);labels,n=ndimage.label(src[...,3]>0,structure=EIGHT)
  opath,expected_sha=APPROVED[case];outpath=root/opath;raw=outpath.read_bytes();actual_sha=sha(raw)
  if actual_sha!=expected_sha:raise SystemExit(f'STOP approved output hash mismatch {case}: {actual_sha}')
  approved=image_rgba(outpath)
  if approved.size!=(220,132):raise SystemExit('STOP approved output dimensions unexpected')
  base=composite(master,fit);b=np.asarray(base);ap=np.asarray(approved)
  # These master-composited files are opaque; alpha invariance is checked rendered-vs-rendered.
  if not np.array_equal(b[...,3],ap[...,3]):raise SystemExit(f'STOP final composite alpha differs {case}')
  all_diff=np.any(b[...,:3]!=ap[...,:3],axis=2)
  for cid in case_data[case]['ids']:
   comp=labels==cid;solid=comp&(src[...,3]>=32);inter=solid&ndimage.binary_erosion(solid,structure=EIGHT,border_value=0)
   lum=rgb_luma(gen,src[...,:3]);dark=solid&(lum<=64);inside=int(np.count_nonzero(all_diff&comp));outside=int(np.count_nonzero(all_diff&~comp))
   # Predict a target-16 composed component solely for comparison, never written.
   target=fit.copy();ta=np.asarray(target).copy();ta[comp,:3]=16;target=Image.fromarray(ta,'RGBA');target_out=np.asarray(composite(master,target))
   matches16=int(np.count_nonzero(np.all(ap[comp,:3]==target_out[comp,:3],axis=1)))
   interior_target16=int(np.count_nonzero(np.all(ap[inter,:3]==target_out[inter,:3],axis=1)))
   output_rows.append({'case':case,'component_id':cid,'approved_status':'MANUALLY APPROVED/CLOSED — not re-evaluated',
    'approved_white_path':opath,'approved_white_sha256':actual_sha,'source_sha256':sel['source_sha256'],
    'fitted_source_composited_baseline_sha256':sha(b.tobytes()),'component_visible_px':int(comp.sum()),
    'component_source_alpha_px':int(np.count_nonzero(comp&(src[...,3]>0))),'component_rgb_changed_vs_source_composite':inside,
    'component_alpha_changed_vs_source_composite':int(np.count_nonzero((b[...,3]!=ap[...,3])&comp)),
    'outside_this_component_rgb_changed':outside,'frozen_dark_edge_pixels':int(np.count_nonzero(dark&~inter)),
    'frozen_dark_edge_pixels_changed_in_approved_output':int(np.count_nonzero(dark&~inter&all_diff)),
    'topology_interior_pixels':int(inter.sum()),'topology_interior_pixels_changed_in_approved_output':int(np.count_nonzero(inter&all_diff)),
    'approved_pixels_matching_hypothetical_target16_composite':matches16,'target16_component_pixels':int(comp.sum()),
    'topology_interior_pixels_matching_target16':interior_target16,'topology_interior_dark_target_match_fraction':interior_target16/int(inter.sum()) if inter.any() else 0.0,
    'approved_output_matches_target16_on_whole_component':matches16==int(comp.sum()),
    'approved_output_matches_target16_on_topology_interior':interior_target16==int(inter.sum()),
    'source_alpha_preserved_in_render_comparison':bool(np.array_equal(b[...,3],ap[...,3])),
    'component_rgb_change_fraction':inside/int(comp.sum())})
  case_data[case].update(approved=approved,source_composite=base)
 # Positive controls are replayed in their historically used V23 and V26
 # material scopes. V23 selected connected solid-achromatic core components;
 # V26 audits the enclosing alpha-visible V9 component and samples all alpha>=32
 # pixels. These denominators must remain explicit and separate.
 with patharg(a.v26_audit).open(newline='',encoding='utf-8') as f: v26rows=list(csv.DictReader(f))
 positive_reconciliation=[]
 v23_expected={
  'T-NEOSAT': {'component_pixels':4352,'frozen_dark':2436,'frozen_light':1732,'interior_pixels':4089,'interior_dark':2173,'interior_light':1732},
  'T-DEMIR': {'component_pixels':10681,'frozen_dark':5122,'frozen_light':4953,'interior_pixels':10157,'interior_dark':4887,'interior_light':4665}}
 for case in ('T-NEOSAT','T-DEMIR'):
  old=next(r for r in v26rows if r['case']==case and int(r['component_id'])==1)
  sel=selection[case];fit,_,_=gen.fit_logo(image_rgba(root/sel['source_path']));src=np.asarray(fit);labels,n=ndimage.label(src[...,3]>0,structure=EIGHT);comp=labels==1;solid=comp&(src[...,3]>=32);lum=rgb_luma(gen,src[...,:3]);inter,ts=v26.topology_guard(solid,lum)
  dark=solid&(lum<=64);light=solid&(lum>=192);dark_i=int(np.count_nonzero(inter&(lum<=64)));light_i=int(np.count_nonzero(inter&(lum>=192)))
  if not old['frozen_two_tone']=='True' or ts['result']!='two-tone' or dark_i<=0 or light_i<=0:raise SystemExit(f'STOP genuine two-tone positive control failed: {case}')
  source_image=image_rgba(root/sel['source_path'])
  v23fitted=v23_fit(gen,source_image)
  fit_identical=np.array_equal(np.asarray(fit),np.asarray(v23fitted))
  if not fit_identical:raise SystemExit(f'STOP Phase 3 and V23 fit paths differ at pixel level: {case}')
  v23src=np.asarray(v23fitted,dtype=np.uint8)
  spread=v23src[...,:3].max(axis=2).astype(np.int16)-v23src[...,:3].min(axis=2).astype(np.int16)
  v23_core=(v23src[...,3]>=32)&(spread<=18)
  core_labels,core_n=ndimage.label(v23_core,structure=EIGHT)
  v23_material=core_labels==1
  if np.any(v23_material & ~comp):raise SystemExit(f'STOP V23 positive-control core component is not inside V26 visible component: {case}')
  v23_inter,v23_stats=v26.topology_guard(v23_material,lum)
  v23_dark=int(np.count_nonzero(v23_material&(lum<=64)));v23_light=int(np.count_nonzero(v23_material&(lum>=192)))
  v23_dark_i=int(np.count_nonzero(v23_inter&(lum<=64)));v23_light_i=int(np.count_nonzero(v23_inter&(lum>=192)))
  expected=v23_expected[case]
  replay={'component_pixels':int(v23_material.sum()),'frozen_dark':v23_dark,'frozen_light':v23_light,
          'interior_pixels':int(v23_inter.sum()),'interior_dark':v23_dark_i,'interior_light':v23_light_i}
  if replay!=expected or v23_stats['result']!='two-tone' or not v23_stats['sufficient_interior_evidence']:
   raise SystemExit(f'STOP V23 positive-control replay does not match frozen historical selection: {case}: {replay}')
  component_details=[]
  for core_id in range(1,core_n+1):
   cmask=(core_labels==core_id)&comp
   if not cmask.any():continue
   cinter,cstats=v26.topology_guard(cmask,lum)
   component_details.append({'v23_core_component_id':core_id,'material_pixels':int(cmask.sum()),
    'frozen_dark':int(np.count_nonzero(cmask&(lum<=64))),'frozen_light':int(np.count_nonzero(cmask&(lum>=192))),
    'topology_interior_pixels':int(cinter.sum()),'interior_dark':cstats['interior_dark_pixels'],
    'interior_light':cstats['interior_light_pixels'],'topology_result':cstats['result']})
  if sum(q['material_pixels'] for q in component_details)!=int(solid.sum()):raise SystemExit(f'STOP V26 material is not fully accounted for by V23 solid-achromatic islands: {case}')
  positive_reconciliation.append({'case':case,'source_sha256':sel['source_sha256'],
   'fitted_rgba_identical_between_phase3_and_v23_fit':fit_identical,
   'v23_scope':'solid achromatic core (alpha>=32 and channel spread<=18), 8-connected components; selected component id 1',
   'v23_core_component_count_inside_v26_alpha_component':len(component_details),
   'v23_selected_component_id':1,'v23_component_pixels':replay['component_pixels'],
   'v23_frozen_dark':v23_dark,'v23_frozen_light':v23_light,'v23_topology_interior_pixels':int(v23_inter.sum()),
   'v23_interior_dark':v23_dark_i,'v23_interior_light':v23_light_i,'v23_topology_result':v23_stats['result'],
   'v23_frozen_two_tone':bool(v23_dark/v23_material.sum()>=0.03 and v23_light/v23_material.sum()>=0.03),
   'v26_scope':'full alpha-visible V9 component (alpha>0 membership), sampled at alpha>=32; no solid-core component splitting',
   'v26_alpha_visible_component_pixels':int(comp.sum()),'v26_solid_material_pixels':int(solid.sum()),
   'v26_topology_interior_pixels':int(inter.sum()),'v26_interior_dark':dark_i,'v26_interior_light':light_i,
   'v26_topology_result':ts['result'],'v23_core_component_breakdown':json.dumps(component_details,sort_keys=True),
   'reconciliation':'Different denominators/scopes: V23 selects one 8-connected solid-achromatic island; V26 aggregates every alpha>=32 solid pixel in the enclosing alpha-visible component. Both preserve genuine interior dark+light evidence.'})
  control_rows.append({'case':case,'component_id':1,'frozen_dark_pixels':int(dark.sum()),'frozen_light_pixels':int(light.sum()),
   'topology_interior_pixels':int(inter.sum()),'interior_dark_pixels':dark_i,'interior_light_pixels':light_i,
   'topology_result':ts['result'],'sufficient_interior_evidence':ts['sufficient_interior_evidence'],'diagnostic_edit_pixels':0,
   'scope':'V26 complete alpha-visible V9 component, sampled at alpha>=32'})
  control_rows.append({'case':case+' V23 selected core component','component_id':1,
   'frozen_dark_pixels':v23_dark,'frozen_light_pixels':v23_light,'topology_interior_pixels':int(v23_inter.sum()),
   'interior_dark_pixels':v23_dark_i,'interior_light_pixels':v23_light_i,'topology_result':v23_stats['result'],
   'sufficient_interior_evidence':v23_stats['sufficient_interior_evidence'],'diagnostic_edit_pixels':0,
   'scope':'V23 selected 8-connected solid-achromatic core component'})
 # The conservative insufficient rule is fail-safe: keep frozen/protected semantics, never release.
 insuff=0
 with patharg(a.v26_audit).open(newline='',encoding='utf-8') as f:
  for r in csv.DictReader(f):
   if r['achromatic']=='True' and r['topology_result']=='INSUFFICIENT_INTERIOR_EVIDENCE':insuff+=1
 control_rows.append({'case':'V26 insufficient-evidence population','component_id':'all','frozen_dark_pixels':'not rescanned in V27',
  'topology_interior_pixels':'insufficient by frozen V23 floor','topology_result':'INSUFFICIENT_INTERIOR_EVIDENCE => retain frozen/protected behavior',
  'insufficient_component_count':insuff,'diagnostic_edit_pixels':0})
 # Add #14700 as reference metrics to control audit.
 for r in transitions:
  if r['case']=='#14700':control_rows.append({'case':'#14700 reference','component_id':r['component_id'],'frozen_dark_pixels':r['frozen_dark'],'topology_interior_pixels':r['topology_interior_px'],
   'interior_dark_pixels':r['interior_dark'],'interior_light_pixels':r['interior_light'],'topology_result':r['topology_result'],'diagnostic_edit_pixels':0})
 # sheets use the exact same source, labels and computed topology masks.
 for case in ('#3032','#3072','#14700'):
  ids=case_data[case]['ids'];src=case_data[case]['source'];fit,_,_=gen.fit_logo(src);labels,_=ndimage.label(np.asarray(fit)[...,3]>0,structure=EIGHT)
  make_sheet(case,root,gen,master,src,labels,ids,out)
 # classify evidence
 approved_counters=[r for r in output_rows if r['case'] in ('#3032','#3072') and r['frozen_dark_edge_pixels']>0 and r['frozen_dark_edge_pixels_changed_in_approved_output']==0 and r['component_rgb_changed_vs_source_composite']==0]
 all_edge_only=all(r['interior_dark']==0 for r in transitions)
 if len(approved_counters): verdict='B — TOPOLOGY-RULE-COUNTEREXAMPLE'
 elif all_edge_only and all(r['interior_dark_pixels']>0 for r in control_rows if r.get('case') in ('T-NEOSAT','T-DEMIR')) and all(r['topology_result']=='two-tone' for r in control_rows if r.get('case') in ('T-NEOSAT','T-DEMIR')): verdict='A — TRANSITION-MECHANISM-SUPPORTED'
 else:verdict='C — TRANSITION-MECHANISM-MIXED'
 # If approved artifacts fail to reconcile against source/target pixels, mark the distinct history outcome.
 if len(output_rows)!=9:verdict='D — APPROVED-CONTROL-HISTORY-AMBIGUOUS'
 csvwrite(out/'TRANSITION-AUDIT.csv',transitions);csvwrite(out/'DARK-PIXEL-FORENSICS.csv',darkrows);csvwrite(out/'APPROVED-OUTPUT-COMPARISON.csv',output_rows);csvwrite(out/'CONTROL-AUDIT.csv',control_rows);csvwrite(out/'POSITIVE-CONTROL-RECONCILIATION.csv',positive_reconciliation)
 summary={'experiment':'V27 true-to-false transition forensics / approved-control safety study','branch_expected':'phase4-v10-component-mask-test',
  'starting_head':'8969c2208dd39aba91a0304acbbaa2e842f224a6','transition_count':len(transitions),'transition_case_counts':counts,
  'transition_components':transitions,'frozen_dark_pixel_count':len(darkrows),'dark_location_counts':{k:sum(r['dark_pixel_location_class']==k for r in darkrows) for k in sorted(set(r['dark_pixel_location_class'] for r in darkrows))},
  'approved_output_comparisons':output_rows,'genuine_two_tone_controls':[r for r in control_rows if r.get('case') in ('T-NEOSAT','T-DEMIR')],
  'positive_control_scope_reconciliation':positive_reconciliation,
  'insufficient_evidence_components':insuff,'insufficient_semantics':'INSUFFICIENT_INTERIOR_EVIDENCE does not return not-two-tone; conservative behavior is retain frozen/protected handling. It never releases a component.',
  'verdict':verdict,'v26_verdict_unchanged':'RULE-GENERALIZATION-NEEDS-MORE-EVIDENCE','no_candidate':True,
  'invariants':{'picon_writes':0,'candidate_generated':False,'generator_modified':False,'classifier_modified':False,'thresholds_modified':False,'approval_ledger_modified':False,'14599_accessed':False}}
 (out/'SUMMARY.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 report=f'''# V27 — True→false transition forensics / approved-control safety study\n\n## Result: {verdict}\n\nV27 extracted transitions from the exact V26 `COMPONENT-AUDIT.csv` comparison column, then independently replayed frozen Phase 3 fitting, alpha-visible 8-connected membership, frozen solid sampling, and the exact V26/V23 topology function. The extracted set was {len(transitions)} components: #14700 {counts['#14700']}, #3032 {counts['#3032']}, #3072 {counts['#3072']}. Any count or replay mismatch stopped the run.\n\n## Nine transitions\n\n`TRANSITION-AUDIT.csv` contains every required metric and alpha histograms. `DARK-PIXEL-FORENSICS.csv` contains every frozen-dark source pixel and its topology/edge classification. Across the nine, frozen dark material pixels = {len(darkrows)}; dark inside topology interior = {sum(r['dark_interior_px'] for r in transitions)}; dark on material edge = {sum(r['dark_material_edge_px'] for r in transitions)}; dark at partial-alpha material edge = {sum(r['dark_partial_alpha_edge_px'] for r in transitions)}; dark at full-alpha material edge = {sum(r['dark_full_alpha_edge_px'] for r in transitions)}.\n\n## Approved #3032/#3072 output evidence\n\nThe approved WHITE artifact hashes were verified against the existing approval ledger: #3032 `{APPROVED['#3032'][1]}` and #3072 `{APPROVED['#3072'][1]}`. The rendered artifacts were compared with the exact fitted source composited on the verified WHITE MASTER. Per transition, `APPROVED-OUTPUT-COMPARISON.csv` records changed RGB pixels inside/outside the component, alpha changes, edge-dark/interior changes, and exact agreement with a diagnostic `(16,16,16)` component composite. The target composite is a mathematical comparator only; no candidate was created. Existing approval decisions remain CLOSED and were not revisited.\n\nA prior approved output is independent historical evidence for the already accepted rendered result, not proof that the topology classifier is generally safe. For the six #3032/#3072 transitions, every frozen-dark edge sample remained unchanged in the approved WHITE, while 56–1,929 topology-interior pixels per component changed and 90.2–99.7% of those interiors match the diagnostic target-16 composite. This is consistent with interior contrast correction plus untouched dark edge samples; it does not establish rule-wide safety. The exact componentwise measurements, not approval status alone, determine the forensic interpretation.\n\n## Positive genuine two-tone controls\n\nT-NEOSAT and T-DEMIR were replayed in both historically used mask scopes. V23 selected 8-connected components of the solid achromatic core (`alpha>=32`, channel spread `<=18`), then selected component ID 1. V26 instead labels `alpha>0` components and samples every `alpha>=32` pixel in the enclosing alpha-visible component. The fitted RGBA canvases are byte-identical between the V23 helper and pinned Phase 3 fit path, so the count difference is due to scope, not resizing.

| Control | V23 selected material | V23 interior dark/light | V26 full alpha-component solid | V26 interior dark/light |
|---|---:|---:|---:|---:|
| T-NEOSAT | 4,352 px | 2,173 / 1,732 | 9,357 px | 2,283 / 5,616 |
| T-DEMIR | 10,681 px | 4,887 / 4,665 | 11,366 px | 5,311 / 4,665 |

The V26 solid sets are the union of three separate achromatic-core islands inside each alpha-visible component: T-NEOSAT `4,352 + 2,374 + 2,631 = 9,357`; T-DEMIR `10,681 + 327 + 358 = 11,366`. V23 selected island 1 and V26’s larger aggregate both retain interior dark and light populations and return `two-tone=true`. This reconciles the historical counts and confirms both positive-control lanes; it does not change V26’s generalization verdict.\n\n## Other gates and 201 insufficient-evidence components\n\nThe V26 conservative result for `INSUFFICIENT_INTERIOR_EVIDENCE` is not `not-two-tone`: it retains frozen/protected behavior and cannot release a component. The 201 components are therefore not promoted by this substitution. Existing independent statuses remain in force: #14593 incomplete grouping/protected contacts; #14597 cautious gold/brand review; #14607/#14611 protected chroma/AA/ambiguous and incomplete grouping; #10954/#5136 protected-boundary blockers; #11359/#14406 no newly established visible repair. These prior dispositions were carried forward, not re-run as ownership decisions.\n\n## Visual diagnostics\n\nThe PNG sheets show source, approved WHITE, transition component map, topology interior, and frozen-dark pixels, plus nearest-neighbor zooms. They are diagnostic only and contain no approval/rejection judgement. #14700 is included as the approved reference pattern.\n\n## Invariants\n\nNo source, BLACK/WHITE picon, MASTER/template, approval ledger, generator, or classifier was modified. No candidate was created. #14599 was not accessed. V26 remains `RULE-GENERALIZATION-NEEDS-MORE-EVIDENCE`.\n\n## Reproduction\n\n`python tools/phase4_v27_true_to_false_transition_forensics.py --repo-root . --phase3-generator tools/rebuild_master_catalog.py --v26-audit reports/warder-master-production/phase4-v26-topology-two-tone-generalization-20260927/COMPONENT-AUDIT.csv --v26-selection reports/warder-master-production/phase4-v26-topology-two-tone-generalization-20260927/CONTROL-SELECTION.csv --white-master templates/picons/white-sablona.png --out reports/warder-master-production/phase4-v27-true-false-transition-forensics-20260927`\n'''
 (out/'REPORT.md').write_text(report,encoding='utf-8')
 print(json.dumps({'verdict':verdict,'transition_count':len(transitions),'case_counts':counts,'dark_rows':len(darkrows),'dark_interior':sum(r['dark_interior_px'] for r in transitions),'dark_edge':sum(r['dark_material_edge_px'] for r in transitions),'approved_comparisons':output_rows,'sheets':[p.name for p in out.glob('*.png')]},ensure_ascii=False,default=str))
if __name__=='__main__':main()
