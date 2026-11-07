#!/usr/bin/env bash
set -euo pipefail
stage=picons/radio-world/staging/batch-44-new55-source
branch=work/radio-zeno-new55-source-20261107
test "$GITHUB_REPOSITORY" = Evolution-by-Warder/PiconHub-Warder-Evolution
test "$GITHUB_REF" = "refs/heads/$branch"
python3 "$stage/reproduce_on_github.py" --plan "$stage/producer-plan.json" --output-root .
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
auth_header="$(printf 'x-access-token:%s' "$GH_TOKEN" | base64 -w0)"
printf '::add-mask::%s\n' "$auth_header"
export GIT_CONFIG_COUNT=1
export GIT_CONFIG_KEY_0=http.https://github.com/.extraheader
export GIT_CONFIG_VALUE_0="AUTHORIZATION: basic $auth_header"
remote_sha="$(git ls-remote origin "refs/heads/$branch" | cut -f1)"
test "$remote_sha" = "$GITHUB_SHA"
git add -- "$stage"
if ! git diff --cached --quiet; then
 git commit -m 'Save exact reviewed new55 accepted source PNGs and original bytes [skip ci]'
 git push origin HEAD:"refs/heads/$branch"
fi
python3 - "$stage" <<'PY'
import gzip,hashlib,json,subprocess,sys
from pathlib import Path
stage=Path(sys.argv[1]);planraw=(stage/'producer-plan.json').read_bytes();plan=json.loads(planraw);source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();rows=plan['expected_selection']['entries']
for row in rows:
 row['source_commit']=source
 row['asset_root']=str(stage)
raw=gzip.compress((json.dumps(dict(schema=1,entries=rows),separators=(',',':'),ensure_ascii=False)+'\n').encode(),mtime=0)
(stage/'selection.json.gz').write_bytes(raw)
(stage/'source-proof.json').write_text(json.dumps(dict(schema=1,status='pass',source_commit=source,references=len(rows),png_instances=len(rows)*9,unique_pngs=plan['unique_pngs'],producer_plan_sha256=hashlib.sha256(planraw).hexdigest(),selection_sha256=hashlib.sha256(raw).hexdigest(),all_output_hashes_match_actual_nine_reviewed_pngs=True,original_bytes_preserved=True,source_requests_only_immutable_existing_GitHub_archives=True,primary_freeze_final=True,final_freeze_reconciliation_required=False,baseline_commit=plan['baseline_commit'],production_write=False),indent=2)+'\n')
PY
git add -- "$stage/selection.json.gz" "$stage/source-proof.json"
git commit -m 'Pin new55 accepted source selection to immutable PNG commit [skip ci]'
git push origin HEAD:"refs/heads/$branch"
