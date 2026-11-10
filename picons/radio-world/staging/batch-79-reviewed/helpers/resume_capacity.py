import json,gzip,hashlib,subprocess
from pathlib import Path
S=Path('picons/radio-world/staging/batch-79-reviewed');rows=json.loads(gzip.decompress((S/'selection.json.gz').read_bytes()))['entries'];assert len(rows)==40
selected=rows[:34];pending=rows[34:];(S/'results').mkdir(exist_ok=True)
def write(p,x):
 b=(json.dumps(x,indent=2,ensure_ascii=False)+'\n').encode();p.write_bytes(gzip.compress(b,mtime=0)if p.suffix=='.gz'else b)
ledger=json.loads(gzip.decompress((S/'visual-ledger.json.gz').read_bytes()));assert len(ledger['entries'])==40
write(S/'results/approved-unpublished-capacity.json.gz',dict(reason='64MiB stable package limit; no multipart support. These6 approved rows retain original immutable source commits and all9 PNGs. Not counted in candidate index. Resume from saved bytes only.',entries=pending))
write(S/'selection.json.gz',dict(entries=selected));ledger['entries']=ledger['entries'][:34];write(S/'visual-ledger.json.gz',ledger)
cfg=json.loads((S/'configuration.json').read_bytes());cfg.update(references=34,expected_coverage=3462,selection_sha256=hashlib.sha256((S/'selection.json.gz').read_bytes()).hexdigest());write(S/'configuration.json',cfg)
write(S/'results/capacity-recovery.json',dict(status='resumed-saved-inputs',initial_references=40,selected_references=34,selected_PNG_instances=306,approved_unpublished_references=6,PNG_rerendered=0,previous_build_failed_before_payload_push=True,limit_bytes=67108864,reason='Initial40-reference DE400x240 white union exceeded64MiB; preserve existing fixed-name stable downloader contract.'))
subprocess.run(['git','config','user.name','github-actions[bot]'],check=True);subprocess.run(['git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com'],check=True);subprocess.run(['git','add',str(S)],check=True);subprocess.run(['git','commit','-m','Resume79 with34 saved references;retain6 capacity-deferred PNG sets [skip ci]'],check=True);subprocess.run(['git','push','origin','HEAD:refs/heads/work/radio-world-batch38-contrast-pass1-history-20261107'],check=True)

subprocess.run(['git','fetch','--depth=1','--no-tags','origin','6a4c08e8110a77a4424d9c7f8efec9a710855e3a'],check=True)
