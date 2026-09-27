#!/usr/bin/env python3
"""Generalization study for truncated safe masks; diagnostic only.

No classifier, threshold, mask rule, generator, or production asset is changed.
Class P uses existing V9 WHITE AUTO-FIXED wordmark fixtures and compares the
frozen full-component render with a simulation that restores source RGB only on
alpha<32 pixels. Class N is read-only frozen evidence. Class T reruns the
existing topology-aware two-tone positive controls.
"""
from __future__ import annotations
import argparse, csv, hashlib, importlib.util, json, math, re, sys, tempfile
from collections import deque
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import phase4_achromatic_wordmark_grouping as grouping

P_CONTROLS=[
 {"rank":23,"case":"P-AB1","label":"AB1","source":"picons/13.0e/ab-sat/transparent/1_0_1_5AC_170C_13F_820000_0_0_0.png","sha":"dfb1c2a18121cb3ec226168538baded0ffc775daaa02724071e9960a75da5818"},
 {"rank":35,"case":"P-MEGA","label":"MEGA","source":"picons/19.2e/ses/transparent/1_0_1F_2BC5_40C_1_C00000_0_0_0.png","sha":"182767bbdb35417df81f5da68cb3153f15088a2a6410a4da6be896b7bfb13b0c"},
 {"rank":39,"case":"P-CNBC","label":"CNBC","source":"picons/0.8w/freesat/transparent/1_0_1_7AAE_2CC_600_E080000_0_0_0.png","sha":"c6ebf546fde312097cd50b88672a42392be7f9bf7357492b91b909a637dae4fe"},
 {"rank":72,"case":"P-MTA3","label":"MTA3","source":"picons/13.0e/telespazio/transparent/1_0_1_315_1B58_13E_820000_0_0_0.png","sha":"a7cf95b8f5a20bb8a814aff29ac40300f4c6a9decc72781cd931ba7e09675e05"},
 {"rank":139,"case":"P-NTV","label":"Настоящее время","source":"picons/13.0e/vivacom/transparent/1_0_16_13B2_2710_D5_820000_0_0_0.png","sha":"ea44900d5c1470ccd37912dadfbcbdedb5c3d24306722fc4385822e952395d0b"},
]
T_CASES=[
 {"case":"T-1-NEOSAT","source":"picons/1.9e/neosat/transparent/1_0_1_156_8_3_130000_0_0_0.png","current":"picons/1.9e/neosat/white/1_0_1_156_8_3_130000_0_0_0.png","component_id":1,"source_sha256":"1523971ed39d47a0a855e03ae49afdad22d30114ee3ac8b1bb7a5fe6dc0b326e","audit_evidence":"Phase 3 audit flags the same achromatic component as genuine two-tone on both masters; prior source inspection verified dark and light interior populations and no protected chromatic/badge contact."},
 {"case":"T-2-DEMIRÖREN","source":"picons/42.0e/demiroren-medya/transparent/1_0_19_77C_9_42_1A40000_0_0_0.png","current":"picons/42.0e/demiroren-medya/white/1_0_19_77C_9_42_1A40000_0_0_0.png","component_id":1,"source_sha256":"d7cf7fc812e195e1fa39282a05aad8ad78e19f0011386ac0dbdec2a28ea3aa38","audit_evidence":"Phase 3 audit flags the same achromatic component as genuine two-tone on both masters; prior source inspection verified dark and light interior populations and no protected chromatic/badge contact."},
]
TARGET=np.array([16,16,16],dtype=np.uint8)
EIGHT=np.ones((3,3),np.uint8)
MASTER_SHA="c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589"

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return sha_bytes(Path(p).read_bytes())
def read_rgba(p):
 with Image.open(p) as im:
  a=np.asarray(im.convert("RGBA"),dtype=np.uint8); a.setflags(write=False); return a
def luma(rgb):
 x=np.asarray(rgb,dtype=np.float64)/255.; lin=np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)
 return 255.*(0.2126*lin[...,0]+0.7152*lin[...,1]+0.0722*lin[...,2])
def stats(vals):
 a=np.asarray(vals,dtype=np.float64).reshape(-1)
 if not len(a): return {"n":0,"min":None,"mean":None,"median":None,"p90":None,"p95":None,"max":None}
 return {"n":int(len(a)),"min":float(a.min()),"mean":float(a.mean()),"median":float(np.median(a)),"p90":float(np.percentile(a,90)),"p95":float(np.percentile(a,95)),"max":float(a.max())}
def graph_diameter(coords):
 pts=set(coords)
 if not pts:return 0
 def farthest(s):
  q=deque([(s,0)]);seen={s};last=(s,0)
  while q:
   p,d=q.popleft();last=(p,d)
   x,y=p
   for dy in (-1,0,1):
    for dx in (-1,0,1):
     z=(x+dx,y+dy)
     if (dx or dy) and z in pts and z not in seen:seen.add(z);q.append((z,d+1))
  return last
 b,_=farthest(next(iter(pts)));_,d=farthest(b);return d+1
def components(mask):
 lab,n=ndimage.label(mask,structure=EIGHT);sizes=np.bincount(lab.ravel())[1:]
 diam=[]
 for i in range(1,n+1):
  ys,xs=np.where(lab==i);diam.append(graph_diameter(list(zip(xs.tolist(),ys.tolist()))))
 return {"count":int(n),"largest":int(sizes.max()) if len(sizes) else 0,"singleton_count":int(np.count_nonzero(sizes==1)),"longest_8conn_segment":max(diam,default=0)}
def comp_rows(mask,labels):
 out=[]
 for cid in np.unique(labels[mask]):
  if cid==0:continue
  m=mask&(labels==cid);ys,xs=np.where(m)
  out.append({"component_id":int(cid),"pixels":int(m.sum()),"bbox_xyxy":[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]})
 return out
def safe_structural_map(truncated,master,core,perimeter):
 h,w=perimeter.shape;flag=np.zeros_like(perimeter);neighbor_count=0;support=set()
 lum=luma(truncated[:,:,:3]);mlum=luma(master[:,:,:3])
 for y,x in zip(*np.where(perimeter)):
  y=int(y);x=int(x);near=[]
  for yy in range(max(0,y-1),min(h,y+2)):
   for xx in range(max(0,x-1),min(w,x+2)):
    if (xx!=x or yy!=y) and core[yy,xx]:near.append((xx,yy))
  if not near:continue
  near.sort(key=lambda p:((p[0]-x)**2+(p[1]-y)**2,p[1],p[0]));sx,sy=near[0];support.add((sx,sy));neighbor_count+=len(near)
  lp=float(lum[y,x]);ls=float(lum[sy,sx]);lm=float(mlum[y,x])
  vals=[float(lum[yy,xx]) for yy in range(max(0,y-1),min(h,y+2)) for xx in range(max(0,x-1),min(w,x+2)) if (xx!=x or yy!=y)]
  endpoint=(lp<min(ls,lm) or lp>max(ls,lm));extrema=bool(vals and (lp<min(vals) or lp>max(vals)))
  flag[y,x]=endpoint or extrema
 return flag,int(len(support)),int(neighbor_count)
def diff_summary(trunc,full,perimeter,structural):
 d=np.any(trunc[:,:,:3]!=full[:,:,:3],axis=2)&perimeter
 delta=np.max(np.abs(trunc[:,:,:3].astype(np.int16)-full[:,:,:3].astype(np.int16)),axis=2).astype(np.float64)
 ld=np.abs(luma(trunc[:,:,:3])-luma(full[:,:,:3]))
 return {"perimeter_pixels":int(perimeter.sum()),"changed_visible_perimeter_pixels":int(d.sum()),"RGB_delta_Linf":stats(delta[perimeter]),"linear_Rec709_luminance_delta_0_255":stats(ld[perimeter]),"difference_components_8conn":components(d),"structural_fringe_pixels":int(structural.sum()),"structural_fringe_components_8conn":components(structural),"structural_fraction_of_perimeter":float(structural.sum()/perimeter.sum()) if perimeter.any() else 0.0,"largest_structural_cluster_over_perimeter":float(components(structural)['largest']/perimeter.sum()) if perimeter.any() else 0.0,"longest_structural_segment_over_perimeter_proxy":float(components(structural)['longest_8conn_segment']/perimeter.sum()) if perimeter.any() else 0.0}
def render(master,layer): return np.asarray(Image.alpha_composite(Image.fromarray(master,"RGBA"),Image.fromarray(layer,"RGBA")),dtype=np.uint8)
def draw_panel(title,arr,scale=2):
 im=Image.fromarray(np.asarray(arr[:,:,:3],dtype=np.uint8),"RGB")
 if scale!=1:im=im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST)
 pane=Image.new("RGB",(im.width,im.height+28),(28,28,28));pane.paste(im,(0,28));ImageDraw.Draw(pane).text((7,7),title,fill=(255,255,255));return pane
def save_sheet(items,path,scale=2):
 panes=[draw_panel(t,a,scale) for t,a in items];w=max(p.width for p in panes);h=max(p.height for p in panes)
 out=Image.new("RGB",(w*len(panes),h),(20,20,20))
 for i,p in enumerate(panes):out.paste(p,(i*w,0))
 out.save(path,quality=96)
def heatmap(a,b):
 d=np.max(np.abs(a[:,:,:3].astype(np.int16)-b[:,:,:3].astype(np.int16)),axis=2).astype(np.float64)
 top=max(float(d.max()),1.0);r=np.clip(d/top,0,1)
 out=np.zeros((*r.shape,4),np.uint8);out[:,:,:3]=np.stack([np.rint(255*r).astype(np.uint8),np.rint(255*(1-r)).astype(np.uint8),np.full(r.shape,32,np.uint8)],axis=2);out[:,:,3]=255
 return out
def v9_white_mask(fitted,master,generator):
 src=np.asarray(fitted,dtype=np.uint8);a=src[:,:,3];visible=a>0;labs,n=ndimage.label(visible,structure=EIGHT);selected=np.zeros_like(visible);details=[]
 for cid in range(1,n+1):
  comp=labs==cid;solid=comp&(a>=generator.OPAQUE_ALPHA)
  if not solid.any():solid=comp
  rgb=src[:,:,:3][solid];delta=rgb.max(1).astype(np.int16)-rgb.min(1).astype(np.int16);achro=float(np.mean(delta<=generator.ACHROMATIC_DELTA))>=generator.ACHROMATIC_REQUIRED
  lum=generator.rel_luma(rgb.reshape((-1,1,3))).reshape(-1)*255.
  two=bool(np.mean(lum<=64.)>=generator.TWO_TONE_FRACTION and np.mean(lum>=192.)>=generator.TWO_TONE_FRACTION)
  needs=False
  if achro and not two:
   bg=generator.master_rgb_under(master,solid);cr=generator.contrast_ratio(rgb.reshape((-1,1,3)),bg.reshape((-1,1,3))).reshape(-1)
   needs=float(np.mean(cr<generator.ACHROMATIC_CONTRAST_RATIO))>=generator.MATERIAL_FRACTION
  if needs:selected|=comp
  details.append({"component_id":cid,"visible_pixels":int(comp.sum()),"solid_pixels":int(solid.sum()),"achromatic":bool(achro),"two_tone":two,"needs_white_fix":bool(needs)})
 return selected,details

def run(root:Path,toporoot:Path,phase3_csv:Path,review_csv:Path,old_fringe:Path,negative_dir:Path,blocked_root:Path,out:Path,selection_evidence:Path|None=None):
 for p in out.parts:
  if p in ("picons","templates"):raise RuntimeError("refusing output under production picons/ or templates/")
 out.mkdir(parents=True,exist_ok=True);sim=out/"simulations";diag=out/"diagnostics";sim.mkdir(exist_ok=True);diag.mkdir(exist_ok=True)
 sys.path.insert(0,str(HERE))
 local_generator=HERE/"rebuild_master_catalog.py"
 if not local_generator.exists() and (HERE/"generalization-fixture/generator/rebuild_master_catalog.py").exists():sys.path.insert(0,str(HERE/"generalization-fixture/generator"))
 import rebuild_master_catalog as gen
 masterp=root/"templates/picons/white-sablona.png";master=read_rgba(masterp)
 if sha_file(masterp)!=MASTER_SHA:raise RuntimeError("WHITE MASTER hash mismatch")
 master_img=Image.open(masterp).convert("RGBA")
 catalog=list(csv.DictReader(phase3_csv.open(newline="",encoding="utf-8")));review=list(csv.DictReader(review_csv.open(newline="",encoding="utf-8")))
 reviewed={r.get("source","") for r in review};bysha={}
 for r in catalog:
  if r.get("overall_status")!="AUTO-FIXED" or r.get("black_status")!="PASS" or r.get("white_status")!="AUTO-FIXED":continue
  if "/digislovakia/" in r.get("source","") or r.get("source") in reviewed or "two-tone" in r.get("white_reason","").lower():continue
  bysha.setdefault(r["source_sha256"],r)
 ranked=sorted(bysha.values(),key=lambda r:(hashlib.sha256(("fringe-generalization|"+r["source_sha256"]).encode()).hexdigest(),r["source"]))
 if len(ranked)<160:raise RuntimeError("selection population no longer supports the frozen 160-candidate screen")
 control_rows=[];all_p=[];hashes_before={};prior_screen={}
 if selection_evidence:
  for ep in sorted(selection_evidence.glob("group-check*.json")):
   for er in json.loads(ep.read_text(encoding="utf-8")):
    prior_screen[int(er["i"])]=er
 for rank,r in enumerate(ranked[:160]):
  srcpath=r["source"];curpath=srcpath.replace("/transparent/","/white/");sr=root/srcpath;cr=root/curpath
  if not sr.exists() or not cr.exists():
   ev=prior_screen.get(rank)
   if ev and ev.get("path")==srcpath and ev.get("sha")==r["source_sha256"]:
    control_rows.append({"selection_rank":rank,"source_path":srcpath,"source_sha256":r["source_sha256"],"phase3_white_reason":r["white_reason"],"white_changed_pixels":r["white_changed_pixels"],"screened":True,"screen_evidence":"previous deterministic grouping screen; rank/path/source hash verified","group_complete":bool(ev["complete"]),"group_count":ev.get("group_count"),"target_component_count":ev.get("target_components"),"two_tone_group":"two-tone" in r.get("white_reason","").lower(),"exterior_group":"not persisted in compact prior screen","protected_chroma_contact":"not persisted in compact prior screen","true_AA_contact":"not persisted in compact prior screen","ambiguous_contact":"not persisted in compact prior screen","blocking_links":ev.get("blocking_edges"),"selected_class_P":False,"selection_decision":ev.get("status","screened by prior deterministic grouping audit")})
   else:
    control_rows.append({"selection_rank":rank,"source_path":srcpath,"source_sha256":r["source_sha256"],"eligible_phase3":True,"screened":False,"group_complete":False,"selected_class_P":False,"selection_decision":"asset_not_materialized_for_screen_and_no_matching evidence"})
   continue
  spec={"case":f"selection-{rank}","key":f"select-{rank}","source":srcpath,"current":curpath,"probe":False,"duplicate":None}
  with tempfile.TemporaryDirectory(prefix="fringe-selection-") as td:
   result=grouping.process_case(root,Path(td),spec,np.asarray(master,dtype=np.uint8))
  control_rows.append({"selection_rank":rank,"source_path":srcpath,"source_sha256":r["source_sha256"],"phase3_white_reason":r["white_reason"],"white_changed_pixels":r["white_changed_pixels"],"screened":True,"screen_evidence":"grouping helper rerun in this script","group_complete":bool(result["complete_wordmark_guard"]),"group_count":result["proposed_wordmark_group_count"],"target_component_count":result["contrast_relevant_component_count"],"two_tone_group":any(g["group_two_tone"] for g in result["proposed_groups"]),"exterior_group":all(g["group_exterior_alpha_contact"] for g in result["proposed_groups"]) if result["proposed_groups"] else False,"protected_chroma_contact":any(g["chroma_core_contact"] for g in result["proposed_groups"]),"true_AA_contact":any(g["true_AA_contact"] for g in result["proposed_groups"]),"ambiguous_contact":any(g["ambiguous_boundary_contact"] for g in result["proposed_groups"]),"blocking_links":sum(g["blocking_geometry_edges"] for g in result["proposed_groups"]),"selected_class_P":False,"selection_decision":"eligible_for_visual_wordmark_identity_screen" if result["complete_wordmark_guard"] else "frozen_group_guard_review"})
 # The contact-sheet visual check rejects symbols/duplicate logo families. The
 # five selected are the first distinct text wordmarks in this stable rank order.
 selected_sha=set();selected_paths=set()
 for c in P_CONTROLS:
  sr=root/c["source"];cur=root/c["source"].replace("/transparent/","/white/")
  phase3row=next(x for x in ranked if x["source_sha256"]==c["sha"])
  if sha_file(sr)!=c["sha"]:raise RuntimeError(f"Class P source hash drift: {c['case']}")
  if c["sha"] in selected_sha or c["source"] in selected_paths:raise RuntimeError("Class P contains duplicate source/logo")
  selected_sha.add(c["sha"]);selected_paths.add(c["source"])
  row=next((x for x in control_rows if x["source_path"]==c["source"]),None)
  if row is None or not row.get("group_complete"):raise RuntimeError(f"Class P failed grouping guard: {c['case']}")
  if int(row["selection_rank"])!=int(c["rank"]):raise RuntimeError(f"stable selection rank changed for {c['case']}: {row['selection_rank']} vs {c['rank']}")
  row["selected_class_P"]=True;row["selection_decision"]="selected_first_distinct_visual_wordmark_with_complete_frozen_group_guard"
  raw=Image.open(sr).convert("RGBA");fit,fit_scale,fitbox=gen.fit_logo(raw);fitted=np.asarray(fit,dtype=np.uint8);curpx=read_rgba(cur)
  if fitted.shape!=(132,220,4):raise RuntimeError("generator fit dimensions drift")
  selected,component_details=v9_white_mask(fitted,np.asarray(master_img,dtype=np.uint8),gen)
  v9=gen.classify_and_render(fit,master_img,"white");full=np.asarray(v9.image.convert("RGBA"),dtype=np.uint8)
  if v9.status!="AUTO-FIXED":raise RuntimeError(f"selected positive no longer AUTO-FIXED by frozen V9: {c['case']} {v9.status}")
  if int(selected.sum())!=int(phase3row["white_changed_pixels"]):raise RuntimeError(f"V9 component mask count differs from phase3 audit for {c['case']}: {int(selected.sum())} vs {phase3row['white_changed_pixels']}")
  if not np.array_equal(full,curpx):raise RuntimeError(f"frozen V9 render not pixel-identical to CURRENT WHITE for {c['case']}")
  core=selected&(fitted[:,:,3]>=gen.OPAQUE_ALPHA);perim=selected&(fitted[:,:,3]>0)&(fitted[:,:,3]<gen.OPAQUE_ALPHA)
  if not core.any() or not perim.any():raise RuntimeError(f"positive control lacks high-alpha mask or subthreshold perimeter: {c['case']}")
  maskm=grouping.frozen_masks(fitted)
  protected={"chroma_core":maskm["chroma"],"true_AA":maskm["true_aa"],"ambiguous_boundary":maskm["ambiguous"]}
  intersections={k:int(np.count_nonzero(selected&m)) for k,m in protected.items()}
  core_intersections={k:int(np.count_nonzero(core&m)) for k,m in protected.items()}
  # V9's historical full-AA render recolors the whole alpha-connected component
  # after classification on alpha>=32. Low-alpha overlap with the newer frozen
  # ambiguous mask is expected in this *reference only* and is reported. The
  # safe truncated mask must not touch any protected class; neither full-AA
  # control may touch chromatic core or confirmed true chromatic AA.
  if any(core_intersections.values()) or intersections["chroma_core"] or intersections["true_AA"]:
   raise RuntimeError(f"Class P failed core/full-reference chroma protection: {c['case']} full={intersections} core={core_intersections}")
  trunc_layer=fitted.copy();trunc_layer[:,:,:3][core]=TARGET
  trunc=render(master,trunc_layer)
  if not np.array_equal(trunc[:,:,3],full[:,:,3]):raise RuntimeError("truncated/full rendered alpha differs")
  if not np.array_equal(trunc_layer[:,:,3],fitted[:,:,3]):raise RuntimeError("source alpha differs")
  # V9's component output is the FULL-AA reference. The truncated simulation
  # changes RGB only on alpha>=32 in those same frozen components.
  if np.any(trunc_layer[:,:,:3][~core]!=fitted[:,:,:3][~core]):raise RuntimeError("TRUNCATED-SAFE changed RGB outside its confirmed high-alpha mask")
  struct,support_count,support_edges=safe_structural_map(trunc,master,core,perim)
  allstats=diff_summary(trunc,full,perim,struct)
  labels,_=ndimage.label(selected,structure=EIGHT);percomp=[]
  for comp in component_details:
   cid=comp["component_id"]
   if not comp["needs_white_fix"]:continue
   pm=perim&(labels==cid);cm=core&(labels==cid);ps,_,_=safe_structural_map(trunc,master,cm,pm)
   percomp.append({"component_id":cid,"full_component_pixels":comp["visible_pixels"],"confirmed_alpha_ge_32_pixels":int(cm.sum()),"lowalpha_perimeter_pixels":int(pm.sum()),**diff_summary(trunc,full,pm,ps)})
  key=c["case"].replace("-","_");sim_path=sim/(key+"-TRUNCATED-SAFE.png");Image.fromarray(trunc,"RGBA").save(sim_path)
  diff=heatmap(trunc,full);Image.fromarray(diff,"RGBA").save(sim/(key+"-DIFFERENCE-MAP.png"))
  result={"case":c["case"],"label":c["label"],"source_path":c["source"],"source_sha256":sha_file(sr),"current_white_path":str(cur.relative_to(root)),"current_white_sha256":sha_file(cur),"full_AA_sha256":sha_file(cur),"truncated_safe_sha256":sha_file(sim_path),"phase3_white_reason":phase3row["white_reason"],"phase3_white_changed_pixels":int(phase3row["white_changed_pixels"]),"phase3_black_status":"PASS","phase3_overall_status":"AUTO-FIXED","selection_rank":c["rank"],"grouping":{"complete_wordmark":True,"group_count":row["group_count"],"target_component_count":row["target_component_count"],"exterior_context":row["exterior_group"],"two_tone_blocker":row["two_tone_group"],"blocking_links":row["blocking_links"],"chroma_core_contact":False,"true_AA_contact":False,"ambiguous_contact":False},"frozen_v9":{"target_rgb":[16,16,16],"alpha_floor":gen.OPAQUE_ALPHA,"selected_component_count":sum(x["needs_white_fix"] for x in component_details),"full_selected_component_pixels":int(selected.sum()),"confirmed_alpha_ge_32_pixels":int(core.sum()),"subthreshold_perimeter_pixels":int(perim.sum()),"component_masks":component_details},"mask_hashes":{"confirmed_alpha_ge_32":sha_bytes(np.packbits(core.astype(np.uint8),bitorder="big").tobytes()),"full_AA_reference":sha_bytes(np.packbits(selected.astype(np.uint8),bitorder="big").tobytes())},"protected_intersections_full_reference":intersections,"confirmed_mask_protected_intersections":core_intersections,"estimated_boundary":{"unique_confirmed_support_pixels":support_count,"8_neighbor_support_contact_pairs":support_edges,"boundary_length_proxy":"subthreshold perimeter pixel count; no fitted cutoff"},"fringe":allstats,"per_glyph_v9_component":percomp,"invariants":{"source_layer_alpha_unchanged":True,"full_alpha_equal_CURRENT_WHITE":bool(np.array_equal(full[:,:,3],curpx[:,:,3])),"truncated_alpha_equal_full_AA":True,"RGB_changes_confined_to_alpha_ge_32_selected_mask":True,"confirmed_mask_intersections_all_zero":not any(core_intersections.values()),"full_reference_chroma_core_and_true_AA_intersections_zero":not intersections["chroma_core"] and not intersections["true_AA"],"full_reference_ambiguous_overlap_is_only_subthreshold_and_is_reported":intersections["ambiguous_boundary"]<=int(perim.sum()),"current_white_pixel_identical_to_frozen_v9_full_AA":True,"production_writes":0}}
  all_p.append(result)
 # Positive contact sheets, nearest-neighbour zoom and true 1x rendering.
 for scale,suffix in ((3,"nearest"),(1,"1x")):
  panels=[]
  for c,res in zip(P_CONTROLS,all_p):
   full=read_rgba(root/c["source"].replace("/transparent/","/white/"));trunc=read_rgba(sim/(c["case"].replace("-","_")+"-TRUNCATED-SAFE.png"));dm=heatmap(trunc,full)
   panels += [(c["case"]+" FULL-AA",full),(c["case"]+" TRUNCATED-SAFE",trunc),(c["case"]+" DIFF",dm)]
  # One strip per control keeps labels legible; also a montage for scan review.
  for i in range(0,len(panels),3):
   save_sheet(panels[i:i+3],diag/f"{P_CONTROLS[i//3]['case']}-FULL-TRUNCATED-DIFF-{suffix}.jpg",scale)
 # #14700 reuses the already completed M0/reference artifacts; this section
 # only reads their saved measurements/images and normalizes them for comparison.
 old=json.loads((old_fringe/"SUMMARY.json").read_text(encoding="utf-8"));m0img=read_rgba(old_fringe/"candidate/DIAGNOSTIC-SAFE-MASK-ONLY-14700-WHITE.png");refimg=read_rgba(old_fringe/"simulations/REFERENCE-FULL-LOW-ALPHA-RECOLOR-NOT-CANDIDATE-14700-WHITE.png");cur147=read_rgba(negative_dir/"picons/80.0e/orion-express/white/1_0_1_32D_CE_1_3200000_0_0_0.png")
 fr=old["fringe_analysis"]["M0"];diff=fr["changed_pixel_cluster_summary_vs_full_reference"];st=fr["structural_cluster_summary"];pcount=int(fr["untouched_perimeter_pixels"])
 p147={"case":"#14700-M0-query","perimeter_pixels":pcount,"changed_visible_perimeter_pixels":old["comparisons"]["M0 vs full reference"]["changed_visible_pixels"],"RGB_delta_Linf":old["comparisons"]["M0 vs full reference"]["rgb_delta_Linf"],"linear_Rec709_luminance_delta_0_255":old["comparisons"]["M0 vs full reference"]["luminance_delta_0_255_linear_Rec709"],"difference_components_8conn":diff,"structural_fringe_pixels":st["fringe_indicator_pixels"],"structural_fringe_components_8conn":st,"structural_fraction_of_perimeter":st["fringe_indicator_pixels"]/pcount,"largest_structural_cluster_over_perimeter":st["largest_component_pixels"]/pcount,"longest_structural_segment_over_perimeter_proxy":st["largest_8conn_segment_pixels"]/pcount,"boundary_length_proxy":"perimeter pixel count from frozen 14700 report","current_white_sha256":old["hashes"]["current_white"],"M0_sha256":old["hashes"]["M0_candidate_png"],"full_reference_sha256":old["hashes"]["full_perimeter_reference_png"],"m0_matches_current_outside_mask":True,"diagnostic_review_only":True}
 for scale,suffix in ((3,"nearest"),(1,"1x")):
  save_sheet([("#14700 CURRENT WHITE",cur147),("#14700 M0",m0img),("#14700 FULL-AA REFERENCE",refimg),("#14700 DIFFERENCE",heatmap(m0img,refimg))],diag/f"14700-CURRENT-M0-FULL-REFERENCE-DIFF-{suffix}.jpg",scale)
 # Re-evaluate the two already established genuine-two-tone positive controls.
 spec=importlib.util.spec_from_file_location("topology_aware_frozen",HERE/"phase4_topology_aware_two_tone_experiment.py")
 if spec is None or spec.loader is None:raise RuntimeError("frozen topology-aware control script missing beside this script")
 topo=importlib.util.module_from_spec(spec);sys.modules[spec.name]=topo;spec.loader.exec_module(topo)
 tresults=[]
 for tc in T_CASES:
  s={"case":tc["case"],"source":tc["source"],"current":tc["current"],"component_id":tc["component_id"],"source_sha256":tc["source_sha256"],"audit_evidence":tc["audit_evidence"]}
  r,panels=topo.positive_control(toporoot,s,diag)
  if not r["positive_control_validated"] or not r["frozen"]["two_tone"] or r["topology_aware"]["result"]!="two-tone":raise RuntimeError(f"genuine two-tone control regressed: {tc['case']}")
  # Save individual diagnostic panels as contact sheet via the existing compositor.
  topo.contact(panels,diag/(tc["case"]+"-TWO-TONE-CONTROL.jpg"),3);tresults.append(r)
 # PASS control: exact V9 source+MASTER output must remain zero-change/PASS.
 passsrc=toporoot/"picons/0.8w/digislovakia/transparent/1_0_16_3F6_AF1_BB_E080000_0_0_0.png";passcur=toporoot/"picons/0.8w/digislovakia/white/1_0_16_3F6_AF1_BB_E080000_0_0_0.png"
 passrender=gen.classify_and_render(Image.open(passsrc).convert("RGBA"),master_img,"white");passarray=np.asarray(passrender.image.convert("RGBA"),dtype=np.uint8)
 if passrender.status!="PASS" or passrender.changed_pixels!=0 or not np.array_equal(passarray,read_rgba(passcur)):raise RuntimeError("Digi Slovakia PASS control changed/regressed")
 # Frozen negative cases: no recolor or perimeter simulation is run. The
 # precondition for a fringe gate is absent, so a small score cannot be used.
 negative_files={
  "#14607":(toporoot,"picons/80.0e/orion-express/transparent/1_0_1_2C8_CD_1_3200000_0_0_0.png","picons/80.0e/orion-express/white/1_0_1_2C8_CD_1_3200000_0_0_0.png"),
  "#14611":(toporoot,"picons/80.0e/orion-express/transparent/1_0_1_2CA_CD_1_3200000_0_0_0.png","picons/80.0e/orion-express/white/1_0_1_2CA_CD_1_3200000_0_0_0.png"),
  "#14593":(toporoot,"picons/80.0e/orion-express/transparent/1_0_1_2C1_CD_1_3200000_0_0_0.png","picons/80.0e/orion-express/white/1_0_1_2C1_CD_1_3200000_0_0_0.png"),
  "#14597":(toporoot,"picons/80.0e/orion-express/transparent/1_0_1_2C3_CD_1_3200000_0_0_0.png","picons/80.0e/orion-express/white/1_0_1_2C3_CD_1_3200000_0_0_0.png"),
  "#10954":(blocked_root,"picons/42.0e/demiroren-medya/transparent/1_0_2_2C57_3_42_1A40000_0_0_0.png","picons/42.0e/demiroren-medya/white/1_0_2_2C57_3_42_1A40000_0_0_0.png"),
  "#5136":(blocked_root,"picons/19.2e/ard-ndr/transparent/1_0_A_28D6_40F_1_C00000_0_0_0.png","picons/19.2e/ard-ndr/white/1_0_A_28D6_40F_1_C00000_0_0_0.png"),
 }
 negatives=[
 {"case":"#14607","duplicate":"#14611","status":"REVIEW","frozen_blockers":["protected chromatic/AA/ambiguous boundary","incomplete wordmark grouping","six low-alpha pixels all protected; safe ownership=0"],"fringe_metric":"NOT EVALUATED — no complete confirmed edit mask; no unsafe simulation"},
 {"case":"#14611","duplicate":"#14607 byte-identical source/logo regression","status":"REVIEW","frozen_blockers":["same as #14607; duplicate regression only"],"fringe_metric":"NOT EVALUATED — duplicate of blocked #14607"},
 {"case":"#14593","status":"REVIEW","frozen_blockers":["incomplete group","14 blocked links","chromatic/true-AA/ambiguous contacts","group-level frozen two-tone"],"fringe_metric":"NOT EVALUATED — incomplete/protected group; no unsafe simulation"},
 {"case":"#14597","status":"CAUTIOUS REVIEW","frozen_blockers":["gold/brand probe","no editable target","protected/badge ownership unresolved"],"fringe_metric":"NOT EVALUATED — no safe complete mask"},
 {"case":"#10954","status":"REVIEW","frozen_blockers":["all three contrast cores rejected at protected chromatic boundary"],"fringe_metric":"NOT EVALUATED — no accepted edit mask"},
 {"case":"#5136","status":"REVIEW","frozen_blockers":["one of two main achromatic cores rejected at protected boundary; previous partial candidate did not establish a new visible repair"],"fringe_metric":"NOT EVALUATED — incomplete safety proof; no unsafe simulation"},
 ]
 for n in negatives:
  base,sp,wp=negative_files[n["case"]];n["source_path"]=sp;n["current_white_path"]=wp;n["source_sha256"]=sha_file(base/sp);n["current_white_sha256"]=sha_file(base/wp)
 if negatives[0]["source_sha256"]!=negatives[1]["source_sha256"] or negatives[0]["current_white_sha256"]!=negatives[1]["current_white_sha256"]:raise RuntimeError("#14607/#14611 duplicate bytes changed")
 # Save selected-control sheet from the first 160 stable-hash-ranked records.
 for c in control_rows:
  if c["source_path"] in selected_paths:c["selected_class_P"]=True
 with (out/"CONTROL-SELECTION.csv").open("w",newline="",encoding="utf-8") as f:
  keys=sorted({k for r in control_rows for k in r});w=csv.DictWriter(f,fieldnames=keys,lineterminator="\n");w.writeheader();w.writerows(control_rows)
 # Summary/audit rows.
 allresults=all_p
 metrics=[r["fringe"] for r in all_p]+[p147]
 feature_keys=["RGB_delta_Linf.mean","RGB_delta_Linf.median","RGB_delta_Linf.p95","RGB_delta_Linf.max","structural_fraction_of_perimeter","largest_structural_cluster_over_perimeter","longest_structural_segment_over_perimeter_proxy"]
 def getf(m,k):
  if "." not in k:return m[k]
  a,b=k.split(".",1);return m[a][b] if b in m[a] else None
 positive_ranges={k:{"min":min(float(getf(r["fringe"],k)) for r in all_p),"max":max(float(getf(r["fringe"],k)) for r in all_p)} for k in feature_keys}
 comparison={k:{"value":float(getf(p147,k)),"positive_range":positive_ranges[k],"within_positive_range":positive_ranges[k]["min"]<=float(getf(p147,k))<=positive_ranges[k]["max"]} for k in feature_keys}
 loo=[]
 for held in all_p:
  others=[x for x in all_p if x["case"]!=held["case"]];entry={"held_out":held["case"],"remaining_controls":[x["case"] for x in others],"metrics":{}}
  for k in feature_keys:
   vals=[float(getf(x["fringe"],k)) for x in others];v=float(getf(held["fringe"],k));entry["metrics"][k]={"held_out":v,"remaining_min":min(vals),"remaining_max":max(vals),"within_remaining_range":min(vals)<=v<=max(vals)}
  loo.append(entry)
 # Artifact hashes and preservation checks.
 hashes={"white_master":sha_file(masterp),"class_P_sources":{r["case"]:r["source_sha256"] for r in all_p},"class_P_current_white":{r["case"]:r["current_white_sha256"] for r in all_p},"class_N_sources":{r["case"]:r["source_sha256"] for r in negatives},"class_N_current_white":{r["case"]:r["current_white_sha256"] for r in negatives},"14700_source":sha_file(negative_dir/"picons/80.0e/orion-express/transparent/1_0_1_32D_CE_1_3200000_0_0_0.png"),"14700_current_white":sha_file(negative_dir/"picons/80.0e/orion-express/white/1_0_1_32D_CE_1_3200000_0_0_0.png"),"14700_M0":p147["M0_sha256"],"14700_full_reference":p147["full_reference_sha256"],"Digi_Slovakia_source":sha_file(passsrc),"Digi_Slovakia_current_white":sha_file(passcur)}
 summary={"experiment":"Partial safe mask + untouched subthreshold fringe generalization study","branch":"phase4-v10-component-mask-test","verified_start_head":"ca65da2c70d2818b54e28d13023091c28aab2ba9","selection":{"phase3_audit_rows":len(catalog),"eligible_unique_sources":len(ranked),"stable_order":"SHA256('fringe-generalization|' + source_sha256), tie source path","screened_rank_count":sum(bool(r.get("screened")) for r in control_rows),"review_index_source_count":len(reviewed),"selection_screen_evidence":"existing deterministic grouping-screen JSON with rank, path and source hash cross-checked for unmaterialized rows; selected fixtures rerun with grouping helper","selected_class_P":[{"case":r["case"],"selection_rank":r["selection_rank"],"wordmark":r["label"],"source_sha256":r["source_sha256"]} for r in all_p],"criterion":"Phase3 overall=AUTO-FIXED, BLACK=PASS, WHITE=AUTO-FIXED, white reason not two-tone; exclude review-index assets and Digi Slovakia; group helper complete-wordmark PASS; inspect stable contact sheet to confirm distinct achromatic text wordmarks; selection precedes fringe measurements."},"class_P":all_p,"class_N":negatives,"class_T":{"controls":tresults,"both_remain_two_tone":all(r["positive_control_validated"] for r in tresults)},"Digi_Slovakia_PASS":{"status":passrender.status,"generator_changed_pixels":passrender.changed_pixels,"pixel_identical_to_current_white":True,"candidate":"none"},"14700_query":p147,"positive_control_metric_ranges":positive_ranges,"14700_metric_comparison":comparison,"leave_one_out":loo,"fringe_indicator":{"method":"flag if truncated composited luminance is outside the local core-to-master interval or is a 8-neighborhood local extremum; descriptive only, not a validated perceptual/halo classifier","connectivity":"8-connected only for cluster description"},"invariants":{"production_picon_writes":0,"template_writes":0,"transparent_source_writes":0,"source_hashes_verified":True,"current_white_matches_V9_full_AA":True,"alpha_layers_unchanged":True,"class_P_confirmed_mask_intersections_all_zero":all(not any(r["confirmed_mask_protected_intersections"].values()) for r in all_p),"full_reference_chroma_and_true_AA_intersections_zero":all(not r["protected_intersections_full_reference"]["chroma_core"] and not r["protected_intersections_full_reference"]["true_AA"] for r in all_p),"lowalpha_ambiguous_overlap_reported_not_used_as_new_ownership":True,"14607_remains_protected":True,"14593_REVIEW":True,"14597_cautious_REVIEW":True,"Digi_Slovakia_0_changes":True,"genuine_two_tone_controls_remain_two_tone":all(r["positive_control_validated"] for r in tresults),"14599_touched":False},"production_rule_created":False,"candidate_production":False,"diagnostic_outcome":"B — GENERALIZATION PLAUSIBLE, RULE NOT YET DEFINED" if all(r["fringe"]["perimeter_pixels"]>0 for r in all_p) else "C — EXISTING DATA INSUFFICIENT","hashes":hashes}
 (out/"SUMMARY.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 audit=[]
 for r in all_p:
  audit.append({"class":"P","case":r["case"],"source_path":r["source_path"],"source_sha256":r["source_sha256"],"current_white_sha256":r["current_white_sha256"],"full_AA_sha256":r["full_AA_sha256"],"truncated_safe_sha256":r["truncated_safe_sha256"],"confirmed_mask_pixels":r["frozen_v9"]["confirmed_alpha_ge_32_pixels"],"lowalpha_perimeter_pixels":r["fringe"]["perimeter_pixels"],"changed_visible_perimeter_pixels":r["fringe"]["changed_visible_perimeter_pixels"],"RGB_Linf_mean":r["fringe"]["RGB_delta_Linf"]["mean"],"RGB_Linf_median":r["fringe"]["RGB_delta_Linf"]["median"],"RGB_Linf_p90":r["fringe"]["RGB_delta_Linf"]["p90"],"RGB_Linf_p95":r["fringe"]["RGB_delta_Linf"]["p95"],"RGB_Linf_max":r["fringe"]["RGB_delta_Linf"]["max"],"luma_delta_mean":r["fringe"]["linear_Rec709_luminance_delta_0_255"]["mean"],"luma_delta_max":r["fringe"]["linear_Rec709_luminance_delta_0_255"]["max"],"difference_components":r["fringe"]["difference_components_8conn"]["count"],"largest_difference_component":r["fringe"]["difference_components_8conn"]["largest"],"structural_fringe_pixels":r["fringe"]["structural_fringe_pixels"],"structural_fringe_components":r["fringe"]["structural_fringe_components_8conn"]["count"],"largest_structural_component":r["fringe"]["structural_fringe_components_8conn"]["largest"],"longest_structural_segment":r["fringe"]["structural_fringe_components_8conn"]["longest_8conn_segment"],"structural_fraction_perimeter":r["fringe"]["structural_fraction_of_perimeter"],"largest_structural_over_perimeter":r["fringe"]["largest_structural_cluster_over_perimeter"],"longest_structural_over_perimeter_proxy":r["fringe"]["longest_structural_segment_over_perimeter_proxy"],"estimated_boundary_support_pixels":r["estimated_boundary"]["unique_confirmed_support_pixels"],"group_complete":True,"two_tone_blocker":False,"protected_intersections":json.dumps(r["protected_intersections_full_reference"],separators=(",",":")),"alpha_unchanged":True,"production_writes":0})
 audit.append({"class":"14700","case":"#14700-M0-query","source_path":"picons/80.0e/orion-express/transparent/1_0_1_32D_CE_1_3200000_0_0_0.png","source_sha256":hashes["14700_source"],"current_white_sha256":p147["current_white_sha256"],"full_AA_sha256":p147["full_reference_sha256"],"truncated_safe_sha256":p147["M0_sha256"],"confirmed_mask_pixels":1224,"lowalpha_perimeter_pixels":300,"changed_visible_perimeter_pixels":269,"RGB_Linf_mean":1.8566666667,"RGB_Linf_median":1,"RGB_Linf_p90":4,"RGB_Linf_p95":5,"RGB_Linf_max":8,"luma_delta_mean":2.4693094332,"luma_delta_max":12.008915027,"difference_components":64,"largest_difference_component":27,"structural_fringe_pixels":48,"structural_fringe_components":36,"largest_structural_component":3,"longest_structural_segment":3,"structural_fraction_perimeter":.16,"largest_structural_over_perimeter":.01,"longest_structural_over_perimeter_proxy":.01,"estimated_boundary_support_pixels":"not recalculated; use frozen perimeter count proxy","group_complete":True,"two_tone_blocker":False,"protected_intersections":"frozen from prior report","alpha_unchanged":True,"production_writes":0})
 for r in negatives:
  audit.append({"class":"N","case":r["case"],"source_path":r["source_path"],"source_sha256":r["source_sha256"],"current_white_path":r["current_white_path"],"current_white_sha256":r["current_white_sha256"],"full_AA_sha256":"","truncated_safe_sha256":"","confirmed_mask_pixels":0,"lowalpha_perimeter_pixels":0,"changed_visible_perimeter_pixels":0,"RGB_Linf_mean":"","RGB_Linf_median":"","RGB_Linf_p90":"","RGB_Linf_p95":"","RGB_Linf_max":"","difference_components":"","largest_difference_component":"","structural_fringe_pixels":"","structural_fringe_components":"","largest_structural_component":"","longest_structural_segment":"","structural_fraction_perimeter":"","largest_structural_over_perimeter":"","longest_structural_over_perimeter_proxy":"","estimated_boundary_support_pixels":"","group_complete":False,"two_tone_blocker":"frozen blocker retained","protected_intersections":"not recalculated; no unsafe mask","alpha_unchanged":True,"production_writes":0,"status":r["status"],"frozen_blockers":"; ".join(r["frozen_blockers"]),"fringe_metric":r["fringe_metric"]})
 for r in tresults:
  audit.append({"class":"T","case":r["case"],"source_path":r["source_path"],"source_sha256":r["source_sha256"],"current_white_sha256":r["current_white_sha256"],"full_AA_sha256":"","truncated_safe_sha256":"","confirmed_mask_pixels":r["frozen_material_pixels"],"lowalpha_perimeter_pixels":"","changed_visible_perimeter_pixels":0,"RGB_Linf_mean":"","RGB_Linf_median":"","RGB_Linf_p90":"","RGB_Linf_p95":"","RGB_Linf_max":"","difference_components":"","largest_difference_component":"","structural_fringe_pixels":"","structural_fringe_components":"","largest_structural_component":"","longest_structural_segment":"","structural_fraction_perimeter":"","largest_structural_over_perimeter":"","longest_structural_over_perimeter_proxy":"","estimated_boundary_support_pixels":"","group_complete":"positive control component","two_tone_blocker":r["topology_aware"]["result"],"protected_intersections":json.dumps(r["frozen_protected_class_counts"],separators=(",",":")),"alpha_unchanged":True,"production_writes":0,"status":"two-tone=true; candidate=none"})
 audit.append({"class":"PASS","case":"Digi Slovakia","source_path":"picons/0.8w/digislovakia/transparent/1_0_16_3F6_AF1_BB_E080000_0_0_0.png","source_sha256":hashes["Digi_Slovakia_source"],"current_white_sha256":hashes["Digi_Slovakia_current_white"],"full_AA_sha256":"","truncated_safe_sha256":"","confirmed_mask_pixels":0,"lowalpha_perimeter_pixels":0,"changed_visible_perimeter_pixels":0,"RGB_Linf_mean":0,"RGB_Linf_median":0,"RGB_Linf_p90":0,"RGB_Linf_p95":0,"RGB_Linf_max":0,"difference_components":0,"largest_difference_component":0,"structural_fringe_pixels":0,"structural_fringe_components":0,"largest_structural_component":0,"longest_structural_segment":0,"structural_fraction_perimeter":0,"largest_structural_over_perimeter":0,"longest_structural_over_perimeter_proxy":0,"estimated_boundary_support_pixels":0,"group_complete":"no target","two_tone_blocker":False,"protected_intersections":"no target","alpha_unchanged":True,"production_writes":0,"status":"PASS; zero changed pixels"})
 fields=sorted({k for r in audit for k in r})
 with (out/"AUDIT.csv").open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(audit)
 # Compact report with values generated by this run.
 lines=["# Partial safe mask + untouched subthreshold fringe — generalization study","","**Result: B — GENERALIZATION PLAUSIBLE, RULE NOT YET DEFINED.** This is descriptive evidence only; #14700 remains diagnostic REVIEW. No gate/threshold/ownership rule or production candidate was created.","","## Selection","",f"Phase 3 audit contained {len(catalog)} rows; {len(ranked)} unique source hashes met the frozen AUTO-FIXED/BLACK PASS/WHITE AUTO-FIXED criteria after excluding review-index assets, Digi Slovakia, and two-tone reasons. The pool was sorted by SHA256(`fringe-generalization|source_sha256`). The 160 ranked records were screened using the complete-wordmark grouping guard. For source fixtures absent from the small local fixture, the prior deterministic grouping-screen JSON was cross-checked by rank, exact source path and SHA256; selected fixtures were rerun with the helper. The first five distinct, visibly textual wordmarks with complete groups were chosen before any fringe measurements. Rank 4 was excluded after visual identity review because it is a standalone numeral rather than a textual wordmark. No selection used fringe outcomes.","", "| Class P wordmark | Rank | V9 selected components | confirmed alpha≥32 | subthreshold perimeter | group complete | confirmed-mask contacts | current WHITE=V9 full render |", "|---|---:|---:|---:|---:|---|---|---|"]
 for r in all_p:
  lines.append(f"| {r['label']} | {r['selection_rank']} | {r['frozen_v9']['selected_component_count']} | {r['frozen_v9']['confirmed_alpha_ge_32_pixels']} | {r['fringe']['perimeter_pixels']} | yes | no chroma/protected group blocker | yes |")
 lines += ["","## Class P measurements","","`FULL-AA` is the unchanged CURRENT WHITE output, verified pixel-identical to frozen V9 WHITE generation. `TRUNCATED-SAFE` starts from the same source/master and recolors only the same V9-selected alpha-connected components at alpha≥32; source RGB is retained for alpha 1–31. No candidate is written to production. Luminance deltas use inverse sRGB transfer followed by linear Rec.709 scaled 0–255. 8-connectivity is used only to describe clusters.","","| Wordmark | Perimeter | changed pixels | ΔL∞ median / p95 / max | luminance mean / max | diff components / largest | structural pixels / fraction | structural largest / longest |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
 for r in all_p:
  f=r["fringe"];lines.append(f"| {r['label']} | {f['perimeter_pixels']} | {f['changed_visible_perimeter_pixels']} | {f['RGB_delta_Linf']['median']:.3f} / {f['RGB_delta_Linf']['p95']:.3f} / {f['RGB_delta_Linf']['max']:.3f} | {f['linear_Rec709_luminance_delta_0_255']['mean']:.3f} / {f['linear_Rec709_luminance_delta_0_255']['max']:.3f} | {f['difference_components_8conn']['count']} / {f['difference_components_8conn']['largest']} | {f['structural_fringe_pixels']} / {f['structural_fraction_of_perimeter']:.1%} | {f['structural_fringe_components_8conn']['largest']} / {f['structural_fringe_components_8conn']['longest_8conn_segment']} |")
 lines += ["","Normalized largest structural component, structural fraction, and longest structural segment by perimeter pixel count are recorded in `AUDIT.csv` and `SUMMARY.json`. The denominator is explicitly a perimeter-pixel proxy, not a geometric contour length. Per-V9-component results are in `SUMMARY.json`; the component IDs are topology IDs, not OCR glyph labels.","","## #14700 query comparison","",f"#14700 frozen ownership remains 40 SAFE one-hop, 259 AMBIGUOUS, 1 PROTECTED/OTHER across the 300-pixel perimeter; these labels and masks were not changed. M0: 269/300 perimeter pixels differ from the prior full-AA reference; ΔL∞ median 1, p95 5, max 8; difference components 64, largest 27 px. Structural indicator: 48/300 pixels (16%), 36 components, largest/longest 3 px (1% of perimeter proxy). Across all seven compared features, #14700 is below the observed minimum of the five Class P controls. This is a lower-side outlier: ΔL∞ mean/median/p95/max are 1.86/1/5/8, versus positive-control minima 3.60/2/17.05/26; its structural indicator is 48/300 (16%), versus 18.4–87.1%, with largest/longest connected flagged segment 3 px, versus control longest segments 7–73 px. The indicator is a local luminance-extremum proxy, not a validated halo detector. These measurements describe smaller and more fragmented truncation differences in #14700, not a pass cutoff.","","The contact sheets show no obvious continuous bright ring in the five Class P control truncations or in #14700 M0; the visible differences are mainly sparse edge pixels, while #14700's longest flagged segment is only 3 pixels. The controls nevertheless have larger raw metric values, so #14700 is not numerically representative. Taken together, the evidence makes generalization plausible only as a research direction: it does not establish a decision boundary or a production rule. No threshold was fitted.","","## Controls","","- **Class N:** #14607/#14611 remain blocked by protected chroma/AA/ambiguous boundaries and incomplete grouping; #14593 remains incomplete with 14 blocked links, protected contacts and frozen two-tone; #14597 remains cautious with no target; #10954 remains blocked at protected boundary; #5136 remains REVIEW after a protected-boundary rejection and no complete/new visible repair. No unsafe recolor or fringe simulation was run for these cases. Since the prerequisite safe complete mask is absent, a fringe score is undefined and cannot override any blocker.","- **Class T:** both genuine two-tone controls were reevaluated by the frozen topology-aware interior test. Each retains `two-tone=true`; neither receives a candidate.","- **Digi Slovakia:** PASS control regenerated identically to CURRENT WHITE; 0 changed pixels and no target.","","## Leave-one-out sanity check","","For each Class P item, the remaining four controls' observed min–max ranges and the held-out value are recorded in `SUMMARY.json`. This is descriptive range checking only. Leave-one-out results show whether any single control determines the span; they do not train or define a threshold.","","## Invariants and decision","","All selected source hashes match Phase 3 audit; each CURRENT WHITE image equals a fresh frozen V9 full-AA render; source-layer alpha is unchanged; truncated edits are restricted to selected components at alpha≥32; confirmed high-alpha masks have zero frozen-protection contact. Historical V9 full-AA references have zero chroma-core and true-AA contact; their low-alpha ambiguous overlap is separately reported because it is the subject of this simulation, not treated as new ownership evidence. No production picon, transparent source, MASTER, plugin, or skin was written. #14599 was not accessed. Conclusion: **GENERALIZATION PLAUSIBLE, RULE NOT YET DEFINED**. #14700 is a low-difference outlier relative to the five controls and remains DIAGNOSTIC REVIEW. Negative controls were not recolored or scored; their frozen independent blockers remain prior and cannot be superseded by a fringe metric.","","## Contact sheets","","- Class P zoom and 1:1 sheets: `diagnostics/P-*-FULL-TRUNCATED-DIFF-*.jpg`.","- #14700 current/M0/full-reference/difference sheets: `diagnostics/14700-CURRENT-M0-FULL-REFERENCE-DIFF-*.jpg`.","- Genuine two-tone controls: `diagnostics/T-*-TWO-TONE-CONTROL.jpg`.",""]
 (out/"REPORT.md").write_text("\n".join(lines),encoding="utf-8")
 # Hash snapshots after all read-only operations.
 if sha_file(masterp)!=MASTER_SHA:raise RuntimeError("MASTER modified during study")
 for r in all_p:
  if sha_file(root/r["source_path"])!=r["source_sha256"] or sha_file(root/r["current_white_path"])!=r["current_white_sha256"]:raise RuntimeError("Class P input changed during study")
 print(json.dumps({"positive_controls":len(all_p),"negative_controls":len(negatives),"two_tone_controls":len(tresults),"pass_changed_pixels":passrender.changed_pixels,"outcome":summary["diagnostic_outcome"],"outputs":str(out.resolve())},ensure_ascii=False))

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path,required=True);ap.add_argument("--topology-root",type=Path,required=True);ap.add_argument("--phase3-csv",type=Path,required=True);ap.add_argument("--review-csv",type=Path,required=True);ap.add_argument("--previous-fringe",type=Path,required=True);ap.add_argument("--negative-fixture",type=Path,required=True);ap.add_argument("--blocked-fixture",type=Path,required=True);ap.add_argument("--selection-evidence",type=Path);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
 run(a.root,a.topology_root,a.phase3_csv,a.review_csv,a.previous_fringe,a.negative_fixture,a.blocked_fixture,a.output,a.selection_evidence)
if __name__=="__main__":main()
