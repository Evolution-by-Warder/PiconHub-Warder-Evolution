#!/usr/bin/env bash
set -eu
stage=picons/radio-world/staging/batch-43-primary-source
branch=work/radio-primary25-source-20261107
if test -f "$stage/source-proof.json"; then
  python3 -c 'import hashlib,json,sys; s=sys.argv[1]; p=json.load(open(s+"/source-proof.json")); b=open(s+"/producer-plan.json","rb").read(); assert p["status"]=="pass" and p["producer_plan_sha256"]==hashlib.sha256(b).hexdigest(); print("Existing exact source producer passed; regeneration skipped")' "$stage"
  exit 0
fi
python3 "$stage/reassemble_inputs.py" .
cp "$stage/producer-plan.json" "$RUNNER_TEMP/primary-plan.json"
python3 "$stage/reproduce_primary_on_github.py" --plan "$RUNNER_TEMP/primary-plan.json" --output-root . --source-cache "$stage/originals"
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add "$stage"
git commit -m 'Save exact25 primary broadcaster source artworks and225 reviewed PNGs [skip ci]'
git push origin HEAD:"refs/heads/$branch"
python3 "$stage/finalize_source.py"
git add "$stage/selection.json.gz" "$stage/source-proof.json" "$stage/WORKING.txt"
git commit -m 'Pin25 primary broadcaster artwork selection to immutable PNG commit [skip ci]'
git push origin HEAD:"refs/heads/$branch"
