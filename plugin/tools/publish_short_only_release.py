#!/usr/bin/env python3
"""Publish one tested short-only PiconHub IPK and preserve source-data trees."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.parse import quote

ROOT=Path.cwd()
spec=importlib.util.spec_from_file_location('short_only_publisher',ROOT/'plugin/tools/publish_plugin_release.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)

def main():
    approval=json.loads((ROOT/'plugin/update/short-only-approval.json').read_text())
    assert os.environ['GITHUB_REPOSITORY']==p.REPO
    assert os.environ['GITHUB_REF']=='refs/heads/release/piconhub-short-only-0.1.33'
    revision=approval.get('package_source_revision',os.environ['GITHUB_SHA']);client=p.GitHub(os.environ['GITHUB_TOKEN'])
    version='0.1.33';path=ROOT/'plugin/build'/('enigma2-plugin-extensions-piconhub_'+version+'_all.ipk')
    document=p.manifest(path,version,(ROOT/'plugin/update/RELEASE-NOTES.md').read_text());item=document['release']
    assert len(list(path.parent.glob('*.ipk')))==1
    assert item['sha256']==approval['expected_package_sha256'],'Build must exactly match the delivered IPK'
    def head(branch):return client.request('GET','/git/ref/heads/'+quote(branch,safe=''))['object']['sha']
    def inspect(sha):
        commit=client.request('GET','/git/commits/'+sha)
        listing=client.request('GET','/git/trees/'+commit['tree']['sha']+'?recursive=1');assert not listing.get('truncated')
        return commit['tree']['sha'],{x['path']:x for x in listing['tree']}
    states={}
    for branch,expected in approval['targets'].items():
        assert head(branch)==expected,'Source advanced: '+branch
        tree,files=inspect(expected)
        for name,digest in approval['original_files'].items():assert files.get(name,{}).get('sha')==digest,(branch,name)
        states[branch]={'head':expected,'tree':tree,'files':files}
    release=client.request('GET','/releases/tags/v'+version,allow_missing=True)
    if release is None:
        release=client.request('POST','/releases',{'tag_name':'v'+version,'target_commitish':revision,'name':'PiconHub '+version,'body':item['notes'],'draft':True,'prerelease':False,'make_latest':'false'})
    assert release['target_commitish']==revision
    assets={x['name']:x for x in release.get('assets',[])}
    assert set(assets).issubset({path.name,path.name+'.sha256'})
    for name,raw in [(path.name,path.read_bytes()),(path.name+'.sha256',(item['sha256']+'  '+path.name+'\n').encode())]:
        asset=assets.get(name)
        if asset is None:
            assert release['draft']
            asset=client.request('POST','/releases/'+str(release['id'])+'/assets?name='+quote(name),binary=raw)
        assert asset['size']==len(raw) and asset['digest']=='sha256:'+hashlib.sha256(raw).hexdigest()
    if release['draft']:client.request('PATCH','/releases/'+str(release['id']),{'draft':False,'prerelease':False,'make_latest':'true'})
    raw=client.public_package(item['url'],item['bytes'])
    assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
    report={'status':'PRODUCTION_VERIFIED','version':version,'release':item,'source_commit':revision,'workflow_run':int(os.environ['GITHUB_RUN_ID']),'short_only':True,'long_transition_created':False,'previous_0_1_32_requires_one_manual_install':True,'settings_and_picons_preserved':True,'physical_receiver_tested':False,'trezor_accessed':False}
    record=json.loads((ROOT/'plugin/production.json').read_text());record.update(approved_on='2026-10-30',approval=approval['authorization'],source_commit=revision)
    record['release']=dict(item,release_url='https://github.com/'+p.REPO+'/releases/tag/v'+version)
    record['validation']={'automated_tests':198,'ci':'passed','workflow_run':int(os.environ['GITHUB_RUN_ID']),'public_ipk_verified':True,'public_update_feed_verified':True,'receiver_tested':False,'limits':'One manual install is required from 0.1.32 because its updater validates the former filename. No long bridge is created, per owner instruction.'}
    record['short_only']=True;record['manual_install_from_0_1_32']=True
    changes={name:(ROOT/name).read_bytes() for name in approval['original_files']}
    changes.update({'plugin/update/stable.json':(json.dumps(document,ensure_ascii=False,indent=2)+'\n').encode(),'plugin/production.json':(json.dumps(record,ensure_ascii=False,indent=2)+'\n').encode(),'reports/piconhub-short-only-0.1.33.json':(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode()})
    entries=[]
    for name,data in changes.items():
        assert name in approval['original_files'] or name in ('plugin/update/stable.json','plugin/production.json','reports/piconhub-short-only-0.1.33.json')
        blob=client.request('POST','/git/blobs',{'encoding':'base64','content':base64.b64encode(data).decode()})
        assert blob['sha']==hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        entries.append({'path':name,'mode':next(iter(states.values()))['files'].get(name,{}).get('mode','100644'),'type':'blob','sha':blob['sha']})
    for branch,state in states.items():
        assert head(branch)==state['head']
        tree=client.request('POST','/git/trees',{'base_tree':state['tree'],'tree':entries})
        made=client.request('POST','/git/commits',{'parents':[state['head']],'tree':tree['sha'],'message':'Release PiconHub 0.1.33 with short filenames only; one manual upgrade from 0.1.32 [skip ci]'})
        assert head(branch)==state['head']
        client.request('PATCH','/git/refs/heads/'+quote(branch,safe=''),{'sha':made['sha'],'force':False})
        unused,now=inspect(made['sha'])
        for name in ('picons','plugin/artwork'):
            if name in state['files']:assert now[name]['sha']==state['files'][name]['sha']
        print('VERIFIED branch',branch,made['sha'],flush=True)
    # Remove obsolete long native files only after the new short release is live.
    previous=client.request('GET','/releases/tags/v0.1.32')
    old_long='enigma2-plugin-extensions-piconhub-warder-evolution_0.1.32_all.ipk'
    old_short='enigma2-plugin-extensions-piconhub_0.1.32_all.ipk'
    assets={x['name']:x for x in previous['assets']};assert assets[old_short]['digest']=='sha256:28b9e238d5689ddf21a0dfaba075cae89440545093750624ae3628766828dde7'
    for name in (old_long,old_long+'.sha256'):
        if name in assets:
            subprocess.run(['gh','api','--method','DELETE','repos/'+p.REPO+'/releases/assets/'+str(assets[name]['id'])],check=True,capture_output=True)
    obsolete=client.request('GET','/releases/tags/v0.1.30',allow_missing=True)
    if obsolete:subprocess.run(['gh','api','--method','DELETE','repos/'+p.REPO+'/releases/'+str(obsolete['id'])],check=True,capture_output=True)
    for branch in states:
        feed=client.request('GET','/contents/plugin/update/stable.json?ref='+quote(branch,safe=''))
        assert json.loads(base64.b64decode(feed['content']))==document
    assert hashlib.sha256(client.public_package(item['url'],item['bytes'])).hexdigest()==item['sha256']
    final=client.request('GET','/releases/tags/v'+version)
    assert {x['name'] for x in final['assets']}=={path.name,path.name+'.sha256'}
    (ROOT/'reports').mkdir(exist_ok=True);(ROOT/'reports/piconhub-short-only-0.1.33.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PRODUCTION_VERIFIED',json.dumps(item),flush=True)

if __name__=='__main__':main()
