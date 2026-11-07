import json,hashlib,tarfile,copy
from pathlib import Path
P=Path(__file__).parent;S='picons/radio-world/staging/batch-44-zeno54-recovery';OLD='2322e554ea89b024db8c184ed193e5be40c8a996';FINAL='890c9edb644d676f5b33855268f39aefbad65be8'
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def save(n,o):(P/n).write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
qs=json.load(open(P/'qa-first27.json'))['entries']+json.load(open(P/'qa-last27.json'))['entries'];assert len(qs)==54 and len({e['index']for e in qs})==54
rows=json.load(open(P/'rendered/rendered-selection.json'))['entries'];byid={r['index']:r for r in rows};obs=json.load(open(P/'eligible-source-observations.json'))['entries'];obsby={o['index']:o for o in obs};old=json.load(open(P/'snapshot2322.json'))['entries'];template=json.load(open(P/'plan113.json'));mf=json.load(open(P/'cache-manifest.json'));shards={s['path']:s for s in mf['shards']}
for q in qs:
 assert q['row']['variants']==byid[q['index']]['variants']and set(q['reviewed_variants'])==set(q['row']['variants']);q['row']=copy.deepcopy(byid[q['index']]);q['row'].pop('variant_paths',None)
qby={q['index']:q for q in qs};accepted=[r for r in rows if qby[r['index']]['decision']=='approve'];holds=[q for q in qs if q['decision']=='hold'];assert len(accepted)==51 and len(holds)==3
save('new-nine-variant-votes.json',dict(schema=1,scope='Fresh physical recovery54 actual nine-variant review; old lost tuples not reused',references=54,png_instances_reviewed=486,approve=51,hold=3,entries=qs))
def resource(h):
 s=shards[mf['objects'][h]];b=None
 with tarfile.open(P/'resource-cache'/(s['sha256']+'.blob'),'r:gz')as t:b=t.extractfile('objects/'+h+'.body').read()
 assert sha(b)==h
 return dict(sha256=h,bytes=len(b),git_blob=blob(b),object_path='objects/'+h+'.body',frozen_archive={**{k:s[k]for k in ['sha256','bytes','git_blob']},'url':'https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'+OLD+'/picons/radio-world/staging/zeno-primary-20261107/'+s['path']})
originals={};primary=[];delivery=[]
for r0 in rows:
 r=copy.deepcopy(r0);r.pop('variant_paths',None);r['asset_root']=S+'/verified-assets';q=qby[r['index']];o=obsby[r['index']];r['final_visual_approval']={k:q[k]for k in ['decision','reason','reviewed_variants']};delivery.append(r);h=o['source_sha256'];originals[h]={**resource(h),'url':o['source_url'],'final_url':o['source_final_url'],'format':o['source_format'],'dimensions':o['source_dimensions']};primary.append(dict(index=o['index'],ref=r['ref'],catalogue_name=r['station']['name'],catalogue_stream=r['station']['url'],catalogue_country=r['station']['group'],api_url=o['api_url'],api_resource=resource(o['api_sha256']),primary_fields=o['primary_fields'],source_sha256=h,source_visual_decision=dict(decision='source_pass',reason='Recovered actual prior source pass, exact immutable API/source/final snapshot reconciliation; new actual all9 QA separately recorded.',source_sha256=h,api_sha256=o['api_sha256']),no_private_headers_or_raw_html=True,final_snapshot_exact_match=True,exact_catalogue_membership=o['exact_catalogue_membership']))
render=json.load(open(P/'rendered/sources.json'));render['source_inventory']={h:v for h,v in render['source_inventory'].items()if h in originals}
# Frozen source plan uses rows, not a fabricated schema.

print('RENDERSCHEMA',list(render)); print('COUNTS',[(k,len(v))for k,v in render.items()if isinstance(v,(list,dict))])
receipt=json.load(open(P/'receipt96.json'));notids=sorted(set([e['index']for e in receipt['source_review']['source_holds']]+[e['index']for e in receipt['final_review']['holds']]+[e['index']for e in holds]))
plan=dict(schema=1,repository='Evolution-by-Warder/PiconHub-Warder-Evolution',stage=S,chunk=1,references=54,png_instances=486,approved_references=51,quarantined_references=3,unique_pngs=len({v[0]for r in delivery for v in r['variants'].values()}),runtime={'pillow':'13.0.0'},resources=template['resources'],originals=originals,primary_observations=primary,render_sources=render,expected_selection={'entries':delivery},must_not_admit_indices=notids,quarantine_indices=[e['index']for e in holds],frozen_checkpoint_commit=OLD,final_frozen_source_commit=FINAL,primary_freeze_final=True,final_freeze_reconciliation_required=False,source_retrieval='Read-only existing immutable GitHub shards only; no live station-source requests',old_manual_receipt_sha256=sha((P/'receipt96.json').read_bytes()),new_actual_nine_review_sha256=sha((P/'new-nine-variant-votes.json').read_bytes()))
save('producer-plan.json',plan)
