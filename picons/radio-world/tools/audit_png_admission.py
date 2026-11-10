"""Independently bind every non-production candidate PNG to an exact approved nine-variant review."""
import argparse,json,gzip
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from visual_gate import read,fingerprint,SIZES,STYLES,merge_ledgers,identity_blocks,explicit_source_resolution
from saved_artwork_import import get
p=argparse.ArgumentParser();p.add_argument('--index',required=True);p.add_argument('--production',required=True);p.add_argument('--ledger',required=True,action='append');p.add_argument('--output',required=True);a=p.parse_args()
index=read(a.index);production=read(a.production);ledger=merge_ledgers(a.ledger)
old={r['id']:r for r in production['countries']};new={r['id']:r for r in index['countries']}
assert len(old)==len(new)==219 and old.keys()==new.keys()
approved={};rejected=set();blocked=identity_blocks(ledger)
for e in ledger['entries']:
 key=fingerprint(e['row'])
 if e['decision']=='hold':rejected.add(key)
 else:
  assert e['decision']=='approve'
  assert (e['row']['country'],e['row']['ref']) not in blocked or explicit_source_resolution(e)
  approved[key]=e['row']
assert not approved.keys() & rejected
byidentity={}
for key,row in approved.items():
 identity=(row['country'],row['ref']);assert identity not in byidentity
 byidentity[identity]=row
entries={e['url']:e for table in (old,new) for r in table.values() if (e:=r['release'])}
with ThreadPoolExecutor(max_workers=12) as pool:
 manifests=dict(zip(entries,pool.map(lambda e:json.loads(get(e)),entries.values())))
checked=set();new_pngs=0;total_pngs=0;seen_collections=set()
for code,row in new.items():
 if not row['release']:continue
 manifest=manifests[row['release']['url']];baseline=manifests[old[code]['release']['url']] if old[code]['release'] else None
 if row['collection'] not in seen_collections:
  seen_collections.add(row['collection']);total_pngs+=sum(len(v['files']) for styles in manifest['packages'].values() for v in styles.values())
 for size in SIZES:
  for style in STYLES:
   before=baseline['packages'][size][style]['files'] if baseline else {}
   current=manifest['packages'][size][style]['files']
   assert before.items()<=current.items()
   for name,digest in current.items():
    if name in before:continue
    ref=name[:-4].replace('_',':');identity=(code,ref)
    assert identity in byidentity,('Unreviewed PNG',code,name)
    value=byidentity[identity]['variants'][size+'/'+style];expected=value['sha256'] if isinstance(value,dict) else value[0]
    assert digest==expected,('Wrong reviewed PNG',code,name,size,style)
    checked.add((code,ref,size,style));new_pngs+=1
assert len(checked)==9*len(byidentity)==new_pngs,(len(checked),len(byidentity),new_pngs)
assert sum(r['picons'] for r in new.values())==1084+len(byidentity)
summary=dict(schema=1,all_new_pngs_bound_to_exact_approved_reviews=True,approved_nonproduction_references=len(byidentity),verified_new_png_variant_entries=new_pngs,candidate_png_variant_entries_including_aliases=total_pngs,protected_production_png_variant_entries=total_pngs-new_pngs,immutable_manifest_urls=len(entries),countries=dict(total=219,available=sum(bool(r['release']) for r in new.values()),complete=sum(r['status']=='complete' for r in new.values()),partial=sum(r['status']=='partial' for r in new.values()),unavailable=sum(r['status']=='unavailable' for r in new.values())),references=dict(total=sum(r['stations'] for r in new.values()),covered=sum(r['picons'] for r in new.values()),remaining=sum(r['stations']-r['picons'] for r in new.values())))
assert summary['protected_production_png_variant_entries']==10332
Path(a.output).write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
