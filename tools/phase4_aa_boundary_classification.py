#!/usr/bin/env python3
"""Isolated V9-threshold AA-boundary classification regression.

Inputs are fixture copies. All output is external to the repository's picons/
tree. The classifier uses no logo-specific coordinates or thresholds.
"""
from __future__ import annotations

import argparse, csv, hashlib, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

SIZE=(220,132); OPAQUE_ALPHA=32; ACHROMATIC_DELTA=18
ACHROMATIC_REQUIRED=.985; CONTRAST_RATIO=2.50; MATERIAL_FRACTION=.08
TWO_TONE_FRACTION=.03; DARK=np.array((16,16,16),dtype=np.uint8)
WHITE_MASTER_SHA256="c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589"
FOUR=np.array([[0,1,0],[1,1,1],[0,1,0]],dtype=np.uint8)
EIGHT=np.ones((3,3),dtype=np.uint8)
CASES=[
 {"case":"#14607","key":"14607","source":"picons/80.0e/orion-express/transparent/1_0_1_2C8_CD_1_3200000_0_0_0.png","current":"picons/80.0e/orion-express/white/1_0_1_2C8_CD_1_3200000_0_0_0.png","duplicate":"","probe":False},
 {"case":"#14611","key":"14611","source":"picons/80.0e/orion-express/transparent/1_0_1_2CA_CD_1_3200000_0_0_0.png","current":"picons/80.0e/orion-express/white/1_0_1_2CA_CD_1_3200000_0_0_0.png","duplicate":"#14607; source/current duplicate regression mapping","probe":False},
 {"case":"#14700","key":"14700","source":"picons/80.0e/orion-express/transparent/1_0_1_32D_CE_1_3200000_0_0_0.png","current":"picons/80.0e/orion-express/white/1_0_1_32D_CE_1_3200000_0_0_0.png","duplicate":"","probe":False},
 {"case":"#14593","key":"14593","source":"picons/80.0e/orion-express/transparent/1_0_1_2C1_CD_1_3200000_0_0_0.png","current":"picons/80.0e/orion-express/white/1_0_1_2C1_CD_1_3200000_0_0_0.png","duplicate":"","probe":False},
 {"case":"#14597","key":"14597","source":"picons/80.0e/orion-express/transparent/1_0_1_2C3_CD_1_3200000_0_0_0.png","current":"picons/80.0e/orion-express/white/1_0_1_2C3_CD_1_3200000_0_0_0.png","duplicate":"","probe":True},
 {"case":"PASS-control","key":"pass","source":"picons/0.8w/digislovakia/transparent/1_0_16_3F6_AF1_BB_E080000_0_0_0.png","current":"picons/0.8w/digislovakia/white/1_0_16_3F6_AF1_BB_E080000_0_0_0.png","duplicate":"","probe":False},
]

def sha(b): return hashlib.sha256(b).hexdigest()
def load(p):
 with Image.open(p) as im:
  im.load()
  if im.format!="PNG" or im.size!=SIZE: raise ValueError(f"invalid fixture {p}: {im.format} {im.size}")
  return np.array(im.convert("RGBA"),dtype=np.uint8)
def fit(src):
 im=Image.fromarray(src,"RGBA"); bbox=im.getchannel("A").getbbox()
 if bbox is None: return src.copy(),bbox
 crop=im.crop(bbox); scale=min(1.,(SIZE[0]-16)/crop.width,(SIZE[1]-16)/crop.height)
 dims=(max(1,round(crop.width*scale)),max(1,round(crop.height*scale)))
 if dims!=crop.size: crop=crop.resize(dims,Image.Resampling.LANCZOS)
 out=Image.new("RGBA",SIZE,(0,0,0,0)); out.alpha_composite(crop,((220-crop.width)//2,(132-crop.height)//2))
 return np.array(out,dtype=np.uint8),bbox
def luma(rgb):
 x=rgb.astype(np.float32)/255.; x=np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)
 return x[...,0]*.2126+x[...,1]*.7152+x[...,2]*.0722
def tile(title,rgba=None,mask=None,color=(255,255,255),bg=(31,31,31)):
 if mask is not None:
  a=np.zeros((*mask.shape,4),dtype=np.uint8); a[:,:,:3]=bg; a[:,:,3]=255; a[mask,:3]=color
  im=Image.fromarray(a,"RGBA")
 else: im=Image.fromarray(rgba,"RGBA")
 canvas=Image.new("RGB",(440,292),(30,30,30)); shown=im.resize((440,264),Image.Resampling.NEAREST)
 if shown.mode=="RGBA": canvas.paste(shown,(0,28),shown)
 else: canvas.paste(shown,(0,28))
 ImageDraw.Draw(canvas).text((8,7),title,fill=(255,255,255))
 return canvas
def contact(panels,path,cols=3):
 rows=(len(panels)+cols-1)//cols; out=Image.new("RGB",(cols*440,rows*292),(20,20,20))
 for i,p in enumerate(panels): out.paste(p,((i%cols)*440,(i//cols)*292))
 out.save(path,quality=94)
def comp_sheet(src,current,cand,label,path):
 panels=[]
 for title,rgba in (("SOURCE (fitted)",src),("CURRENT WHITE",current),("COLOR-TOPOLOGY CANDIDATE",cand)):
  # show the complete 220x132 picon enlarged on white background
  canvas=Image.new("RGB",(440,292),(255,255,255)); ImageDraw.Draw(canvas).text((8,7),f"{label} — {title}",fill=(10,10,10))
  im=Image.fromarray(rgba,"RGBA").resize((440,264),Image.Resampling.NEAREST); canvas.paste(im,(0,28),im); panels.append(canvas)
 out=Image.new("RGB",(1320,292),(255,255,255))
 for i,p in enumerate(panels): out.paste(p,(i*440,0))
 out.save(path,quality=95)

def run(root,out,master):
 out.mkdir(parents=True,exist_ok=True); (out/"candidates").mkdir(exist_ok=True); (out/"masks").mkdir(exist_ok=True); (out/"comparisons").mkdir(exist_ok=True)
 rows=[]; cache={}; master_sha=sha((root/"templates/picons/white-sablona.png").read_bytes())
 if master_sha!=WHITE_MASTER_SHA256: raise RuntimeError(f"white master hash mismatch: {master_sha}")
 master_px=load(root/"templates/picons/white-sablona.png")
 for case in CASES:
  src_bytes=(root/case["source"]).read_bytes(); cur_bytes=(root/case["current"]).read_bytes()
  src=load(root/case["source"]); current=load(root/case["current"]); fitted,bbox=fit(src)
  alpha=fitted[:,:,3]; visible=alpha>0; solid=alpha>=OPAQUE_ALPHA; rgb=fitted[:,:,:3].astype(np.int16)
  delta=rgb.max(2)-rgb.min(2); chroma=solid&(delta>ACHROMATIC_DELTA); achro=solid&(delta<=ACHROMATIC_DELTA)
  ach_labels,ach_n=ndimage.label(achro,structure=FOUR); chroma_labels,chroma_n=ndimage.label(chroma,structure=EIGHT)
  old_ring=(ndimage.binary_dilation(chroma,structure=EIGHT)&visible)&~chroma
  # Only positive, local pixel evidence can promote ring pixels to true AA.
  # Criterion thresholds are the frozen V9 chromatic delta (18) and alpha floor (32).
  true_aa=np.zeros_like(chroma); geometric=np.zeros_like(chroma); aa_amb=np.zeros_like(chroma)
  offsets=[(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
  for y,x in zip(*np.where(old_ring)):
   relations=[]
   for dy,dx in offsets:
    yy,xx=y+dy,x+dx
    if yy<0 or yy>=132 or xx<0 or xx>=220 or not chroma[yy,xx]: continue
    dist=int(np.max(np.abs(rgb[y,x]-rgb[yy,xx])))
    atten=bool(alpha[y,x]<alpha[yy,xx])
    # Both color continuity and alpha attenuation are required for positive AA proof.
    relations.append((dist<=ACHROMATIC_DELTA,atten))
   proofs=[c and a for c,a in relations]
   contradiction=[c!=a for c,a in relations]
   if relations and all(proofs): true_aa[y,x]=True
   elif relations and (any(proofs) or any(contradiction) or alpha[y,x]<255): aa_amb[y,x]=True
   elif relations and alpha[y,x]==255 and all((not c and not a) for c,a in relations): geometric[y,x]=True
   else: aa_amb[y,x]=True
  low_alpha=visible&(alpha<OPAQUE_ALPHA)
  ambiguous=low_alpha|aa_amb
  # Source alpha below V9 solid floor is ambiguous. Exterior reachability of such
  # pixels is positive evidence only; it is never itself an edit mask.
  amb_labels,amb_n=ndimage.label(ambiguous,structure=EIGHT)
  borders=np.unique(np.r_[amb_labels[0,:],amb_labels[-1,:],amb_labels[:,0],amb_labels[:,-1]])
  exterior=np.isin(amb_labels,borders)&ambiguous
  bg=master_px[:,:,:3].astype(np.float32)*(master_px[:,:,3:4].astype(np.float32)/255.)
  proposal=np.zeros_like(chroma); accepted=[]; rejected=[]; decisions=[]; relevant=0
  for idx in range(1,ach_n+1):
   comp=ach_labels==idx; vals=rgb[comp].astype(np.uint8)
   if not vals.size: continue
   lf=luma(vals.reshape(-1,1,3)).reshape(-1); bf=luma(bg[comp].reshape(-1,1,3)).reshape(-1)
   ratio=(np.maximum(lf,bf)+.05)/(np.minimum(lf,bf)+.05); low_frac=float(np.mean(ratio<CONTRAST_RATIO))
   needs=low_frac>=MATERIAL_FRACTION
   if not needs: decisions.append(f"{idx}:readable({low_frac:.3f})"); continue
   relevant+=1
   ach_fraction=float(np.mean((vals.max(1).astype(int)-vals.min(1).astype(int))<=ACHROMATIC_DELTA))
   lum8=luma(vals.reshape(-1,1,3)).reshape(-1)*255
   two_tone=(np.mean(lum8<=64)>=TWO_TONE_FRACTION and np.mean(lum8>=192)>=TWO_TONE_FRACTION)
   ring=ndimage.binary_dilation(comp,structure=EIGHT)&~comp
   touches_true=bool(np.any(ring&true_aa)); touches_amb=bool(np.any(ring&aa_amb)); touches_core=bool(np.any(ring&chroma))
   exterior_contact=bool(np.any(ring&exterior))
   if ach_fraction<ACHROMATIC_REQUIRED: why="REVIEW-class-fraction"
   elif two_tone: why="REVIEW-two-tone"
   elif touches_true: why="REVIEW-true-chromatic-AA-boundary"
   elif touches_amb: why="REVIEW-ambiguous-AA-boundary"
   elif touches_core: why="REVIEW-chroma-core-contact"
   elif not exterior_contact: why="REVIEW-no-exterior-alpha-topology"
   else:
    proposal|=comp; accepted.append(idx); decisions.append(f"{idx}:candidate-separated({low_frac:.3f})"); continue
   rejected.append(idx); decisions.append(f"{idx}:{why}")
  incomplete=bool(accepted and rejected)
  if incomplete: proposal[:]=False; decisions.append("CASE:REVIEW-incomplete-wordmark-separation")
  # Cautious brand/gold probe is diagnostic only; never emits an edit.
  if case["probe"]: proposal[:]=False; decisions.append("CASE:REVIEW-probe-only-brand-protection")
  intersect=int(np.count_nonzero(proposal&(chroma|true_aa|aa_amb)))
  if intersect: raise RuntimeError(f"edit intersects core/AA/ambiguous class {case['case']}: {intersect}")
  candidate_layer=fitted.copy(); changed=proposal&np.any(candidate_layer[:,:,:3]!=DARK,axis=2)
  candidate_layer[:,:,:3][proposal]=DARK
  alpha_equal=bool(np.array_equal(candidate_layer[:,:,3],fitted[:,:,3]))
  chroma_equal=bool(np.array_equal(candidate_layer[chroma],fitted[chroma]))
  aa_equal=bool(np.array_equal(candidate_layer[true_aa],fitted[true_aa]))
  if not(alpha_equal and chroma_equal and aa_equal): raise RuntimeError(f"preservation invariant failed {case['case']}")
  if np.any(proposal&(chroma|true_aa|aa_amb)): raise RuntimeError("hard fail: edit reaches possible chromatic or AA pixel")
  composite=Image.alpha_composite(Image.fromarray(master_px,"RGBA"),Image.fromarray(candidate_layer,"RGBA"))
  if not accepted or incomplete or case["probe"]: composite=Image.fromarray(current,"RGBA")
  candidate_path=out/"candidates"/(case["key"]+"-white.png"); composite.save(candidate_path)
  cand_px=np.array(composite.convert("RGBA")); curr_diff=int(np.count_nonzero(np.any(cand_px!=current,axis=2)))
  if case["case"]=="PASS-control" and (int(changed.sum()) or curr_diff): raise RuntimeError("PASS control changed")
  # complete wordmark guard passes only when every contrast-relevant component
  # was accepted, with no component rejected and no case-level override.
  wordmark_guard=(relevant>0 and len(accepted)==relevant and not rejected and not incomplete and not case["probe"])
  final_status="PASS" if case["case"]=="PASS-control" else ("AUTO-FIX-CANDIDATE" if int(changed.sum()) and wordmark_guard else "REVIEW")
  reason=("PASS control preserved exactly, zero changed pixels" if case["case"]=="PASS-control" else
   "complete contrast-relevant achromatic components passed boundary and exterior topology guards" if final_status=="AUTO-FIX-CANDIDATE" else
   "cautious probe; no edit emitted" if case["probe"] else
   "; ".join(sorted({d.split(":",1)[1] for d in decisions if "REVIEW" in d})) or "no complete safe contrast repair demonstrated")
  # Mask panel class paints are mutually informative; AA ambiguous gets its own panel.
  stem=case["key"]
  sourcepanel=fitted
  panels=[tile("SOURCE (fitted; transparent canvas)",rgba=sourcepanel),
   tile("CHROMA CORE",mask=chroma,color=(236,54,65)),
   tile("OLD DILATED PROTECTED (core + ring)",mask=chroma|old_ring,color=(238,169,31)),
   tile("NEW TRUE-AA PROTECTED",mask=true_aa,color=(244,106,38)),
   tile("NEW AMBIGUOUS (including low alpha)",mask=ambiguous,color=(170,90,220)),
   tile("RELEASED FROM OLD RING (geometric-only)",mask=geometric,color=(60,190,255)),
   tile("EDITABLE ACHRO CORE / EMITTED MASK",mask=proposal,color=(71,210,122)),
   tile("CANDIDATE on WHITE",rgba=cand_px)]
  contact(panels,out/"masks"/(stem+"-MASK-CLASSIFICATION.jpg"),cols=3)
  comp_sheet(fitted,current,cand_px,case["case"],out/"comparisons"/(stem+"-SOURCE-CURRENT-CANDIDATE.jpg"))
  row={"case_number":case["case"],"source_path":case["source"],"current_white_path":case["current"],"source_sha256":sha(src_bytes),"current_white_sha256":sha(cur_bytes),"candidate_sha256":sha(candidate_path.read_bytes()),"duplicate_relationship":case["duplicate"],"old_protected_boundary_pixel_count":int(old_ring.sum()),"new_protected_AA_pixel_count":int(true_aa.sum()),"pixels_removed_from_old_boundary_protection":int(geometric.sum()),"pixels_newly_classified_ambiguous_in_boundary":int(np.count_nonzero(aa_amb&old_ring)),"total_ambiguous_visible_pixel_count":int(ambiguous.sum()),"edit_mask_protected_intersection_pixels":intersect,"alpha_unchanged":alpha_equal,"chroma_core_unchanged":chroma_equal,"new_true_AA_unchanged":aa_equal,"candidate_vs_current_changed_pixels":curr_diff,"changed_achromatic_core_pixels":int(changed.sum()),"achromatic_component_count":int(ach_n),"chromatic_component_count":int(chroma_n),"accepted_separated_component_count":len(accepted),"rejected_ambiguous_component_count":len(rejected),"contrast_relevant_component_count":relevant,"complete_wordmark_guard":wordmark_guard,"status":final_status,"reason":reason,"component_decisions":";".join(decisions),"fitted_bbox":str(bbox)}
  rows.append(row); cache[case["key"]]=(fitted,current,cand_px)
  if case["key"]=="14607":
   cache["14611"]=(fitted,current,cand_px)
   # source/current digest assertions establish duplicate reuse, don't process twice
 for dup,orig in (("14611","14607"),):
  d=next(x for x in rows if x["case_number"]=="#"+dup); o=next(x for x in rows if x["case_number"]=="#"+orig)
  if d["source_sha256"]!=o["source_sha256"] or d["current_white_sha256"]!=o["current_white_sha256"] or d["candidate_sha256"]!=o["candidate_sha256"]: raise RuntimeError("#14607/#14611 are not byte-identical; duplicate mapping must be reviewed")
 with (out/"AUDIT.csv").open("w",newline="",encoding="utf-8") as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
 (out/"SUMMARY.json").write_text(json.dumps({"classifier":"strict source-RGB continuity + alpha attenuation; frozen V9 alpha floor and delta; no logo-specific masks","white_master_sha256":master_sha,"results":rows},indent=2),encoding="utf-8")
 # Group #14607/#14611 only once as requested; retain both rows in audit.
 grouped=[]
 for key in ("14607","14700","14593","14597","pass"):
  a,b,c=cache[key]; grouped.append((key,a,b,c))
 sheet=Image.new("RGB",(1320,292*len(grouped)),(255,255,255))
 for j,(key,a,b,c) in enumerate(grouped):
  tmp=out/"comparisons"/(key+"-SOURCE-CURRENT-CANDIDATE.jpg")
  im=Image.open(tmp).convert("RGB"); sheet.paste(im,(0,j*292))
 sheet.save(out/"COMPARISON-SHEET.jpg",quality=94)

def main():
 p=argparse.ArgumentParser(); p.add_argument("--fixture-root",type=Path,required=True); p.add_argument("--output-dir",type=Path,required=True)
 a=p.parse_args(); out=a.output_dir.resolve()
 if "picons" in out.parts: raise SystemExit("output directory must remain outside production picons/")
 run(a.fixture_root.resolve(),out,None)
if __name__=="__main__": main()
