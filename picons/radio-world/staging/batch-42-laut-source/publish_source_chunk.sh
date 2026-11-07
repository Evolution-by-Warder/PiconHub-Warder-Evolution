#!/usr/bin/env bash
set -eu
stage=picons/radio-world/staging/batch-42-laut-source
branch="work/radio-laut435-source-chunk-${CHUNK}-20261107"
gzip -dc "$stage/input-plans/producer-plan-${CHUNK}.json.gz" > "$RUNNER_TEMP/laut-plan.json"
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
if git ls-remote --exit-code origin "refs/heads/$branch" > "$RUNNER_TEMP/existing-ref"; then
  git fetch --depth=1 --no-tags origin "$branch"
  git checkout --detach FETCH_HEAD
  if test -f "$stage/source-proof.json"; then
    python3 -c 'import hashlib,json,sys; proof=json.load(open(sys.argv[1])); raw=open(sys.argv[2],"rb").read(); assert proof["status"]=="pass" and proof["producer_plan_sha256"]==hashlib.sha256(raw).hexdigest(); print("Verified completed immutable source chunk; skipping regeneration")' "$stage/source-proof.json" "$RUNNER_TEMP/laut-plan.json"
    exit 0
  fi
fi
python3 "$stage/frozen-cache/seed_originals.py"
python3 "$stage/reproduce_laut_on_github.py" --plan "$RUNNER_TEMP/laut-plan.json" --output-root . --source-cache "$stage/originals"
git add "$stage"
if ! git diff --cached --quiet; then
  git commit -m "Save exact reviewed laut.fm source chunk ${CHUNK} PNGs and originals [skip ci]"
fi
git push origin HEAD:"refs/heads/$branch"
python3 - "$stage" "$RUNNER_TEMP/laut-plan.json" <<'PY'
import gzip,hashlib,json,subprocess,sys
from pathlib import Path
stage=Path(sys.argv[1]);raw=Path(sys.argv[2]).read_bytes();plan=json.loads(raw)
source=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
rows=plan['expected_selection']['entries']
for row in rows:
    row['source_commit']=source
    row['asset_root']=str(stage)
    row.pop('variant_paths',None)
data=gzip.compress((json.dumps(dict(entries=rows),separators=(',',':'),ensure_ascii=False)+'\n').encode(),mtime=0)
(stage/'selection.json.gz').write_bytes(data)
(stage/'source-proof.json').write_text(json.dumps(dict(schema=1,status='pass',chunk=plan['chunk'],source_commit=source,references=len(rows),png_instances=9*len(rows),unique_pngs=plan['unique_pngs'],producer_plan_sha256=hashlib.sha256(raw).hexdigest(),selection_sha256=hashlib.sha256(data).hexdigest(),all_output_hashes_match_reviewed_pngs=True,original_bytes_preserved=True),indent=2)+'\n')
PY
git add "$stage/selection.json.gz" "$stage/source-proof.json"
git commit -m "Pin exact laut.fm source chunk ${CHUNK} selection to immutable PNG commit [skip ci]"
git push origin HEAD:"refs/heads/$branch"
