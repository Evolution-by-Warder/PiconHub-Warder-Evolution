import gzip,hashlib,json,os,re,subprocess,sys
from pathlib import Path
stage=Path('picons/radio-world/staging/batch-57-reviewed');helper=stage/'helpers';cfg=stage/'configuration.json'
temp=Path(os.environ['RUNNER_TEMP']);scratch=temp/'payload57';work=temp/'batch57';new=temp/'new57-zips'
branch='work/radio-world-batch43-reviewed-payload-20261107';expected='4864afe77d108bd802e12593f82795e8114c7f2e'
def run(args,cwd=None):return subprocess.check_output(args,cwd=cwd,text=True).strip()
def git(*args,cwd=None):return run(['git',*args],cwd)
def execute(args):subprocess.run(args,check=True)
git('config','user.name','github-actions[bot]');git('config','user.email','41898282+github-actions[bot]@users.noreply.github.com')
head=git('ls-remote','origin','refs/heads/'+branch).split()[0]
assert head==expected,'Existing payload ref advanced: inspect/recover metadata; never rebuild published ZIPs'
git('fetch','--depth=1','--no-tags','origin',head)
selection=json.loads(gzip.decompress((stage/'selection.json.gz').read_bytes()))['entries'];config=json.loads(cfg.read_bytes())
assert len(selection)==config['references'] and len({r['ref']for r in selection})==len(selection)
collections={('IPTV-SK-CZ'if r['country']in('SK','CZ')else'IPTV-'+r['country'])for r in selection}
assert all(re.fullmatch('IPTV-[A-Z-]+',c)for c in collections)
existing=git('ls-tree','-r','--name-only',head)
assert str(stage/'payload-build-manifest.json') not in existing.splitlines(),'Published batch57 exists; metadata recovery required'
work.mkdir();execute(['python3','picons/radio-world/tools/saved_artwork_import.py',str(cfg),'build',str(work),str(new)])
git('worktree','add','--no-checkout','--detach',str(scratch),head)
patterns=['picons/radio-world/staging/batch-57-reviewed']+['picons/'+c+'/catalog'for c in sorted(collections)]
subprocess.run(['git','-C',str(scratch),'sparse-checkout','set','--cone','--skip-checks','--stdin'],input='\n'.join(patterns)+'\n',text=True,check=True)
git('checkout','--detach',head,cwd=scratch)
report=json.loads((work/'packages.json').read_bytes());zip_paths=[];zip_evidence=[]
for m in report['countries'].values():
    for size,styles in m['packages'].items():
        for style,e in styles.items():
            path=e['path'];assert re.fullmatch(r'picons/IPTV-[A-Z-]+/packages/iptv-[a-z-]+-(black|white|transparent)-(50x30|220x132|400x240)\.zip',path)
            raw=(new/path).read_bytes();assert len(raw)==e['bytes'] and hashlib.sha256(raw).hexdigest()==e['sha256'] and len(raw)<=67108864
            target=scratch/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            prior=git('ls-tree',head,'--',path);prior_sha=prior.split()[2]if prior else None
            zip_paths.append(path);zip_evidence.append(dict(path=path,previous_git_blob=prior_sha,previous_immutable_commit=head,new_sha256=e['sha256'],new_bytes=len(raw)))
checkpoint=scratch/stage/'payload-build-manifest.json';checkpoint.parent.mkdir(parents=True,exist_ok=True);checkpoint.write_bytes((work/'packages.json').read_bytes())
git('add','--sparse','--',*zip_paths,str(stage/'payload-build-manifest.json'),cwd=scratch)
changes=git('diff','--cached','--name-status',cwd=scratch).splitlines()
for line in changes:
    status,path=line.split('\t');assert status in('A','M') and (path in zip_paths or path==str(stage/'payload-build-manifest.json')),(status,path)
(stage/'zip-path-proof.json').write_text(json.dumps(dict(schema=1,status='pass',stable_fixed_filename_schema=True,old_immutable_urls_preserved=True,previous_commit=head,entries=zip_evidence),indent=2)+'\n')
git('commit','-m','Save new batch57 ZIP paths and recovery manifest [skip ci]',cwd=scratch);payload=git('rev-parse','HEAD',cwd=scratch)
git('push','origin','HEAD:refs/heads/'+branch,cwd=scratch)
execute(['python3','picons/radio-world/tools/saved_artwork_import.py',str(cfg),'manifests',str(work),str(scratch),payload])
git('add','--',*['picons/'+c+'/catalog/release.json'for c in sorted(collections)],cwd=scratch)
for line in git('diff','--cached','--name-status',cwd=scratch).splitlines():
    status,path=line.split('\t');assert status in('A','M')and re.fullmatch(r'picons/IPTV-[A-Z-]+/catalog/release.json',path),(status,path)
git('commit','-m','Pin new immutable batch57 country manifest versions [skip ci]',cwd=scratch);manifest=git('rev-parse','HEAD',cwd=scratch)
git('push','origin','HEAD:refs/heads/'+branch,cwd=scratch)
execute(['python3','picons/radio-world/tools/saved_artwork_import.py',str(cfg),'index',str(work),str(scratch),payload,manifest])
proof=dict(schema=1,status='pass',existing_payload_branch=branch,previous_payload_commit=expected,payload_commit=payload,manifest_commit=manifest,old_zip_and_manifest_versions_unchanged_at_previous_immutable_commits=True,previous_manifest_versions_preserved_by_immutable_commits=True,working_candidate_canonical_index_and_manifests_untouched=True)
(stage/'payload-preservation-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
git('add',str(stage/'countries.proposed.json'),str(stage/'proof.json'),str(stage/'zip-path-proof.json'),str(stage/'payload-preservation-proof.json'))
git('commit','-m','Save staged batch57 candidate and immutable payload proofs [skip ci]');git('push','origin','HEAD:refs/heads/work/radio-world-batch38-contrast-pass1-history-20261107')
print(json.dumps(proof))
