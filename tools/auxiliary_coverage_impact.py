#!/usr/bin/env python3
"""Compare the strict safe auxiliary tree with pinned current runtime ZIPs."""
from __future__ import annotations
import hashlib,json,zipfile
from collections import Counter,defaultdict
from io import BytesIO
from pathlib import Path,PurePosixPath
from PIL import Image

BASE=Path('reports/warder-master-production')
RUN=BASE/'auxiliary-ingress-run-2026-10-06'
GATE=BASE/'auxiliary-publishability-gate-2026-10-07'
OUT=BASE/'auxiliary-coverage-impact-2026-10-07'
ARCHIVES={
 'provider':{'transparent':Path('/tmp/piconhub-provider-transparent.zip'),'black':Path('/tmp/aux-source-recovery-provider-black.zip'),'white':Path('/tmp/aux-source-recovery-provider-white.zip')},
 'satellite':{'transparent':Path('/tmp/piconhub-satellite-transparent.zip'),'black':Path('/tmp/aux-source-recovery-satellite-black.zip'),'white':Path('/tmp/aux-source-recovery-satellite-white.zip')},
}
def sha(b):return hashlib.sha256(b).hexdigest()
def load_jsonl(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def main():
 provenance=json.load(open(RUN/'input-provenance.json'))
 expected={
  ('provider','transparent'):'provider-transparent',('provider','black'):'provider-black',('provider','white'):'provider-white',
  ('satellite','transparent'):'satellite-transparent',('satellite','black'):'satellite-black',('satellite','white'):'satellite-white'}
 inventories={}; archive_summary={}
 for domain,variants in ARCHIVES.items():
  inventories[domain]={}
  for variant,path in variants.items():
   pin=provenance['assets'][expected[(domain,variant)]]
   raw=path.read_bytes()
   if len(raw)!=pin['size_input'] or sha(raw)!=pin['sha256_input']: raise SystemExit(f'pinned current runtime ZIP mismatch: {domain} {variant}')
   z=zipfile.ZipFile(path); bad=z.testzip()
   if bad: raise SystemExit(f'ZIP CRC error {domain} {variant}: {bad}')
   entries={}; duplicates=[]
   for name in z.namelist():
    p=PurePosixPath(name)
    if name.endswith('/') or p.suffix.lower()!='.png': continue
    filename=p.name
    if filename in entries: duplicates.append(filename); continue
    data=z.read(name)
    im=Image.open(BytesIO(data)); im.load()
    if im.format!='PNG': raise SystemExit(f'bad PNG member {name}')
    entries[filename]={'archive_member':name,'sha256':sha(data),'dimensions':[im.width,im.height],'mode':im.mode,'byte_count':len(data)}
   inventories[domain][variant]=entries
   archive_summary[f'{domain}-{variant}']={'url':pin['url'],'archive':pin['archive'],'size_bytes':len(raw),'sha256':sha(raw),'zip_crc':'PASS','png_count':len(entries),'duplicate_filename_entries':sorted(duplicates)}
 # Strict safe identities and the excluded identities are the full known migration scope.
 safe={}
 for x in load_jsonl(GATE/'publishability-manifest.jsonl'):
  dom='provider' if x['domain']=='provider-logo' else 'satellite'; safe[(dom,x['identity_filename'])]=x
 exclusions={}
 for x in load_jsonl(GATE/'exclusion-manifest.jsonl'):
  dom='provider' if x['domain']=='provider-logo' else 'satellite'; exclusions[(dom,x['filename'])]=x
 if set(safe)&set(exclusions): raise SystemExit('safe/excluded identity overlap')
 current_keys={(d,n) for d,vs in inventories.items() for names in vs.values() for n in names}
 known=set(safe)|set(exclusions)|current_keys
 # Ensure family/identity coverage is tied to the accepted checkpoint, not a sample.
 if len(safe)!=173 or len(exclusions)!=1431: raise SystemExit('gate checkpoint totals do not match accepted baseline')
 rows=[]
 for domain,filename in sorted(known):
  variants={v:inventories[domain][v].get(filename) for v in ('transparent','black','white')}
  current_present=[v for v,x in variants.items() if x]
  k=(domain,filename)
  if k in safe: cls='SAFE-REPLACED'; subclass='PUBLISHABLE-SAFE-TRIAD'; exclusion=None
  elif not current_present: cls='NO-CURRENT-RUNTIME'; subclass='NONE'; exclusion=exclusions.get(k)
  elif variants['transparent']:
   cls='LEGACY-ONLY-IF-SAFE-TREE'; subclass='TRANSPARENT-ONLY-CURRENT'; exclusion=exclusions.get(k)
  else:
   cls='LEGACY-ONLY-IF-SAFE-TREE'; subclass='BLACK/WHITE-ONLY-CURRENT'; exclusion=exclusions.get(k)
  if cls!='SAFE-REPLACED' and cls!='NO-CURRENT-RUNTIME' and exclusion is None:
   raise SystemExit(f'current runtime identity missing gate exclusion: {domain} {filename}')
  rows.append({'identity':('provider-logo::' if domain=='provider' else 'satellite-logo::')+filename,'filename':filename,'domain':domain,'classification':cls,'subclassification':subclass,'current_variants':{v:variants[v] for v in ('transparent','black','white')},'safe_triads':safe[k] if k in safe else None,'family_id':exclusion.get('family_id') if exclusion else None,'exclusion_class':exclusion.get('exclusion_class') if exclusion else None,'exclusion_reason':exclusion.get('exact_reason') if exclusion else None})
 # Per-domain and per-variant exact set arithmetic.
 summary_domains={}
 for domain in ('provider','satellite'):
  current={v:set(inventories[domain][v]) for v in ('transparent','black','white')}
  safe_names={name for d,name in safe if d==domain}
  union=set.union(*current.values()) if current else set()
  if not safe_names<=union: raise SystemExit(f'safe identity absent from current runtime {domain}')
  provider_total_expected=1335 if domain=='provider' else 269
  publish_expected=172 if domain=='provider' else 1
  if len(union)!=provider_total_expected or len(safe_names)!=publish_expected: raise SystemExit(f'identity totals mismatch {domain}')
  summary_domains[domain]={'current_runtime_identities':len(union),'safe_replaced_identities':len(safe_names),'would_disappear_identities':len(union-safe_names),'current_variant_identities':{v:len(current[v]) for v in current},'safe_variant_identities':{v:len(safe_names) for v in current},'variant_identities_missing_after_safe_only':{v:len(current[v]-safe_names) for v in current},'legacy_only_if_safe_tree':len(union-safe_names),'transparent_only_current_subclass':len((current['transparent']-safe_names)),'black_white_only_current_subclass':len(union-current['transparent']),'no_current_runtime':0}
  # Our mutually exclusive subtype partition is expected to cover every non-safe identity.
  if summary_domains[domain]['transparent_only_current_subclass']+summary_domains[domain]['black_white_only_current_subclass']!=summary_domains[domain]['would_disappear_identities']:
   raise SystemExit(f'coverage subclasses do not partition exclusions for {domain}')
 # The known historical scope is fully represented by current runtime union in this pinned snapshot.
 if len(rows)!=1604: raise SystemExit(f'expected 1604 known identities, got {len(rows)}')
 losses=sum(v['would_disappear_identities'] for v in summary_domains.values())
 safe_total=sum(v['safe_replaced_identities'] for v in summary_domains.values())
 significant=losses>0
 proposal={
  'decision':'SAFE-ONLY MIGRATION NOT VIABLE; HYBRID FALLBACK REQUIRED',
  'reason':f'Safe-only replacement would remove {losses} of 1604 current runtime identities ({losses/1604:.1%}); provider loss {summary_domains["provider"]["would_disappear_identities"]}/{summary_domains["provider"]["current_runtime_identities"]}, satellite loss {summary_domains["satellite"]["would_disappear_identities"]}/{summary_domains["satellite"]["current_runtime_identities"]}.',
  'status':'PROPOSAL ONLY; NO CONSUMER OR PACKAGE CHANGES',
  'provider':{'priority_directory':'piconProv_220x132/','legacy_fallback_directory':'piconProv/','rule':'Place only approved Warder-safe 220x132 triad filenames in the priority directory. Keep existing legacy files in the base directory for identities absent from the safe priority set; do not relabel them Warder-approved.'},
  'satellite':{'priority_directory':'piconSat_220x132/','legacy_fallback_directory':'piconSat/','rule':'Place only approved Warder-safe 220x132 triad filenames in the priority directory. Keep existing legacy files in the base directory for identities absent from the safe priority set; do not relabel them Warder-approved.'},
  'consumer_contract':'Preserve the existing 220-width lookup order: *_220x132 first, then base directory fallback. This report does not modify the consumer.',
  'review_and_unresolved':'Keep REVIEW-BLOCKED and SOURCE-UNRESOLVED assets in existing legacy runtime storage only; never copy them into or mark them as approved in the Warder safe directory.',
  'no_publish':True}
 OUT.mkdir(parents=True,exist_ok=True)
 with (OUT/'current-runtime-inventory.jsonl').open('w') as f:
  for x in rows:f.write(json.dumps(x,sort_keys=True)+'\n')
 with (OUT/'safe-vs-current-mapping.jsonl').open('w') as f:
  for x in rows:f.write(json.dumps({'identity':x['identity'],'domain':x['domain'],'classification':x['classification'],'subclassification':x['subclassification'],'current_variants':{v:bool(x['current_variants'][v]) for v in ('transparent','black','white')},'safe_triads':bool(x['safe_triads']),'family_id':x['family_id'],'exclusion_class':x['exclusion_class']},sort_keys=True)+'\n')
 with (OUT/'coverage-loss-manifest.jsonl').open('w') as f:
  for x in rows:
   if x['classification']!='SAFE-REPLACED':f.write(json.dumps(x,sort_keys=True)+'\n')
 (OUT/'hybrid-migration-proposal.json').write_text(json.dumps(proposal,indent=2,sort_keys=True)+'\n')
 summary={'checkpoint':'a97acf919b93e4efaa1fc31766c55a634b487208','current_source_repo':'Evolution-by-Warder/FullHDGlass-Warder-Evolution','current_source_branch':'main','archives':archive_summary,'provider':summary_domains['provider'],'satellite':summary_domains['satellite'],'total_current_runtime_identities':sum(x['current_runtime_identities'] for x in summary_domains.values()),'total_safe_replaced':safe_total,'total_would_disappear':losses,'class_counts':{'SAFE-REPLACED':sum(x['classification']=='SAFE-REPLACED' for x in rows),'LEGACY-ONLY-IF-SAFE-TREE':sum(x['classification']=='LEGACY-ONLY-IF-SAFE-TREE' for x in rows),'TRANSPARENT-ONLY-CURRENT':sum(x['subclassification']=='TRANSPARENT-ONLY-CURRENT' for x in rows),'BLACK/WHITE-ONLY-CURRENT':sum(x['subclassification']=='BLACK/WHITE-ONLY-CURRENT' for x in rows),'NO-CURRENT-RUNTIME':sum(x['classification']=='NO-CURRENT-RUNTIME' for x in rows)},'subclass_counts':dict(Counter(x['subclassification'] for x in rows)),'safe_only_migration_viable':False if significant else True,'hybrid_fallback_required':significant,'hybrid_proposal':proposal,'production_changed':False,'test202':'NOT BUILT'}
 (OUT/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
 readme=f"""# Auxiliary coverage impact\n\nPinned current runtime archive inventory compared by auxiliary filename identity with strict publishable safe triads.\n\n- Provider: {summary_domains['provider']['current_runtime_identities']} current identities; {summary_domains['provider']['safe_replaced_identities']} safe; {summary_domains['provider']['would_disappear_identities']} absent from safe-only tree.\n- Satellite: {summary_domains['satellite']['current_runtime_identities']} current identities; {summary_domains['satellite']['safe_replaced_identities']} safe; {summary_domains['satellite']['would_disappear_identities']} absent from safe-only tree.\n- Safe-only migration: NOT VIABLE. Hybrid fallback: REQUIRED.\n- B (`LEGACY-ONLY-IF-SAFE-TREE`) is the exclusion umbrella; C and D subtypes separate those with a current transparent file from black/white-only identities.\n\nThe hybrid document is a proposal only. Current FullHDGlass consumer behavior is preserved by placing safe triads in the `*_220x132/` priority directory and leaving base legacy directories intact as fallback. No production ZIPs, downloads manifests, or consumer code were changed.\n"""
 (OUT/'README.md').write_text(readme)
 print(json.dumps(summary,indent=2,sort_keys=True))
if __name__=='__main__':main()
