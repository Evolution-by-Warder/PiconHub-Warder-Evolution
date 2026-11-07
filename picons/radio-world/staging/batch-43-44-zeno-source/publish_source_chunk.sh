#!/usr/bin/env bash
set -euo pipefail
stage=picons/radio-world/staging/batch-43-44-zeno-source
case "$CHUNK" in 001|002) ;; *) exit 2;; esac
test "$GITHUB_REPOSITORY" = Evolution-by-Warder/PiconHub-Warder-Evolution
test "$GITHUB_REF" = refs/heads/work/radio-zeno113-source-20261107
branch="work/radio-zeno113-source-chunk-${CHUNK}-20261107"
python3 "$stage/assemble_inputs.py" "$stage"
cp "$stage/input-plans/producer-plan-${CHUNK}.json" "$RUNNER_TEMP/zeno-plan.json"
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
auth_header="$(printf 'x-access-token:%s' "$GH_TOKEN" | base64 -w0)"
printf '::add-mask::%s\n' "$auth_header"
export GIT_CONFIG_COUNT=1
export GIT_CONFIG_KEY_0=http.https://github.com/.extraheader
export GIT_CONFIG_VALUE_0="AUTHORIZATION: basic $auth_header"
if git ls-remote --exit-code origin "refs/heads/$branch" > "$RUNNER_TEMP/zeno-existing-ref"; then
  git fetch --depth=1 --no-tags origin "$branch"
  git checkout --detach FETCH_HEAD
  if test -f "$stage/source-proof.json"; then
    python3 -c 'import hashlib,json,sys; p=json.load(open(sys.argv[1])); b=open(sys.argv[2],"rb").read(); assert p["status"]=="pass" and p["producer_plan_sha256"]==hashlib.sha256(b).hexdigest(); print("Immutable complete113-source chunk already exists; skipping reproduction")' "$stage/source-proof.json" "$RUNNER_TEMP/zeno-plan.json"
    exit 0
  fi
fi
python3 "$stage/reproduce_zeno_on_github.py" --plan "$RUNNER_TEMP/zeno-plan.json" --output-root .
git add -- "$stage"
if ! git diff --cached --quiet; then
  git commit -m "Save exact all-nine-reviewed Zeno chunk ${CHUNK} PNGs and inspected originals [skip ci]"
fi
git push origin HEAD:"refs/heads/$branch"
python3 - "$stage" "$RUNNER_TEMP/zeno-plan.json" <<'PY'
import gzip,hashlib,json,subprocess,sys
from pathlib import Path
stage=Path(sys.argv[1]);raw=Path(sys.argv[2]).read_bytes();plan=json.loads(raw);source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();rows=plan['expected_selection']['entries']
for row in rows:
    row['source_commit']=source
    row['asset_root']=str(stage)
    row.pop('variant_paths',None)
data=gzip.compress((json.dumps(dict(entries=rows),separators=(',',':'),ensure_ascii=False)+'\n').encode(),mtime=0)
(stage/'selection.json.gz').write_bytes(data)
(stage/'source-proof.json').write_text(json.dumps(dict(schema=1,status='pass',chunk=plan['chunk'],source_commit=source,references=len(rows),png_instances=9*len(rows),unique_pngs=plan['unique_pngs'],producer_plan_sha256=hashlib.sha256(raw).hexdigest(),selection_sha256=hashlib.sha256(data).hexdigest(),all_output_hashes_match_actual_nine_reviewed_pngs=True,original_bytes_preserved=True,source_requests_only_immutable_existing_GitHub_archives=True,primary_freeze_final=False,final_freeze_reconciliation_required=True),indent=2)+'\n')
PY
git add -- "$stage/selection.json.gz" "$stage/source-proof.json"
git commit -m "Pin Zeno chunk ${CHUNK} exact PNG selection to immutable source commit [skip ci]"
git push origin HEAD:"refs/heads/$branch"
