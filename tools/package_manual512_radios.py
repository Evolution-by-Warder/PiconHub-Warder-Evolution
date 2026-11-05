"""Package reviewed Radio originals, verify nine variants, preserve prior approved checkpoint."""
from pathlib import Path
from PIL import Image
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse,hashlib,io,json,re,zipfile,time
PINS={'white':'c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589','black':'61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe'}
SIZES={'50x30':(50,30),'220x132':(220,132),'400x240':(400,240)}
SHA=lambda b:hashlib.sha256(b).hexdigest()
def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--ready',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--review-root',type=Path,required=True);p.add_argument('--cache',type=Path,required=True);p.add_argument('--templates',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--catalogue',type=Path,required=True);p.add_argument('--snapshot-file',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=True)
 rows=json.load(open(a.ready));baseline=json.load(open(a.baseline/'complete-ready-manifest.json'));before={r['reference'] for r in baseline};new={r['reference'] for r in rows};assert len(new)==len(rows) and not new&before
 masters={'transparent':Image.new('RGBA',(220,132))}
 for style,digest in PINS.items():
  raw=(a.templates/(style+'.png')).read_bytes();assert SHA(raw)==digest;masters[style]=Image.open(io.BytesIO(raw)).convert('RGBA')
 expected_cache={};evidence=set();verified_assets=set();all_input=json.load(open(a.review_root/'source-files/assistant-review-input.json'))
 for row in all_input:
  s=row['source'];evidence.add(s['path']);raster=s.get('frozen_svg_raster');evidence.add(row['page']['path'])
  assert SHA((a.review_root/'source-files'/s['path']).read_bytes())==s['sha256']
  if raster:evidence.add(raster['path']);assert SHA((a.review_root/'source-files'/raster['path']).read_bytes())==raster['sha256']
 for number,row in enumerate(rows,1):
  assert re.fullmatch(r'(4097|5001|5002):0:2:(?:[A-Fa-f0-9]+:){6}[A-Fa-f0-9]+',row['reference']);assert set(row['renders'])=={size+'/'+style for size in SIZES for style in masters}
  source=row['source'];key=source['sha256'];assert row['asset_snapshot'] and len(row['asset_snapshot'])==40
  if key not in expected_cache:
   raster=source.get('frozen_svg_raster',source);raw=(a.cache/raster['path']).read_bytes();assert SHA(raw)==raster['sha256'];mark=Image.open(io.BytesIO(raw)).convert('RGBA');mark.thumbnail((192,104),Image.Resampling.LANCZOS);pos=((220-mark.width)//2,(132-mark.height)//2);expected={}
   for style,master in masters.items():
    canvas=master.copy()
    if style=='transparent':canvas.paste(mark,pos)
    else:canvas.alpha_composite(mark,pos)
    for size,dim in SIZES.items():
     target=canvas if dim==(220,132) else canvas.resize(dim,Image.Resampling.LANCZOS);expected[size+'/'+style]=SHA(target.tobytes())
   expected_cache[key]=expected
  for variant,asset in row['renders'].items():
   path=a.cache/asset['path'];raw=path.read_bytes();assert len(raw)==asset['bytes'] and SHA(raw)==asset['sha256']
   if asset['sha256'] not in verified_assets:
    with Image.open(io.BytesIO(raw)) as im:im.verify()
    with Image.open(io.BytesIO(raw)) as im:
     assert im.mode=='RGBA' and im.size==SIZES[variant.split('/')[0]];assert SHA(im.tobytes())==expected_cache[key][variant]
    verified_assets.add(asset['sha256'])
  if number%100==0:print('Verified nine variants',number,'/',len(rows),flush=True)
 print('All PNG pixels verified; waiting for saved source snapshot',flush=True)
 deadline=time.monotonic()+900
 while not a.snapshot_file.exists():
  if time.monotonic()>deadline:raise TimeoutError('Git snapshot not saved; approved local PNG remain preserved')
  time.sleep(1)
 snapshot=a.snapshot_file.read_text().strip();assert re.fullmatch('[a-f0-9]{40}',snapshot)
 for row in rows:row['asset_snapshot']=snapshot
 tag='Manual512_'+datetime.now(ZoneInfo('Europe/Bratislava')).strftime('%Y%m%d_%H%M%S');packages=[]
 for start in range(0,len(rows),200):
  part=rows[start:start+200];name='Warder_Radio_'+tag+'_cast'+str(start//200+1).zfill(2)+'_'+str(len(part))+'_ref_'+str(len(part)*9)+'_PNG.zip';path=a.output/name
  with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
   for row in part:
    for variant,asset in sorted(row['renders'].items()):z.write(a.cache/asset['path'],variant+'/'+row['reference'].replace(':','_')+'.png')
   z.writestr('new-ready-manifest.json',json.dumps(part,ensure_ascii=False,indent=2)+'\n')
  with zipfile.ZipFile(path) as z:assert z.testzip() is None;assert sum(n.endswith('.png') for n in z.namelist())==len(part)*9
  packages.append(dict(name=name,bytes=path.stat().st_size,sha256=SHA(path.read_bytes()),references=len(part),pngs=len(part)*9));print('Saved package',len(packages),len(part),'references',flush=True)
 combined=list(baseline)
 for row in rows:combined.append(dict(country=row.get('country','WORLD'),reference=row['reference'],origins=['git/'+row['asset_snapshot']],asset_root=row['asset_root'],renders=row['renders'],station={k:row[k] for k in ['name','url','reference','group','country'] if k in row},status='ready_verified_owner_approved',asset_batch=tag,source=row['source'],page=row['page'],verification=row['verification']))
 dump(a.output/'complete-ready-manifest.json',combined);dump(a.output/'ready-references.json',sorted(before|new))
 decisions=json.load(open(a.review_root/'next-source-decisions-complete.json'));assert decisions['last_saved_ready_references']==len(combined);decisions['supplement_snapshots']=sorted({row['asset_snapshot'] for row in rows});dump(a.output/'source-decisions-complete.json',decisions)
 catalogue=json.load(open(a.catalogue));allgroups={x['group'] for x in catalogue};oldgroups={x['group'] for x in catalogue if x['reference'] in before};newgroups={x['group'] for x in catalogue if x['reference'] in before|new};coverage=dict(total_countries=len(allgroups)-1,covered_countries=len(newgroups)-1,new_countries=sorted(newgroups-oldgroups),remaining_countries=sorted(allgroups-newgroups),non_country_group='HDF Radio zoznam',main_catalogue_ready=sum(x['reference'] in before|new for x in catalogue),main_catalogue_total=len(catalogue));dump(a.output/'coverage.json',coverage)
 summary=dict(complete=True,tag=tag,baseline_references=len(baseline),new_references=len(rows),new_pngs=len(rows)*9,combined_references=len(combined),combined_pngs=len(combined)*9,source_hashes_reviewed=len(json.load(open(a.review_root/'selected-source-claim.json'))['sources']),source_hashes_used_new=len(expected_cache),source_hashes_visually_approved=512-len(json.load(open(a.review_root/'review-decisions.json'))['exceptions']),new_reviewed_unique_source_hashes=decisions['checked_unique_source_hashes']-json.load(open(a.baseline/'source-decisions-complete.json'))['checked_unique_source_hashes'],already_closed_source_hashes_preserved=0,reviewed_source_hashes_total=decisions['checked_unique_source_hashes'],source_snapshots=sorted({row['asset_snapshot'] for row in rows}),packages=packages,coverage=coverage,countries=dict(Counter(x['group'] for x in rows)),verified_master_pixels=True,approved_baseline_modified=False,production_changed=False);dump(a.output/'summary.json',summary)
 recovery=a.output/('Warder_Radio_'+tag+'_originaly_stav_a_obnova.zip')
 with zipfile.ZipFile(recovery,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name in ['summary.json','complete-ready-manifest.json','ready-references.json','source-decisions-complete.json','coverage.json']:z.write(a.output/name,name)
  for rel in sorted(evidence):z.write(a.review_root/'source-files'/rel,rel)
  for style in PINS:z.write(a.templates/(style+'.png'),'templates/'+style+'.png')
  for name in ['selected-source-claim.json','review-decisions.json','prepare_selected_review.py','package_reviewed_radios.py','deduplication-baseline.json']:z.write(a.review_root/name,'review/'+name)
  for name in ['assistant-review-input.json','assistant-review-decisions.json','assistant-source-decisions.json']:z.write(a.review_root/'source-files'/name,'review/'+name)
  z.write(Path(__file__).resolve().parent/'render_manual512_radio.py','review/review_missing_country_logos.py')
  z.writestr('new-ready-manifest.json',json.dumps(rows,ensure_ascii=False,indent=2)+'\n');z.write(a.catalogue,'catalogue-reference-map.json')
 with zipfile.ZipFile(recovery) as z:assert z.testzip() is None
 summary.update(recovery_file=recovery.name,recovery_bytes=recovery.stat().st_size,recovery_sha256=SHA(recovery.read_bytes()));dump(a.output/'saved-result.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main()
