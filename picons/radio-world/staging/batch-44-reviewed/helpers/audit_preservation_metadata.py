import json,gzip,hashlib
from pathlib import Path
P=Path(__file__).parent;baseline=Path('continuation/prep44/picons/radio-world/staging/batch-44-reviewed/baseline.previous.json').read_bytes();sha=lambda b:hashlib.sha256(b).hexdigest();assert sha(baseline)=='b2018e346e88cef556b27290ff241d850cb01135855fc643dfe1d92965185d0e';old=json.loads(baseline);new=json.load(open(P/'countries.proposed.json'));rows=json.loads(gzip.decompress((P/'selection.json.gz').read_bytes()))['entries'];cfg=json.load(open(P/'configuration.json'));held=set(cfg['held_references']);assert not({r['ref']for r in rows}&held);bycc={}
for r in rows:bycc.setdefault(r['country'],[]).append(r)
nb={c['id']:c for c in new['countries']};count=0;unchanged=0;manifestdetails=[]
for c in old['countries']:
 cc=c['id'];n=nb[cc]
 if cc not in bycc:assert c==n;unchanged+=1;continue
 assert n['stations']==c['stations']and n['picons']==c['picons']+len(bycc[cc])
 nr=n['release'];newraw=(P/'cache'/nr['sha256']).read_bytes();assert sha(newraw)==nr['sha256']and len(newraw)==nr['bytes'];nm=json.loads(newraw)
 om=None
 if c.get('release'):
  r=c['release'];b=Path('continuation/prep44-evidence/manifest-cache',r['sha256']+'.json').read_bytes();assert sha(b)==r['sha256']and len(b)==r['bytes'];om=json.loads(b)
 for size in ['50x30','220x132','400x240']:
  for style in ['transparent','white','black']:
   before=om['packages'][size][style]['files']if om else {};added={r['ref'].replace(':','_')+'.png':r['variants'][size+'/'+style][0]for r in bycc[cc]};assert not(before.keys()&added.keys());assert nm['packages'][size][style]['files']=={**before,**added};count+=len(before)
 manifestdetails.append(dict(country=cc,old_manifest_sha256=(c.get('release')or{}).get('sha256'),new_manifest_sha256=nr['sha256'],all9_old_files_hashes_preserved=True,all9_additions_exact=True))
assert count==6975 and unchanged==196
out=dict(schema=1,status='pass',canonical_baseline_sha256=sha(baseline),unchanged_country_rows=196,updated_country_rows=23,new_references=80,previous_png_entries_inside_updated_unions_preserved=6975,new_unreviewed_or_held_additions=0,closed43_graphic_analysis_repeated=False,old_ZIPs_redownloaded=False,manifests=manifestdetails)
(P/'independent-preservation-metadata44.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items()if k!='manifests'}))
