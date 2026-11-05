#!/usr/bin/env python3
"""Controlled PiconHub integration of verified source and canonical reuse."""
from pathlib import Path
from collections import defaultdict,Counter
import argparse,subprocess,json,hashlib,tempfile,os,importlib.util
from vhannibal_final_assets import produce
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*args,input=None,env=None):return subprocess.check_output(['git',*args],input=input,env=env).decode().strip()
def ref(path):return Path(path).stem
def identity(r):return tuple(r.split('_')[3:7])
def write_commit(branch,base,updates,message):
 current=git('ls-remote','origin','refs/heads/'+branch).split()[0];assert current==base,('Concurrent branch update',branch,current,base)
 with tempfile.TemporaryDirectory() as t:
  env=os.environ.copy();env['GIT_INDEX_FILE']=str(Path(t)/'index');git('read-tree',base,env=env)
  lines=''.join('100644 '+h+'\t'+p+'\n' for p,h in sorted(updates.items()));git('update-index','--index-info',input=lines.encode(),env=env);tree=git('write-tree',env=env);commit=git('commit-tree',tree,'-p',base,input=(message+'\n').encode());stage='factory/vhannibal-final-'+('master-stage' if branch=='warder-master-production' else 'source-stage');oldstage=git('ls-remote','origin','refs/heads/'+stage).split();oldstage=oldstage[0] if oldstage else '';subprocess.run(['git','push','--force-with-lease=refs/heads/'+stage+':'+oldstage,'origin',commit+':refs/heads/'+stage],check=True);return commit

def run(data):
 config=json.load(open(data/'config.json'));plans=json.load(open(data/'plans.json'));assets=json.load(open(data/'asset-index.json'));indexed={a['asset_id']:a for a in assets};mastertree=json.load(open(data/'master-tree.json'));paths={x['path']:x['sha'] for x in mastertree};byid=defaultdict(list)
 for x in mastertree:byid[identity(ref(x['path']))].append(x)
 output=data/'assets';output.mkdir(exist_ok=True)
 from concurrent.futures import ThreadPoolExecutor
 import urllib.request
 pending={(a.get('source_ref',config['master_base']),v['sha']):v for a in assets if a['kind']!='SOURCE_GRAPHIC' for v in a['master_sources'].values()}
 def fetch_existing(item):
  (commit,h),v=item;p=output/(h+'.png')
  if not p.exists():p.write_bytes(urllib.request.urlopen('https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'+commit+'/'+v['path'],timeout=90).read())
  raw=p.read_bytes();assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==h
 with ThreadPoolExecutor(max_workers=12) as pool:list(pool.map(fetch_existing,pending.items()))
 produce(output,data/'asset-index.json',data/'source-subset.zip',data/'templates',config['master_base'])
 written={};before={};preflight=[];assetpaths={};rows_byref={r['reference']:r for r in plans};blobdata={}
 for a in assets:
  for style,o in a['outputs'].items():
   raw=(output/o['file']).read_bytes();assert sha(raw)==o['sha256'];h=git('hash-object','-w','--stdin',input=raw);blobdata[(a['asset_id'],style)]=h
 for r in plans:
  if r['choice'] not in ('SOURCE_GRAPHIC_PROCESS','EXISTING_MASTER_REUSE','EXISTING_SOURCE_BANK_REUSE') and not r.get('canonical_extension_verified'):continue
  a=indexed[r['asset_id']];existing=byid.get(identity(r['reference']),[]);folders={str(Path(x['path']).parent.parent) for x in existing}
  if r['choice']=='EXISTING_MASTER_REUSE':folders={str(Path(r['master']['transparent']['path']).parent.parent)}
  if not folders:folders={'picons/'+r['position']+'/'+r['provider_slug']}
  for folder in folders:
   for style in ('transparent','white','black'):
    h=blobdata[(a['asset_id'],style)];target=folder+'/'+style+'/'+r['reference']+'.png';targets={target}
    if r.get('canonical_extension_verified'):targets.update(x['path'] for x in existing if Path(x['path']).parent.name==style)
    for target in targets:
     if '/canal-plus-sk/' in target or '/canal-plus-cz/' in target:continue
     if target in paths and paths[target]==h:continue
     # Existing masters are replaced only by a separately verified CANAL alias.
     assert target not in paths or r.get('canonical_extension_verified'),('Unexpected existing master replacement',target)
     if target in written:assert written[target]==h
     written[target]=h;before[target]=paths.get(target);check={'path':target,'reference':ref(target),'position':r['position'],'station_names':[r['name']],'content_sha256':a['outputs'][style]['sha256'],'resolution':'220x132','family':'channel-'+style}
     if r.get('canonical_extension_verified'):check.update(operation='CANAL_CANONICAL_REUSE',source_reference=r['canal_source_reference'])
     preflight.append(check)
  for style,o in a['outputs'].items():assetpaths['factory/temp/vhannibal-final-20261105/assets/'+o['file']]=blobdata[(a['asset_id'],style)]
 guarddir=data/'guard';spec=importlib.util.spec_from_file_location('guard',guarddir/'guard.py');guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard);decisions=guard.validate_plan(preflight);assert all(x['allowed'] for x in decisions),[x for x in decisions if not x['allowed']][:3]
 # Fetch both immutable bases without checking out their picon trees.
 for base in (config['factory_base'],config['master_base']):subprocess.run(['git','fetch','--no-tags','--filter=blob:none','--depth=1','origin',base],check=True)
 summary=json.load(open(data/'summary.json'));report={'status':'MASTER_AND_FACTORY_INTEGRATED_LIVE_PUBLICATION_NEXT','master_paths_changed':len(written),'master_paths_added':sum(v is None for v in before.values()),'master_paths_replaced_by_verified_canal':sum(v is not None for v in before.values()),'source_input_summary':summary,'input_code_commit':git('rev-parse','HEAD'),'pending_action':'Publish missing live references/sizes from the complete verified plan; do not re-render these assets.','changed_paths':[{'path':p,'before_git_sha':before[p],'git_sha':h} for p,h in sorted(written.items())]}
 reportbytes=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode();reportsha=git('hash-object','-w','--stdin',input=reportbytes);guardsha=git('hash-object','-w','--stdin',input=(guarddir/'reuse-evidence.json').read_bytes());master_updates={**written,'reports/warder-master-production/vhannibal-final-20261105.json':reportsha,'reports/warder-master-production/canal235-protection/reuse-evidence.json':guardsha};factory_updates={**written,**assetpaths,'factory/temp/vhannibal-final-20261105/source-integration.json':reportsha,'factory/temp/vhannibal-review-20261105/canal235-protection/reuse-evidence.json':guardsha}
 for name in ('config.json','plans.json','asset-index.json','summary.json','exceptions.json','source-dispositions.json'):
  raw=(data/name).read_bytes();h=git('hash-object','-w','--stdin',input=raw);factory_updates['factory/temp/vhannibal-final-20261105/'+name]=h
 master=write_commit('warder-master-production',config['master_base'],master_updates,'Complete verified Vhannibal master coverage with canonical artwork reuse');factory=write_commit('factory-warder-development',config['factory_base'],factory_updates,'Integrate complete Vhannibal source plan and preserve canonical graphics');report.update(master_commit=master,factory_commit=factory);(data/'source-result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print('SOURCE_COMPLETE',json.dumps({'master_commit':master,'factory_commit':factory,'paths':len(written)}),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('data',type=Path);a=p.parse_args();run(a.data)
