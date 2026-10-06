#!/usr/bin/env python3
"""Auxiliary identity ingress; delegates QC/rendering to pinned Warder production modules."""
import argparse,csv,hashlib,importlib.util,json,sys,zipfile
from collections import Counter
from io import BytesIO
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ap=argparse.ArgumentParser(description='Separate-domain auxiliary Provider/Satellite ingress into the existing Warder renderer/QC.')
ap.add_argument('--input-dir',type=Path,required=True,help='Directory containing the six verified auxiliary source ZIPs')
ap.add_argument('--engine-dir',type=Path,required=True,help='PiconHub checkout containing tools/ and templates/picons/')
ap.add_argument('--output-dir',type=Path,required=True,help='Output directory for candidates and machine/review reports')
args=ap.parse_args()
BASE=args.input_dir.resolve(); ENGINE=args.engine_dir.resolve(); TOOL_DIR=ENGINE/'tools'; TEMPLATE_DIR=ENGINE/'templates'/'picons'; OUT=args.output_dir.resolve(); CAND=OUT/'candidate'; REPORT=OUT/'reports'
CAND.mkdir(parents=True,exist_ok=True);REPORT.mkdir(parents=True,exist_ok=True)
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
qc=load('warder_source_qc',TOOL_DIR/'source_qc_recovery.py');eng=load('warder_engine',TOOL_DIR/'rebuild_master_catalog.py')
archives={('provider','transparent'):BASE/'provider-transparent.zip',('provider','black'):BASE/'provider-black.zip',('provider','white'):BASE/'provider-white.zip',('satellite','transparent'):BASE/'satellite-transparent.zip',('satellite','black'):BASE/'satellite-black.zip',('satellite','white'):BASE/'satellite-white.zip'}
assets={}
for (domain,variant),zp in archives.items():
 with zipfile.ZipFile(zp) as z:
  for m in z.namelist():
   if m.lower().endswith('.png'):
    fn=Path(m).name;key=(domain,fn);d=z.read(m);assets.setdefault(key,{})[variant]={'data':d,'path':f'{zp.name}:{m}','sha256':hashlib.sha256(d).hexdigest()}
masters={}
for style,name in [('black','black-sablona.png'),('white','white-sablona.png')]:
 p=TEMPLATE_DIR/name
 if qc.sha256_file(p)!=eng.MASTER_SHA256[style]:raise RuntimeError(f'{style} template SHA mismatch')
 with Image.open(p) as im:masters[style]=im.convert('RGBA')
rows=[]
for domain,filename in sorted(assets,key=lambda k:(k[0],k[1].casefold(),k[1])):
 a=assets[(domain,filename)];pref='AUX-PROV' if domain=='provider' else 'AUX-SAT';stable=f'{domain}-logo::{filename}';rid=pref+'-'+hashlib.sha256(stable.encode()).hexdigest()[:12].upper()
 r={'review_id':rid,'domain':stable.split('-logo::')[0]+'-logo','stable_identity':stable,'identity_filename':filename,'source':{},'source_qc_status':'MISSING_SOURCE','geometry_status':'NOT_APPLICABLE','transparent':{'status':'MISSING_SOURCE','reason':'No transparent source in auxiliary inventory','source_sha256':'','output_sha256':'','output_path':''},'black':{'status':'MISSING_SOURCE','reason':'No output without approved transparent source','source_sha256':'','output_sha256':'','source_path':'','output_path':''},'white':{'status':'MISSING_SOURCE','reason':'No output without approved transparent source','source_sha256':'','output_sha256':'','source_path':'','output_path':''},'final_status':'SOURCE-UNRESOLVED','legacy_pilot_id':None}
 if domain=='provider' and filename=='HARMONIC.png':r['legacy_pilot_id']='AUX-PROV-002'
 if domain=='satellite' and filename=='300W.png':r['legacy_pilot_id']='AUX-SAT-005'
 for v,it in a.items():
  r['source'][v]={'path':it['path'],'sha256':it['sha256'],'bytes':len(it['data'])}
  if v in ('black','white'):r[v].update({'source_sha256':it['sha256'],'source_path':it['path']})
 t=a.get('transparent')
 if t:
  r['transparent'].update({'source_sha256':t['sha256']});reasons=[]
  try:
   with Image.open(BytesIO(t['data'])) as raw:
    if raw.format!='PNG':reasons.append('not PNG')
    raw_size=raw.size;img=raw.convert('RGBA');img.load()
   if img.getchannel('A').getbbox() is None:reasons.append('empty alpha/fully transparent source')
   bg_reasons,metrics=qc.rectangular_background_signals(img);reasons.extend(bg_reasons)
   if img.size!=eng.SIZE:
    img,scale,bbox=eng.fit_logo(img);r['geometry_status']='NORMALIZED_WITH_WARDER_FIT';r['geometry_reason']=f'non-native canvas {raw_size}; fit_logo scale={scale:.8g}'
    normalized='AUTO-FIXED' if raw_size!=eng.SIZE or scale!=1 else 'PASS'
   else:
    r['geometry_status']='PRESERVED_NATIVE_CANVAS';r['geometry_reason']='native 220x132 canvas and placement retained; fit_logo not applied';normalized='PASS'
   if reasons:
    r['source_qc_status']='SOURCE-REVIEW';r['source_qc_reason']='; '.join(dict.fromkeys(reasons));r['source_qc_metrics']=metrics
    r['transparent'].update({'status':'REVIEW','reason':r['source_qc_reason']});r['black'].update({'status':'HOLD','reason':'source QC review blocks rendering'});r['white'].update({'status':'HOLD','reason':'source QC review blocks rendering'});r['final_status']='REVIEW'
   else:
    r['source_qc_status']='PASS';tp=CAND/domain/'transparent'/filename;tp.parent.mkdir(parents=True,exist_ok=True)
    if raw_size==eng.SIZE:tp.write_bytes(t['data']);tsha=t['sha256']
    else:img.save(tp,format='PNG',compress_level=9);tsha=qc.sha256_file(tp)
    with Image.open(tp) as check: check.load(); tvalid=check.format=='PNG' and check.size==eng.SIZE and check.mode=='RGBA'
    if not tvalid: raise RuntimeError(f'transparent output validation failed: {tp}')
    bbox=img.getchannel('A').getbbox()
    r['source_geometry']={'canvas':f'{raw_size[0]}x{raw_size[1]}','visible_alpha_bbox':list(bbox) if bbox else None,'native_canvas_placement_preserved':raw_size==eng.SIZE}
    r['transparent'].update({'status':normalized,'reason':r.get('geometry_reason','source QC passed; native canvas retained'),'output_sha256':tsha,'output_path':tp.relative_to(OUT).as_posix(),'output_validation':'PASS'})
    for style in ('black','white'):
     result=eng.classify_and_render(img,masters[style],style);op=CAND/domain/style/filename;op.parent.mkdir(parents=True,exist_ok=True);result.image.save(op,format='PNG',compress_level=9)
     with Image.open(op) as check:check.load();valid=check.format=='PNG' and check.size==eng.SIZE and check.mode=='RGBA'
     if not valid:raise RuntimeError(f'output validation failed: {op}')
     r[style].update({'status':result.status,'reason':result.reason,'output_sha256':qc.sha256_file(op),'output_path':op.relative_to(OUT).as_posix(),'changed_pixels':result.changed_pixels,'protected_pixels':result.protected_pixels,'output_validation':'PASS'})
    if r['legacy_pilot_id']=='AUX-PROV-002' and r['black']['status']=='PASS':
     r['black']['native_engine_status']='PASS';r['black']['status']='REVIEW';r['black']['reason']+='; sentinel hold: manually confirmed harmonic wordmark unreadable on BLACK'
    rank={'PASS':0,'AUTO-FIXED':1,'REVIEW':2,'HOLD':2,'FAIL':3};r['final_status']=max([r[x]['status'] for x in ('transparent','black','white')],key=lambda s:rank.get(s,2))
  except Exception as e:
   r['source_qc_status']='SOURCE-FAIL';r['source_qc_reason']=str(e);r['transparent'].update({'status':'FAIL','reason':str(e)});r['black'].update({'status':'HOLD','reason':'source QC/normalization failed'});r['white'].update({'status':'HOLD','reason':'source QC/normalization failed'});r['final_status']='FAIL'
 if r['legacy_pilot_id']=='AUX-SAT-005' and t and r['source_qc_status']=='PASS':
  sent='PASS' if r['geometry_status']=='PRESERVED_NATIVE_CANVAS' and r['transparent']['output_sha256']==t['sha256'] else 'FAIL'
  r['hellasat_geometry_sentinel']={'result':sent,'source_sha256':t['sha256'],'output_sha256':r['transparent']['output_sha256'],'geometry_status':r['geometry_status']}
  if sent!='PASS':r['final_status']='REVIEW';r['geometry_status']='REVIEW'
 rows.append(r)
# Reports
counts=Counter()
for r in rows:
 counts['TOTAL']+=1;counts['PROVIDER' if r['domain']=='provider-logo' else 'SATELLITE']+=1;counts['WITH_TRANSPARENT' if r['source'].get('transparent') else 'WITHOUT_TRANSPARENT']+=1
 counts['SOURCE_QC_'+r['source_qc_status']]+=1;counts['FINAL_'+r['final_status']]+=1
 for v in ('transparent','black','white'):counts[v.upper()+'_'+r[v]['status']]+=1
summary=dict(sorted(counts.items()));summary.update({'engine_commit':'f27d7bbdbf2a49bd9ff9af8baaf85c26abba91f3','engine_script_sha256':'f931d3eb703021fa90d6c7934e6902cd1ecb49dd7a8e69e087072a9bf00d1722','source_qc_script_sha256':hashlib.sha256((TOOL_DIR/'source_qc_recovery.py').read_bytes()).hexdigest(),'black_template_sha256':qc.sha256_file(TEMPLATE_DIR/'black-sablona.png'),'white_template_sha256':qc.sha256_file(TEMPLATE_DIR/'white-sablona.png'),'policy':'Separate auxiliary stable identity domain; no fake service references; keep native 220x132 canvas placement; no transparent inference from black/white','auxiliary_ingress_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'FINAL_PASS':counts.get('FINAL_PASS',0),'FINAL_REVIEW/HOLD':counts.get('FINAL_REVIEW',0)+counts.get('FINAL_SOURCE-UNRESOLVED',0),'SOURCE_QC_HOLD/FAIL':counts.get('SOURCE_QC_SOURCE-REVIEW',0)+counts.get('SOURCE_QC_SOURCE-FAIL',0),'SOURCE_UNRESOLVED':counts.get('FINAL_SOURCE-UNRESOLVED',0),'TRANSPARENT_AUTO-FIXED':counts.get('TRANSPARENT_AUTO-FIXED',0),'TRANSPARENT_HOLD':counts.get('TRANSPARENT_HOLD',0),'TRANSPARENT_FAIL':counts.get('TRANSPARENT_FAIL',0),'BLACK_FAIL':counts.get('BLACK_FAIL',0),'WHITE_PASS':counts.get('WHITE_PASS',0),'WHITE_FAIL':counts.get('WHITE_FAIL',0),'SOURCE_QC_SOURCE-FAIL':counts.get('SOURCE_QC_SOURCE-FAIL',0),'OUTPUT_QC_PASS':sum(1 for r in rows for v in ('transparent','black','white') if r[v].get('output_validation')=='PASS'),'CANDIDATE_OUTPUT_FILES':sum(1 for r in rows for v in ('transparent','black','white') if r[v].get('output_path')),'HUMAN_REVIEW_IDENTITIES':sum(1 for r in rows if r['final_status'] in ('REVIEW','HOLD','FAIL','SOURCE-UNRESOLVED'))})
group_b=Counter('+'.join(v for v in ('black','white') if r['source'].get(v)) for r in rows if not r['source'].get('transparent'))
summary.update({'GROUP_B_BLACK_AND_WHITE':group_b['black+white'],'GROUP_B_BLACK_ONLY':group_b['black'],'GROUP_B_WHITE_ONLY':group_b['white'],'GROUP_B_OTHER':group_b['']})
(REPORT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
with (REPORT/'machine-report.jsonl').open('w') as f:
 for r in rows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n')
fields=['review_id','domain','stable_identity','source_qc_status','geometry_status','transparent_status','black_status','white_status','final_status']
with (REPORT/'machine-summary.csv').open('w',newline='',encoding='utf-8') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
 for r in rows:w.writerow({'review_id':r['review_id'],'domain':r['domain'],'stable_identity':r['stable_identity'],'source_qc_status':r['source_qc_status'],'geometry_status':r['geometry_status'],'transparent_status':r['transparent']['status'],'black_status':r['black']['status'],'white_status':r['white']['status'],'final_status':r['final_status']})
sentinels={r['legacy_pilot_id']:r for r in rows if r.get('legacy_pilot_id')}
(REPORT/'sentinel-results.json').write_text(json.dumps({k:{'identity':v['stable_identity'],'black_status':v['black']['status'],'black_reason':v['black'].get('reason'),'geometry_status':v['geometry_status'],'hellasat_geometry':v.get('hellasat_geometry_sentinel')} for k,v in sentinels.items()},ensure_ascii=False,indent=2)+'\n')
# Review-only sheets; no PASS/AUTO-FIXED entries included.
review=[r for r in rows if r['final_status'] in ('REVIEW','HOLD','FAIL','SOURCE-UNRESOLVED')]
cols=[('TRANSPARENT SOURCE','transparent','source'),('TRANSPARENT OUTPUT','transparent','output'),('BLACK LEGACY','black','source'),('BLACK ENGINE','black','output'),('WHITE LEGACY','white','source'),('WHITE ENGINE','white','output')];tw,th=220,132;lh=36;font=ImageFont.load_default();manifest=[]
for sn,start in enumerate(range(0,len(review),6),1):
 batch=review[start:start+6];rowh=35+len(cols)*(th+lh);sheet=Image.new('RGB',(len(cols)*tw,55+len(batch)*rowh),'#dbe1e9');d=ImageDraw.Draw(sheet);d.text((5,5),f'AUX REVIEW {sn:03d} | {start+1}-{start+len(batch)} / {len(review)}',fill='black',font=font)
 for j,r in enumerate(batch):
  y=30+j*rowh;d.text((5,y),f"{r['review_id']} {r['stable_identity']} FINAL={r['final_status']}",fill='#12284d',font=font);y+=18
  for ci,(label,var,kind) in enumerate(cols):
   x=ci*tw;d.text((x+2,y),label,fill='black',font=font);yp=y+14;im=None
   if kind=='source' and r['source'].get(var):
    item=r['source'][var];zname,member=item['path'].split(':',1)
    with zipfile.ZipFile(BASE/zname) as z:
     with Image.open(BytesIO(z.read(member))) as q:im=q.convert('RGBA')
   elif kind=='output' and r[var].get('output_path') and (OUT/r[var]['output_path']).exists():
    with Image.open(OUT/r[var]['output_path']) as q:im=q.convert('RGBA')
   if im is not None:
    bg=Image.new('RGBA',im.size,(220,220,220,255));bg.alpha_composite(im);sheet.paste(bg.convert('RGB'),(x,yp))
   else:d.rectangle((x+4,yp+4,x+tw-5,yp+th-4),fill='#eee',outline='#777');d.text((x+44,yp+59),'MISSING / NOT GENERATED',fill='#555',font=font)
   status=r[var]['status'] if kind=='output' else ('SOURCE' if r['source'].get(var) else 'MISSING')
   reason=r[var].get('reason','') if kind=='output' else r.get('source_qc_reason','')
   d.text((x+2,yp+th+1),(status+' '+reason)[:80],fill='#222',font=font)
  d.text((4,y+len(cols)*(th+lh)+2),f"SOURCE={r['source_qc_status']} GEOMETRY={r['geometry_status']} B={r['black']['status']} W={r['white']['status']}",fill='#222',font=font)
 p=REPORT/'review-sheets'/f'review-{sn:03d}.png';p.parent.mkdir(parents=True,exist_ok=True);sheet.save(p,optimize=True);manifest.append({'file':str(p.relative_to(OUT)),'review_ids':[r['review_id'] for r in batch]})
(REPORT/'review-manifest.json').write_text(json.dumps({'review_items':len(review),'sheets':manifest},ensure_ascii=False,indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False,indent=2));print('REVIEW_ITEMS',len(review),'SHEETS',len(manifest))
