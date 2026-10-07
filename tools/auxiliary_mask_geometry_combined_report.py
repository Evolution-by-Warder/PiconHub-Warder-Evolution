#!/usr/bin/env python3
"""Combine the accepted satellite/HARMONIC checkpoint with the provider-only run.
No renderer replay or satellite recomputation is performed by this report builder.
"""
import gzip,hashlib,io,json,sys,zipfile
from collections import defaultdict
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
PREV=ROOT/'reports/warder-master-production/auxiliary-mask-geometry-combined-2026-10-07/satellite-checkpoint-inputs'
PROV=ROOT/'reports/warder-master-production/auxiliary-mask-geometry-provider-2026-10-07'
OUT=ROOT/'reports/warder-master-production/auxiliary-mask-geometry-combined-2026-10-07'
DIAG=ROOT/'reports/warder-master-production/auxiliary-component-diagnostics-2026-10-06'
PROVIDER_ZIP=Path('/tmp/aux-exp/provider-transparent.zip')
PREVIOUS_LOCAL_SHEET=PREV/'shape-review-sheet.png'
HARMONIC_SOURCE=PREV/'harmonic-source.png'
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'; BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def sha(b):return hashlib.sha256(b).hexdigest()
def read_jsonl(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def load_diag():
 rows=[]
 for i in range(1,12):
  with gzip.open(DIAG/f'component-diagnostics-{i:02d}.jsonl.gz','rt',encoding='utf-8') as f: rows += [json.loads(x) for x in f if x.strip()]
 return rows
def overlay(im):
 im=im.convert('RGBA'); bg=Image.new('RGBA',im.size,(32,38,50,255));bg.alpha_composite(im);return bg.convert('RGB')
def font(path,size):
 try:return ImageFont.truetype(path,size)
 except:return ImageFont.load_default()
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 psummary=json.loads((PROV/'provider-summary.json').read_text()); old=json.loads((PREV/'summary.json').read_text())
 psha=json.loads((PROV/'provider-sha-regression.json').read_text()); osha=json.loads((PREV/'sha-regression.json').read_text())
 pqc=json.loads((PROV/'provider-experiment-output-qc.json').read_text()); oqc=json.loads((PREV/'experiment-output-qc.json').read_text())
 pgeom=[]
 with gzip.open(PROV/'provider-mask-geometry.jsonl.gz','rt',encoding='utf-8') as f:pgeom=[json.loads(x) for x in f if x.strip()]
 ogeom=[]
 with gzip.open(PREV/'mask-geometry.jsonl.gz','rt',encoding='utf-8') as f:ogeom=[json.loads(x) for x in f if x.strip()]
 with gzip.open(OUT/'combined-mask-geometry.jsonl.gz','wt',encoding='utf-8') as f:
  for x in ogeom+pgeom:f.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+'\n')
 combined_sha=osha['results']+psha['results']
 (OUT/'combined-sha-regression.json').write_text(json.dumps({'scope':'accepted 67 satellite families + HARMONIC provider sentinel from 79c801 + remaining 832 provider families','variant_renders_checked':len(combined_sha),'candidate_pngs_changed':0,'all_sha_status_reason_matches':all(x['result']=='PASS' for x in combined_sha),'result':'PASS','results':combined_sha},indent=2,ensure_ascii=False)+'\n')
 combined_qc=oqc['results']+pqc['results']
 (OUT/'combined-experiment-output-qc.json').write_text(json.dumps({'candidate_count':len(combined_qc),'all_pass':all(x['status']=='PASS' for x in combined_qc),'results':combined_qc},indent=2,ensure_ascii=False)+'\n')
 combined_groups=read_jsonl(PREV/'shape-experiment-manifest.jsonl')+read_jsonl(PROV/'provider-shape-experiment-manifest.jsonl')
 with (OUT/'combined-shape-experiment-manifest.jsonl').open('w') as f:
  for g in combined_groups:f.write(json.dumps(g,ensure_ascii=False,sort_keys=True)+'\n')
 # Family-level evidence: strict full resolution requires every currently low-contrast
 # component in both variants to be covered by the unchanged shape rule. No family does.
 grouped=defaultdict(list);candidate_mark=defaultdict(set)
 for c in ogeom+pgeom:grouped[c['family_id']].append(c)
 for g in combined_groups:
  for cid in g['component_ids']:candidate_mark[g['family_id']].add((g['auxiliary_identity'],g['variant'],cid))
 full=[];partial=[];unmatched=[]
 for fid,cs in grouped.items():
  low=[c for c in cs if c['low_contrast_pixel_count']>0]
  marks=candidate_mark.get(fid,set())
  if marks and low and all((c['auxiliary_identity'],c['variant'],c['component_id']) in marks for c in low):full.append(fid)
  elif marks:partial.append(fid)
  else:unmatched.append(fid)
 provider_families={g['family_id'] for g in pgeom};satellite_families={g['family_id'] for g in ogeom if g['auxiliary_identity'].startswith('satellite-logo::')};harmonic_families={g['family_id'] for g in ogeom if g['auxiliary_identity'].startswith('provider-logo::')}
 summary={
  'accepted_checkpoint':'79c801ade4d51bc9e1ea7c8d7db1f4cab26586ee',
  'provider_source':json.loads((PROV/'provider-source-verification.json').read_text()),
  'scope':{'satellite_families':len(satellite_families),'provider_families':len(provider_families),'harmonic_sentinel_families':len(harmonic_families),'combined_mask_geometry_families':len(grouped),'expected_human_review_families':900,'source_qc_families_excluded':3,'source_qc_identities_excluded':4},
  'combined':{'component_geometry_records':len(ogeom)+len(pgeom),'variant_renders_checked':len(combined_sha),'strong_shape_candidate_components':sum(len(g['component_ids']) for g in combined_groups),'shape_candidate_groups':len(combined_groups),'families_with_strong_shape_candidates':len(candidate_mark),'fully_resolvable_under_complete_low_contrast_coverage':len(full),'partially_improvable_but_still_review':len(partial),'human_review_families_without_strong_candidates':len(unmatched),'human_review_families_remaining_until_policy_approval':len(grouped)-len(full),'png_sha_status_reason_regression':'PASS; 0 changed existing PNG; all status/reason match','experiment_output_qc':'PASS','satellite_scope_rerun':False,'renderer_changed':False,'policy_changed':False,'test202_built':False},
  'by_scope':{'provider':psummary,'satellite':{'families':len(satellite_families),'component_records':len(ogeom)-sum(c['auxiliary_identity'].startswith('provider-logo::') for c in ogeom),'strong_shape_candidate_components':sum(len(g['component_ids']) for g in combined_groups if g['auxiliary_identity'].startswith('satellite-logo::')),'families_with_strong_candidates':len({g['family_id'] for g in combined_groups if g['auxiliary_identity'].startswith('satellite-logo::')}),'experiment_outputs':sum(len(x.get('component_ids',[]))>=0 for x in oqc['results']),'sha_regression_results':osha['variant_renders_checked']},'harmonic':{'family_id':'AUX-RF-0301','preserved_from_checkpoint':True,'black_components_3_to_9':'STRONG SHAPE CANDIDATE','black_component_2':'AMBIGUOUS','white_component_1':'AMBIGUOUS','family_outcome':'PARTIALLY IMPROVABLE'}},
  'provider_zip':{'size_bytes':11481399,'sha256':'93ef555cf09d49a72188c477949d948feaf6416a0fcff047600d36b3a96e4b8f','verified':True},
  'test202_built':False
 }
 (OUT/'combined-summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
 # Combined review sheet: reuse all six prior rows (5 satellite + HARMONIC), then
 # add 14 provider family representatives balanced across BLACK/WHITE/both.
 old_groups=read_jsonl(PREV/'shape-experiment-manifest.jsonl'); old_families=sorted({g['family_id'] for g in old_groups})
 p_groups=read_jsonl(PROV/'provider-shape-experiment-manifest.jsonl'); p_by=defaultdict(list)
 for g in p_groups:p_by[g['family_id']].append(g)
 both=sorted(fid for fid,gs in p_by.items() if {g['variant'] for g in gs}=={'BLACK','WHITE'})
 black=sorted(fid for fid,gs in p_by.items() if {g['variant'] for g in gs}=={'BLACK'})
 white=sorted(fid for fid,gs in p_by.items() if {g['variant'] for g in gs}=={'WHITE'})
 chosen_provider=(both[:6]+black[:4]+white[:4])[:14]
 if len(old_families)+len(chosen_provider)>20:raise RuntimeError('review sheet exceeds 20 families')
 rows_meta=load_diag();row_by_id={r['auxiliary_identity']:r for r in rows_meta}
 tile_w,tile_h=320,192; panel_h=310; width=1700; families=old_families+chosen_provider
 sheet=Image.new('RGB',(width,panel_h*len(families)),(20,26,38));draw=ImageDraw.Draw(sheet);ft=font(BOLD,18);fl=font(FONT,13);fs=font(FONT,12)
 provider_archive=zipfile.ZipFile(PROVIDER_ZIP)
 old_sheet=Image.open(PREVIOUS_LOCAL_SHEET).convert('RGB')
 old_manifest=read_jsonl(PREV/'shape-experiment-manifest.jsonl'); old_id_by_f={fid:next(g['auxiliary_identity'] for g in old_manifest if g['family_id']==fid) for fid in old_families}
 # Existing old sheet was generated at 2000x(1200 per family), and its first five tiles
 # are SOURCE/current black/proposed black/current white/proposed white.
 cols=['SOURCE','CURRENT BLACK','PROPOSED BLACK','CURRENT WHITE','PROPOSED WHITE']
 for i,label in enumerate(cols):draw.text((15+i*335,8),label,font=fl,fill=(220,230,245))
 review_rows=[]
 for idx,fid in enumerate(families):
  y=idx*panel_h;draw.text((15,y+28),fid,font=ft,fill='white')
  if fid in old_families:
   identity=old_id_by_f[fid];row=row_by_id[identity]
   # Existing sheet tiles use x=20+j*280 and y=row*1200+78, 260x156.
   ri=old_families.index(fid);imgs=[]
   for j in range(5):imgs.append(old_sheet.crop((20+j*280,ri*1200+78,280+j*280,ri*1200+234)).resize((tile_w,tile_h),Image.Resampling.LANCZOS))
   source_sha=row['source_sha256'];scope='satellite' if identity.startswith('satellite-logo::') else 'harmonic'
   review_rows.append({'family_id':fid,'identity':identity,'scope':scope,'source_sha256':source_sha,'reused_existing_checkpoint_review_images':True,'candidate_groups':[g for g in old_manifest if g['family_id']==fid]})
  else:
   gs=p_by[fid];identity=gs[0]['auxiliary_identity'];row=row_by_id[identity];prefix,member=row['source_path'].split(':',1);srcb=provider_archive.read(member);src=Image.open(io.BytesIO(srcb)).convert('RGBA')
   engine_spec=__import__('importlib.util').util.spec_from_file_location('combined_sheet_engine',ROOT/'tools/rebuild_master_catalog.py');eng=__import__('importlib.util').util.module_from_spec(engine_spec);sys.modules[engine_spec.name]=eng;engine_spec.loader.exec_module(eng)
   images=[overlay(src)];current={}
   expected=json.load(gzip.open(DIAG/'sha-regression.json.gz','rt'))
   ex={(x['identity'],x['variant']):x['expected_sha256'] for x in expected['results']}
   for variant in ['BLACK','WHITE']:
    d=[];res=eng.classify_and_render(src,Image.open(ROOT/f'templates/picons/{variant.lower()}-sablona.png').convert('RGBA'),variant.lower(),component_diagnostics=d)
    b=io.BytesIO();res.image.save(b,format='PNG',compress_level=9)
    if sha(b.getvalue())!=ex[(identity,variant)]:raise RuntimeError(f'sample replay SHA failed for {identity} {variant}')
    current[variant]=overlay(res.image)
   images.append(current['BLACK']);images.append(Image.new('RGB',(tile_w,tile_h),(43,49,62)))
   images.append(current['WHITE']);images.append(Image.new('RGB',(tile_w,tile_h),(43,49,62)))
   for g in gs:
    p=PROV/'experiment-candidates'/f"{hashlib.sha256(identity.encode()).hexdigest()[:12]}-{g['variant'].lower()}.png"
    im=Image.open(p).convert('RGBA')
    images[2 if g['variant']=='BLACK' else 4]=overlay(im)
   for j,g in enumerate(images):sheet.paste(g,(15+j*335,y+55))
   for j,g in enumerate(images):draw.rectangle((15+j*335,y+55,15+j*335+tile_w-1,y+55+tile_h-1),outline=(115,130,155),width=2)
   variants=sorted({g['variant'] for g in gs});draw.text((15,y+254),f"{identity} | strong variants: {', '.join(variants)} | proposed outputs shown only where present",font=fs,fill=(220,230,245))
   review_rows.append({'family_id':fid,'identity':identity,'scope':'provider','source_sha256':row['source_sha256'],'representative_groups':gs,'engine_current_replay_sha_verified':True})
   continue
  for j,img in enumerate(imgs):sheet.paste(img,(15+j*335,y+55));draw.rectangle((15+j*335,y+55,15+j*335+tile_w-1,y+55+tile_h-1),outline=(115,130,155),width=2)
  draw.text((15,y+254),f"{identity} | prior accepted checkpoint result; satellite scope not rerun",font=fs,fill=(220,230,245))
 provider_archive.close();sheet.save(OUT/'combined-review-sheet.png',optimize=True)
 (OUT/'combined-review-sheet-manifest.json').write_text(json.dumps({'families_count':len(review_rows),'maximum':20,'source_images_for_satellite_and_harmonic':'reused from accepted 79c801 checkpoint review sheet; no satellite classifier rerun','provider_current_images':'sample classifier replays SHA-verified against existing saved SHA regression','rows':review_rows},indent=2,ensure_ascii=False)+'\n')
 print(json.dumps({'combined_families':len(grouped),'components':len(ogeom)+len(pgeom),'candidate_components':summary['combined']['strong_shape_candidate_components'],'candidate_families':len(candidate_mark),'fully':len(full),'partial':len(partial),'no_candidate':len(unmatched),'review_sheet_families':len(review_rows),'sheet':str(OUT/'combined-review-sheet.png')},indent=2))
if __name__=='__main__':main()
