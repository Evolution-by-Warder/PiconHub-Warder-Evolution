import urllib.parse
"""Copy immutable approved candidate artwork; never render or infer logo identity."""
import json,gzip,copy,hashlib,subprocess,sys,io
from pathlib import Path
from zipfile import ZipFile
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
S=Path('picons/radio-world/staging');stage=S/'batch-73-reviewed';prev=S/'batch-72-reviewed'
sys.path.insert(0,'picons/radio-world/tools')
from visual_gate import read,merge_ledgers,validate_selection,identity_blocks
from saved_artwork_import import get
sha=lambda b:hashlib.sha256(b).hexdigest()
def write(p,x):
 b=(json.dumps(x,indent=2,ensure_ascii=False)+'\n').encode();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(gzip.compress(b,mtime=0)if p.suffix=='.gz'else b)
desc=read(stage/'source-inputs/recovery-spec.json');cfg=read(prev/'configuration.json');raw=(prev/'countries.proposed.json').read_bytes();assert sha(raw)==desc['baseline_sha256']
world=json.loads(gzip.decompress(get(cfg['world'])));current=json.loads(gzip.decompress(get(desc['current'])));audit=json.loads(gzip.decompress(get(desc['audit'])))['checks']

# Resolve immutable catalogue records by reference/hash only in memory. Never persist URL query values.
def original(st):
 matches=[x for x in world if x['reference']==st['reference'] and x['group']==st['group']]
 assert len(matches)==1
 item=matches[0]
 pair,side=next((p,k)for p in desc['pairs'] for k in ('new','old') if p[k]['reference']==st['reference'] and p[k]['group']==st['group'])
 assert hashlib.sha256(item['url'].encode()).hexdigest()==pair['catalog_url_sha256'][side]
 assert {**item,'url':item['url'].split('?')[0]}==st
 assert set(urllib.parse.parse_qs(urllib.parse.urlsplit(item['url']).query,keep_blank_values=True))<=set(pair['allowed_query_names'])
 return item
def observation(st):
 original(st);result=dict(desc['live_observations'][st['reference']]);result['url']=st['url']
 if 'final_url'in result:result['final_url']=result['final_url'].split('?')[0]
 return result

countries={c['name']:c['id']for c in json.loads(raw)['countries']};production=json.loads(get(desc['production_index']));prod={c['id']:c for c in production['countries']}
paths=[S/'source-ledger-reviewed-20261107/visual-ledger.json.gz',S/'visual-review-34-36/decisions.json.gz']+[S/f'batch-{n}-reviewed/visual-ledger.json.gz'for n in range(39,73)]
ledger=merge_ledgers(paths);known={(e['row']['country'],e['row']['ref'])for e in ledger['entries']};blocks=identity_blocks(ledger);rejected={(e['row']['country'],e['row']['ref'])for e in ledger['entries']if e['decision']=='hold'}
manifests={c:json.loads(get(prod[c]['release']))for c in sorted({countries[p['new']['group']]for p in desc['pairs']})}
rows=[];facts=[];tasks=[]
for pair in desc['pairs']:
 st=pair['new'];old=pair['old'];code=countries[st['group']];assert original(st) in world and original(old) in world and original(st) in current
 assert (code,st['reference'])not in known and (code,st['reference'])not in blocks and st['reference']not in cfg['held_references']
 assert (code,old['reference'])not in blocks|rejected and old['reference']not in cfg['held_references']
 r=dict(index=730000+len(rows),country=code,ref=st['reference'],station={k:st[k]for k in ['name','url','group']},asset_root=str(stage),variants={},provenance=dict(alias_of_approved_ref=old['reference'],alias_of_approved_country=code,approval_authority='Existing approved candidate artwork through72, including protected production; exact reuse authorized by owner',production_index=desc['production_index'],production_release=prod[code]['release'],identity_basis=pair['identity_basis'],catalog_url_sha256=pair['catalog_url_sha256']))
 f=dict(station=st,approved_station=old,production_release=prod[code]['release'],identity_basis=pair['identity_basis'],new_audit={k:observation(st).get(k)for k in ['url','checked_at','http_status','content_type','icy_name','sample_bytes','sample_sha256','status']},approved_audit={k:observation(old).get(k)for k in ['url','checked_at','http_status','content_type','icy_name','sample_bytes','sample_sha256','status']})
 for size,styles in manifests[code]['packages'].items():
  for style,pkg in styles.items():
   name=old['reference'].replace(':','_')+'.png';assert name in pkg['files'];tasks.append((len(rows),size,style,pkg,name))
 rows.append(r);facts.append(f)
assert len(rows)==3 and len(tasks)==27
# Fetch each source archive once; extract only the selected immutable PNGs.
groups={}
for task in tasks:groups.setdefault(task[3]['url'],[]).append(task)
def extract(group):
 package=group[0][3];data=get(package);out=[]
 with ZipFile(io.BytesIO(data))as z:
  for idx,size,style,pkg,name in group:
   b=z.read(name);assert sha(b)==pkg['files'][name]
   with Image.open(io.BytesIO(b))as im:assert im.mode=='RGBA'and im.size==tuple(map(int,size.split('x')));im.verify()
   out.append((idx,size+'/'+style,b))
 return out
(stage/'verified-assets').mkdir(exist_ok=True)
with ThreadPoolExecutor(max_workers=6)as pool:
 for results in pool.map(extract,groups.values()):
  for idx,variant,b in results:
   digest=sha(b);(stage/'verified-assets'/f'{digest}.png').write_bytes(b);rows[idx]['variants'][variant]=[digest,len(b),hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()]
write(stage/'source-inputs/production-authority-proof.json',dict(status='pass',production_index=desc['production_index'],entries=facts,PNG_instances=27,new_renders=0))
subprocess.run(['git','config','user.name','github-actions[bot]'],check=True);subprocess.run(['git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com'],check=True)
subprocess.run(['git','add',str(stage/'verified-assets'),str(stage/'source-inputs/production-authority-proof.json')],check=True)
subprocess.run(['git','commit','-m','Save 27 byte-identical approved candidate source PNGs for batch73 [skip ci]'],check=True)
subprocess.run(['git','push','origin','HEAD:refs/heads/work/radio-world-batch38-contrast-pass1-history-20261107'],check=True)
commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
for r in rows:
 r['source_commit']=commit;r['final_visual_approval']=dict(decision='approve',reason='Byte-identical reuse of nine owner-approved candidate variants; no new graphic',reviewed_variants=r['variants'])
write(stage/'selection.json.gz',dict(entries=rows));write(stage/'visual-ledger.json.gz',dict(entries=[dict(row=r,decision='approve',reason=r['final_visual_approval']['reason'],reviewed_variants=r['variants'])for r in rows],source_holds=[],pending_sources=[]))
write(stage/'source-inputs/public-observations.json',dict(schema=1,stream_audit=desc['audit'],current_world=desc['current'],entries=facts,no_new_endpoint_requests=False,no_new_artwork=True))
(stage/'baseline.previous.json').write_bytes(raw);cfg.update(batch='73-reviewed',references=3,parent_candidate=desc['parent'],expected_coverage=3421,selection_sha256=sha((stage/'selection.json.gz').read_bytes()),baseline_index=dict(url='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'+desc['parent']+'/picons/radio-world/staging/batch-72-reviewed/countries.proposed.json',bytes=len(raw),sha256=sha(raw)))
write(stage/'configuration.json',cfg)
write(stage/'results/next-source-observations.json.gz',dict(schema=1,next_batch=74,previous_frontier='../batch-72-reviewed/results/next-source-observations.json.gz',configuration_holds_unchanged=923,completed_selection_refs=[r['ref']for r in rows],production_comparisons=desc['frontier'],next='Seek publisher mapping for remaining production comparisons; conflicts and generic ICY remain blocked.'))
print('Prepared9 references /27 byte-identical approved production PNG variants')
