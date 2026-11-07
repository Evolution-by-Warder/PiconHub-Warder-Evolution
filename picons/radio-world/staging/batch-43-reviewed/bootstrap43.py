#!/usr/bin/env python3
"""GitHub-CI-only bootstrap43. Copies approved metadata; never renders a PNG."""
import copy,gzip,hashlib,json,re,subprocess,sys,urllib.request,urllib.parse
from pathlib import Path,PurePosixPath
sys.path.insert(0,'picons/radio-world/tools')
from visual_gate import read,merge_ledgers,validate_selection
REPO='Evolution-by-Warder/PiconHub-Warder-Evolution'
PARENT='b99fe072f36d03871cc9c0e7546a5fc9294846a0'
PREP='00a5ffcf4b3140800756ea06f963c96c04121bc6'
OLD='80e62a88981ee09b1da90ed74b13a0a38bb31b88'
FROZEN='2322e554ea89b024db8c184ed193e5be40c8a996'
VOTES='ef2a66805edab4378c51937c870a1b870cc82e92'
OLDROOT='picons/radio-world/staging/zeno-primary-20261107'
ZENOROOT='picons/radio-world/staging/batch-43-44-zeno-source'
PRIMARYROOT='picons/radio-world/staging/batch-43-primary-source'
CONTRASTROOT='picons/radio-world/staging/contrast-repairs49-20261107'
stage=Path('picons/radio-world/staging/batch-43-reviewed')
inbox=stage/'bootstrap-inputs';inbox.mkdir(parents=True,exist_ok=True)
resources=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def put(path,b):
    path=Path(path);assert not path.exists()or path.read_bytes()==b,'Refusing unequal existing '+str(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        with path.open('xb')as f:f.write(b)
def packed(x):return gzip.compress((json.dumps(x,ensure_ascii=False,separators=(',',':'))+'\n').encode(),mtime=0)
def get(name,commit,path,expected,size=None):
    assert re.fullmatch('[0-9a-f]{40}',commit)
    p=PurePosixPath(path);assert not p.is_absolute()and'..'not in p.parts
    assert re.fullmatch('[0-9a-f]{40}|[0-9a-f]{64}',expected)
    url='https://raw.githubusercontent.com/'+REPO+'/'+commit+'/'+path
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=90)as r:
        assert urllib.parse.urlsplit(r.url).hostname=='raw.githubusercontent.com'
        b=r.read(32*1024*1024+1)
    assert len(b)<=32*1024*1024 and(size is None or len(b)==size)
    assert(blob(b)if len(expected)==40 else sha(b))==expected,'Pinned resource mismatch '+path
    put(inbox/name,b)
    resources.append(dict(commit=commit,path=path,expected_hash=expected,bytes=len(b),sha256=sha(b),git_blob=blob(b)))
    return b
def doc(b):return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
def rows(b):return doc(b)['entries']
# Exact four existing producer exports; these commits already contain the gzip exports.
z1=rows(get('zeno-001.json.gz','797f1454e1b46ff35829fb9f0f2e575f219829d5',ZENOROOT+'/selection.json.gz','c2caf759bcfe2501e75589b0b202ff22493230a93becfde59d0cdfc5b3965a5a'))
z2=rows(get('zeno-002.json.gz','825fd7e06b68493e933a5b6f8f5e09e5397d68fc',ZENOROOT+'/selection.json.gz','0f2fcd84212d485a6fe26b9080d87189a0539776bd9c2aec329ac3ccda781449'))
original_primary25=rows(get('primary-original25.json.gz','20b053d08f6609e5ff1fd583aa8808a073600bf1',PRIMARYROOT+'/selection.json.gz','d9a69bd529627c6068170bfc4c3c74a79cf5f2b2ed3f11dcd3e457096d5aa10d',21987))
primary=rows(get('primary-country-eligible24.json','7d89aff05454562b415e01c8815d00b58390169f',PRIMARYROOT+'/selection-country-eligible24.json','015c598d75c376b9d2592948999051652b557170354afdf0c145563694bdc9d3',118087))
put(inbox/'primary-selection.json.gz',packed(dict(entries=primary)))
get('hdf-quarantine.json','7d89aff05454562b415e01c8815d00b58390169f',PRIMARYROOT+'/hdf-quarantine.json','7540fbfab3b59e2a09b0ed20d3120a9cffad91e14ebf739e630d685e6c9b3514',7292)
get('country-eligibility-correction.json','7d89aff05454562b415e01c8815d00b58390169f',PRIMARYROOT+'/country-eligibility-correction.json','e245f23ac445f9d42a36883c6ec14b71ee8118c3195f54ca1413227d0981e480',3345)
contrast=rows(get('contrast-selection.json.gz','c6da653d3fb4454a03f1b11b1b4ca76835bfeb4d',CONTRASTROOT+'/selection.json.gz','d41ae2031001ca98ae23ec500eefa4855df20fc56a953b7560e6718382a3a61a',2588))
assert[len(z1),len(z2),len(primary),len(contrast)]==[100,13,24,3]
assert{r['source_commit']for r in z1}=={'11e30204d7cbe194d8ec630bee340cdd59c8990b'}
assert{r['source_commit']for r in z2}=={'2996fa4e94fa4df4a01c8ade769d3a6c720f6b85'}
assert{r['source_commit']for r in primary}=={'efba5e37c481b3f4a6e9f4db97c52dc722c7b450'}
assert{r['source_commit']for r in contrast}=={'3380a5292d7e542ce13dcd100e2c5e4dca89bc2f'}
zeno=z1+z2;allrows=zeno+primary+contrast
assert len(allrows)==len({r['ref']for r in allrows})==140

# The actual fixed catalogue is authoritative; names/domains cannot synthesize country refs.
worlddoc=doc(get('pinned-world.json.gz','8180aa0df6e185efad120338bc53ca04bc5e492a','picons/IPTV-SK-CZ/catalog/global/search/2ae88890a953c2f68d3f20352ad56a7390645bd3ce189573dd94e50c8a65abfe.json.gz','2ae88890a953c2f68d3f20352ad56a7390645bd3ce189573dd94e50c8a65abfe',1264142))
baseline_doc=doc(get('baseline42.json',PARENT,'picons/radio-world/catalog/countries.json','8dfc9b924bc2c144997c1333840364ae12a2c7497baa2bcf02a9e9c5ef633d70',81907))
country_names={r['id']:r['name']for r in baseline_doc['countries']}
def country_eligible(r):
    station=r['station']
    return station['group']==country_names[r['country']]and any(w['reference']==r['ref']and all(w[k]==station[k]for k in('name','url','group'))for w in worlddoc)
hdf_ref='4097:0:2:8FC5:8AD9:EF:0:0:0:0'
old_byref={r['ref']:r for r in original_primary25};assert len(old_byref)==25
hdf_original=old_byref[hdf_ref];assert hdf_original['station']['group']=='HDF Radio zoznam'
assert not country_eligible(hdf_original),'Original actual HDF-only reference must fail'
fake_country=copy.deepcopy(hdf_original);fake_country['station']['group']='Austria'
assert not country_eligible(fake_country),'Blind country-group relabel must also fail'
assert{r['ref']for r in primary}==set(old_byref)-{hdf_ref}
assert all(r==old_byref[r['ref']]for r in primary),'Eligible24 must be unchanged original25 subset'
assert all(country_eligible(r)for r in allrows),'Every actual140 row must have a complete exact country catalogue match'
hdf_country_guard=dict(regressions_pass=2,actual_country_membership_pass=140,eligible_primary24_exact_original_subset=True,hdf_reference=hdf_ref,all_exact_ref_matches=[w for w in worlddoc if w['reference']==hdf_ref],all_exact_name_url_matches=[w for w in worlddoc if w['name']==hdf_original['station']['name']and w['url']==hdf_original['station']['url']])

primary_ledger_raw=get('primary-country-eligible-ledger.json','7d89aff05454562b415e01c8815d00b58390169f',PRIMARYROOT+'/visual-ledger-country-eligible.json','5906df1d413eb1c779cff7681e5ddf866cd5c604e51d7a4a2f5cd6d676f53da3',250732)
put(inbox/'primary-ledger.json.gz',packed(doc(primary_ledger_raw)))
get('contrast-ledger.json.gz','c6da653d3fb4454a03f1b11b1b4ca76835bfeb4d',CONTRASTROOT+'/visual-ledger.json.gz','1d2980c21fc84f5ea0fbb19875b8bc6ce61176c53ddadfe5faafed6b7ec8dd16',5237)
validate_selection(primary,read(inbox/'primary-ledger.json.gz'));validate_selection(contrast,read(inbox/'contrast-ledger.json.gz'))
history=['source-ledger-reviewed-20261107/visual-ledger.json.gz','visual-review-34-36/decisions.json.gz',*[f'batch-{n}-reviewed/visual-ledger.json.gz'for n in(39,40,41,42)]]
prior=[Path('picons/radio-world/staging')/p for p in history]
assert len(prior)==6 and all(p.is_file()for p in prior)
# Independent exact approvals plus existing history are mandatory before any technical exclusion.
validate_selection(primary+contrast,merge_ledgers(prior+[inbox/'primary-ledger.json.gz',inbox/'contrast-ledger.json.gz']))
qa=[]
for name,pin in [('initial34.json','d66ebcd13021dd4e24a1e2cc2d551034cb11b5d8'),('range-0000-0759-checkpoint-c619.json','7697051534d96718b3467a9ce6cbffb826b76e1c'),('range-0760-1518-checkpoint-4de3.json','4e304a72c1d954659d1baa6d532a7ed6675d28ae')]:
    qa+=doc(get('old-qa-'+name,OLD,OLDROOT+'/source-qa/'+name,pin))['entries']
assert len(qa)==len({v['row']['ref']for v in qa})==262
oldpass={v['row']['ref']for v in qa if v['decision']=='source_pass'}
oldhold=[v for v in qa if v['decision']=='hold']
assert len(oldpass)==141 and len(oldhold)==121
snapshot=doc(get('frozen-source-review-rows.json',FROZEN,OLDROOT+'/checkpoint/source-review-rows.json','d31cbd35dc4e6914330bf93751c7532a2958bc11'))
assert len(snapshot['entries'])==1519
frozen={v['row']['ref']:v for v in snapshot['entries']if v['status']=='logo-frozen'}
assert len(frozen)==sum(v['status']=='logo-frozen'for v in snapshot['entries'])==364
oldrefs={v['row']['ref']for v in qa};assert oldrefs<=frozen.keys()
for v in qa:assert v['row']['country']==frozen[v['row']['ref']]['row']['country']
newrefs=set(frozen)-oldrefs;assert len(newrefs)==102

FINAL='890c9edb644d676f5b33855268f39aefbad65be8'
final_snapshot=doc(get('final-source-review-rows.json',FINAL,OLDROOT+'/checkpoint/source-review-rows.json','f8aa4db17f98b2d4ba337cc124db28be1bca3915'))
assert len(final_snapshot['entries'])==1519
final_frozen={e['row']['ref']:e for e in final_snapshot['entries']if e['status']=='logo-frozen'}
assert len(final_frozen)==419
final_reconciled=[]
for r in zeno:
    e=final_frozen[r['ref']];old=frozen[r['ref']]
    assert e['status']=='logo-frozen'
    assert e['row']['ref']==r['ref']and e['row']['country']==r['country']
    assert all(e['row']['station'][k]==r['station'][k]==old['row']['station'][k]for k in('name','url','group'))
    assert e['source']['sha256']==old['source']['sha256']==r['provenance']['source_sha256']
    assert e['api_evidence']['sha256']==old['api_evidence']['sha256']==r['provenance']['page_sha256']
    assert all(e['api_station'][k]==old['api_station'][k]for k in('country','streamURL','streamName'))
    target=urllib.parse.urlsplit(r['station']['url']);stream=urllib.parse.urlsplit(e['api_station']['streamURL'])
    assert target.hostname==stream.hostname=='stream.zeno.fm'
    assert target.path.strip('/')==stream.path.strip('/')==e['api_station']['streamName']==e['row']['zeno_mount']
    assert e['api_station']['country']==e['row']['station']['group']==r['station']['group']
    final_reconciled.append(r['ref'])
assert len(final_reconciled)==113

index=doc(get('final-nine-votes-index.json',VOTES,ZENOROOT+'/final-nine-votes-index.json','a426c98173652bf566ca54b7e98c4a6ffe1fd83c'))
votes=[]
assert index['references']==141 and len(index['parts'])==5
for i,p in enumerate(index['parts']):
    assert p['path']==f'final-nine-votes/part-{i:03d}.json'
    part=doc(get(f'final-nine-votes-{i:03d}.json',VOTES,ZENOROOT+'/'+p['path'],p['sha256'],p['bytes']))['entries'];assert len(part)==p['entries'];votes+=part
assert len(votes)==len({v['row']['ref']for v in votes})==141
assert{v['row']['ref']for v in votes}==oldpass
assert sum(v['decision']=='approve'for v in votes)==113 and sum(v['decision']=='hold'for v in votes)==28
variants={f'{size}/{style}'for size in('50x30','220x132','400x240')for style in('transparent','white','black')}
assert all(set(v['reviewed_variants'])==variants for v in votes if v['decision']=='approve')
assert{r['ref']for r in zeno}=={v['row']['ref']for v in votes if v['decision']=='approve'}
independent={r['ref']:r for r in primary+contrast}
assert len(independent)==27 and not({v['row']['ref']for v in oldhold}&independent.keys())
excluded=newrefs&independent.keys()
for ref in excluded:assert independent[ref]['country']==frozen[ref]['row']['country']
technical=newrefs-excluded;assert len(technical)+len(excluded)==102
holds=[]
for v in oldhold:
    h=copy.deepcopy(v['row']);assert not h.get('variants')
    h.update(decision='hold',hold_kind='actual-source-visual-rejection',reason=v['reason'],source_qa_evidence=v)
    holds.append(h)
for ref in sorted(technical):
    e=frozen[ref];h=copy.deepcopy(e['row']);assert not h.get('variants')
    h.update(hold_kind='technical-unavailable-local-review',reason='Conservative technical quarantine after unavailable local review. This is not a station identity rejection; no visual approval or PNG fingerprint is inferred.',snapshot_evidence=dict(commit=FROZEN,path=OLDROOT+'/checkpoint/source-review-rows.json',git_blob='d31cbd35dc4e6914330bf93751c7532a2958bc11',source_sha256=e['source']['sha256'],api_sha256=e['api_evidence']['sha256']))
    holds.append(h)
assert len(holds)==121+len(technical) and not any(h.get('variants')for h in holds)
ledger=dict(schema=3,entries=votes,source_holds=holds,contingency=dict(actual_missing31_decisions_not_reconstructed=True,known_actual_source_holds=121,conservative_new_pool=102,technical_excluded_only_independently_approved_refs=sorted(excluded),technical_quarantined=len(technical),not_identity_rejections=True))
put(inbox/'zeno-selection.json.gz',packed(dict(entries=zeno)));put(inbox/'zeno-ledger.json.gz',packed(ledger))
validate_selection(zeno,ledger)
baseline=get('baseline42.json',PARENT,'picons/radio-world/catalog/countries.json','8dfc9b924bc2c144997c1333840364ae12a2c7497baa2bcf02a9e9c5ef633d70',81907)
prep_path=Path('picons/radio-world/preparation/batch-43/prepare43.py')
put(prep_path,get('prepare43.py',PREP,str(prep_path),'84d08be1309b1ffa34797b8e2e29af1d48bdbf9e226d112048f897dda06d5ff6',9124))
args=[sys.executable,str(prep_path),'--parent',PARENT,'--baseline',str(inbox/'baseline42.json'),'--history-root','picons/radio-world/staging','--config-template','picons/radio-world/staging/batch-42-reviewed/configuration.json','--stage',str(stage),'--expected-total','140']
for name,count in [('zeno',113),('primary',24),('contrast',3)]:
    args+=['--source',str(inbox/(name+'-selection.json.gz'))+':'+str(inbox/(name+'-ledger.json.gz')),'--expected-source-count',str(count)]

# Supersede only the exact earlier141 prepared metadata; preserve its immutable Git history.
previous141={"bootstrap-proof.json":"6782f939ecef75a7c6a2f6eae9621e53e63d0200","configuration.json":"aeaf6806ff6877a8f4574c4931134e76cca42d45","preparation-proof.json":"889c9a74e7534d06011ce84b52fca65494943357","selection.json.gz":"49ad67c518dcb4afc0e444d5865931d5bcd5e189","visual-ledger.json.gz":"8028649e8ae2b0996dcdfd375ae6cb351061459d"}
cfgpath=stage/'configuration.json'
if cfgpath.exists()and json.loads(cfgpath.read_bytes())['references']==141:
    assert all((stage/name).is_file()and blob((stage/name).read_bytes())==expected for name,expected in previous141.items()),'Earlier141 preparation changed unexpectedly'
    for name in previous141:(stage/name).unlink()

subprocess.run(args,check=True)
proof=dict(schema=1,status='prepared-from-immutable-GitHub-exports-not-country-built',resources=resources,old_source_qa=262,actual_source_holds=121,actual_nine_variant_votes=141,actual_approved_zeno=113,new_source_snapshot=364,technical_pool=102,technical_excluded_independent=sorted(excluded),technical_quarantined=len(technical),references=140,png_instances=1260,expected_coverage=3010,source_country_regressions_pass=2,country_membership_references_pass=140,hdf_country_guard=hdf_country_guard,final_source_reconciliation=dict(commit=FINAL,approved_reconciled=113,final_source_frozen=419,new55_not_activated=True),previous141_metadata_transition=previous141,missing31_actual_reasons_not_invented=True,selection_sha256=sha((stage/'selection.json.gz').read_bytes()),ledger_sha256=sha((stage/'visual-ledger.json.gz').read_bytes()))
put(stage/'bootstrap-proof.json',(json.dumps(proof,indent=2)+'\n').encode())
print(json.dumps(proof,indent=2))
