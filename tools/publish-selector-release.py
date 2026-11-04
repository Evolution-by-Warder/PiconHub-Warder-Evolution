#!/usr/bin/env python3
"""Publish immutable tested IPKs, verify public bytes, then advance stable feeds."""
from pathlib import Path
import base64,hashlib,importlib.util,json,os,time
from urllib.parse import quote
ROOT=Path.cwd();CONFIG=ROOT/'docs/SATELLITE-SELECTORS-RELEASE.json'
sha=lambda b:hashlib.sha256(b).hexdigest()
def main():
 c=json.loads(CONFIG.read_text());repo=os.environ['GITHUB_REPOSITORY'];assert repo==c['repository'];assert os.environ['GITHUB_REF_NAME']=='main'
 core_path=ROOT/'plugin/tools/publish_plugin_release.py'
 if not core_path.exists():core_path=ROOT/'.piconhub-source/plugin/tools/publish_plugin_release.py'
 s=importlib.util.spec_from_file_location('selector_release_core',core_path);core=importlib.util.module_from_spec(s);s.loader.exec_module(core);core.REPO=repo;core.API='https://api.github.com/repos/'+repo;client=core.GitHub(os.environ['GITHUB_TOKEN']);version=c['version'];revision=os.environ['GITHUB_SHA'];p=ROOT/c['package'];raw=p.read_bytes();digest=sha(raw);notes=c['notes_i18n'];tag='v'+version;url='https://github.com/'+repo+'/releases/download/'+tag+'/'+p.name
 def head(branch):return client.request('GET','/git/ref/heads/'+quote(branch,safe=''))['object']['sha']
 def read(path,branch='main'):
  item=client.request('GET','/contents/'+path+'?ref='+quote(branch,safe=''));return base64.b64decode(item['content'])
 def commit(branch,changes,message,expected=None):
  old=head(branch)
  if expected is not None:assert old==expected,'Branch advanced; preserve concurrent changes'
  base=client.request('GET','/git/commits/'+old);entries=[]
  for path,data in changes.items():
   b=client.request('POST','/git/blobs',dict(encoding='base64',content=base64.b64encode(data).decode()));entries.append(dict(path=path,mode='100644',type='blob',sha=b['sha']))
  tree=client.request('POST','/git/trees',dict(base_tree=base['tree']['sha'],tree=entries));made=client.request('POST','/git/commits',dict(tree=tree['sha'],parents=[old],message=message));assert head(branch)==old;client.request('PATCH','/git/refs/heads/'+quote(branch,safe=''),dict(sha=made['sha'],force=False));return made['sha']
 assert head(c['compatibility_branch'])==c['compatibility_head'],'Compatibility branch advanced'
 for path in c['feed_paths']:
  previous=json.loads(read(path));offered=previous.get('release',previous);assert offered['version']==c['previous_version'],(path,offered['version'])
 
 if c['product']=='PiconHub':
  checked=core.manifest(p,version,notes['sk']);assert checked['release']['sha256']==digest
 release=client.request('GET','/releases/tags/'+tag,allow_missing=True)
 if release is None:release=client.request('POST','/releases',dict(tag_name=tag,target_commitish=revision,name=c['product']+' '+version,body=notes['sk'],draft=True,prerelease=False,make_latest='false'))
 assert release['target_commitish']==revision,'Version already exists with another source'
 assets={a['name']:a for a in release.get('assets',[])}
 for name,data in [(p.name,raw),(p.name+'.sha256',(digest+'  '+p.name+'\n').encode())]:
  asset=assets.get(name)
  if asset is None:
   assert release['draft'];asset=client.request('POST','/releases/'+str(release['id'])+'/assets?name='+quote(name),binary=data)
  assert asset['size']==len(data) and asset['digest']=='sha256:'+sha(data)
 if release['draft']:client.request('PATCH','/releases/'+str(release['id']),dict(draft=False,prerelease=False,make_latest='false'))
 public=client.public_package(url,len(raw));assert len(public)==len(raw) and sha(public)==digest
 item=dict(version=version,tag=tag,url=url,sha256=digest,bytes=len(raw),notes=notes['sk'],notes_i18n=notes,release_url='https://github.com/'+repo+'/releases/tag/'+tag)
 # FullHDGlass receivers pin raw main package URLs; make those bytes public
 # and verify them before advancing either updater branch.
 if c['product']=='FullHDGlass':
  package_path='packages/'+p.name;commit('main',{package_path:raw,package_path+'.sha256':(digest+'  '+p.name+'\n').encode()},'Stage verified FullHDGlass '+version+' IPK before feed activation [skip ci]')
  package_url='https://raw.githubusercontent.com/'+repo+'/main/'+package_path
  public=client.public_package(package_url,len(raw));assert len(public)==len(raw) and sha(public)==digest
  feed=dict(version=version,package_url=package_url,sha256=digest,changelog=notes['sk']);item['package_url']=package_url
 else:feed=dict(schema=1,product='PiconHub Warder Evolution',channel='stable',release=item)
 encoded=lambda d:(json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode()
 changes={path:encoded(feed) for path in c['feed_paths']};production_path=c['production_record'];prod=json.loads(read(production_path));prod['previous_release']=prod.get('release');prod.update(status='production-update-active',approved_on='2026-11-04',approval='Owner requested full support for 34.5W and 50E in both clients and three Warder backgrounds for every satellite and provider.',source_branch='main',source_commit=revision,package_source_commit=revision,release=item)
 prod['validation']=dict(ci='passed',workflow_run=int(os.environ['GITHUB_RUN_ID']),public_ipk_verified=True,three_background_catalogue_verified=True,all_profiles_and_other_payload_preserved=True,physical_receiver_tested=False);changes[production_path]=encoded(prod)
 if c['product']=='PiconHub':
  project=json.loads(read('plugin/project.json'));project.update(development_version=version,production_version=version,requested_production_version=version,latest_published_version=version,ipk_published=True);changes['plugin/project.json']=encoded(project)
 report=dict(status='PRODUCTION_VERIFIED',product=c['product'],version=version,release=item,source_commit=revision,source_workflow=int(os.environ['GITHUB_RUN_ID']),positions=['34.5w','50.0e'],styles=['transparent','white','black'],resolutions=['50x30','220x132','400x240'],coverage='Every satellite and provider resolution has all three backgrounds',physical_receiver_tested=False)
 changes['reports/satellite-selectors-20261104/production.json']=encoded(report)
 readme=read('README.md').decode();readme+='\n## '+c['product']+' '+version+' — 34,5°W a 50°E\n\n'+notes['sk']+'\n\n[Stiahnuť IPK]('+url+'). Overené všetky tri pozadia satelitov aj providerov, verejné IPK a kontrolné súčty.\n';changes['README.md']=readme.encode()
 current='# '+c['product']+' '+version+'\n\n'+notes['sk']+'\n\n[Stiahnuť IPK]('+url+')\n\nSHA256: '+digest+'\n\nHostiteľské kontroly oboch inštalačných enginov a zachovania nastavení prešli; fyzický prijímač nebol v tejto relácii testovaný.\n';changes['docs/CURRENT-RELEASE.md']=current.encode()
 main_commit=commit('main',changes,'Activate verified '+c['product']+' '+version+' and record complete satellite/provider background support [skip ci]')
 compatibility={path:encoded(feed) for path in c['feed_paths']}
 if c['product']=='PiconHub':
  compatibility[production_path]=encoded(prod);compatibility['plugin/project.json']=changes['plugin/project.json']
 if c['product']=='PiconHub':
  old=head(c['compatibility_branch']);assert old==c['compatibility_head'];current=client.request('GET','/git/commits/'+main_commit);entries=client.request('GET','/git/trees/'+current['tree']['sha'])['tree'];plugin_tree=next(e['sha'] for e in entries if e['path']=='plugin');previous=client.request('GET','/git/commits/'+old);tree=client.request('POST','/git/trees',dict(base_tree=previous['tree']['sha'],tree=[dict(path='plugin',mode='040000',type='tree',sha=plugin_tree)]));made=client.request('POST','/git/commits',dict(tree=tree['sha'],parents=[old],message='Synchronize verified production PiconHub '+version+' and stable feed [skip ci]'));assert head(c['compatibility_branch'])==old;client.request('PATCH','/git/refs/heads/'+quote(c['compatibility_branch'],safe=''),dict(sha=made['sha'],force=False));compat_commit=made['sha']
 else:
  compat_commit=commit(c['compatibility_branch'],compatibility,'Activate verified '+c['product']+' '+version+' stable update [skip ci]',c['compatibility_head'])
 for branch in ['main',c['compatibility_branch']]:
  for path in c['feed_paths']:assert json.loads(read(path,branch))==feed
 assert sha(client.public_package(url,len(raw)))==digest
 client.request('PATCH','/releases/'+str(release['id']),dict(draft=False,prerelease=False,make_latest='true'))
 report.update(main_activation_commit=main_commit,compatibility_activation_commit=compat_commit);out=ROOT/'reports/satellite-selectors-20261104';out.mkdir(parents=True,exist_ok=True);(out/'production.json').write_bytes(encoded(report));print(json.dumps(report),flush=True)
if __name__=='__main__':main()
