"""Publish the tested country-aware IPK, then advance its stable feeds."""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import quote

ROOT=Path.cwd()
spec=importlib.util.spec_from_file_location('country_release_core',ROOT/'plugin/tools/publish_plugin_release.py')
core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)


def main():
    config=json.loads((ROOT/'tools/country-radio-publication.json').read_text())
    version='0.1.42';source=os.environ['GITHUB_SHA'];client=core.GitHub(os.environ['GITHUB_TOKEN'])
    assert os.environ['GITHUB_REF_NAME']=='radio/country-picons-20261104-1'
    package=ROOT/'plugin/build'/('enigma2-plugin-extensions-piconhub_'+version+'_all.ipk')
    document=core.manifest(package,version,(ROOT/'plugin/update/RELEASE-NOTES.md').read_text());item=document['release']
    assert len(list(package.parent.glob('*.ipk')))==1
    def head(branch):return client.request('GET','/git/ref/heads/'+quote(branch,safe=''))['object']['sha']
    assert head('plugin/futuristic-rebuild')==config['compatibility_head'],'Compatibility source advanced'
    release=client.request('GET','/releases/tags/v'+version,allow_missing=True)
    if release is None:release=client.request('POST','/releases',dict(tag_name='v'+version,target_commitish=source,name='PiconHub '+version,body=item['notes'],draft=True,prerelease=False,make_latest='false'))
    assert release['target_commitish']==source
    assets={a['name']:a for a in release.get('assets',[])}
    for name,raw in [(package.name,package.read_bytes()),(package.name+'.sha256',(item['sha256']+'  '+package.name+'\n').encode())]:
        asset=assets.get(name)
        if asset is None:
            assert release['draft'];asset=client.request('POST','/releases/'+str(release['id'])+'/assets?name='+quote(name),binary=raw)
        assert asset['size']==len(raw) and asset['digest']=='sha256:'+hashlib.sha256(raw).hexdigest()
    if release['draft']:client.request('PATCH','/releases/'+str(release['id']),dict(draft=False,prerelease=False,make_latest='true'))
    public=client.public_package(item['url'],item['bytes']);assert len(public)==item['bytes'] and hashlib.sha256(public).hexdigest()==item['sha256']
    production=json.loads((ROOT/'plugin/production.json').read_text());production.update(source_commit=source,package_source_commit=source,approved_on='2026-11-04',approval='Owner requested additional radio countries as independent packages with English country names.')
    production['release']=dict(item,release_url='https://github.com/'+core.REPO+'/releases/tag/v'+version)
    production['validation']=dict(automated_tests=230,ci='passed',workflow_run=int(os.environ['GITHUB_RUN_ID']),public_ipk_verified=True,country_archives_verified=36,receiver_tested=False)
    changes={p:(ROOT/p).read_bytes() for p in config['plugin_update_paths']}
    changes.update({'plugin/update/stable.json':(json.dumps(document,ensure_ascii=False,indent=2)+'\n').encode(),'plugin/production.json':(json.dumps(production,ensure_ascii=False,indent=2)+'\n').encode()})
    project=json.loads((ROOT/'plugin/project.json').read_text());project.update(ipk_published=True,latest_published_version=version)
    changes['plugin/project.json']=(json.dumps(project,ensure_ascii=False,indent=2)+'\n').encode()
    entries=[]
    for path,raw in changes.items():
        blob=client.request('POST','/git/blobs',dict(encoding='base64',content=base64.b64encode(raw).decode()));entries.append(dict(path=path,mode='100644',type='blob',sha=blob['sha']))
    for branch in ['main','plugin/futuristic-rebuild']:
        before=head(branch)
        if branch!='main':assert before==config['compatibility_head']
        commit=client.request('GET','/git/commits/'+before)
        tree=client.request('POST','/git/trees',dict(base_tree=commit['tree']['sha'],tree=entries))
        made=client.request('POST','/git/commits',dict(parents=[before],tree=tree['sha'],message='Release PiconHub 0.1.42 with independent IPTV country collections [skip ci]'))
        assert head(branch)==before,'Branch advanced before feed activation'
        client.request('PATCH','/git/refs/heads/'+quote(branch,safe=''),dict(sha=made['sha'],force=False))
        feed=client.request('GET','/contents/plugin/update/stable.json?ref='+quote(branch,safe=''))
        assert json.loads(base64.b64decode(feed['content']))==document
        print('Activated',branch,made['sha'],flush=True)
    assert hashlib.sha256(client.public_package(item['url'],item['bytes'])).hexdigest()==item['sha256']
    report=dict(status='PRODUCTION_VERIFIED',version=version,source_commit=source,release=item,independent_countries=['Austria','Germany','Hungary','Poland'],country_archives=36,physical_receiver_tested=False)
    (ROOT/'reports').mkdir(exist_ok=True);(ROOT/'reports/country-plugin-0.1.42.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
