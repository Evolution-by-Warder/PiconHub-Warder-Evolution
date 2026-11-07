#!/usr/bin/env bash
set -euo pipefail
stage=picons/radio-world/staging/batch-44-zeno54-recovery
branch=work/radio-zeno54-recovered-source-20261107
test "$GITHUB_REPOSITORY" = Evolution-by-Warder/PiconHub-Warder-Evolution
test "$GITHUB_REF" = "refs/heads/$branch"
python3 "$stage/assemble_inputs.py" "$stage"
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
auth_header="$(printf 'x-access-token:%s' "$GH_TOKEN" | base64 -w0)"
printf '::add-mask::%s\n' "$auth_header"
export GIT_CONFIG_COUNT=1
export GIT_CONFIG_KEY_0=http.https://github.com/.extraheader
export GIT_CONFIG_VALUE_0="AUTHORIZATION: basic $auth_header"
if test -f "$stage/source-proof.json"; then
  python3 - "$stage" <<'PY'
import json,sys,hashlib
from pathlib import Path
p=Path(sys.argv[1]);s=json.loads((p/'source-proof.json').read_bytes());assert s['status']=='pass'and s['references']==51 and s['preserved_png_instances']==486
for n,k in [('selection.json.gz','selection_sha256'),('visual-ledger.json.gz','ledger_sha256'),('recovery54-proof.json','recovery_proof_sha256')]:assert hashlib.sha256((p/n).read_bytes()).hexdigest()==s[k]
print('Already complete source checkpoint, no reproduction')
PY
  exit 0
fi
python3 "$stage/reproduce_recovery54.py" --plan "$stage/producer-plan.json" --output-root .
git add -- "$stage"
if ! git diff --cached --quiet; then git commit -m 'Preserve physical486 recovered PNGs:459 eligible,27 quarantine and54 originals [skip ci]'; fi
git push origin HEAD:"refs/heads/$branch"
pixel="$(git rev-parse HEAD)"
python3 "$stage/finalize_recovery54.py" proof "$stage" "$pixel"
git add -- "$stage/recovery54-proof.json"
git commit -m 'Pin actual recovery54 pixel proofs and fresh51approve3hold nine-variant QA [skip ci]'
git push origin HEAD:"refs/heads/$branch"
proofcommit="$(git rev-parse HEAD)"
python3 "$stage/finalize_recovery54.py" ledger "$stage" "$proofcommit"
git add -- "$stage/selection.json.gz" "$stage/visual-ledger.json.gz" "$stage/source-proof.json"
git commit -m 'Export51 exact recovered references with explicit physical-proof hold resolution [skip ci]'
git push origin HEAD:"refs/heads/$branch"
