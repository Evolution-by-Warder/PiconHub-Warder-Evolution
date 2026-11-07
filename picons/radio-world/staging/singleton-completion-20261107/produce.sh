#!/usr/bin/env bash
set -euo pipefail
stage=picons/radio-world/staging/singleton-completion-20261107
python3 "$stage/reassemble_originals.py"
python3 "$stage/verify_evidence_parts.py"
python3 "$stage/reproduce_on_github.py" --plan "$stage/reproduce-plan.json" --output-root . --object-cache .
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add "$stage/originals" "$stage/verified-assets" "$stage/reproduction-proof.json"
git commit -m 'Save54 reviewed singleton radio PNGs without changing existing artwork [skip ci]'
git push origin HEAD:refs/heads/work/radio-singleton6-source-20261107
python3 "$stage/pin_selection.py"
git add "$stage/selection.json.gz" "$stage/source-proof.json"
git commit -m 'Pin6 reviewed radio singleton sources to immutable54PNG pixel commit [skip ci]'
git push origin HEAD:refs/heads/work/radio-singleton6-source-20261107
