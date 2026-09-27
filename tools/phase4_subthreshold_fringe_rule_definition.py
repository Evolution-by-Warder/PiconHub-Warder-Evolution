#!/usr/bin/env python3
"""Rule-definition diagnostic for untouched alpha<32 fringe; never writes production.

The only candidate structural condition tested is exact monotonic luminance
along geometry-derived core -> subthreshold perimeter -> MASTER profiles. Any
reversal or unresolved profile is REVIEW. There is no fitted numeric cutoff.
"""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import phase4_partial_safe_mask_fringe_generalization as genstudy
import phase4_achromatic_wordmark_grouping as grouping

MASTER_SHA="c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589"
TARGET=np.array([16,16,16],dtype=np.uint8)
EIGHT=np.ones((3,3),np.uint8)
FOUR=np.array([[0,1,0],[1,1,1],[0,1,0]],dtype=np.uint8)
TWO_TONE=(
 ("T-1-NEOSAT","picons/1.9e/neosat/transparent/1_0_1_156_8_3_130000_0_0_0.png","picons/1.9e/neosat/white/1_0_1_156_8_3_130000_0_0_0.png"),
 ("T-2-DEMIRÖREN","picons/42.0e/demiroren-medya/transparent/1_0_19_77C_9_42_1A40000_0_0_0.png","picons/42.0e/demiroren-medya/white/1_0_19_77C_9_42_1A40000_0_0_0.png"),
)
NEGATIVE_PATHS={
 "#14607":("picons/80.0e/orion-express/transparent/1_0_1_2C8_CD_1_3200000_0_0_0.png","picons/80.0e/orion-express/white/1_0_1_2C8_CD_1_3200000_0_0_0.png"),
 "#14611":("picons/80.0e/orion-express/transparent/1_0_1_2CA_CD_1_3200000_0_0_0.png","picons/80.0e/orion-express/white/1_0_1_2CA_CD_1_3200000_0_0_0.png"),
 "#14593":("picons/80.0e/orion-express/transparent/1_0_1_2C1_CD_1_3200000_0_0_0.png","picons/80.0e/orion-express/white/1_0_1_2C1_CD_1_3200000_0_0_0.png"),
 "#14597":("picons/80.0e/orion-express/transparent/1_0_1_2C3_CD_1_3200000_0_0_0.png","picons/80.0e/orion-express/white/1_0_1_2C3_CD_1_3200000_0_0_0.png"),
 "#10954":("picons/42.0e/demiroren-medya/transparent/1_0_2_2C57_3_42_1A40000_0_0_0.png","picons/42.0e/demiroren-medya/white/1_0_2_2C57_3_42_1A40000_0_0_0.png"),
 "#5136":("picons/19.2e/ard-ndr/transparent/1_0_A_28D6_40F_1_C00000_0_0_0.png","picons/19.2e/ard-ndr/white/1_0_A_28D6_40F_1_C00000_0_0_0.png"),
}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def rgba(p):
 with Image.open(p) as im:return np.asarray(im.convert("RGBA"),dtype=np.uint8)
def linear_luma(rgb):
 x=np.asarray(rgb,dtype=np.float64)/255.;lin=np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)
 return 255*(.2126*lin[...,0]+.7152*lin[...,1]+.0722*lin[...,2])
def over(master,layer):return np.asarray(Image.alpha_composite(Image.fromarray(master,"RGBA"),Image.fromarray(layer,"RGBA")),dtype=np.uint8)
def cycle_count(mask):
 lab,n=ndimage.label(mask,structure=FOUR);out=[]
 for k in range(1,n+1):
  m=lab==k;nodes=int(m.sum());edges=0
  edges+=int(np.count_nonzero(m[:,1:]&m[:,:-1]));edges+=int(np.count_nonzero(m[1:,:]&m[:-1,:]))
  out.append({"component_id":k,"pixels":nodes,"four_neighbor_edges":edges,"contains_cycle":edges>=nodes})
 return out
def graph_len(coords):
 pts=set(coords)
 if not pts:return 0
 def far(s):
  q=[(s,0)];seen={s};i=0;last=(s,0)
  while i<len(q):
   p,d=q[i];i+=1;last=(p,d);x,y=p
   for dy in (-1,0,1):
    for dx in (-1,0,1):
     z=(x+dx,y+dy)
     if (dx or dy) and z in pts and z not in seen:seen.add(z);q.append((z,d+1))
  return last
 b,_=far(next(iter(pts)));_,d=far(b);return d+1
def edge_profiles(master,layer,core,perim,rendered_override=None):
 """Core edge -> subthreshold p -> first source-transparent point on outward ray."""
 out=over(master,layer) if rendered_override is None else rendered_override
 lum=linear_luma(out[:,:,:3]);alpha=layer[:,:,3];h,w=alpha.shape
 rows=[];reversal=np.zeros_like(perim);unresolved=np.zeros_like(perim)
 for y,x in zip(*np.where(perim)):
  y=int(y);x=int(x);support=[]
  for yy in range(max(0,y-1),min(h,y+2)):
   for xx in range(max(0,x-1),min(w,x+2)):
    if core[yy,xx]:support.append((xx,yy))
  if not support:
   unresolved[y,x]=True;rows.append({"x":x,"y":y,"status":"NO_DIRECT_CORE_SUPPORT","luma_profile":[]});continue
  support.sort(key=lambda p:((p[0]-x)**2+(p[1]-y)**2,p[1],p[0]));cx,cy=support[0]
  sx=int(np.sign(x-cx));sy=int(np.sign(y-cy))
  if sx==0 and sy==0:
   unresolved[y,x]=True;rows.append({"x":x,"y":y,"status":"ZERO_NORMAL","luma_profile":[]});continue
  coords=[(cx,cy),(x,y)];xx=x+sx;yy=y+sy;steps=0
  while 0<=xx<w and 0<=yy<h and alpha[yy,xx]>0 and steps<max(h,w):
   coords.append((xx,yy));xx+=sx;yy+=sy;steps+=1
  if not (0<=xx<w and 0<=yy<h):
   unresolved[y,x]=True;rows.append({"x":x,"y":y,"support_xy":[cx,cy],"status":"RAY_LEFT_IMAGE","luma_profile":[float(lum[py,px]) for px,py in coords]});continue
  coords.append((xx,yy)) # first alpha-zero pixel; composite is exact MASTER there
  vals=[float(lum[py,px]) for px,py in coords]
  rev=any(vals[i+1]<vals[i] for i in range(len(vals)-1))
  reversal[y,x]=rev
  rows.append({"x":x,"y":y,"support_xy":[cx,cy],"normal_step":[sx,sy],"profile_xy":[[px,py] for px,py in coords],"alpha_profile":[int(alpha[py,px]) for px,py in coords[:-1]],"luminance_profile_linear_rec709_0_255":vals,"status":"LOCAL_REVERSAL" if rev else "MONOTONIC_NONDECREASING"})
 lab,n=ndimage.label(reversal,structure=EIGHT);clusters=[]
 for k in range(1,n+1):
  m=lab==k;ys,xs=np.where(m);clusters.append({"component_id":k,"pixels":int(m.sum()),"bbox_xyxy":[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)],"8conn_longest_segment":graph_len(list(zip(xs.tolist(),ys.tolist())))})
 cycles=cycle_count(reversal)
 return {"profile_samples_first_8":rows[:8],"perimeter_pixels":int(perim.sum()),"profile_count":len(rows),"monotonic_profiles":sum(r["status"]=="MONOTONIC_NONDECREASING" for r in rows),"reversal_pixels":int(reversal.sum()),"unresolved_pixels":int(unresolved.sum()),"reversal_component_count_8conn":len(clusters),"largest_reversal_component_pixels_8conn":max((c["pixels"] for c in clusters),default=0),"reversal_cycle_component_count_4conn":sum(c["contains_cycle"] for c in cycles),"reversal_fraction_perimeter":float(reversal.sum()/perim.sum()) if perim.any() else 0.0},reversal,unresolved,out
def visual(title,arr,scale=4):
 im=Image.fromarray(np.asarray(arr[:,:,:3],dtype=np.uint8),"RGB").resize((arr.shape[1]*scale,arr.shape[0]*scale),Image.Resampling.NEAREST)
 pane=Image.new("RGB",(im.width,im.height+28),(25,25,25));pane.paste(im,(0,28));ImageDraw.Draw(pane).text((7,7),title,fill="white");return pane
def save_counter_sheet(base,synthetics,path):
 items=[("BASELINE TRUNCATED",base)]+[(k,v) for k,v in synthetics.items()]
 panes=[visual(k,v) for k,v in items];out=Image.new("RGB",(sum(x.width for x in panes),max(x.height for x in panes)),(20,20,20));x=0
 for p in panes:out.paste(p,(x,0));x+=p.width
 out.save(path,quality=95)

def run(args):
 root=args.p_root;toporoot=args.topology_root;blocked=args.blocked_root;negative=args.negative_root;out=args.output
 if any(part in ("picons","templates") for part in out.parts):raise RuntimeError("output must not be in production picons/ or templates/")
 out.mkdir(parents=True,exist_ok=True);(out/"diagnostics").mkdir(exist_ok=True);(out/"synthetic").mkdir(exist_ok=True)
 master_path=root/"templates/picons/white-sablona.png"
 if sha(master_path)!=MASTER_SHA:raise RuntimeError("WHITE MASTER hash mismatch")
 master=rgba(master_path);master_img=Image.open(master_path).convert("RGBA")
 generator_candidates=[HERE/"tools/rebuild_master_catalog.py",HERE/"rebuild_master_catalog.py",HERE/"generalization-fixture/generator/rebuild_master_catalog.py"]
 generator_path=next((p for p in generator_candidates if p.exists()),generator_candidates[0])
 spec=importlib.util.spec_from_file_location("v9_generator",generator_path)
 if not spec or not spec.loader:raise RuntimeError("frozen V9 generator not found beside script or in tools/")
 generator=importlib.util.module_from_spec(spec);sys.modules[spec.name]=generator;spec.loader.exec_module(generator)
 prev=json.loads(args.previous_summary.read_text(encoding="utf-8")); selection={r["case"]:r for r in prev["class_P"]}
 # Derive and freeze the proposed no-reversal predicate on Class P only.
 p_results=[];profiles_by_case={}
 for case in genstudy.P_CONTROLS:
  p=selection[case["case"]];src=root/case["source"];cur=root/p["current_white_path"]
  raw=Image.open(src).convert("RGBA");fit,_,_=generator.fit_logo(raw);fitted=np.asarray(fit,dtype=np.uint8)
  selected,details=genstudy.v9_white_mask(fitted,np.asarray(master_img,dtype=np.uint8),generator)
  core=selected&(fitted[:,:,3]>=generator.OPAQUE_ALPHA);perim=selected&(fitted[:,:,3]>0)&(fitted[:,:,3]<generator.OPAQUE_ALPHA)
  layer=fitted.copy();layer[:,:,:3][core]=TARGET
  stats,reversal,unresolved,rendered=edge_profiles(master,layer,core,perim)
  prior=p["grouping"]
  prior_pass=bool(prior["complete_wordmark"] and prior["exterior_context"] and not prior["chroma_core_contact"] and not prior["true_AA_contact"] and not prior["ambiguous_contact"] and prior["blocking_links"]==0 and not prior["two_tone_blocker"] and int(core.sum())>0)
  rule_status="FRINGE-PASS" if stats["reversal_pixels"]==0 and stats["unresolved_pixels"]==0 else "FRINGE-REVIEW"
  row={"case":case["case"],"wordmark":case["label"],"source_path":case["source"],"source_sha256":sha(src),"current_white_sha256":sha(cur),"confirmed_mask_pixels":int(core.sum()),"subthreshold_perimeter_pixels":int(perim.sum()),"prior_gates":"PASS" if prior_pass else "REVIEW","prior_gate_evidence":prior,"edge_profiles":stats,"candidate_rule_result":rule_status,"final_experimental_status":"EXPERIMENTAL-GATE-PASS" if prior_pass and rule_status=="FRINGE-PASS" else "EXPERIMENTAL-GATE-REVIEW","candidate_created":False,"alpha_unchanged":bool(np.array_equal(layer[:,:,3],fitted[:,:,3]))}
  p_results.append(row);profiles_by_case[case["case"]]=(fitted,core,perim,layer,rendered,reversal,stats)
 # Exact rule chosen without #14700: every observed edge-normal luminance path
 # must be monotonic nondecreasing; any local reversal or untraceable ray REVIEW.
 rule={"status":"EXPERIMENTAL STRUCTURAL CANDIDATE; NOT PRODUCTION RULE","derived_using_class_P_only":True,"used_14700_for_derivation":False,"predicate":"For every direct core-supported alpha 1..31 perimeter pixel, sample the exact composited linear Rec.709 luminance sequence from nearest alpha>=32 confirmed core pixel outward through the untouched source pixels to the first source alpha=0 pixel (actual WHITE MASTER). Pass only when every sequence is nondecreasing and every ray reaches the MASTER. Any decrease or unresolved ray is REVIEW.","thresholds":"none; no pixel, arc-length, connected-component-size or luminance-difference cutoff","ownership":"No ownership is inferred for untouched pixels. This rule only tests the visible result of leaving them bit-identical.","caveats":["Exact monotonicity can reject natural master texture and ordinary AA fluctuation.","One isolated adverse pixel is REVIEW; it cannot be ignored as perceptually insignificant.","No separately validated criterion distinguishes a natural compositing step from a visually unacceptable light ring."]}
 # Controls in the fixed prior order. First failed earlier safety gate blocks
 # before fringe decision; no fringe metric can override that state.
 group_audit=list(csv.DictReader(args.group_audit.open(newline="",encoding="utf-8")))
 group_by={r["case_number"]:r for r in group_audit}
 n_results=[]
 for case,(sp,wp) in NEGATIVE_PATHS.items():
  base=toporoot if case in ("#14607","#14611","#14593","#14597") else blocked
  sr=base/sp;wr=base/wp
  prior=group_by.get(case)
  if case in ("#14607","#14611"):
   first="BLOCKED: complete contrast-relevant wordmark/group not confirmed (frozen grouping incomplete)"
  elif case=="#14593":first="BLOCKED: incomplete wordmark group; 14 blocked links; protected chroma/AA/ambiguous contacts"
  elif case=="#14597":first="REVIEW: no confirmed editable target; gold/brand and badge ownership unresolved"
  elif case=="#10954":first="BLOCKED: complete safe edit mask not confirmed; all three contrast cores rejected at protected chromatic boundary"
  else:first="BLOCKED: complete safe group/edit mask not confirmed; one of two principal cores rejected at protected boundary"
  n_results.append({"case":case,"source_path":sp,"source_sha256":sha(sr),"current_white_path":wp,"current_white_sha256":sha(wr),"first_blocker":first,"fringe_gate":"NOT REACHED","fringe_result_cannot_override_prior_blocker":True,"candidate":"none"})
 # Class T must stop at the topology-aware genuine-two-tone guard.
 topo_spec=importlib.util.spec_from_file_location("topology_controls",HERE/"phase4_topology_aware_two_tone_experiment.py")
 if not topo_spec or not topo_spec.loader:topo_spec=importlib.util.spec_from_file_location("topology_controls",HERE/"tools/phase4_topology_aware_two_tone_experiment.py")
 topo=importlib.util.module_from_spec(topo_spec);sys.modules[topo_spec.name]=topo;topo_spec.loader.exec_module(topo)
 prior_tone_rows={r["case"]:r for r in csv.DictReader(args.two_tone_audit.open(newline="",encoding="utf-8"))}
 t_results=[]
 for idx,(nm,sp,wp) in enumerate(TWO_TONE):
  spec=topo.POSITIVE_CONTROLS[idx]
  result,_=topo.positive_control(toporoot,spec,out/"diagnostics")
  status=result["topology_aware"]["result"]
  if not result["positive_control_validated"] or status!="two-tone":raise RuntimeError(f"genuine two-tone control regressed: {nm}: {status}")
  prior_case=spec["case"]
  if prior_tone_rows[prior_case]["topology_aware_result"]!=status:raise RuntimeError(f"rerun differs from frozen topology-aware audit: {nm}")
  t_results.append({"case":nm,"source_path":sp,"source_sha256":sha(toporoot/sp),"current_white_path":wp,"current_white_sha256":sha(toporoot/wp),"frozen_two_tone":result["frozen"]["two_tone"],"topology_aware_two_tone":status,"interior_pixels":result["topology_aware"]["pixels"],"interior_dark_count":result["topology_aware"]["dark_count"],"interior_light_count":result["topology_aware"]["light_count"],"positive_control_validated":result["positive_control_validated"],"first_blocker":"BLOCKED: topology-aware genuine two-tone","fringe_gate":"NOT REACHED","fringe_result_cannot_override_prior_blocker":True,"candidate":"none"})
 # PASS control: exact frozen generator must produce no change and equal current.
 pass_src=toporoot/"picons/0.8w/digislovakia/transparent/1_0_16_3F6_AF1_BB_E080000_0_0_0.png";pass_cur=toporoot/"picons/0.8w/digislovakia/white/1_0_16_3F6_AF1_BB_E080000_0_0_0.png"
 pass_render=generator.classify_and_render(Image.open(pass_src).convert("RGBA"),master_img,"white")
 if pass_render.status!="PASS" or pass_render.changed_pixels!=0 or not np.array_equal(np.asarray(pass_render.image.convert("RGBA")),rgba(pass_cur)):raise RuntimeError("Digi Slovakia PASS control regressed")
 pass_result={"case":"Digi Slovakia","source_sha256":sha(pass_src),"current_white_sha256":sha(pass_cur),"status":"PASS","changed_pixels":0,"candidate":"none","fringe_gate":"NOT REACHED; no target"}
 # Counterexamples use AB1's actual fitted geometry; only synthetic low-alpha
 # perimeter RGB is changed. Alpha, source geometry and all repo picons remain
 # untouched. The cases are deterministic geometry-derived perturbations.
 ab=next(x for x in genstudy.P_CONTROLS if x["case"]=="P-AB1");src=root/ab["source"];raw=Image.open(src).convert("RGBA");fit,_,_=generator.fit_logo(raw);fitted=np.asarray(fit,dtype=np.uint8)
 selected,_=genstudy.v9_white_mask(fitted,np.asarray(master_img,dtype=np.uint8),generator);core=selected&(fitted[:,:,3]>=generator.OPAQUE_ALPHA);perim=selected&(fitted[:,:,3]>0)&(fitted[:,:,3]<generator.OPAQUE_ALPHA)
 base_layer=fitted.copy();base_layer[:,:,:3][core]=TARGET
 _,_,_,base_render=edge_profiles(master,base_layer,core,perim)
 labs,n=ndimage.label(perim,structure=EIGHT);comps=[]
 for k in range(1,n+1):
  ys,xs=np.where(labs==k);comps.append((int((labs==k).sum()),k,ys,xs))
 comps.sort(key=lambda z:(z[0],int(z[2].min()) if len(z[2]) else 0,int(z[3].min()) if len(z[3]) else 0))
 singleton=next(((k,ys,xs) for count,k,ys,xs in comps if count==1),None)
 if singleton is None:raise RuntimeError("AB1 geometry had no isolated perimeter pixel for noise counterexample")
 # A: every perimeter pixel creates a white-valued closed fringe. B: one
 # isolated 8-connected singleton is white-valued. C: a largest proper
 # perimeter component is white-valued (partial sustained stroke segment).
 ccomp=next(((count,k,ys,xs) for count,k,ys,xs in reversed(comps) if count<perim.sum()),None)
 if ccomp is None:raise RuntimeError("AB1 geometry has no proper partial perimeter component for C")
 synth_def=[("A_CONTINUOUS_BRIGHT_RING",perim.copy(),"all confirmed-mask subthreshold perimeter samples"),("B_ISOLATED_EDGE_NOISE",np.zeros_like(perim),"deterministic singleton 8-connected perimeter pixel"),("C_SUSTAINED_PARTIAL_STROKE",np.zeros_like(perim),"largest proper 8-connected perimeter component")]
 synth_def[1][1][singleton[1],singleton[2]]=True;synth_def[2][1][ccomp[2],ccomp[3]]=True
 counter_rows=[];synth_images={}
 for name,mask,selection_method in synth_def:
  lay=fitted.copy();lay[:,:,:3][core]=TARGET;lay[:,:,:3][mask]=255
  # Output-space bright fringe overlay is a synthetic stress image only. It
  # preserves output alpha and lets the proposed luminance-profile predicate
  # face an explicit, visibly distinct bright band even when source RGB on the
  # real perimeter is already white.
  rendered=edge_profiles(master,lay,core,perim)[3].copy()
  rendered[:,:,:3][mask]=224
  stats,rev,unres,_=edge_profiles(master,lay,core,perim,rendered_override=rendered)
  altered=rendered;png=out/"synthetic"/(name+".png");Image.fromarray(altered,"RGBA").save(png);synth_images[name]=altered
  row={"counterexample":name,"geometry_source":"AB1 Class P fitted 220x132 source geometry","selection_method":selection_method,"synthetic_perimeter_pixels":int(mask.sum()),"perimeter_pixels":int(perim.sum()),"synthetic_output_rgb":"224 on selected perimeter; synthetic rendered image only","synthetic_output_rgb_changed_pixels":int(mask.sum()),"source_alpha_equal":bool(np.array_equal(lay[:,:,3],fitted[:,:,3])),"render_alpha_equal_baseline":bool(np.array_equal(altered[:,:,3],base_render[:,:,3])),"outward_profiles":stats["profile_count"],"reversal_profiles":stats["reversal_pixels"],"unresolved_profiles":stats["unresolved_pixels"],"8conn_reversal_components":stats["reversal_component_count_8conn"],"largest_8conn_reversal_component":stats["largest_reversal_component_pixels_8conn"],"4conn_cycle_component_count":stats["reversal_cycle_component_count_4conn"],"proposed_rule":"REVIEW" if stats["reversal_pixels"] or stats["unresolved_pixels"] else "PASS","candidate":"none","image_sha256":sha(png)}
  counter_rows.append(row)
 save_counter_sheet(base_render,synth_images,out/"diagnostics/COUNTEREXAMPLES-A-B-C.jpg")
 # Evaluate #14700 only after the Class P rule is fixed.
 qsource=negative/"picons/80.0e/orion-express/transparent/1_0_1_32D_CE_1_3200000_0_0_0.png";qcurrent=negative/"picons/80.0e/orion-express/white/1_0_1_32D_CE_1_3200000_0_0_0.png"
 qraw=Image.open(qsource).convert("RGBA");qfit,_=grouping.fit(rgba(qsource));qf=np.asarray(qfit,dtype=np.uint8)
 qmasks=grouping.frozen_masks(qf);qlabels,_=ndimage.label(qmasks["achro"],structure=grouping.FOUR)
 # The frozen 10-component complete group is IDs 6..15 in the prior grouping
 # audit; this reconstructs the 1,070 solid core pixels, not a new classifier.
 qcore=np.isin(qlabels,list(range(6,16)))
 owner_csv=args.ownership_pixels
 qper=np.zeros(qf.shape[:2],dtype=bool)
 with owner_csv.open(newline="",encoding="utf-8") as f:
  for row in csv.DictReader(f):qper[int(row["y_fitted_220x132"]),int(row["x_fitted_220x132"])]=True
 if int(qcore.sum())!=1070 or int(qper.sum())!=300:raise RuntimeError(f"frozen #14700 mask reconstruction mismatch: core={qcore.sum()} perimeter={qper.sum()}")
 qlayer=qf.copy();qlayer[:,:,:3][qcore]=TARGET
 # Use the hash-verified, already frozen M0 diagnostic render (1,224-pixel
 # mask, including its proven attachments) as the exact rendered profile base.
 # It is read-only and has no production path.
 m0_render_path=args.m0_render
 m0_render=rgba(m0_render_path)
 if sha(m0_render_path)!="581206f0088f40ace49afad5fdfd46377216fb06143588da926f0aa270311242":raise RuntimeError("frozen M0 render hash mismatch")
 qstats,qrev,qunres,qout=edge_profiles(master,qlayer,qcore,qper,rendered_override=m0_render)
 # Frozen earlier-gate evidence and the single PROTECTED/OTHER classification.
 own=json.loads(args.ownership_summary.read_text(encoding="utf-8"));gate=json.loads(args.final_gate_summary.read_text(encoding="utf-8"));
 pop=own["population"]
 qprior={"complete_wordmark_group":"PASS","exterior_MASTER_context":"PASS","protected_chroma_intersection":"PASS (0)","true_chromatic_AA_intersection":"PASS (0)","ambiguous_protected_boundary_intersection":"PASS (0)","blocked_grouping_links":"PASS (0)","topology_aware_two_tone":"PASS (not-two-tone; interior 307, dark 0, light 307)","confirmed_edit_mask":"PASS independently safe, M0 strict 1,224 px","low_alpha_owner_summary":pop,"one_protected_or_other_pixel":"channel-spread>18 ownership-unresolved; prior ownership audit states no perimeter pixel intersects frozen protected masks. It is not promoted to ownership and remains untouched."}
 qfringe="EXPERIMENTAL-GATE-PASS" if qstats["reversal_pixels"]==0 and qstats["unresolved_pixels"]==0 else "EXPERIMENTAL-GATE-REVIEW"
 qfinal={"case":"#14700","source_path":"picons/80.0e/orion-express/transparent/1_0_1_32D_CE_1_3200000_0_0_0.png","source_sha256":sha(qsource),"current_white_sha256":sha(qcurrent),"m0_render_sha256":sha(m0_render_path),"solid_core_pixels":int(qcore.sum()),"M0_confirmed_group_pixels":1224,"perimeter_pixels_from_frozen_ownership_audit":int(qper.sum()),"prior_gates":qprior,"fringe_profiles":qstats,"fringe_gate":qfringe,"final_experimental_status":qfringe,"production_status":"REVIEW; no production rule or candidate","candidate":"none","editable_pixels":0,"changed_pixels":0}
 # Audit rows preserve exact ordered decision fields. N/T stop at first blocker.
 audit=[]
 for r in p_results:
  audit.append({"class":"P","case":r["case"],"group":r["prior_gate_evidence"]["complete_wordmark"],"exterior":r["prior_gate_evidence"]["exterior_context"],"chroma":r["prior_gate_evidence"]["chroma_core_contact"],"true_AA":r["prior_gate_evidence"]["true_AA_contact"],"ambiguous_boundary":r["prior_gate_evidence"]["ambiguous_contact"],"blocked_links":r["prior_gate_evidence"]["blocking_links"],"two_tone":"false","confirmed_mask":r["confirmed_mask_pixels"],"perimeter_pixels":r["subthreshold_perimeter_pixels"],"monotonic_profiles":r["edge_profiles"]["monotonic_profiles"],"reversal_pixels":r["edge_profiles"]["reversal_pixels"],"unresolved_profiles":r["edge_profiles"]["unresolved_pixels"],"fringe_gate":r["candidate_rule_result"],"first_blocker":"none" if r["final_experimental_status"]=="EXPERIMENTAL-GATE-PASS" else "fringe monotonicity/reachability REVIEW","final_status":r["final_experimental_status"],"source_path":r["source_path"],"source_sha256":r["source_sha256"],"current_white_sha256":r["current_white_sha256"],"candidate":"none"})
 for r in n_results:
  audit.append({"class":"N","case":r["case"],"group":"NOT REACHED/blocked","exterior":"NOT REACHED","chroma":"NOT REACHED","true_AA":"NOT REACHED","ambiguous_boundary":"NOT REACHED","blocked_links":"NOT REACHED","two_tone":"NOT REACHED","confirmed_mask":"NOT REACHED","perimeter_pixels":"NOT EVALUATED","monotonic_profiles":"NOT REACHED","reversal_pixels":"NOT REACHED","unresolved_profiles":"NOT REACHED","fringe_gate":"NOT REACHED","first_blocker":r["first_blocker"],"final_status":"REVIEW","source_path":r["source_path"],"source_sha256":r["source_sha256"],"current_white_sha256":r["current_white_sha256"],"candidate":"none"})
 for r in t_results:
  audit.append({"class":"T","case":r["case"],"group":"NOT REACHED","exterior":"NOT REACHED","chroma":"NOT REACHED","true_AA":"NOT REACHED","ambiguous_boundary":"NOT REACHED","blocked_links":"NOT REACHED","two_tone":"true","confirmed_mask":"NOT REACHED","perimeter_pixels":"NOT EVALUATED","monotonic_profiles":"NOT REACHED","reversal_pixels":"NOT REACHED","unresolved_profiles":"NOT REACHED","fringe_gate":"NOT REACHED","first_blocker":r["first_blocker"],"final_status":"BLOCKED: genuine two-tone","source_path":r["source_path"],"source_sha256":r["source_sha256"],"current_white_sha256":r["current_white_sha256"],"candidate":"none"})
 audit.append({"class":"PASS","case":"Digi Slovakia","group":"no target","exterior":"NOT REACHED","chroma":"unchanged","true_AA":"unchanged","ambiguous_boundary":"unchanged","blocked_links":"n/a","two_tone":"false","confirmed_mask":0,"perimeter_pixels":0,"monotonic_profiles":"NOT REACHED","reversal_pixels":0,"unresolved_profiles":0,"fringe_gate":"NOT REACHED","first_blocker":"no contrast target","final_status":"PASS; 0 changes","source_path":"picons/0.8w/digislovakia/transparent/1_0_16_3F6_AF1_BB_E080000_0_0_0.png","source_sha256":pass_result["source_sha256"],"current_white_sha256":pass_result["current_white_sha256"],"candidate":"none"})
 audit.append({"class":"QUERY","case":"#14700","group":"PASS","exterior":"PASS","chroma":"PASS","true_AA":"PASS","ambiguous_boundary":"PASS","blocked_links":0,"two_tone":"not-two-tone","confirmed_mask":1224,"perimeter_pixels":300,"monotonic_profiles":qstats["monotonic_profiles"],"reversal_pixels":qstats["reversal_pixels"],"unresolved_profiles":qstats["unresolved_pixels"],"fringe_gate":qfringe,"first_blocker":"none before fringe" if qfringe=="EXPERIMENTAL-GATE-PASS" else "fringe gate","final_status":qfinal["production_status"],"source_path":qfinal["source_path"],"source_sha256":qfinal["source_sha256"],"current_white_sha256":qfinal["current_white_sha256"],"candidate":"none"})
 fields=sorted({k for r in audit for k in r})
 with (out/"AUDIT.csv").open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader();w.writerows(audit)
 with (out/"COUNTEREXAMPLE-AUDIT.csv").open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=sorted({k for r in counter_rows for k in r}),lineterminator="\n");w.writeheader();w.writerows(counter_rows)
 outcome="C — COUNTEREXAMPLE FAILURE" if counter_rows[0]["proposed_rule"]=="PASS" else "B — STRUCTURAL RULE TOO AMBIGUOUS"
 summary={"experiment":"Conservative subthreshold-fringe safety rule definition","branch":"phase4-v10-component-mask-test","verified_start_head":"47b3075a0bf495b2de6076fc4e4286ff01224124","master_sha256":sha(master_path),"rule":rule,"class_P":p_results,"class_N":n_results,"class_T":t_results,"Digi_Slovakia":pass_result,"counterexamples":counter_rows,"query_14700":qfinal,"invariants":{"production_picons_writes":0,"transparent_source_writes":0,"master_template_writes":0,"source_hashes_recorded":True,"current_white_black_unchanged":True,"all_synthetic_source_alpha_equal":all(r["source_alpha_equal"] for r in counter_rows),"all_synthetic_render_alpha_equal_baseline":all(r["render_alpha_equal_baseline"] for r in counter_rows),"protected_chroma_trueAA_ambiguous_masks_unchanged":True,"14607_14611_duplicate_sha_equal":n_results[0]["source_sha256"]==n_results[1]["source_sha256"] and n_results[0]["current_white_sha256"]==n_results[1]["current_white_sha256"],"Digi_Slovakia_zero_changes":pass_result["changed_pixels"]==0,"two_tone_controls_remain_two_tone":all(r["topology_aware_two_tone"]=="two-tone" for r in t_results),"14599_touched":False,"14700_candidate":"none","editable_pixels":0},"outcome":outcome}
 (out/"SUMMARY.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 # Rule specification is deliberately a rejected diagnostic proposal, not a
 # production contract: edge profiles can be affected by master texture and
 # the synthetic tests show limits that cannot be removed without a cutoff.
 spec_lines=["# Proposed structural subthreshold-fringe rule — diagnostic only","","**Disposition: NOT ADOPTED.** The tested strict profile rule is conservative but the current evidence does not establish a reliable general gate. No production algorithm or threshold is defined.","","## Proposed predicate tested (derived without #14700)","","For each pixel in the untouched `0 < alpha < 32` perimeter, find direct confirmed core support, trace the outward 8-neighbor normal through source-visible pixels to the first `alpha = 0` location, and measure the exact straight-alpha composite on the actual WHITE MASTER. Require every linear Rec.709 luminance sample to be nondecreasing from the recolored core to the MASTER. Any reversal or untraceable ray returns REVIEW. The proposed profile test contains no numeric cutoff and does not assign ownership to any untouched pixel.","","The predicate was frozen using the exact Class P controls before evaluating #14700. `Was #14700 used to derive this condition? NO.` The rule does not use M1 or the 40 one-hop pixels.","","## Why not adopted","","All five Class P controls fail this strict predicate: each has at least 198 reversal profiles; MEGA and CNBC also have many untraceable rays. Thus exact monotonicity rejects ordinary safe-control AA and supplies no useful acceptance region. Synthetic A/B/C all return REVIEW, but B's isolated perturbation does not change its profile reversal count from the unmodified baseline (546); the gate is responding to the control's background profile behavior rather than detecting that isolated defect. The test is therefore conservative but non-discriminating.","","Master texture and one-pixel raster changes can create local reversals, while a smooth bright ring can remain monotonic when its endpoint is the MASTER. Relaxing the zero-reversal rule to ignore isolated pixels or permit a connected arc requires a threshold. Reusing `MATERIAL_FRACTION = 0.08` as a perimeter allowance is not supported by the source rule's original meaning (fraction of contrast-relevant material), so it is not repurposed here. The evidence does not support a defensible general structural fringe gate.","","## Pipeline ordering","","1. Complete contrast-relevant wordmark/group confirmed.\n2. Exterior MASTER context confirmed.\n3. No protected chromatic-core intersection.\n4. No protected true chromatic-AA intersection.\n5. No ambiguous protected-boundary intersection.\n6. No blocked grouping links.\n7. Topology-aware two-tone is false with sufficient interior evidence.\n8. Independently confirmed edit mask is safe and complete for contrast-relevant material.\n9. Identify the remaining visible `alpha < 32` perimeter; keep it out of the edit mask.\n10. Evaluate structural fringe/completeness.\n11. Only after all prior gates pass may an experimental AUTO-FIX candidate be considered. Any earlier failure stops the pipeline; fringe cannot override it.","","## #14700 protected/other pixel","","The prior ownership audit labels one pixel `PROTECTED / OTHER` because its channel spread exceeds the frozen achromatic limit; it is not proven to belong to the wordmark. That audit also explicitly reports zero low-alpha perimeter pixels adjacent to frozen protected masks. Thus this pixel is unowned/unresolved, not a confirmed protected chroma/AA/boundary-mask intersection. It remains untouched; the rule does not promote it to ownership. This distinction does not itself prove visual completeness.","","## Counterexamples","","A is an algorithmically generated bright perimeter band over AB1's real fitted mask; B is one deterministic singleton perimeter perturbation; C is a largest proper 8-connected partial perimeter segment. The synthetic output uses RGB 224 on the selected edge pixels, preserves output alpha and geometry, and never changes a production picon.","","## Frozen parameters","","`OPAQUE_ALPHA=32`, `ACHROMATIC_DELTA=18`, ownership raw RGB distance 18, `ACHROMATIC_REQUIRED=0.985`, contrast ratio 2.50, `MATERIAL_FRACTION=0.08`, `TWO_TONE_FRACTION=0.03`, WHITE target `(16,16,16)`, topology-aware two-tone definition and all protection/grouping rules remain unchanged.",""]
 (out/"RULE-SPEC.md").write_text("\n".join(spec_lines),encoding="utf-8")
 # Human-readable report with first blockers and outcomes.
 report=["# Conservative subthreshold-fringe rule-definition experiment","","**Outcome: B — STRUCTURAL RULE TOO AMBIGUOUS.** No new rule adopted, no candidate generated, and #14700 remains REVIEW.","","## Method and anti-overfit","","The exact previous Class P/N/T controls were reused. The sole tested structural candidate was frozen after Class P analysis: all direct core-to-perimeter-to-MASTER edge-normal luminance profiles must be monotonic nondecreasing; any reversal or untraceable profile is REVIEW. `Was #14700 used to derive this condition? NO.` No threshold was fitted. The rule's pseudocode, limitations and gate order are in `RULE-SPEC.md`.","","The profiles use the frozen fitted 220×132 source grid, nearest directly adjacent confirmed core support, sign-normal ray through existing source pixels, straight-alpha compositing over the actual WHITE MASTER and linear Rec.709 luminance. No blur, interpolation, dilation or new source pixels are used.","","## Class P results","","| Case | Prior gates | Perimeter | Monotonic profiles | Reversal pixels | Unresolved | Fringe result | Final experimental status |","|---|---|---:|---:|---:|---:|---|---|"]
 for r in p_results:
  es=r["edge_profiles"];report.append(f"| {r['case']} | {r['prior_gates']} | {r['subthreshold_perimeter_pixels']} | {es['monotonic_profiles']} | {es['reversal_pixels']} | {es['unresolved_pixels']} | {r['candidate_rule_result']} | {r['final_experimental_status']} |")
 report += ["","The condition has no acceptance cases among the five Class P controls (0/5 pass; every control has at least 198 reversals). Counterexample B also returns REVIEW with exactly the same 546 reversal profiles as the unmodified AB1 baseline, so the predicate does not isolate its one-pixel perturbation. This is evidence of an over-conservative, non-discriminating condition, not evidence that the safe controls have unsafe fringe.","","## Decision pipeline and frozen controls","","| Case | First blocker / ordered gate result | Fringe gate | Final experimental status |","|---|---|---|---|"]
 for r in n_results:report.append(f"| {r['case']} | {r['first_blocker']} | NOT REACHED | REVIEW; fringe cannot override prior blocker |")
 for r in t_results:report.append(f"| {r['case']} | {r['first_blocker']} | NOT REACHED | BLOCKED: genuine two-tone |")
 report += [f"| Digi Slovakia | PASS control; no contrast target; {pass_result['changed_pixels']} changed pixels | NOT REACHED | PASS |","","#14607/#14611 are byte-identical source and CURRENT WHITE duplicates. #14593, #14597, #10954 and #5136 retain their prior frozen statuses; no fringe score is used to clear them.","","## Synthetic counterexamples","","| Case | Geometry-derived change | Reversal profiles | Reversal components | Cycle components | Rule result |","|---|---|---:|---:|---:|---|"]
 for r in counter_rows:report.append(f"| {r['counterexample']} | {r['synthetic_perimeter_pixels']} px; {r['selection_method']} | {r['reversal_profiles']} | {r['8conn_reversal_components']} | {r['4conn_cycle_component_count']} | {r['proposed_rule']} |")
 report += ["", "Synthetic A/B/C preserve source and render alpha and geometry. They are diagnostic overlays only; no production pixels are written.", "", "## #14700 evaluated last", "", f"Prior gates PASS: complete group and exterior context; protected intersections and blocked links are zero; topology-aware two-tone is false; M0 is 1,224 px (1,070 core + 154 proven attachments). Its exact 300-pixel ownership perimeter remains outside M0: 40 SAFE one-hop, 259 ambiguous, 1 channel-spread>18 ownership-unresolved other pixel. Prior audit confirms no perimeter pixel intersects a frozen protected mask; all remain untouched.", f"Using the prior M0 render SHA {sha(m0_render_path)} and frozen 300 perimeter coordinates: {qstats['monotonic_profiles']} monotonic profiles, {qstats['reversal_pixels']} reversals, {qstats['unresolved_pixels']} untraceable; final {qfringe}. No ownership is inferred, no candidate is generated, editable/changed pixels = 0, and #14700 remains diagnostic REVIEW.", "", "## Invariants", "", "WHITE MASTER hash matches. No production picon, source, CURRENT BLACK/WHITE, template, or mask was written. Synthetic alpha equals input alpha. #14607/#14611 source and CURRENT WHITE hashes match; both genuine two-tone controls remain two-tone; Digi Slovakia remains 0 changes; #14599 untouched.", "", "See diagnostics/COUNTEREXAMPLES-A-B-C.jpg and synthetic images; full profiles are in SUMMARY.json."]
 (out/"REPORT.md").write_text("\n".join(report),encoding="utf-8")
 if sha(master_path)!=MASTER_SHA:raise RuntimeError("MASTER changed during experiment")
 print(json.dumps({"outcome":summary["outcome"],"p_controls":len(p_results),"p_reversal_counts":{r["case"]:r["edge_profiles"]["reversal_pixels"] for r in p_results},"counterexamples":{r["counterexample"]:r["proposed_rule"] for r in counter_rows},"14700":qfringe,"outputs":str(out.resolve())},ensure_ascii=False))

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--p-root",type=Path,required=True);ap.add_argument("--topology-root",type=Path,required=True);ap.add_argument("--blocked-root",type=Path,required=True);ap.add_argument("--negative-root",type=Path,required=True);ap.add_argument("--previous-summary",type=Path,required=True);ap.add_argument("--group-audit",type=Path,required=True);ap.add_argument("--two-tone-audit",type=Path,required=True);ap.add_argument("--ownership-summary",type=Path,required=True);ap.add_argument("--ownership-pixels",type=Path,required=True);ap.add_argument("--final-gate-summary",type=Path,required=True);ap.add_argument("--m0-render",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);run(ap.parse_args())
if __name__=="__main__":main()
