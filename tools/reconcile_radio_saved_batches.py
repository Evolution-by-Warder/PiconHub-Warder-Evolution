import json,zipfile,hashlib,io,copy
from pathlib import Path,PurePosixPath
from PIL import Image
from collections import Counter
p=Path(__file__).parent;parent=p.parent;out=p/'finished';out.mkdir(exist_ok=True);SHA=lambda b:hashlib.sha256(b).hexdigest();baseline=json.load(open(parent/'strict-ocr/finished/complete-ready-manifest.json'));before={x['reference']:x for x in baseline};badref='4097:0:2:4932:961E:ED:0:0:0:0';assert badref in before;kept={k:v for k,v in before.items() if k!=badref};oldreg=json.load(open(parent/'strict-ocr/finished/source-decisions-complete.json'))
source_recovery=next((parent/'baseline22').glob('*.zip'))
with zipfile.ZipFile(source_recovery) as z:
 manifest=json.loads(z.read('complete-ready-manifest.json'));newreg=json.loads(z.read('source-decisions-complete.json'));expected={x['name']:x for x in json.loads(z.read('packages.json'))};qa22rows=json.loads(z.read('ready-manifest.json'))
newrows={x['reference']:x for x in manifest if x['reference'] not in before};assert len(newrows)==881;duplicates=[x for x in qa22rows if x['reference'] in before];assert len(duplicates)==49
conflicts=[]
for row in duplicates:
 ref=row['reference'];different={k:dict(retained=before[ref]['renders'][k]['sha256'],batch22=v['sha256']) for k,v in row['renders'].items() if before[ref]['renders'][k]['sha256']!=v['sha256']}
 if different:conflicts.append(dict(reference=ref,resolution='Retain all previously saved PNG bytes without replacement',variants=different))
assert len(conflicts)==42
sizes={'50x30':(50,30),'220x132':(220,132),'400x240':(400,240)};packages=[];seen=set();verified=set()
for number,f in enumerate(sorted((parent/'baseline22/png-packages').glob('*.zip')),1):
 assert f.stat().st_size==expected[f.name]['bytes'] and SHA(f.read_bytes())==expected[f.name]['sha256'];partrefs=set();members=[]
 with zipfile.ZipFile(f) as z:
  for member in z.namelist():
   if not member.endswith('.png'):continue
   parts=PurePosixPath(member).parts;ref=PurePosixPath(member).stem.replace('_',':')
   if ref not in newrows:continue
   variant='/'.join(parts[-3:-1]);asset=newrows[ref]['renders'][variant];raw=z.read(member);assert SHA(raw)==asset['sha256'] and len(raw)==asset['bytes']
   if asset['sha256'] not in verified:
    with Image.open(io.BytesIO(raw)) as im:im.verify()
    with Image.open(io.BytesIO(raw)) as im:assert im.mode=='RGBA' and im.size==sizes[variant.split('/')[0]]
    verified.add(asset['sha256'])
   partrefs.add(ref);members.append((variant+'/'+PurePosixPath(member).name,raw))
  assert len(members)==len(partrefs)*9 and not seen&partrefs;seen|=partrefs;part=[newrows[r] for r in sorted(partrefs)];name='Warder_Radio_Davka22_Zlucene_cast'+str(number).zfill(2)+'_'+str(len(part))+'_ref_'+str(len(part)*9)+'_PNG.zip';dest=out/name
  with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as target:
   for member,raw in members:target.writestr(member,raw)
   target.writestr('new-ready-manifest.json',json.dumps(part,ensure_ascii=False,indent=2)+'\n')
  with zipfile.ZipFile(dest) as check:assert check.testzip() is None
  packages.append(dict(name=name,bytes=dest.stat().st_size,sha256=SHA(dest.read_bytes()),references=len(part),pngs=len(part)*9));print('Verified unique batch22 part',number,len(part),flush=True)
assert seen==set(newrows)
# Correct the first supplement download by withholding the one unconfirmed generic globe.
original=next(p.glob('Warder_Radio_Finalizacia_20261105_177*.zip'));replacement=out/'Warder_Radio_Finalizacia_20261105_176_ref_1584_PNG.zip'
with zipfile.ZipFile(original) as z,zipfile.ZipFile(replacement,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as target:
 rows=json.loads(z.read('new-ready-manifest.json'));part=[r for r in rows if r['reference']!=badref];assert len(part)==176;n=0
 for member in z.namelist():
  if member.endswith('.png') and PurePosixPath(member).stem.replace('_',':')!=badref:target.writestr(member,z.read(member));n+=1
 assert n==1584;target.writestr('new-ready-manifest.json',json.dumps(part,ensure_ascii=False,indent=2)+'\n')
with zipfile.ZipFile(replacement) as z:assert z.testzip() is None
combined=list(kept.values())+[newrows[r] for r in sorted(newrows)];assert len(combined)==19756 and all(next(x for x in combined if x['reference']==ref)==row for ref,row in kept.items())
registry=copy.deepcopy(oldreg);reg={x['sha256']:x for x in registry['decisions']};decision_conflicts=[]
for row in newreg['decisions']:
 h=row['sha256']
 if h not in reg:reg[h]=row
 elif row['decision']!=reg[h]['decision']:decision_conflicts.append(dict(sha256=h,earlier=reg[h],batch22=row))
# Official saved Tempo FM page embeds a file explicitly named Avatar_Logo_Tempo_FM_2025.png.
tempo='d6a7d01f94cb8290d6ff49850db5034e3b09d4264a7f0502c75c9c1ca751fd71';reg[tempo].setdefault('additional_reviews',[]).append(dict(review='QA22_reconciliation',decision='approve',reason='Current saved official tempofm.com.br page explicitly embeds Avatar_Logo_Tempo_FM_2025.png. This direct broadcaster proof resolves the catalogue-only uncertainty without changing PNG.'))
christo='4edb0069666fba28bc7f95aeac0d6bd65636f16667018ba0db72b86174dbf5bd';prior=copy.deepcopy(reg[christo]);reg[christo].update(decision='needs_replacement_or_stronger_programme_identity',reason='Generic globe from a directory-only image does not independently establish Cristo Viene La Red identity; withheld from ready pending broadcaster evidence.',superseded_review=prior)
registry.update(decisions=list(reg.values()),checked_unique_source_hashes=len(reg),last_saved_ready_references=len(combined),qa22_claim_closed=True,final775_claim_closed=True,strict_ocr_complete=True);assert len(reg)==14373
cat=json.load(open('/tmp/radio-country-check-catalogue.json'));ready={x['reference'] for x in combined};groups={r['group'] for r in cat if r['group']!='HDF Radio zoznam'};covered={r['group'] for r in cat if r['reference'] in ready and r['group'] in groups};missing=[r for r in cat if r['reference'] not in ready];coverage=dict(total_countries=len(groups),covered_countries=len(covered),remaining_countries=sorted(groups-covered),main_catalogue_total=len(cat),main_catalogue_ready=len(cat)-len(missing),main_catalogue_remaining=len(missing));assert coverage['main_catalogue_remaining']==21197
reconciliation=dict(baseline_references=len(baseline),batch22_raw_new=930,batch22_overlapping_ready=49,duplicate_different_png_sets_retained_earlier=len(conflicts),unique_new_batch22_references=len(newrows),withheld_previous_reference=dict(reference=badref,reason=reg[christo]['reason'],previously_saved_png_preserved=before[badref]),png_conflicts=conflicts,source_decision_conflicts=decision_conflicts,source_resolution=dict(Tempo_FM='Approve based on current saved official broadcaster page and explicitly named logo file',Cristo_Viene_La_Red='Hold generic directory-only globe pending independent broadcaster identity'))
summary=dict(complete_merge=True,catalogue_complete=False,production_changed=False,baseline_references=len(baseline),unique_new_batch22_references=881,quarantined_previously_ready_references=1,total_ready_references=len(combined),total_ready_pngs=len(combined)*9,source_hashes_reviewed=len(reg),coverage=coverage,all_new_png_sha256_crc_dimensions_and_rgba_verified=True,all_prior_png_bytes_preserved=True,packages=packages,replacement176=dict(name=replacement.name,bytes=replacement.stat().st_size,sha256=SHA(replacement.read_bytes())));
report=dict(project='Radio plugin',catalogue_complete=False,ready_references=len(combined),ready_main_catalogue=coverage['main_catalogue_ready'],remaining_main_catalogue=len(missing),coverage=coverage,references=[dict(station=r,status='not_saved_ready') for r in missing],notes=['Some remaining references have candidate images requiring independent programme identity review.','QA22 and775 reviews are closed and imported; strict screening completed4045 references,7 visually accepted and1held for Q2 programme identity.','Do not count automatic candidates as ready. Original catalogue names,streams,groups and service references are preserved.'])
for name,obj in [('summary.json',summary),('reconciliation.json',reconciliation),('coverage.json',coverage),('packages.json',packages)]: (out/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
(out/'Warder_Radio_Zostavajuce_referencie_20261105.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
recovery=out/'Warder_Radio_Zluceny_stav_20261105_19756_ref.zip'
with zipfile.ZipFile(recovery,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for name,obj in [('complete-ready-manifest.json',combined),('ready-references.json',sorted(ready)),('source-decisions-complete.json',registry),('quarantined-ready-references.json',[reconciliation['withheld_previous_reference']])]:z.writestr(name,json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
 for f in out.glob('*.json'):z.write(f,f.name)
 for st in ['white','black']:z.write(parent.parent/'snapshot-files/templates'/(st+'.png'),'templates/'+st+'.png')
 z.write(Path(__file__),'review/reconcile.py');z.writestr('README.txt','Current complete merged checkpoint19756 references. Older approved PNG bytes are preserved;49 batch22 duplicate references were filtered out. One previously counted generic globe is withheld until programme identity is established. Original PNG bytes remain in historical recovery. Source originals and code remain in prior immutable Git snapshots and saved recovery archives; this checkpoint contains full current manifests and the reconciliation audit. Production downloads unchanged.\n')
with zipfile.ZipFile(recovery) as z:assert z.testzip() is None
summary['recovery']=dict(name=recovery.name,bytes=recovery.stat().st_size,sha256=SHA(recovery.read_bytes()));(out/'saved-result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
